"""M3ndel Extraction API — POST /extraction/extract endpoint.

Two pipelines available:
  - /extract        — Legacy monolithic pipeline (ExtractorService + Instructor)
  - /extract-agent  — New multi-agent pipeline (Classify → Extract → Audit → Result)
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.modules.extraction.extractor import ExtractorService
from app.modules.extraction.agents.orchestrator import OrchestratorAgent
from app.modules.extraction.cost_tracker import CostTracker
from app.modules.extraction.pdf_service import parse_pdf
from app.modules.extraction.schemas import ExtractionResponse, ExtractionResult

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
