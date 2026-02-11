from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    canonical_name: str
    aliases: list[str] = []
    cas_number: str | None = None
    category: str | None = None


class ProductOut(ProductCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InternalPriceCreate(BaseModel):
    product_raw: str
    product_id: int | None = None
    price_value: float
    price_currency: str = "USD"
    price_unit: str = "mt"
    price_raw: str | None = None
    specs: str | None = None
    delivery_term: str | None = None
    location: str | None = None
    packaging: str | None = None
    quantity: str | None = None
    producer: str | None = None
    custom_fields: dict | None = None
    source_format: str = "text"
    source_ref: str | None = None
    confidence: float | None = None


class InternalPriceUpdate(BaseModel):
    product_raw: str | None = None
    price_value: float | None = None
    price_currency: str | None = None
    price_unit: str | None = None
    specs: str | None = None
    delivery_term: str | None = None
    location: str | None = None
    packaging: str | None = None
    quantity: str | None = None
    producer: str | None = None
    custom_fields: dict | None = None


class InternalPriceOut(BaseModel):
    id: int
    product_raw: str
    product_id: int | None = None
    price_value: float
    price_currency: str
    price_unit: str
    price_raw: str | None = None
    specs: str | None = None
    delivery_term: str | None = None
    location: str | None = None
    packaging: str | None = None
    quantity: str | None = None
    producer: str | None = None
    custom_fields: dict | None = None
    source_format: str
    source_ref: str | None = None
    confidence: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarketPriceOut(BaseModel):
    id: int
    time: datetime
    product_raw: str
    product_id: int | None = None
    price_value: float
    price_currency: str
    price_unit: str
    location: str | None = None
    price_type: str | None = None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketPriceQuery(BaseModel):
    start_date: datetime
    end_date: datetime
    source: str | None = None
    unit: str | None = None
    price_types: list[str] | None = None
    product: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int
