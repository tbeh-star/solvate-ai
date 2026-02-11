"""M3ndel Extraction Engine — Pydantic schemas for all 33 Notion DB attributes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Base unit: every extracted value carries provenance
# ---------------------------------------------------------------------------


class MendelFact(BaseModel):
    """Single extracted fact with source provenance and confidence."""

    value: str | float | None = None
    unit: str | None = None
    source_section: str = Field(
        ..., description="e.g. 'TDS Spec Table', 'SDS Sec 9', 'RPI Global Inventories'"
    )
    raw_string: str = Field(..., description="Original text quote from the document")
    confidence: Literal["high", "medium", "low"]
    is_specification: bool = Field(
        False, description="True if value is a guaranteed spec (not typical)"
    )
    test_method: str | None = Field(
        None, description="e.g. 'DIN 51757', 'PH. EUR. 2.2.20'"
    )


# ---------------------------------------------------------------------------
# Document metadata
# ---------------------------------------------------------------------------


class DocumentInfo(BaseModel):
    """Metadata about the parsed document."""

    document_type: Literal["TDS", "SDS", "RPI", "CoA", "Brochure", "unknown"]
    language: str = "en"
    manufacturer: str | None = None
    brand: str | None = Field(
        None, description="ELASTOSIL, FERMOPURE, GENIOSIL, BELSIL, POWERSIL, VINNAPAS"
    )
    revision_date: str | None = None
    page_count: int = 0


# ---------------------------------------------------------------------------
# Group 1: Identity & Classification
# ---------------------------------------------------------------------------


class IdentityData(BaseModel):
    """Product identity and classification attributes."""

    product_name: str
    product_line: str | None = Field(
        None, description="Brand line: ELASTOSIL, GENIOSIL, etc."
    )
    wacker_sku: str | None = Field(None, description="ERP/SAP material ID")
    material_numbers: list[str] = []
    product_url: str | None = None
    grade: MendelFact | None = Field(
        None, description="Tech / Food / Pharma / Cosmetic + EP/USP"
    )


# ---------------------------------------------------------------------------
# Group 2: Chemical Identity
# ---------------------------------------------------------------------------


class ChemicalData(BaseModel):
    """Chemical identity and composition."""

    cas_numbers: MendelFact = Field(..., description="Primary key, comma-separated if multiple")
    chemical_components: list[str] = Field(
        default_factory=list, description="Substance names"
    )
    chemical_synonyms: list[str] = []
    purity: MendelFact | None = Field(
        None, description="e.g. '>99.5%', '98.5-101.0%'"
    )


# ---------------------------------------------------------------------------
# Group 3: Physical & Technical Properties
# ---------------------------------------------------------------------------


class PhysicalData(BaseModel):
    """Physical and technical specifications."""

    physical_form: MendelFact | None = Field(
        None, description="Liquid / Powder / Paste / Granular"
    )
    density: MendelFact | None = Field(
        None, description="g/cm³ @ temperature — N/A for solids like FERMOPURE"
    )
    flash_point: MendelFact | None = Field(None, description="°C")
    temperature_range: MendelFact | None = Field(
        None, description="Operating or storage range"
    )
    shelf_life: MendelFact | None = Field(None, description="Months")
    cure_system: MendelFact | None = Field(
        None, description="Acetoxy / Oxime / Alkoxy / Addition / Moisture / Amine"
    )


# ---------------------------------------------------------------------------
# Group 4: Application & Usage
# ---------------------------------------------------------------------------


class ApplicationData(BaseModel):
    """Application context and packaging."""

    main_application: str | None = None
    usage_restrictions: list[str] = Field(
        default_factory=list, description="Restrictions — triggers RED FLAG"
    )
    packaging_options: list[str] = Field(
        default_factory=list, description="Drums, IBCs, Cartridges, 25 kg Bags"
    )


# ---------------------------------------------------------------------------
# Group 5: Safety & Regulatory
# ---------------------------------------------------------------------------


class SafetyData(BaseModel):
    """Safety, regulatory, and compliance data."""

    ghs_statements: list[str] = Field(
        default_factory=list, description="H319, H315, P264, etc."
    )
    un_number: MendelFact | None = Field(
        None, description="Exclusively from SDS Section 14"
    )
    certifications: list[str] = Field(
        default_factory=list, description="RoHS, REACH, FDA, NSF, Halal, Kosher"
    )
    global_inventories: list[str] = Field(
        default_factory=list,
        description="TSCA, REACH, IECSC, K-REACH, DSL, ENCS, etc.",
    )
    blocked_countries: list[str] = Field(
        default_factory=list, description="Derived: not in inventory → blocked"
    )
    blocked_industries: list[str] = []


# ---------------------------------------------------------------------------
# Group 6: Compliance (derived, not directly from PDF)
# ---------------------------------------------------------------------------


class ComplianceData(BaseModel):
    """WIAW compliance verdict — derived from safety data."""

    wiaw_status: Literal["GREEN LIGHT", "ATTENTION", "RED FLAG"] | None = None
    sales_advisory: str | None = Field(
        None, description="GO / CHECK / STOP"
    )


# ---------------------------------------------------------------------------
# Main extraction result
# ---------------------------------------------------------------------------


class ExtractionResult(BaseModel):
    """Complete extraction output matching the 33-attribute Notion schema."""

    document_info: DocumentInfo
    identity: IdentityData
    chemical: ChemicalData
    physical: PhysicalData
    application: ApplicationData
    safety: SafetyData
    compliance: ComplianceData
    missing_attributes: list[str] = Field(
        ..., description="Names of the 33 attributes not found in the document"
    )
    extraction_warnings: list[str] = []


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------


class ExtractionRequest(BaseModel):
    """Optional hints for the extraction endpoint."""

    document_type_hint: Literal["TDS", "SDS", "RPI", "CoA", "Brochure", "auto"] = "auto"


class CascadeInfo(BaseModel):
    """Metadata about the cascade/fallback flow."""

    cascade_triggered: bool = False
    primary_provider: str | None = Field(None, description="First provider tried (e.g. google)")
    primary_model: str | None = None
    primary_missing_count: int | None = Field(
        None, description="How many attributes the primary provider missed"
    )
    fallback_provider: str | None = Field(None, description="Fallback provider (e.g. anthropic)")
    fallback_model: str | None = None
    fallback_missing_count: int | None = Field(
        None, description="How many attributes the fallback provider missed"
    )
    threshold: int | None = Field(None, description="Missing-attribute threshold that triggered fallback")


class ExtractionResponse(BaseModel):
    """Response envelope for POST /extraction/extract."""

    success: bool
    result: ExtractionResult | None = None
    error: str | None = None
    processing_time_ms: int = 0
    provider: str | None = Field(None, description="LLM provider that produced the final result")
    model: str | None = Field(None, description="Model that produced the final result")
    cascade: CascadeInfo | None = Field(None, description="Cascade/fallback metadata (if enabled)")
    markdown_preview: str | None = None
