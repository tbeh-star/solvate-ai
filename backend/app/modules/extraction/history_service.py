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
