"""M3ndel Agent 2: Doc-Type-Specific Extractor Pool.

5 focused sub-extractors with doc-type-specific prompts (500-800 tokens each)
instead of the monolithic 2500-token prompt. Each sub-extractor produces a full
ExtractionResult dict with non-relevant fields set to null.

Sub-Extractors:
  - TDSExtractor:      15 focus fields (spec tables, physical props, grade)
  - SDSExtractor:      12 focus fields (GHS, CAS, Section 9/14/15)
  - RPIExtractor:       8 focus fields (inventories, certifications, blocked)
  - CoAExtractor:       5 focus fields (batch data, purity, CAS)
  - BrochureExtractor:  4 focus fields (product name, application, packaging)
"""

from __future__ import annotations

import structlog

from app.modules.extraction.agent_schemas import PartialExtraction
from app.modules.extraction.agents.base import BaseAgent
from app.modules.extraction.agents.sanitizer import sanitize_extraction_json
from app.modules.extraction.cost_tracker import CostTracker
from app.modules.extraction.schemas import ExtractionResult

logger = structlog.get_logger()

# JSON schema hint appended to all extractor prompts (shared across doc types)
_RESPONSE_SCHEMA_HINT = """
## JSON Schema (abbreviated)
{
  "document_info": {"document_type": "TDS|SDS|RPI|CoA|Brochure|unknown", "language": "en", "manufacturer": "...", "brand": "...", "revision_date": "...", "page_count": 0},
  "identity": {"product_name": "...", "product_line": "...", "wacker_sku": null, "material_numbers": [], "product_url": null, "grade": {"value": "...", "unit": null, "source_section": "...", "raw_string": "...", "confidence": "high|medium|low", "is_specification": false, "test_method": null}},
  "chemical": {"cas_numbers": {"value": "...", "unit": null, "source_section": "...", "raw_string": "...", "confidence": "high", "is_specification": true, "test_method": null}, "chemical_components": [], "chemical_synonyms": [], "purity": null},
  "physical": {"physical_form": null, "density": null, "flash_point": null, "temperature_range": null, "shelf_life": null, "cure_system": null},
  "application": {"main_application": null, "usage_restrictions": [], "packaging_options": []},
  "safety": {"ghs_statements": [], "un_number": null, "certifications": [], "global_inventories": [], "blocked_countries": [], "blocked_industries": []},
  "compliance": {"wiaw_status": null, "sales_advisory": null},
  "missing_attributes": ["attribute_name_1", "..."],
  "extraction_warnings": []
}

Each MendelFact object requires: value, source_section, raw_string, confidence. Optional: unit, is_specification, test_method.
"""


class DocTypeExtractor(BaseAgent):
    """Base class for doc-type-specific extractors."""

    agent_name = "Extractor"
    prompt_file: str = ""  # Override in subclasses

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        super().__init__(provider=provider, model=model, cost_tracker=cost_tracker)
        if self.prompt_file:
            base_prompt = self.load_prompt(self.prompt_file)
            self._system_prompt = f"{base_prompt}\n\n{_RESPONSE_SCHEMA_HINT}"
        else:
            self._system_prompt = _RESPONSE_SCHEMA_HINT

    def extract(
        self,
        markdown: str,
        doc_type: str,
        file_name: str = "",
    ) -> PartialExtraction:
        """Extract structured data from a document.

        Args:
            markdown: Full document markdown content.
            doc_type: Document type (TDS, SDS, RPI, CoA, Brochure).
            file_name: Original filename for logging.

        Returns:
            PartialExtraction with the extraction result and metadata.
        """
        user_content = (
            f"Extract all chemical product data from this {doc_type} document.\n\n"
            f"---\n\n{markdown}"
        )

        try:
            result = self.call_llm(
                system_prompt=self._system_prompt,
                user_content=user_content,
                response_json=True,
                file_name=file_name,
                doc_type=doc_type,
            )

            raw_data = result["content"]

            # Sanitize LLM output (fix common format errors)
            sanitized = sanitize_extraction_json(raw_data)

            # Validate through Pydantic
            extraction = ExtractionResult.model_validate(sanitized)
            extraction_dict = extraction.model_dump()

            # Determine which fields were extracted vs missing
            missing = extraction.missing_attributes
            # All 33 attribute names minus missing = extracted
            extracted = [f for f in _ALL_ATTRIBUTE_NAMES if f not in missing]

            logger.info(
                f"{self.agent_name} extraction complete",
                file=file_name,
                doc_type=doc_type,
                extracted_count=len(extracted),
                missing_count=len(missing),
            )

            return PartialExtraction(
                source_file=file_name,
                doc_type=doc_type,
                extraction_result=extraction_dict,
                extracted_fields=extracted,
                missing_fields=missing,
                warnings=extraction.extraction_warnings,
            )

        except Exception as e:
            logger.error(
                f"{self.agent_name} extraction failed",
                file=file_name,
                doc_type=doc_type,
                error=str(e),
            )
            return PartialExtraction(
                source_file=file_name,
                doc_type=doc_type,
                extraction_result={},
                extracted_fields=[],
                missing_fields=list(_ALL_ATTRIBUTE_NAMES),
                warnings=[f"Extraction error: {e}"],
            )


