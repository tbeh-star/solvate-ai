"""M3ndel Agent Contracts — Pydantic models for inter-agent communication.

Defines the data structures that flow between agents:
  Classifier -> Orchestrator:   ClassificationResult
  Extractor  -> Orchestrator:   PartialExtraction
  Orchestrator -> Merger:       ProductGroup
  Auditor    -> Orchestrator:   AuditResult
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent 1: Classifier output
# ---------------------------------------------------------------------------


class ClassificationResult(BaseModel):
    """Output of the Classifier agent — doc-type + brand detection."""

    doc_type: Literal["TDS", "SDS", "RPI", "CoA", "Brochure", "unknown"] = Field(
        ..., description="Detected document type"
    )
    brand: str | None = Field(
        None,
        description="Wacker brand: ELASTOSIL, FERMOPURE, GENIOSIL, BELSIL, POWERSIL, VINNAPAS",
    )
    product_name: str | None = Field(None, description="Primary product name if detected")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Classification confidence 0.0-1.0"
    )
    reasoning: str = Field(
        ..., description="Brief explanation of classification decision"
    )


# ---------------------------------------------------------------------------
# Agent 2: Extractor output
# ---------------------------------------------------------------------------


class PartialExtraction(BaseModel):
    """Output of a single doc-type-specific extractor.

    Contains the full ExtractionResult dict (all 33 attributes, nulls for
    non-relevant fields) plus metadata about what was actually extracted.
    """

    source_file: str = Field(..., description="Path or filename of the source PDF")
    doc_type: Literal["TDS", "SDS", "RPI", "CoA", "Brochure", "unknown"]
    extraction_result: dict = Field(
        ..., description="Full ExtractionResult as dict (validated via Pydantic)"
    )
    extracted_fields: list[str] = Field(
        default_factory=list,
        description="Field names that were actually populated",
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Field names that could not be extracted",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Extraction warnings or ambiguities",
    )
    audit_result: AuditResult | None = Field(
        default=None,
        description="Quality audit result, if this extraction was audited",
    )


# ---------------------------------------------------------------------------
# Agent 4: Merger input — groups partial extractions per product
# ---------------------------------------------------------------------------


class ProductGroup(BaseModel):
    """A group of partial extractions for the same product.

    The Merger combines these into a single Golden Record using the
    Truth Hierarchy: TDS(5) > CoA(4) > SDS(3) > RPI(2) > Brochure(1).
    """

    product_name: str = Field(..., description="Canonical product name")
    product_folder: str = Field(..., description="Filesystem folder path")
    brand: str = Field(default="", description="Wacker brand")
    partial_extractions: list[PartialExtraction] = Field(
        default_factory=list,
        description="All partial extractions for this product",
    )


# ---------------------------------------------------------------------------
# Agent 3: Auditor output
# ---------------------------------------------------------------------------


class AuditCorrection(BaseModel):
    """A single correction proposed by the Auditor."""

    field_name: str = Field(..., description="Attribute being corrected")
    original_value: str | None = Field(None, description="Value before correction")
    corrected_value: str | None = Field(None, description="Proposed corrected value")
    reason: str = Field(..., description="Why the correction is needed")
    source_quote: str | None = Field(
        None, description="Supporting quote from source document"
    )


class AuditResult(BaseModel):
    """Output of the Quality Auditor — cross-checks extraction against source."""

    corrections: list[AuditCorrection] = Field(
        default_factory=list,
        description="Proposed corrections to extracted values",
    )
    overall_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall quality score"
    )
    flagged_issues: list[str] = Field(
        default_factory=list,
        description="Issues that need human review",
    )
    pass_audit: bool = Field(
        ..., description="True if extraction passes quality threshold"
    )


# ---------------------------------------------------------------------------
# Truth Hierarchy — priority ranking per doc type
# ---------------------------------------------------------------------------

DOC_TYPE_PRIORITY: dict[str, int] = {
    "TDS": 5,       # Highest: spec tables
    "CoA": 4,       # Batch-tested values
    "SDS": 3,       # Safety/regulatory
    "RPI": 2,       # Inventory/compliance
    "Brochure": 1,  # Lowest: marketing
    "unknown": 0,
}

# Fields that are UNION-merged (all sources combined, no override)
UNION_MERGE_FIELDS = {
    "certifications",
    "global_inventories",
    "ghs_statements",
    "blocked_countries",
    "blocked_industries",
    "chemical_synonyms",
    "material_numbers",
    "extraction_warnings",
}
