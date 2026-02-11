from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    aliases: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)
    cas_number: Mapped[Optional[str]] = mapped_column(String(20))
    category: Mapped[Optional[str]] = mapped_column(Text)  # legacy, kept for backward compat

    # Taxonomy enrichment fields
    inci_name: Mapped[Optional[str]] = mapped_column(Text)
    chemical_family: Mapped[Optional[str]] = mapped_column(String(100))
    physical_form: Mapped[Optional[str]] = mapped_column(String(50))
    brand_name: Mapped[Optional[str]] = mapped_column(String(200))
    producer: Mapped[Optional[str]] = mapped_column(String(200))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InternalPrice(Base):
    __tablename__ = "internal_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id")
    )
    product_raw: Mapped[str] = mapped_column(Text, nullable=False)
    price_value: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    price_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="mt")
    price_raw: Mapped[Optional[str]] = mapped_column(Text)
    specs: Mapped[Optional[str]] = mapped_column(Text)
    delivery_term: Mapped[Optional[str]] = mapped_column(String(10))
    location: Mapped[Optional[str]] = mapped_column(Text)
    packaging: Mapped[Optional[str]] = mapped_column(Text)
    quantity: Mapped[Optional[str]] = mapped_column(Text)
    producer: Mapped[Optional[str]] = mapped_column(Text)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    source_format: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_internal_prices_org", "org_id"),
        Index("idx_internal_prices_product", "product_id"),
        Index("idx_internal_prices_created", "created_at"),
    )


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id")
    )
    product_raw: Mapped[str] = mapped_column(Text, nullable=False)
    price_value: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    price_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="mt")
    location: Mapped[Optional[str]] = mapped_column(Text)
    price_type: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_market_prices_time", "time"),
        Index("idx_market_prices_product", "product_id"),
        Index("idx_market_prices_source", "source"),
    )


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(15, 8), nullable=False)


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)
