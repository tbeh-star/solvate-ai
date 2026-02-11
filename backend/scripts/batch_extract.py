#!/usr/bin/env python3
"""M3ndel Batch Extraction Runner — Process multiple PDFs with cost tracking.

Discovers PDFs in the input folder, extracts structured data via Gemini Flash
(with optional Sonnet cascade fallback), tracks all costs, and exports results
to JSON + CSV.

Usage:
    # Process all PDFs in default input folder
    python -m scripts.batch_extract

    # Process specific brand folder
    python -m scripts.batch_extract --input-dir /path/to/pdfs

    # Limit to N PDFs (for testing)
    python -m scripts.batch_extract --limit 5

    # Only TDS documents
    python -m scripts.batch_extract --doc-type TDS

    # Disable cascade (Gemini only, cheapest)
    python -m scripts.batch_extract --no-cascade

    # Specific brand
    python -m scripts.batch_extract --brand ELASTOSIL

    # Dry run (just list PDFs, no extraction)
    python -m scripts.batch_extract --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Add backend to path for imports
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

# Load .env before importing app modules
from dotenv import load_dotenv
load_dotenv(_backend / ".env")

import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

from app.modules.extraction.batch_extractor import (
    BatchExtractorService,
    ExtractionWithTokens,
)
from app.modules.extraction.cost_tracker import CostTracker
from app.modules.extraction.pdf_service import parse_pdf

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

# _backend = 03_SRC/backend, project_root = Desktop/Claude
_project_root = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_INPUT_DIR = _project_root / "02_Input" / "Wacker"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "batch_results"

# ---------------------------------------------------------------------------
# PDF Discovery
# ---------------------------------------------------------------------------


@dataclass
class PDFFile:
    """Discovered PDF file with metadata derived from path."""

    path: Path
    file_name: str
    brand: str  # Derived from parent folder (e.g. "ELASTOSIL®" → "ELASTOSIL")
    product_folder: str  # Product subfolder name
    size_bytes: int
    size_mb: float


def discover_pdfs(
    input_dir: Path,
    *,
    brand_filter: str | None = None,
    doc_type_filter: str | None = None,
    max_size_mb: float = 20.0,
) -> list[PDFFile]:
    """Discover all PDFs in the input directory tree.

    Directory structure expected:
        input_dir/
        ├── BRAND®/
        │   ├── Product Name/
        │   │   ├── PRODUCT-TDS-en.pdf
        │   │   ├── PRODUCT-SDS-en.pdf
        │   │   └── PRODUCT-RPI-en.pdf
        │   └── ...
        └── ...
    """
    pdfs: list[PDFFile] = []

    if not input_dir.exists():
        logger.error("Input directory not found", path=str(input_dir))
        return pdfs

    for pdf_path in sorted(input_dir.rglob("*.pdf")):
        # Skip hidden files and temp files
        if pdf_path.name.startswith(".") or pdf_path.name.startswith("~"):
            continue

        # Derive brand from path
        # e.g. /Wacker/ELASTOSIL®/Product/file.pdf → "ELASTOSIL"
        relative = pdf_path.relative_to(input_dir)
        parts = relative.parts

        brand = parts[0].replace("®", "").strip() if len(parts) > 0 else "unknown"
        product_folder = parts[1] if len(parts) > 2 else parts[0] if len(parts) > 1 else ""

        # Apply brand filter
        if brand_filter and brand_filter.upper() not in brand.upper():
            continue

        # Apply doc type filter (heuristic from filename)
        if doc_type_filter:
            fn_upper = pdf_path.name.upper()
            if f"-{doc_type_filter.upper()}" not in fn_upper and f"_{doc_type_filter.upper()}" not in fn_upper:
                continue

        size_bytes = pdf_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        # Skip files that are too large
        if size_mb > max_size_mb:
            logger.warning("Skipping oversized PDF", file=pdf_path.name, size_mb=f"{size_mb:.1f}")
            continue

        pdfs.append(PDFFile(
            path=pdf_path,
            file_name=pdf_path.name,
            brand=brand,
            product_folder=product_folder,
            size_bytes=size_bytes,
            size_mb=round(size_mb, 2),
        ))

    return pdfs


# ---------------------------------------------------------------------------
# Single PDF processing
# ---------------------------------------------------------------------------


@dataclass
class BatchResult:
    """Result of processing a single PDF."""

    file_name: str
    file_path: str
    brand: str
    product_folder: str
    doc_type: str
    success: bool
    error: str | None = None

    # Extraction data
    product_name: str | None = None
    cas_numbers: str | None = None
    missing_count: int = 0
    missing_attributes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Provider info
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0

    # Full result (for JSON export)
    full_result: dict | None = field(default=None, repr=False)


def process_single_pdf(
    pdf_file: PDFFile,
    extractor: BatchExtractorService,
) -> BatchResult:
    """Process a single PDF through the extraction pipeline."""
    start = time.time()

    try:
        # Step 1: Parse PDF
        pdf_bytes = pdf_file.path.read_bytes()
        parsed = parse_pdf(pdf_bytes)

        # Step 2: Extract
        extraction = extractor.extract(
            markdown=parsed.full_markdown,
            doc_type=parsed.doc_type,
            file_name=pdf_file.file_name,
        )

        duration_ms = int((time.time() - start) * 1000)

        if extraction.error or extraction.result is None:
            return BatchResult(
                file_name=pdf_file.file_name,
                file_path=str(pdf_file.path),
                brand=pdf_file.brand,
                product_folder=pdf_file.product_folder,
                doc_type=parsed.doc_type,
                success=False,
                error=extraction.error or "No result returned",
                provider=extraction.provider,
                model=extraction.model,
                duration_ms=duration_ms,
            )

        result = extraction.result

        # Extract key fields for CSV
        product_name = result.identity.product_name if result.identity else None
        cas_value = None
        if result.chemical and result.chemical.cas_numbers:
            cas_value = str(result.chemical.cas_numbers.value) if result.chemical.cas_numbers.value else None

        return BatchResult(
            file_name=pdf_file.file_name,
            file_path=str(pdf_file.path),
            brand=pdf_file.brand,
            product_folder=pdf_file.product_folder,
            doc_type=parsed.doc_type,
            success=True,
            product_name=product_name,
            cas_numbers=cas_value,
            missing_count=len(result.missing_attributes),
            missing_attributes=result.missing_attributes,
            warnings=result.extraction_warnings,
            provider=extraction.provider,
            model=extraction.model,
            input_tokens=extraction.input_tokens,
            output_tokens=extraction.output_tokens,
            cache_read_tokens=extraction.cache_read_tokens,
            cost_usd=0.0,  # computed by CostTracker
            duration_ms=duration_ms,
            full_result=result.model_dump(),
        )

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error("PDF processing failed", file=pdf_file.file_name, error=str(e))
        return BatchResult(
            file_name=pdf_file.file_name,
            file_path=str(pdf_file.path),
            brand=pdf_file.brand,
            product_folder=pdf_file.product_folder,
            doc_type="unknown",
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------


def export_csv(results: list[BatchResult], output_path: Path) -> None:
    """Export results to CSV (summary — one row per PDF)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file_name", "brand", "product_folder", "doc_type", "success",
        "product_name", "cas_numbers", "missing_count", "provider", "model",
        "input_tokens", "output_tokens", "cache_read_tokens", "duration_ms",
        "error", "warnings",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            writer.writerow({
                "file_name": r.file_name,
                "brand": r.brand,
                "product_folder": r.product_folder,
                "doc_type": r.doc_type,
                "success": r.success,
                "product_name": r.product_name or "",
                "cas_numbers": r.cas_numbers or "",
                "missing_count": r.missing_count,
                "provider": r.provider,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cache_read_tokens": r.cache_read_tokens,
                "duration_ms": r.duration_ms,
                "error": r.error or "",
                "warnings": "; ".join(r.warnings) if r.warnings else "",
            })

    logger.info("CSV exported", path=str(output_path), rows=len(results))