# ---------------------------------------------------------------------------
# Doc-type-specific extractors
# ---------------------------------------------------------------------------


class TDSExtractor(DocTypeExtractor):
    """Technical Data Sheet extractor — 15 focus fields."""
    agent_name = "TDS-Extractor"
    prompt_file = "extractor_tds.txt"


class SDSExtractor(DocTypeExtractor):
    """Safety Data Sheet extractor — 12 focus fields."""
    agent_name = "SDS-Extractor"
    prompt_file = "extractor_sds.txt"


class RPIExtractor(DocTypeExtractor):
    """Regulatory Product Information extractor — 8 focus fields."""
    agent_name = "RPI-Extractor"
    prompt_file = "extractor_rpi.txt"


class CoAExtractor(DocTypeExtractor):
    """Certificate of Analysis extractor — 5 focus fields."""
    agent_name = "CoA-Extractor"
    prompt_file = "extractor_coa.txt"


class BrochureExtractor(DocTypeExtractor):
    """Brochure / Marketing Material extractor — 4 focus fields."""
    agent_name = "Brochure-Extractor"
    prompt_file = "extractor_brochure.txt"


# ---------------------------------------------------------------------------
# Factory + Registry
# ---------------------------------------------------------------------------

# All 33 attribute names from the ExtractionResult schema
_ALL_ATTRIBUTE_NAMES = {
    # Identity
    "product_name", "product_line", "wacker_sku", "material_numbers",
    "product_url", "grade",
    # Chemical
    "cas_numbers", "chemical_components", "chemical_synonyms", "purity",
    # Physical
    "physical_form", "density", "flash_point", "temperature_range",
    "shelf_life", "cure_system",
    # Application
    "main_application", "usage_restrictions", "packaging_options",
    # Safety
    "ghs_statements", "un_number", "certifications", "global_inventories",
    "blocked_countries", "blocked_industries",
    # Compliance
    "wiaw_status", "sales_advisory",
    # Document Info
    "document_type", "language", "manufacturer", "brand", "revision_date",
    "page_count",
}

# Map doc_type -> extractor class
EXTRACTOR_REGISTRY: dict[str, type[DocTypeExtractor]] = {
    "TDS": TDSExtractor,
    "SDS": SDSExtractor,
    "RPI": RPIExtractor,
    "CoA": CoAExtractor,
    "Brochure": BrochureExtractor,
}


def get_extractor(
    doc_type: str,
    provider: str | None = None,
    model: str | None = None,
    cost_tracker: CostTracker | None = None,
) -> DocTypeExtractor:
    """Factory: get the appropriate extractor for a document type.

    Falls back to TDSExtractor for unknown doc types (most generic prompt).
    """
    cls = EXTRACTOR_REGISTRY.get(doc_type, TDSExtractor)
    return cls(provider=provider, model=model, cost_tracker=cost_tracker)
