from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.events import service
from app.modules.events.schemas import (
    EventType,
    IndustryEventOut,
    PaginatedEventsResponse,
    SourceName,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=PaginatedEventsResponse)
async def list_events(
    event_type: EventType | None = Query(None),
    source_name: SourceName | None = Query(None),
    company: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> PaginatedEventsResponse:
    items, total = await service.list_events(
        db,
        event_type=event_type.value if event_type else None,
        source_name=source_name.value if source_name else None,
        company=company,
        page=page,
        page_size=page_size,
    )
    return PaginatedEventsResponse(
        items=[IndustryEventOut.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{event_id}", response_model=IndustryEventOut)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> IndustryEventOut:
    event = await service.get_event(db, event_id)
    if not event:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Event not found")
    return IndustryEventOut.model_validate(event)