def export_json(results: list[BatchResult], output_path: Path) -> None:
    """Export full extraction results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export_data = []
    for r in results:
        entry: dict[str, Any] = {
            "file_name": r.file_name,
            "file_path": r.file_path,
            "brand": r.brand,
            "product_folder": r.product_folder,
            "doc_type": r.doc_type,
            "success": r.success,
            "error": r.error,
            "provider": r.provider,
            "model": r.model,
            "duration_ms": r.duration_ms,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cache_read_tokens": r.cache_read_tokens,
        }
        if r.full_result:
            entry["extraction"] = r.full_result
        export_data.append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    logger.info("JSON exported", path=str(output_path), entries=len(export_data))


def export_cost_csv(cost_tracker: CostTracker, output_path: Path) -> None:
    """Export cost tracking records to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = cost_tracker.to_records_list()

    if not records:
        return

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    logger.info("Cost CSV exported", path=str(output_path), rows=len(records))


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------


def print_progress(
    current: int,
    total: int,
    result: BatchResult,
    cost_tracker: CostTracker,
) -> None:
    """Print a progress line for each processed PDF."""
    status = "✅" if result.success else "❌"
    missing = f"missing={result.missing_count}" if result.success else f"error={result.error[:50] if result.error else '?'}"

    # Running cost total
    total_cost = sum(r.cost_usd for r in cost_tracker.records)

    print(
        f"  [{current:3d}/{total}] {status} {result.file_name[:55]:55s} "
        f"| {result.doc_type:8s} | {missing:25s} | "
        f"{result.provider:10s} | {result.duration_ms:5d}ms | "
        f"total: ${total_cost:.4f}"
    )


# ---------------------------------------------------------------------------
# Main batch runner
# ---------------------------------------------------------------------------


