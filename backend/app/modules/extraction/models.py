"""Extraction persistence models — ExtractionRun + GoldenRecord.

ExtractionRun tracks each batch invocation of the agent pipeline.
GoldenRecord stores the merged, deduplicated product data as JSONB,
enabling flexible queries without schema migrations when new attributes
are added to ExtractionResult.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExtractionRun(Base):
    """One execution of the batch agent pipeline."""

    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pdf_count: Mapped[Optional[int]] = mapped_column(Integer)
    golden_records_count: Mapped[Optional[int]] = mapped_column(Integer)
    total_cost: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running | completed | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)


class GoldenRecord(Base):
    """Merged product data from one or more PDFs — the single source of truth."""

    __tablename__ = "golden_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extraction_runs.id"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(200))

    # --- Versioning & regional variant fields ---
    region: Mapped[str] = mapped_column(
        String(10), nullable=False, default="GLOBAL"
    )
    doc_language: Mapped[Optional[str]] = mapped_column(String(5))
    revision_date: Mapped[Optional[str]] = mapped_column(String(20))
    document_type: Mapped[Optional[str]] = mapped_column(String(10))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    golden_record: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_files: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)
    source_count: Mapped[Optional[int]] = mapped_column(Integer)
    missing_count: Mapped[Optional[int]] = mapped_column(Integer)
    completeness: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_golden_records_run", "run_id"),
        Index("idx_golden_records_product", "product_name"),
        Index("idx_golden_records_brand", "brand"),
        Index(
            "idx_golden_records_jsonb",
            "golden_record",
            postgresql_using="gin",
        ),
        # One product+region per run (prevents duplicates within a batch)
        Index(
            "uq_golden_records_run_product_region",
            "run_id",
            "product_name",
            "region",
            unique=True,
        ),
        # Version-history lookup
        Index(
            "idx_golden_records_version",
            "product_name",
            "region",
            "version",
        ),
        # NOTE: idx_golden_records_latest is a partial index created via
        # raw SQL in the migration (WHERE is_latest = true). SQLAlchemy
        # Index() doesn't natively support partial indexes in __table_args__.
    )
