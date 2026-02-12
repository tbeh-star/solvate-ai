"""History service — DB queries for ExtractionRun & GoldenRecord."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.extraction.models import ExtractionRun, GoldenRecord


async def list_runs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ExtractionRun], int]:
    """Return a paginated list of extraction runs, newest first."""
    count_query = select(func.count()).select_from(ExtractionRun)
    total = (await db.execute(count_query)).scalar_one()

    query = (
        select(ExtractionRun)
        .order_by(ExtractionRun.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_run_detail(
    db: AsyncSession,
    run_id: int,
) -> ExtractionRun | None:
    """Return a single extraction run by ID (or None)."""
    result = await db.execute(
        select(ExtractionRun).where(ExtractionRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def get_golden_record_by_id(
    db: AsyncSession,
    record_id: int,
) -> GoldenRecord | None:
    """Return a single golden record by ID (or None)."""
    result = await db.execute(
        select(GoldenRecord).where(GoldenRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def list_golden_records(
    db: AsyncSession,
    run_id: int | None = None,
    latest_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[GoldenRecord], int]:
    """Return paginated golden records, optionally filtered by run_id.

    Args:
        latest_only: If True, only return the latest version per (product, region).
    """
    base = select(GoldenRecord)
    count_base = select(func.count()).select_from(GoldenRecord)

    if run_id is not None:
        base = base.where(GoldenRecord.run_id == run_id)
        count_base = count_base.where(GoldenRecord.run_id == run_id)

    if latest_only:
        base = base.where(GoldenRecord.is_latest == True)  # noqa: E712
        count_base = count_base.where(GoldenRecord.is_latest == True)  # noqa: E712

    total = (await db.execute(count_base)).scalar_one()

    query = (
        base.order_by(GoldenRecord.product_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def list_product_versions(
    db: AsyncSession,
    product_name: str,
    region: str | None = None,
) -> list[GoldenRecord]:
    """Return all versions of a product, newest first.

    Optionally filter by region. If region is None, returns versions
    across all regions for that product name.
    """
    query = select(GoldenRecord).where(
        GoldenRecord.product_name == product_name
    )
    if region is not None:
        query = query.where(GoldenRecord.region == region)
    query = query.order_by(GoldenRecord.version.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Version diff
# ---------------------------------------------------------------------------

_DIFF_SECTIONS = (
    "document_info",
    "identity",
    "chemical",
    "physical",
    "application",
    "safety",
    "compliance",
)


def _is_mendel_fact(val: object) -> bool:
    """Return True if *val* looks like a serialised MendelFact dict."""
    return isinstance(val, dict) and "value" in val and "source_section" in val


def _stringify(val: object) -> str:
    """Best-effort display string for any value."""
    if val is None:
        return ""
    if isinstance(val, list):
        return "; ".join(str(v) for v in val)
    return str(val)


def compute_diff(
    json_a: dict, json_b: dict
) -> tuple[list[dict], int]:
    """Field-by-field diff of two ExtractionResult dicts.

    Returns ``(sections, total_change_count)`` where *sections* is a list of
    ``{"section": str, "changes": [DiffEntry-like dicts]}``.
    """
    sections: list[dict] = []
    total = 0

    for section_name in _DIFF_SECTIONS:
        sec_a = json_a.get(section_name, {}) or {}
        sec_b = json_b.get(section_name, {}) or {}
        all_keys = sorted(set(list(sec_a.keys()) + list(sec_b.keys())))

        changes: list[dict] = []
        for key in all_keys:
            val_a = sec_a.get(key)
            val_b = sec_b.get(key)

            # --- MendelFact comparison ---
            if _is_mendel_fact(val_a) or _is_mendel_fact(val_b):
                fa = val_a if _is_mendel_fact(val_a) else {}
                fb = val_b if _is_mendel_fact(val_b) else {}
                va, vb = fa.get("value"), fb.get("value")
                ua, ub = fa.get("unit"), fb.get("unit")
                ca, cb = fa.get("confidence"), fb.get("confidence")

                if va is None and vb is not None:
                    changes.append(
                        {"field": key, "change_type": "added",
                         "old_value": None, "new_value": vb,
                         "old_unit": None, "new_unit": ub,
                         "old_confidence": None, "new_confidence": cb}
                    )
                elif va is not None and vb is None:
                    changes.append(
                        {"field": key, "change_type": "removed",
                         "old_value": va, "new_value": None,
                         "old_unit": ua, "new_unit": None,
                         "old_confidence": ca, "new_confidence": None}
                    )
                elif va != vb or ua != ub or ca != cb:
                    changes.append(
                        {"field": key, "change_type": "changed",
                         "old_value": va, "new_value": vb,
                         "old_unit": ua, "new_unit": ub,
                         "old_confidence": ca, "new_confidence": cb}
                    )
                continue

            # --- List comparison ---
            if isinstance(val_a, list) or isinstance(val_b, list):
                la = set(_stringify(v) for v in (val_a or []))
                lb = set(_stringify(v) for v in (val_b or []))
                added = sorted(lb - la)
                removed = sorted(la - lb)
                if added:
                    changes.append(
                        {"field": key, "change_type": "added",
                         "old_value": None, "new_value": added,
                         "old_unit": None, "new_unit": None,
                         "old_confidence": None, "new_confidence": None}
                    )
                if removed:
                    changes.append(
                        {"field": key, "change_type": "removed",
                         "old_value": removed, "new_value": None,
                         "old_unit": None, "new_unit": None,
                         "old_confidence": None, "new_confidence": None}
                    )
                continue

            # --- Primitive comparison ---
            sa = _stringify(val_a)
            sb = _stringify(val_b)
            if sa == sb:
                continue
            if not sa and sb:
                ct = "added"
            elif sa and not sb:
                ct = "removed"
            else:
                ct = "changed"
            changes.append(
                {"field": key, "change_type": ct,
                 "old_value": sa or None, "new_value": sb or None,
                 "old_unit": None, "new_unit": None,
                 "old_confidence": None, "new_confidence": None}
            )

        if changes:
            sections.append({"section": section_name, "changes": changes})
            total += len(changes)

    return sections, total
