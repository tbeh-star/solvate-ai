from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.events.models import EventCollectorRun, IndustryEvent
from app.modules.events.schemas import ExtractedEvent, RawArticle


async def create_event(
    db: AsyncSession,
    article: RawArticle,
    event: ExtractedEvent,
    dedup_hash: str,
) -> IndustryEvent:
    """Create a new IndustryEvent from extracted data."""
    row = IndustryEvent(
        event_title=event.event_title,
        event_type=event.event_type.value,
        event_date=event.event_date,
        summary=event.summary,
        raw_text=article.snippet,
        confidence=event.confidence,
        source_url=article.url,
        source_name=article.source_name.value,
        companies=event.companies,
        company_roles=event.company_roles,
        products=event.products,
        segments=event.segments,
        regions=event.regions,
        is_exclusive=event.is_exclusive,
        deal_value=event.deal_value,
        deal_duration=event.deal_duration,
        effective_date=event.effective_date,
        geographic_scope=event.geographic_scope,
        exec_quotes=[q.model_dump() for q in event.exec_quotes] if event.exec_quotes else None,
        key_people=[p.model_dump() for p in event.key_people] if event.key_people else None,
        strategic_rationale=event.strategic_rationale,
        dedup_hash=dedup_hash,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def dedup_hash_exists(db: AsyncSession, dedup_hash: str) -> bool:
    """Check if an event with this dedup hash already exists."""
    result = await db.execute(
        select(func.count()).select_from(IndustryEvent).where(
            IndustryEvent.dedup_hash == dedup_hash
        )
    )
    return result.scalar_one() > 0


async def update_notion_page_id(
    db: AsyncSession, event_id: int, notion_page_id: str
) -> None:
    """Update the Notion page ID for an event."""
    result = await db.execute(
        select(IndustryEvent).where(IndustryEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event:
        event.notion_page_id = notion_page_id
        await db.flush()


async def list_events(
    db: AsyncSession,
    event_type: str | None = None,
    source_name: str | None = None,
    company: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[IndustryEvent], int]:
    """List events with optional filters and pagination."""
    base = select(IndustryEvent)

    if event_type:
        base = base.where(IndustryEvent.event_type == event_type)
    if source_name:
        base = base.where(IndustryEvent.source_name == source_name)
    if company:
        base = base.where(IndustryEvent.companies.any(company))

    count_query = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = base.order_by(IndustryEvent.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_event(db: AsyncSession, event_id: int) -> IndustryEvent | None:
    """Get a single event by ID."""
    result = await db.execute(
        select(IndustryEvent).where(IndustryEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def create_collector_run(
    db: AsyncSession, source: str, started_at: datetime
) -> EventCollectorRun:
    """Create a new collector run record."""
    run = EventCollectorRun(
        source=source,
        started_at=started_at,
        status="running",
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def finish_collector_run(
    db: AsyncSession,
    run_id: int,
    status: str,
    events_found: int = 0,
    events_new: int = 0,
    error_message: str | None = None,
) -> None:
    """Update a collector run with final status."""
    result = await db.execute(
        select(EventCollectorRun).where(EventCollectorRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run:
        run.finished_at = datetime.now()
        run.status = status
        run.events_found = events_found
        run.events_new = events_new
        run.error_message = error_message
        await db.flush()