def run_batch(
    input_dir: Path,
    output_dir: Path,
    *,
    limit: int | None = None,
    brand_filter: str | None = None,
    doc_type_filter: str | None = None,
    cascade_enabled: bool = True,
    cascade_threshold: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.5,
) -> None:
    """Main batch extraction entry point."""

    print("=" * 80)
    print("  M3NDEL BATCH EXTRACTION ENGINE")
    print("=" * 80)
    print(f"  Input:     {input_dir}")
    print(f"  Output:    {output_dir}")
    print(f"  Brand:     {brand_filter or 'ALL'}")
    print(f"  Doc Type:  {doc_type_filter or 'ALL'}")
    print(f"  Cascade:   {'ON' if cascade_enabled else 'OFF'}")
    print(f"  Limit:     {limit or 'ALL'}")
    print()

    # --- Step 1: Discover PDFs ---
    pdfs = discover_pdfs(
        input_dir,
        brand_filter=brand_filter,
        doc_type_filter=doc_type_filter,
    )

    if limit:
        pdfs = pdfs[:limit]

    print(f"  Found {len(pdfs)} PDFs to process")
    print()

    if not pdfs:
        print("  No PDFs found. Exiting.")
        return

    # Show brand distribution
    brand_counts: dict[str, int] = {}
    total_size_mb = 0.0
    for pdf in pdfs:
        brand_counts[pdf.brand] = brand_counts.get(pdf.brand, 0) + 1
        total_size_mb += pdf.size_mb

    print("  Brand distribution:")
    for brand, count in sorted(brand_counts.items()):
        print(f"    {brand}: {count} PDFs")
    print(f"  Total size: {total_size_mb:.1f} MB")
    print()

    if dry_run:
        print("  DRY RUN — listing PDFs without extraction:")
        for i, pdf in enumerate(pdfs, 1):
            print(f"    [{i:3d}] {pdf.file_name} ({pdf.size_mb:.1f} MB) — {pdf.brand}")
        print(f"\n  Estimated Gemini cost: ~${len(pdfs) * 0.001:.2f}")
        print(f"  Estimated Sonnet cost: ~${len(pdfs) * 0.014:.2f}")
        return

    # --- Step 2: Initialize extractor + tracker ---
    cost_tracker = CostTracker()
    extractor = BatchExtractorService(
        cost_tracker=cost_tracker,
        cascade_enabled=cascade_enabled,
        cascade_threshold=cascade_threshold,
    )

    # --- Step 3: Process PDFs ---
    results: list[BatchResult] = []
    success_count = 0
    error_count = 0
    start_time = time.time()

    print("-" * 80)
    print("  Processing...")
    print("-" * 80)

    for i, pdf in enumerate(pdfs, 1):
        result = process_single_pdf(pdf, extractor)
        results.append(result)

        if result.success:
            success_count += 1
        else:
            error_count += 1

        print_progress(i, len(pdfs), result, cost_tracker)

        # Rate limiting (avoid hitting API quotas)
        if i < len(pdfs) and delay_seconds > 0:
            time.sleep(delay_seconds)

    elapsed = time.time() - start_time
    print()

    # --- Step 4: Export results ---
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"batch_results_{timestamp}.csv"
    json_path = output_dir / f"batch_results_{timestamp}.json"
    cost_csv_path = output_dir / f"batch_costs_{timestamp}.csv"

    export_csv(results, csv_path)
    export_json(results, json_path)
    export_cost_csv(cost_tracker, cost_csv_path)

    # --- Step 5: Print summary ---
    print(cost_tracker.summary_text())

    print()
    print("  EXTRACTION SUMMARY")
    print("  " + "-" * 40)
    print(f"  Total PDFs:     {len(results)}")
    print(f"  Successful:     {success_count}")
    print(f"  Failed:         {error_count}")
    print(f"  Success Rate:   {success_count / max(len(results), 1) * 100:.1f}%")
    print(f"  Elapsed:        {elapsed:.1f}s ({elapsed / max(len(results), 1):.1f}s/PDF)")
    print()
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  Cost: {cost_csv_path}")
    print("=" * 80)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="M3ndel Batch Extraction — Process PDFs with LLM extraction + cost tracking"
    )
    parser.add_argument(
        "--input-dir", type=Path, default=DEFAULT_INPUT_DIR,
        help=f"Input directory containing PDFs (default: {DEFAULT_INPUT_DIR})"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for results (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of PDFs to process (for testing)"
    )
    parser.add_argument(
        "--brand", type=str, default=None,
        help="Filter by brand (e.g. ELASTOSIL, FERMOPURE, GENIOSIL)"
    )
    parser.add_argument(
        "--doc-type", type=str, default=None,
        help="Filter by document type in filename (e.g. TDS, SDS, RPI)"
    )
    parser.add_argument(
        "--no-cascade", action="store_true",
        help="Disable cascade fallback (Gemini only, cheapest)"
    )
    parser.add_argument(
        "--cascade-threshold", type=int, default=None,
        help="Missing attribute threshold for cascade (default: from config)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List PDFs without running extraction"
    )
    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Delay between API calls in seconds (rate limiting, default: 0.5)"
    )

    args = parser.parse_args()

    run_batch(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        limit=args.limit,
        brand_filter=args.brand,
        doc_type_filter=args.doc_type,
        cascade_enabled=not args.no_cascade,
        cascade_threshold=args.cascade_threshold,
        dry_run=args.dry_run,
        delay_seconds=args.delay,
    )


if __name__ == "__main__":
    main()
