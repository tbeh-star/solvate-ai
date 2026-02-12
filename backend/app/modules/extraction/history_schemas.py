"""History API schemas — read-only views of ExtractionRun & GoldenRecord."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Golden Record views
# ---------------------------------------------------------------------------


class GoldenRecordSummary(BaseModel):
    """Compact view of a Golden Record (used in lists and run details)."""

    model_config = {"from_attributes": True}

    id: int
    product_name: str
    brand: str | None = None
    source_files: list[str] = Field(default_factory=list)
    source_count: int | None = None
    missing_count: int | None = None
    completeness: float | None = None
    created_at: datetime

    # Versioning & regional variant fields
    region: str = "GLOBAL"
    doc_language: str | None = None
    revision_date: str | None = None
    document_type: str | None = None
    version: int = 1
    is_latest: bool = True


class GoldenRecordDetail(GoldenRecordSummary):
    """Full Golden Record including the JSONB extraction data."""

    golden_record: dict = Field(
        ..., description="Full ExtractionResult as persisted JSONB"
    )


# ---------------------------------------------------------------------------
# Version diff
# ---------------------------------------------------------------------------


class DiffEntry(BaseModel):
    """A single field-level change between two versions."""

    field: str
    change_type: str  # "added" | "removed" | "changed"
    old_value: str | float | list | dict | None = None
    new_value: str | float | list | dict | None = None
    old_unit: str | None = None
    new_unit: str | None = None
    old_confidence: str | None = None
    new_confidence: str | None = None


class SectionDiff(BaseModel):
    """Changes within one ExtractionResult section."""

    section: str
    changes: list[DiffEntry]


class VersionDiffResponse(BaseModel):
    """Full diff between two golden record versions."""

    record_a: GoldenRecordSummary
    record_b: GoldenRecordSummary
    sections: list[SectionDiff]
    total_changes: int
    summary: str


# ---------------------------------------------------------------------------
# Extraction Run views
# ---------------------------------------------------------------------------


class ExtractionRunSummary(BaseModel):
    """Compact view of an ExtractionRun (used in the runs list)."""

    model_config = {"from_attributes": True}

    id: int
    started_at: datetime
    finished_at: datetime | None = None
    pdf_count: int | None = None
    golden_records_count: int | None = None
    status: str
    total_cost: float | None = None


class ExtractionRunDetail(ExtractionRunSummary):
    """Run detail with its associated Golden Records."""

    golden_records: list[GoldenRecordSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Paginated response wrappers (typed, unlike the generic PaginatedResponse)
# ---------------------------------------------------------------------------


class PaginatedRuns(BaseModel):
    """Paginated list of extraction runs."""

    items: list[ExtractionRunSummary]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedGoldenRecords(BaseModel):
    """Paginated list of golden records."""

    items: list[GoldenRecordSummary]
    total: int
    page: int
    page_size: int
    pages: int
