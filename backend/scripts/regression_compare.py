#!/usr/bin/env python3
"""Field-by-Field Regression: Compare Monolith vs Agent Pipeline extractions.

Compares the batch results from the old monolithic pipeline against the new
multi-agent pipeline, field by field, to identify improvements and regressions.

Usage:
    python -m scripts.regression_compare

Output:
    - Per-field comparison (populated count old vs new)
    - Per-PDF diff (what changed)
    - Summary statistics
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration: paths to the two batch result files
# ---------------------------------------------------------------------------

_OUTPUT = Path(__file__).resolve().parent.parent / "output"
MONOLITH_JSON = _OUTPUT / "batch_results" / "batch_results_20260210_194712.json"
AGENT_JSON = _OUTPUT / "agent_results" / "agent_partials_20260210_225544.json"
REPORT_PATH = _OUTPUT / "agent_results" / "regression_report.txt"

# All 33 attributes we track (grouped by section)
FIELD_MAP: dict[str, list[str]] = {
    "identity": ["product_name", "product_line", "wacker_sku", "material_numbers", "product_url", "grade"],
    "chemical": ["cas_numbers", "chemical_components", "chemical_synonyms", "purity"],
    "physical": ["physical_form", "density", "flash_point", "temperature_range", "shelf_life", "cure_system"],
    "application": ["main_application", "usage_restrictions", "packaging_options"],
    "safety": ["ghs_statements", "un_number", "certifications", "global_inventories", "blocked_countries", "blocked_industries"],
    "compliance": ["wiaw_status", "sales_advisory"],
    "document_info": ["document_type", "language", "manufacturer", "brand", "revision_date"],
}

# Flat list of all tracked fields
ALL_FIELDS: list[str] = []
for section_fields in FIELD_MAP.values():
    ALL_FIELDS.extend(section_fields)


def _is_populated(val) -> bool:
    """Check if a value is meaningfully populated (not null/empty)."""
    if val is None:
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    if isinstance(val, list) and len(val) == 0:
        return False
    if isinstance(val, dict):
        # MendelFact: check if "value" key is populated
        v = val.get("value")
        if v is None:
            return False
        if isinstance(v, str) and v.strip() == "":
            return False
    return True


def _get_value_str(val) -> str:
    """Get a human-readable string for a field value."""
    if val is None:
        return "—"
    if isinstance(val, dict):
        v = val.get("value", val)
        if isinstance(v, dict):
            return str(v)[:60]
        return str(v)[:60] if v is not None else "—"
    if isinstance(val, list):
        if len(val) == 0:
            return "[]"
        return f"[{len(val)} items]"
    return str(val)[:60]


def _get_field(extraction: dict, section: str, field: str):
    """Extract a field value from the nested extraction dict."""
    sec = extraction.get(section, {})
    if not isinstance(sec, dict):
        return None
    return sec.get(field)


def load_results() -> tuple[dict[str, dict], dict[str, dict]]:
    """Load both result sets, keyed by filename."""
    with open(MONOLITH_JSON) as f:
        mono_list = json.load(f)

    with open(AGENT_JSON) as f:
        agent_list = json.load(f)

    # Key by filename
    mono = {}
    for entry in mono_list:
        fn = entry["file_name"]
        mono[fn] = entry.get("extraction", {})

    agent = {}
    for entry in agent_list:
        fn = Path(entry["source_file"]).name
        agent[fn] = entry.get("extraction_result", {})

    return mono, agent


def compare(mono: dict[str, dict], agent: dict[str, dict]) -> str:
    """Run the full field-by-field comparison and return a report string."""
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("  REGRESSION REPORT: Monolith vs Agent Pipeline")
    lines.append("=" * 80)

    # Find common files
    mono_files = set(mono.keys())
    agent_files = set(agent.keys())
    common = sorted(mono_files & agent_files)
    only_mono = mono_files - agent_files
    only_agent = agent_files - mono_files

    lines.append(f"\n  Files in Monolith:  {len(mono_files)}")
    lines.append(f"  Files in Agent:     {len(agent_files)}")
    lines.append(f"  Common (compared):  {len(common)}")
    if only_mono:
        lines.append(f"  Only in Monolith:   {len(only_mono)} ({', '.join(sorted(only_mono)[:3])}...)")
    if only_agent:
        lines.append(f"  Only in Agent:      {len(only_agent)} ({', '.join(sorted(only_agent)[:3])}...)")

    # --- Per-field population comparison ---
    lines.append(f"\n{'=' * 80}")
    lines.append(f"  FIELD POPULATION COMPARISON (populated count across {len(common)} PDFs)")
    lines.append(f"{'=' * 80}")
    lines.append(f"  {'Field':<30s} {'Monolith':>10s} {'Agent':>10s} {'Diff':>8s} {'Status':>10s}")
    lines.append(f"  {'-' * 70}")

    total_mono_populated = 0
    total_agent_populated = 0
    field_stats: dict[str, dict] = {}

    for section, fields in FIELD_MAP.items():
        for field in fields:
            mono_count = 0
            agent_count = 0
            for fn in common:
                mono_val = _get_field(mono[fn], section, field)
                agent_val = _get_field(agent[fn], section, field)
                if _is_populated(mono_val):
                    mono_count += 1
                if _is_populated(agent_val):
                    agent_count += 1

            diff = agent_count - mono_count
            total_mono_populated += mono_count
            total_agent_populated += agent_count

            if diff > 0:
                status = f"+{diff} ✅"
            elif diff < 0:
                status = f"{diff} ⚠️"
            else:
                status = "="

            field_stats[field] = {
                "section": section,
                "mono": mono_count,
                "agent": agent_count,
                "diff": diff,
            }

            lines.append(f"  {field:<30s} {mono_count:>10d} {agent_count:>10d} {diff:>+8d} {status:>10s}")

    lines.append(f"  {'-' * 70}")
    total_diff = total_agent_populated - total_mono_populated
    lines.append(
        f"  {'TOTAL':<30s} {total_mono_populated:>10d} {total_agent_populated:>10d} "
        f"{total_diff:>+8d} {'✅' if total_diff >= 0 else '⚠️'}"
    )

    # --- Regressions (fields where Agent is worse) ---
    regressions = {f: s for f, s in field_stats.items() if s["diff"] < 0}
    if regressions:
        lines.append(f"\n{'=' * 80}")
        lines.append(f"  ⚠️  REGRESSIONS ({len(regressions)} fields with fewer populated values)")
        lines.append(f"{'=' * 80}")
        for field, stats in sorted(regressions.items(), key=lambda x: x[1]["diff"]):
            lines.append(f"  {field}: {stats['mono']} → {stats['agent']} ({stats['diff']:+d})")

    # --- Improvements (fields where Agent is better) ---
    improvements = {f: s for f, s in field_stats.items() if s["diff"] > 0}
    if improvements:
        lines.append(f"\n{'=' * 80}")
        lines.append(f"  ✅ IMPROVEMENTS ({len(improvements)} fields with more populated values)")
        lines.append(f"{'=' * 80}")
        for field, stats in sorted(improvements.items(), key=lambda x: -x[1]["diff"]):
            lines.append(f"  {field}: {stats['mono']} → {stats['agent']} ({stats['diff']:+d})")

    # --- Per-PDF missing count comparison ---
    lines.append(f"\n{'=' * 80}")
    lines.append(f"  PER-PDF MISSING COUNT COMPARISON")
    lines.append(f"{'=' * 80}")

    mono_missing_total = 0
    agent_missing_total = 0
    pdf_diffs: list[tuple[str, int, int]] = []

    for fn in common:
        mono_ext = mono[fn]
        agent_ext = agent[fn]

        mono_missing = len(mono_ext.get("missing_attributes", []))
        agent_missing = len(agent_ext.get("missing_attributes", []))

        mono_missing_total += mono_missing
        agent_missing_total += agent_missing

        if mono_missing != agent_missing:
            pdf_diffs.append((fn, mono_missing, agent_missing))

    mono_avg = mono_missing_total / len(common) if common else 0
    agent_avg = agent_missing_total / len(common) if common else 0

    lines.append(f"  Average missing per PDF:  Monolith={mono_avg:.1f}  Agent={agent_avg:.1f}  Diff={agent_avg - mono_avg:+.1f}")
    lines.append(f"  Total missing:            Monolith={mono_missing_total}  Agent={agent_missing_total}")

    # Top 10 biggest changes
    pdf_diffs.sort(key=lambda x: x[1] - x[2], reverse=True)
    if pdf_diffs:
        lines.append(f"\n  Top improvements (fewer missing in Agent):")
        for fn, mono_m, agent_m in pdf_diffs[:10]:
            diff = agent_m - mono_m
            lines.append(f"    {fn:<60s} {mono_m:>3d} → {agent_m:>3d} ({diff:+d})")

        lines.append(f"\n  Top regressions (more missing in Agent):")
        for fn, mono_m, agent_m in reversed(pdf_diffs[-10:]):
            diff = agent_m - mono_m
            if diff > 0:
                lines.append(f"    {fn:<60s} {mono_m:>3d} → {agent_m:>3d} ({diff:+d})")

    # --- Doc-type classification comparison ---
    lines.append(f"\n{'=' * 80}")
    lines.append(f"  DOC-TYPE CLASSIFICATION COMPARISON")
    lines.append(f"{'=' * 80}")

    doc_type_changes: list[tuple[str, str, str]] = []
    for fn in common:
        mono_dt = mono[fn].get("document_info", {}).get("document_type", "?")
        agent_dt = agent[fn].get("document_info", {}).get("document_type", "?")
        if mono_dt != agent_dt:
            doc_type_changes.append((fn, mono_dt, agent_dt))

    lines.append(f"  Classification changes: {len(doc_type_changes)} / {len(common)}")
    for fn, old_dt, new_dt in sorted(doc_type_changes):
        lines.append(f"    {fn:<60s} {old_dt:>10s} → {new_dt}")

    lines.append(f"\n{'=' * 80}")
    lines.append(f"  END OF REPORT")
    lines.append(f"{'=' * 80}")

    return "\n".join(lines)


def main() -> None:
    mono, agent = load_results()
    report = compare(mono, agent)

    # Print to console
    print(report)

    # Save to file
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
