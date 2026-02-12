"""M3ndel Extraction API — /extraction/ endpoints.

Pipelines:
  - /extract        — Legacy monolithic pipeline (ExtractorService + Instructor)
  - /extract-agent  — New multi-agent pipeline, single PDF
  - /extract-batch  — Multi-agent pipeline, multiple PDFs at once

History (read-only):
  - /runs           — Paginated list of past extraction runs
  - /runs/{id}      — Single run with golden records
  - /golden-records — Paginated golden records (optional run_id filter)
"""

from __future__ import annotations

import math
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.extraction.models import ExtractionRun, GoldenRecord
from app.modules.extraction.extractor import ExtractorService
from app.modules.extraction.agents.orchestrator import OrchestratorAgent
from app.modules.extraction.cost_tracker import CostTracker
from app.modules.extraction.history_schemas import (
    DiffEntry,
    ExtractionRunDetail,
    ExtractionRunSummary,
    GoldenRecordDetail,
    GoldenRecordSummary,
    PaginatedGoldenRecords,
    PaginatedRuns,
    SectionDiff,
    VersionDiffResponse,
)
from app.modules.extraction.history_service import (
    compute_diff,
    get_golden_record_by_id,
    get_run_detail,
    list_golden_records,
    list_product_versions,
    list_runs,
)
from app.modules.extraction.pdf_service import parse_pdf
from app.modules.extraction.versioning import assign_version, resolve_region
from app.modules.extraction.schemas import (
    BatchExtractionResponse,
    BatchExtractionResultSchema,
    ConfirmExtractionRequest,
    ConfirmExtractionResponse,
    ExtractionResponse,
    ExtractionResult,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/extraction", tags=["extraction"])


@router.post("/extract", response_model=ExtractionResponse)
async def extract_pdf(
    file: UploadFile = File(..., description="PDF document (TDS, SDS, RPI, CoA, or Brochure)"),
    document_type_hint: str = Form("auto", description="Document type hint: TDS|SDS|RPI|CoA|Brochure|auto"),
) -> ExtractionResponse:
    """Upload a PDF and extract structured chemical product data.

    Pipeline: PDF → PyMuPDF parse → Markdown → LLM (Instructor) → ExtractionResult

    Cascade mode (default ON): tries cheap provider first (e.g. Gemini Flash),
    auto-falls back to quality provider (e.g. Claude Sonnet) when >N attributes missing.
    """
    start = time.monotonic()

    # --- Validate file ---
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    size_mb = len(pdf_bytes) / (1024 * 1024)

    if size_mb > settings.extraction_max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f} MB (max {settings.extraction_max_file_size_mb} MB).",
        )

    logger.info("Extraction request", filename=file.filename, size_mb=round(size_mb, 2))

    try:
        # --- Step 1: Parse PDF to Markdown ---
        parsed = parse_pdf(pdf_bytes)

        # --- Step 2: Determine document type ---
        doc_type = parsed.doc_type
        if document_type_hint != "auto":
            doc_type = document_type_hint  # type: ignore[assignment]
            logger.info("Document type overridden by hint", hint=document_type_hint)

        # --- Step 3: Extract via LLM ---
        extractor = ExtractorService()
        result = extractor.extract(markdown=parsed.full_markdown, doc_type=doc_type)

        # Enrich document_info with parse metadata
        result.document_info.page_count = parsed.page_count
        if parsed.metadata.get("brand"):
            result.document_info.brand = parsed.metadata["brand"]

        elapsed_ms = int((time.monotonic() - start) * 1000)

        return ExtractionResponse(
            success=True,
            result=result,
            processing_time_ms=elapsed_ms,
            provider=extractor.provider,
            model=extractor.model,
            cascade=extractor.cascade_info,
            markdown_preview=parsed.full_markdown[:2000],
        )

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.error("Extraction failed", error=str(exc), exc_info=True)
        return ExtractionResponse(
            success=False,
            error=str(exc),
            processing_time_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# NEW: Multi-Agent Pipeline endpoint
# ---------------------------------------------------------------------------


@router.post("/extract-agent", response_model=ExtractionResponse)
async def extract_pdf_agent(
    file: UploadFile = File(..., description="PDF document (TDS, SDS, RPI, CoA, or Brochure)"),
) -> ExtractionResponse:
    """Upload a PDF and extract structured data via the multi-agent pipeline.

    Pipeline: PDF → Classify (Agent 1) → Extract (Agent 2) → Audit (Agent 3) → ExtractionResult

    The agent pipeline uses doc-type-specific prompts (500-800 tokens) instead of
    the monolithic 2500-token prompt, resulting in better accuracy at lower cost.
    """
    start = time.monotonic()

    # --- Validate file ---
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    size_mb = len(pdf_bytes) / (1024 * 1024)

    if size_mb > settings.extraction_max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f} MB (max {settings.extraction_max_file_size_mb} MB).",
        )

    logger.info(
        "Agent extraction request",
        filename=file.filename,
        size_mb=round(size_mb, 2),
    )

    try:
        # Write PDF to temp file (Orchestrator expects a file path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        # Run agent pipeline
        cost_tracker = CostTracker()
        orchestrator = OrchestratorAgent(cost_tracker=cost_tracker)
        partial = orchestrator.process_single_pdf(tmp_path)

        # Clean up temp file
        tmp_path.unlink(missing_ok=True)

        # Convert PartialExtraction dict -> ExtractionResult
        if partial.extraction_result:
            result = ExtractionResult.model_validate(partial.extraction_result)
        else:
            raise ValueError(
                f"Agent extraction returned no result. "
                f"Warnings: {partial.warnings}"
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        cost_summary = cost_tracker.summary()

        # Determine provider from cost tracker
        providers = cost_summary.get("providers", {})
        provider_name = next(iter(providers), "google") if providers else "google"

        return ExtractionResponse(
            success=True,
            result=result,
            processing_time_ms=elapsed_ms,
            provider=provider_name,
            model="agent-pipeline",
            markdown_preview=None,  # Not included to keep response lean
        )

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.error("Agent extraction failed", error=str(exc), exc_info=True)
        # Clean up temp file on error
        if "tmp_path" in locals():
            tmp_path.unlink(missing_ok=True)
        return ExtractionResponse(
            success=False,
            error=str(exc),
            processing_time_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# NEW: Batch Multi-Agent Pipeline endpoint
# ---------------------------------------------------------------------------

MAX_BATCH_FILES = 20


@router.post("/extract-batch", response_model=BatchExtractionResponse)
async def extract_pdf_batch(
    files: list[UploadFile] = File(..., description="Multiple PDF documents"),
) -> BatchExtractionResponse:
    """Upload multiple PDFs and extract structured data via the multi-agent pipeline.

    Processes each PDF sequentially through: Classify → Extract → Audit → Result.
    Returns individual results per file.
    """
    start = time.monotonic()

    # --- Validate ---
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: {len(files)} (max {MAX_BATCH_FILES}).",
        )
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    logger.info("Batch extraction request", file_count=len(files))

    # Write all PDFs to temp dir, track original filenames
    tmp_dir = Path(tempfile.mkdtemp(prefix="mendel_batch_"))
    file_map: list[tuple[str, Path]] = []  # (original_name, tmp_path)

    try:
        for upload in files:
            if not upload.filename or not upload.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Only PDF files accepted. Got: {upload.filename}",
                )
            pdf_bytes = await upload.read()
            size_mb = len(pdf_bytes) / (1024 * 1024)
            if size_mb > settings.extraction_max_file_size_mb:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large: {upload.filename} ({size_mb:.1f} MB, max {settings.extraction_max_file_size_mb} MB).",
                )
            # Use index prefix to avoid name collisions
            safe_name = f"{len(file_map):03d}_{upload.filename}"
            tmp_path = tmp_dir / safe_name
            tmp_path.write_bytes(pdf_bytes)
            file_map.append((upload.filename, tmp_path))

        # Process batch via orchestrator
        cost_tracker = CostTracker()
        orchestrator = OrchestratorAgent(cost_tracker=cost_tracker)
        partials = orchestrator.process_batch([p for _, p in file_map])

        results: list[BatchExtractionResultSchema] = []
        successful = 0
        failed = 0

        for idx, partial in enumerate(partials):
            original_name = file_map[idx][0]
            if partial.extraction_result:
                result_obj = ExtractionResult.model_validate(partial.extraction_result)
                results.append(BatchExtractionResultSchema(
                    filename=original_name,
                    success=True,
                    result=result_obj,
                ))
                successful += 1
            else:
                results.append(BatchExtractionResultSchema(
                    filename=original_name,
                    success=False,
                    error="; ".join(partial.warnings) or "No result",
                ))
                failed += 1

        total_ms = int((time.monotonic() - start) * 1000)
        cost_summary = cost_tracker.summary()
        providers = cost_summary.get("providers", {})
        provider_name = next(iter(providers), "google") if providers else "google"

        return BatchExtractionResponse(
            success=successful > 0,
            results=results,
            total_processing_time_ms=total_ms,
            provider=provider_name,
            successful_count=successful,
            failed_count=failed,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Confirm & persist extraction results to the database
# ---------------------------------------------------------------------------


@router.post("/confirm", response_model=ConfirmExtractionResponse)
async def confirm_extraction(
    request: ConfirmExtractionRequest,
    db: AsyncSession = Depends(get_db),
) -> ConfirmExtractionResponse:
    """Persist batch extraction results to the database.

    Creates an ExtractionRun and one GoldenRecord per unique product.
    Deduplicates by product_name within the batch (UNIQUE constraint).
    The DB session auto-commits via the get_db() dependency.
    """
    successful = [r for r in request.results if r.success and r.result]

    if not successful:
        raise HTTPException(
            status_code=400,
            detail="No successful extraction results to confirm.",
        )

    # Create the ExtractionRun entry
    run = ExtractionRun(
        finished_at=datetime.now(timezone.utc),
        pdf_count=len(request.results),
        golden_records_count=len(successful),
        status="completed",
    )
    db.add(run)
    await db.flush()  # Generates run.id

    # Create GoldenRecord per unique (product_name, region) combination.
    # The composite key allows the same product to exist multiple times
    # when it has region-specific SDS variants (EU vs US vs JP).
    seen_keys: set[tuple[str, str]] = set()  # (product_name, region)
    for item in successful:
        assert item.result is not None  # guarded by filter above
        name = item.result.identity.product_name
        region = resolve_region(item.result)
        key = (name, region)

        if key in seen_keys:
            logger.warning(
                "Duplicate product+region in batch, skipping",
                product_name=name,
                region=region,
                filename=item.filename,
            )
            continue
        seen_keys.add(key)

        # Auto-increment version and obsolete previous records
        version, obsoleted = await assign_version(db, name, region)

        missing = len(item.result.missing_attributes)
        golden = GoldenRecord(
            run_id=run.id,
            product_name=name,
            brand=item.result.document_info.brand,
            region=region,
            doc_language=item.result.document_info.language,
            revision_date=item.result.document_info.revision_date,
            document_type=item.result.document_info.document_type,
            version=version,
            is_latest=True,
            golden_record=item.result.model_dump(),
            source_files=[item.filename],
            source_count=1,
            missing_count=missing,
            completeness=round(((33 - missing) / 33) * 100, 1),
        )
        db.add(golden)

    logger.info(
        "Extraction confirmed",
        run_id=run.id,
        golden_records_created=len(seen_keys),
    )

    # get_db() auto-commits after this return
    return ConfirmExtractionResponse(
        run_id=run.id,
        golden_records_created=len(seen_keys),
    )


# ---------------------------------------------------------------------------
# History — read-only endpoints for extraction runs & golden records
# ---------------------------------------------------------------------------


@router.get("/runs", response_model=PaginatedRuns)
async def get_extraction_runs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRuns:
    """Return a paginated list of extraction runs, newest first."""
    items, total = await list_runs(db, page=page, page_size=page_size)
    return PaginatedRuns(
        items=[
            ExtractionRunSummary.model_validate(r, from_attributes=True)
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/runs/{run_id}", response_model=ExtractionRunDetail)
async def get_extraction_run_detail(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> ExtractionRunDetail:
    """Return a single extraction run with its golden records."""
    run = await get_run_detail(db, run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Extraction run {run_id} not found.")

    records, _ = await list_golden_records(db, run_id=run_id, page=1, page_size=500)

    run_summary = ExtractionRunSummary.model_validate(run, from_attributes=True)
    return ExtractionRunDetail(
        **run_summary.model_dump(),
        golden_records=[
            GoldenRecordSummary.model_validate(r, from_attributes=True)
            for r in records
        ],
    )


@router.get("/golden-records", response_model=PaginatedGoldenRecords)
async def get_golden_records(
    run_id: int | None = Query(None, description="Filter by extraction run ID"),
    latest_only: bool = Query(
        False, description="Only return the latest version per product+region"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedGoldenRecords:
    """Return paginated golden records, optionally filtered by run_id."""
    items, total = await list_golden_records(
        db, run_id=run_id, latest_only=latest_only, page=page, page_size=page_size
    )
    return PaginatedGoldenRecords(
        items=[
            GoldenRecordSummary.model_validate(r, from_attributes=True)
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


def _fact_value(fact: object) -> str:
    """Extract display value from a MendelFact or primitive."""
    if fact is None:
        return ""
    if isinstance(fact, dict) and "value" in fact:
        v = str(fact.get("value", ""))
        u = fact.get("unit", "")
        return f"{v} {u}".strip() if u else v
    return str(fact)


def _flatten_golden_record(record: GoldenRecord) -> dict:
    """Flatten a GoldenRecord into a flat dict for CSV/Excel export."""
    gr = record.golden_record or {}
    return {
        "id": record.id,
        "product_name": record.product_name,
        "brand": record.brand or "",
        "region": record.region,
        "version": record.version,
        "is_latest": record.is_latest,
        "document_type": gr.get("document_info", {}).get("document_type", ""),
        "language": gr.get("document_info", {}).get("language", ""),
        "manufacturer": gr.get("document_info", {}).get("manufacturer", ""),
        "revision_date": gr.get("document_info", {}).get("revision_date", ""),
        "product_line": gr.get("identity", {}).get("product_line", ""),
        "wacker_sku": gr.get("identity", {}).get("wacker_sku", ""),
        "cas_numbers": _fact_value(gr.get("chemical", {}).get("cas_numbers")),
        "chemical_components": "; ".join(gr.get("chemical", {}).get("chemical_components", [])),
        "purity": _fact_value(gr.get("chemical", {}).get("purity")),
        "physical_form": _fact_value(gr.get("physical", {}).get("physical_form")),
        "density": _fact_value(gr.get("physical", {}).get("density")),
        "flash_point": _fact_value(gr.get("physical", {}).get("flash_point")),
        "temperature_range": _fact_value(gr.get("physical", {}).get("temperature_range")),
        "shelf_life": _fact_value(gr.get("physical", {}).get("shelf_life")),
        "cure_system": _fact_value(gr.get("physical", {}).get("cure_system")),
        "main_application": gr.get("application", {}).get("main_application", ""),
        "packaging_options": "; ".join(gr.get("application", {}).get("packaging_options", [])),
        "ghs_statements": "; ".join(gr.get("safety", {}).get("ghs_statements", [])),
        "un_number": _fact_value(gr.get("safety", {}).get("un_number")),
        "certifications": "; ".join(gr.get("safety", {}).get("certifications", [])),
        "global_inventories": "; ".join(gr.get("safety", {}).get("global_inventories", [])),
        "wiaw_status": gr.get("compliance", {}).get("wiaw_status", ""),
        "completeness": record.completeness or 0,
        "missing_count": record.missing_count or 0,
        "source_files": "; ".join(record.source_files or []),
        "created_at": str(record.created_at),
    }


@router.get("/golden-records/export")
async def export_golden_records(
    format: str = Query("csv", description="Export format: csv or xlsx"),
    run_id: int | None = Query(None, description="Filter by extraction run"),
    latest_only: bool = Query(True, description="Only export latest versions"),
    db: AsyncSession = Depends(get_db),
):
    """Export golden records as CSV or Excel file."""
    import io
    import pandas as pd
    from fastapi.responses import StreamingResponse

    if format not in ("csv", "xlsx"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid format '{format}'. Must be 'csv' or 'xlsx'.",
        )

    records, _ = await list_golden_records(
        db, run_id=run_id, latest_only=latest_only, page=1, page_size=10_000
    )
    if not records:
        raise HTTPException(status_code=404, detail="No records found for export.")

    rows = [_flatten_golden_record(r) for r in records]
    df = pd.DataFrame(rows)

    buffer = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=golden_records.xlsx"},
        )
    else:
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=golden_records.csv"},
        )


@router.get("/golden-records/{record_id}", response_model=GoldenRecordDetail)
async def get_golden_record_detail(
    record_id: int,
    db: AsyncSession = Depends(get_db),
) -> GoldenRecordDetail:
    """Return a single golden record with full JSONB extraction data."""
    record = await get_golden_record_by_id(db, record_id=record_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Golden record {record_id} not found."
        )
    return GoldenRecordDetail.model_validate(record, from_attributes=True)


@router.get(
    "/golden-records/{id1}/diff/{id2}",
    response_model=VersionDiffResponse,
)
async def get_version_diff(
    id1: int,
    id2: int,
    db: AsyncSession = Depends(get_db),
) -> VersionDiffResponse:
    """Compare two golden record versions and return structured diff."""
    record_a = await get_golden_record_by_id(db, record_id=id1)
    record_b = await get_golden_record_by_id(db, record_id=id2)
    if record_a is None:
        raise HTTPException(status_code=404, detail=f"Record {id1} not found.")
    if record_b is None:
        raise HTTPException(status_code=404, detail=f"Record {id2} not found.")

    sections, total = compute_diff(record_a.golden_record, record_b.golden_record)

    added = sum(1 for s in sections for c in s["changes"] if c["change_type"] == "added")
    removed = sum(1 for s in sections for c in s["changes"] if c["change_type"] == "removed")
    changed = sum(1 for s in sections for c in s["changes"] if c["change_type"] == "changed")
    summary = f"{changed} changed, {added} added, {removed} removed"

    return VersionDiffResponse(
        record_a=GoldenRecordSummary.model_validate(record_a, from_attributes=True),
        record_b=GoldenRecordSummary.model_validate(record_b, from_attributes=True),
        sections=[SectionDiff(**s) for s in sections],
        total_changes=total,
        summary=summary,
    )


@router.get(
    "/golden-records/{record_id}/versions",
    response_model=list[GoldenRecordSummary],
)
async def get_record_versions(
    record_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[GoldenRecordSummary]:
    """Return all versions of the same product+region, newest first.

    Looks up the record by ID, then queries all records sharing the same
    product_name and region. Useful for the version-history flyout in the UI.
    """
    record = await db.get(GoldenRecord, record_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Golden record {record_id} not found."
        )

    versions = await list_product_versions(
        db, product_name=record.product_name, region=record.region
    )
    return [
        GoldenRecordSummary.model_validate(v, from_attributes=True)
        for v in versions
    ]
