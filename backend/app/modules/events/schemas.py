from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    distribution_agreement = "distribution_agreement"
    acquisition = "acquisition"
    partnership = "partnership"
    force_majeure = "force_majeure"
    plant_shutdown = "plant_shutdown"
    capacity_expansion = "capacity_expansion"
    regulatory_change = "regulatory_change"
    supply_disruption = "supply_disruption"
    price_change = "price_change"
    other = "other"


class SourceName(str, Enum):
    google_news = "google_news"
    google_search = "google_search"
    icis = "icis"
    chemanalyst = "chemanalyst"
    company_website = "company_website"
    linkedin_via_google = "linkedin_via_google"
    other = "other"


# --- Source collector output ---


class RawArticle(BaseModel):
    title: str
    url: str
    snippet: str
    source_name: SourceName
    published_date: date | None = None


# --- OpenAI extraction output ---


class ExecQuote(BaseModel):
    name: str
    title: str | None = None
    company: str | None = None
    quote: str


class KeyPerson(BaseModel):
    name: str
    title: str | None = None
    company: str | None = None


class ExtractedEvent(BaseModel):
    # Core
    event_title: str
    event_type: EventType
    companies: list[str] = []
    company_roles: dict[str, str] = {}
    products: list[str] = []
    segments: list[str] = []
    regions: list[str] = []
    event_date: date | None = None
    summary: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    is_relevant: bool = True

    # Enriched deal details
    is_exclusive: bool | None = None
    deal_value: str | None = None
    deal_duration: str | None = None
    effective_date: date | None = None
    geographic_scope: str | None = None
    exec_quotes: list[ExecQuote] = []
    key_people: list[KeyPerson] = []
    strategic_rationale: str | None = None


# --- API response schemas ---


class IndustryEventOut(BaseModel):
    id: int
    event_title: str
    event_type: str
    event_date: date | None = None
    summary: str | None = None
    confidence: float | None = None
    source_url: str
    source_name: str
    companies: list[str] = []
    company_roles: dict | None = None
    products: list[str] = []
    segments: list[str] = []
    regions: list[str] = []
    is_exclusive: bool | None = None
    deal_value: str | None = None
    deal_duration: str | None = None
    effective_date: date | None = None
    geographic_scope: str | None = None
    exec_quotes: list[dict] | None = None
    key_people: list[dict] | None = None
    strategic_rationale: str | None = None
    status: str
    notion_page_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListQuery(BaseModel):
    event_type: EventType | None = None
    source_name: SourceName | None = None
    company: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class PaginatedEventsResponse(BaseModel):
    items: list[IndustryEventOut]
    total: int
    page: int
    page_size: int
    pages: int
