from __future__ import annotations

from typing import Optional

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndustryEvent(Base):
    __tablename__ = "industry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Core event info
    event_title: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_date: Mapped[Optional[date]] = mapped_column(Date)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Source info
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Companies & products
    companies: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)
    company_roles: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    products: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)
    segments: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)
    regions: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)

    # Enriched deal details
    is_exclusive: Mapped[Optional[bool]] = mapped_column(Boolean)
    deal_value: Mapped[Optional[str]] = mapped_column(Text)
    deal_duration: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    geographic_scope: Mapped[Optional[str]] = mapped_column(Text)
    exec_quotes: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    key_people: Mapped[Optional[list[dict]]] = mapped_column(JSONB)
    strategic_rationale: Mapped[Optional[str]] = mapped_column(Text)

    # Dedup & status
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="auto_detected")
    notion_page_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_industry_events_type", "event_type"),
        Index("idx_industry_events_date", "event_date"),
        Index("idx_industry_events_source", "source_name"),
        Index("idx_industry_events_created", "created_at"),
        Index("idx_industry_events_dedup", "dedup_hash"),
    )


class EventCollectorRun(Base):
    __tablename__ = "event_collector_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    events_found: Mapped[int] = mapped_column(Integer, default=0)
    events_new: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)
