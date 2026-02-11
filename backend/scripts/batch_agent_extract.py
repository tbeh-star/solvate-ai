#!/usr/bin/env python3
"""M3ndel Agent-Based Batch Extraction Runner.

Processes PDFs through the multi-agent pipeline:
  1. Classify each PDF (doc-type + brand)
  2. Extract with doc-type-specific agents
  3. Group by product folder
  4. Merge into Golden Records

Usage:
    # Process all PDFs with agent pipeline
    python -m scripts.batch_agent_extract

    # Limit to N PDFs (for testing)
    python -m scripts.batch_agent_extract --limit 5

    # Only specific brand
    python -m scripts.batch_agent_extract --brand ELASTOSIL

    # Skip merge (only extract, no Golden Records)
    python -m scripts.batch_agent_extract --no-merge

    # Dry run (list PDFs only)
    python -m scripts.batch_agent_extract --dry-run

    # Specific provider/model
    python -m scripts.batch_agent_extract --provider google --model gemini-2.5-flash
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
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

from app.modules.extraction.agents.orchestrator import OrchestratorAgent
from app.modules.extraction.cost_tracker import CostTracker

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_project_root = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_INPUT_DIR = _project_root / "02_Input" / "Wacker"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "agent_results"


# ---------------------------------------------------------------------------
# PDF Discovery (reuse from batch_extract.py pattern)
# ---------------------------------------------------------------------------


@dataclass
class PDFFile:
    """Discovered PDF with path metadata."""

    path: Path
    file_name: str
    brand: str
    product_folder: str
    size_bytes: int
    size_mb: float


def discover_pdfs(
    input_dir: Path,
    *,
    brand_filter: str | None = None,
    doc_type_filter: str | None = None,
    max_size_mb: float = 20.0,
) -> list[PDFFile]:
    """Discover all PDFs in the Wacker directory tree."""
    pdfs: list[PDFFile] = []

    if not input_dir.exists():
        logger.error("Input directory not found", path=str(input_dir))
        return pdfs

    for pdf_path in sorted(input_dir.rglob("*.pdf")):
        if pdf_path.name.startswith(".") or pdf_path.name.startswith("~"):
            continue

        relative = pdf_path.relative_to(input_dir)
        parts = relative.parts
        brand = parts[0].replace("\u00ae", "").strip() if len(parts) > 0 else "unknown"
        product_folder = parts[1] if len(parts) > 2 else parts[0] if len(parts) > 1 else ""

        if brand_filter and brand_filter.upper() not in brand.upper():
            continue

        if doc_type_filter:
            fn_upper = pdf_path.name.upper()
            if f"-{doc_type_filter.upper()}" not in fn_upper and f"_{doc_type_filter.upper()}" not in fn_upper:
                continue

        size_bytes = pdf_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

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
# Export helpers
# ---------------------------------------------------------------------------


def export_results(
    output_dir: Path,
    partials: list,
    golden_records: list[dict],
    cost_summary: dict,
    pipeline_summary: dict,
) -> None:
    """Export batch results to JSON and CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Partials JSON ---
    partials_path = output_dir / f"agent_partials_{timestamp}.json"
    partials_data = []
    for p in partials:
        entry = {
            "source_file": p.source_file,
            "doc_type": p.doc_type,
            "extracted_count": len(p.extracted_fields),
            "missing_count": len(p.missing_fields),
            "missing_fields": p.missing_fields,
            "warnings": p.warnings,
            "extraction_result": p.extraction_result,
        }
        if p.audit_result:
            entry["audit_result"] = p.audit_result.model_dump()
        partials_data.append(entry)
    with open(partials_path, "w") as f:
        json.dump(partials_data, f, indent=2, default=str)
    logger.info(f"Partials exported: {partials_path}")

    # --- Golden Records JSON ---
    golden_path = output_dir / f"agent_golden_records_{timestamp}.json"
    golden_data = []
    for g in golden_records:
        gr = g.get("golden_record")
        golden_data.append({
            "product_name": g["product_name"],
            "product_folder": g["product_folder"],
            "brand": g["brand"],
            "source_count": g["source_count"],
            "error": g["error"],
            "golden_record": gr.model_dump() if gr else None,
            "missing_count": len(gr.missing_attributes) if gr else None,
            "missing_attributes": gr.missing_attributes if gr else None,
        })
    with open(golden_path, "w") as f:
        json.dump(golden_data, f, indent=2, default=str)
    logger.info(f"Golden Records exported: {golden_path}")

    # --- Summary CSV (one row per Golden Record) ---
    csv_path = output_dir / f"agent_summary_{timestamp}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "product_name", "brand", "source_count",
            "missing_count", "error", "product_folder",
        ])
        for g in golden_records:
            gr = g.get("golden_record")
            writer.writerow([
                g["product_name"],
                g["brand"],
                g["source_count"],
                len(gr.missing_attributes) if gr else "N/A",
                g["error"] or "",
                g["product_folder"],
            ])
    logger.info(f"Summary CSV exported: {csv_path}")

    # --- Cost report ---
    cost_path = output_dir / f"agent_costs_{timestamp}.json"
    with open(cost_path, "w") as f:
        json.dump({
            "pipeline_summary": pipeline_summary,
            "cost_summary": cost_summary,
        }, f, indent=2, default=str)
    logger.info(f"Cost report exported: {cost_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="M3ndel Agent-Based Batch Extraction")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR,
                        help="Root input directory (default: 02_Input/Wacker)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for results")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max PDFs to process (0 = all)")
    parser.add_argument("--brand", type=str, default=None,
                        help="Filter by brand (e.g. ELASTOSIL)")
    parser.add_argument("--doc-type", type=str, default=None,
                        help="Filter by doc type in filename (e.g. TDS)")
    parser.add_argument("--provider", type=str, default=None,
                        help="LLM provider (google, anthropic)")
    parser.add_argument("--model", type=str, default=None,
                        help="LLM model name")
    parser.add_argument("--no-merge", action="store_true",
                        help="Skip merging (extract only)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List PDFs without processing")

    args = parser.parse_args()

    # Discover PDFs
    pdfs = discover_pdfs(
        args.input_dir,
        brand_filter=args.brand,
        doc_type_filter=args.doc_type,
    )

    if args.limit > 0:
        pdfs = pdfs[:args.limit]

    print(f"\n{'='*60}")
    print(f"  M3NDEL AGENT EXTRACTION PIPELINE")
    print(f"{'='*60}")
    print(f"  PDFs found:    {len(pdfs)}")
    print(f"  Input dir:     {args.input_dir}")
    print(f"  Output dir:    {args.output_dir}")
    print(f"  Provider:      {args.provider or 'default'}")
    print(f"  Model:         {args.model or 'default'}")
    print(f"  Merge:         {'No' if args.no_merge else 'Yes'}")
    print(f"{'='*60}\n")

    if not pdfs:
        print("No PDFs found. Check input directory.")
        return

    # Brand distribution
    brands: dict[str, int] = {}
    for pdf in pdfs:
        brands[pdf.brand] = brands.get(pdf.brand, 0) + 1
    for brand, count in sorted(brands.items()):
        print(f"  {brand}: {count} PDFs")
    print()

    if args.dry_run:
        print("--- DRY RUN ---")
        for pdf in pdfs:
            print(f"  {pdf.brand}/{pdf.product_folder}/{pdf.file_name} ({pdf.size_mb:.1f} MB)")
        return

    # Run pipeline
    cost_tracker = CostTracker()
    orchestrator = OrchestratorAgent(
        provider=args.provider,
        model=args.model,
        cost_tracker=cost_tracker,
    )

    pdf_paths = [pdf.path for pdf in pdfs]

    if args.no_merge:
        # Extract only
        partials = orchestrator.process_batch(pdf_paths)
        golden_records: list[dict] = []
        pipeline_summary = {
            "total_pdfs": len(pdfs),
            "successful": sum(1 for p in partials if p.extraction_result),
            "failed": sum(1 for p in partials if not p.extraction_result),
        }
    else:
        # Full pipeline (extract + group + merge)
        result = orchestrator.run_full_pipeline(pdf_paths)
        partials = result["partials"]
        golden_records = result["golden_records"]
        pipeline_summary = result["pipeline_summary"]

    # Print cost report
    print(cost_tracker.summary_text())

    # Print pipeline summary
    print(f"\n{'='*60}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'='*60}")
    for key, val in pipeline_summary.items():
        print(f"  {key}: {val}")
    print(f"{'='*60}\n")

    # Print Golden Record summary
    if golden_records:
        print(f"\n{'='*60}")
        print(f"  GOLDEN RECORDS")
        print(f"{'='*60}")
        for gr in golden_records:
            status = "OK" if gr["golden_record"] else f"FAIL: {gr['error']}"
            missing = len(gr["golden_record"].missing_attributes) if gr["golden_record"] else "N/A"
            print(f"  {gr['brand']}/{gr['product_name']}: {gr['source_count']} sources, {missing} missing [{status}]")
        print(f"{'='*60}\n")

    # Export
    export_results(
        args.output_dir,
        partials=partials,
        golden_records=golden_records,
        cost_summary=cost_tracker.summary(),
        pipeline_summary=pipeline_summary,
    )


if __name__ == "__main__":
    main()
