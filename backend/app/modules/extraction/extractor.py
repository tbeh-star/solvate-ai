"""M3ndel Extractor Service — Multi-provider LLM extraction via Instructor.

Supports cascade mode: try cheap provider first (e.g. Gemini Flash),
automatically fall back to quality provider (e.g. Claude Sonnet) when
too many attributes are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import instructor
import structlog

from app.core.config import settings
from app.modules.extraction.schemas import CascadeInfo, ExtractionResult

logger = structlog.get_logger()

# Default models per provider (used when extraction_model is not explicitly set for the provider)
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4@20250514",  # Sonnet 4 via Vertex AI (15k quota)
    "google": "gemini-2.5-flash",
    "openai": "gpt-4.1",
}

# ---------------------------------------------------------------------------
# System prompts per document type
# ---------------------------------------------------------------------------

_BASE_PROMPT = """\
You are a Senior Chemical Data Analyst at Nordmann, a global chemical distributor.
Your task is to extract structured product data from the document below.

## Rules
- Extract ONLY facts explicitly stated in the document. Never infer or guess.
- For each extracted value, record the exact source section and original text quote.
- Confidence levels:
  - "high": Value comes from a specification table or clearly labeled field.
  - "medium": Value comes from flowing text or typical properties.
  - "low": Value is derived, implied, or from marketing material.
- Mark `is_specification: true` only for guaranteed spec values (not typical).
- CAS number is the primary key. Always extract it if present.
- Density is optional — set to null for powders/solids where not applicable.

## Truth Hierarchy (when conflicting values appear)
1. TDS Specification Table (highest priority)
2. TDS Typical Properties
3. SDS (Safety Data Sheet)
4. RPI (Raw Product Information)
5. Brochure / Marketing (lowest priority)

## Grade Classification
Pharma (EP+USP) > Infant Food > Food > Cosmetic > Technical

## Wacker Brand Logic
- ELASTOSIL: Silicone sealants/adhesives → look for Cure System, Movement Capability, Modulus
- FERMOPURE: Compendial grades → look for Loss on Drying, Endotoxin, Microbiological limits
- GENIOSIL: Silane-based → look for Viscosity, Alkoxy Type, Hydrolysis Products
- POWERSIL: High-performance silicones → look for RPI data, Global Inventories
- BELSIL: Personal care silicones → look for INCI name, Cosmetic certifications
- VINNAPAS: Construction polymers → look for Ash Content, Bulk Density, Film properties

## Target Attributes (33 fields)
### Identity: Product Name, Product Line, Wacker SKU, Material Numbers, Product URL, Grade
### Chemical: CAS Numbers, Chemical Components, Chemical Synonyms, Purity
### Physical: Physical Form, Density, Flash Point, Temperature Range, Shelf Life, Cure System
### Application: Main Application, Usage Restrictions, Packaging Options
### Safety: GHS Statements (H+P), UN Number (SDS Sec 14 only), Certifications, Global Inventories, Blocked Countries, Blocked Industries
### Compliance: WIAW Status, Sales Advisory
### Quality: list all attributes NOT found in `missing_attributes`

For any attribute not found in this document, add its name to `missing_attributes`.
Add warnings to `extraction_warnings` for ambiguous values or conflicts.
"""

_TDS_PROMPT = """\
## Document Type: Technical Data Sheet (TDS)
Focus areas:
- **Specification Table** (highest priority): Density, Purity, Viscosity, Flash Point, pH/Acid Number
- **Typical Properties**: Physical Form, Appearance, Color, Odor
- **Grade**: Tech / Food / Pharma / Cosmetic — look for labels like "food grade", "EP", "USP"
- **Product Identity**: Product Name, Product Line, SKU if present
- **Cure System** (for ELASTOSIL): Acetoxy, Oxime, Alkoxy, Addition, Moisture-curing
- **Packaging**: Listed at bottom or in a separate section
- **Shelf Life**: Usually stated in months, check storage section
- **Application**: Often in the product description or "Applications" section

If a value appears in BOTH Specification Table AND Typical Properties, prefer the Spec Table value.
"""

_SDS_PROMPT = """\
## Document Type: Safety Data Sheet (SDS)
The SDS follows GHS format with 16 standard sections. Focus areas:
- **Section 1**: Product Name, Manufacturer, Product URL
- **Section 2**: GHS Hazard statements (H-codes), Precautionary statements (P-codes)
- **Section 3**: CAS Number(s), Chemical Components, Purity/Concentration
- **Section 9**: Physical Properties — Density, Flash Point, pH, Viscosity, Physical Form, Appearance
- **Section 14**: Transport — UN Number (EXCLUSIVE source for UN number)
- **Section 15**: Regulatory information — Certifications, Global Inventories (TSCA, REACH, DSL, etc.)

CRITICAL: UN Number must ONLY come from Section 14. Do not use other sections for this.
GHS statements come exclusively from Section 2.
"""

_RPI_PROMPT = """\
## Document Type: Raw Product Information (RPI)
RPI documents contain regulatory and compliance data. Focus areas:
- **Global Chemical Inventories**: TSCA, REACH, IECSC, K-REACH, DSL, NDSL, ENCS, ISHL, AICS, NZIoC, PICCS, TCSI, CICR
- **Certifications**: FDA, NSF, Halal, Kosher, REACH registered, etc.
- **Regulatory Status**: Listed/Not Listed per country inventory
- **Product Identity**: Product Name, CAS Number
- **Blocked Countries**: Derive from inventories where product is NOT listed
- **Usage Restrictions**: Any stated limitations

RPI data has lower priority than TDS/SDS for physical properties but is the PRIMARY source for:
- Global Inventories
- Regulatory compliance status
- Blocked Countries (derived)
"""

_COA_PROMPT = """\
## Document Type: Certificate of Analysis (CoA)
CoA documents contain batch-specific test results. Focus areas:
- **Batch/LOT Number**: Record in metadata
- **Test Results**: Compare against specification limits
- **Purity**: Actual tested value
- **Physical Properties**: Density, Viscosity, pH — as tested
- **Identity Confirmation**: CAS, Product Name

IMPORTANT: CoA values are batch-specific. Set confidence to "medium" unless the value
matches a specification limit exactly. Mark `is_specification: false` for all CoA test results.
"""

_BROCHURE_PROMPT = """\
## Document Type: Brochure / Marketing Material
Brochures contain general product information. Focus areas:
- **Product Line**: Brand family, application areas
- **Main Application**: Use cases, industries
- **Physical Form**: General descriptions
- **Packaging Options**: Often listed in brochures
- **Product Comparisons**: May contain multiple products — extract for the primary product only

IMPORTANT: All values from brochures should have confidence "low" unless they contain
explicit specification data (rare). Never set `is_specification: true` for brochure data.
"""

_UNKNOWN_PROMPT = """\
## Document Type: Unknown
Could not automatically classify this document. Analyze the content and extract
whatever attributes are present. Use conservative confidence levels ("medium" or "low").
"""

_DOC_TYPE_PROMPTS: dict[str, str] = {
    "TDS": _TDS_PROMPT,
    "SDS": _SDS_PROMPT,
    "RPI": _RPI_PROMPT,
    "CoA": _COA_PROMPT,
    "Brochure": _BROCHURE_PROMPT,
    "unknown": _UNKNOWN_PROMPT,
}


# ---------------------------------------------------------------------------
# Extractor Service
# ---------------------------------------------------------------------------


@dataclass
class _ProviderSpec:
    """Internal: describes one LLM provider + model combo.

    Client can be None initially (lazy init for fallback — avoids requiring
    API keys for providers that may never be used).
    """

    provider: str
    model: str
    client: Any = field(default=None, repr=False)


class ExtractorService:
    """Multi-provider LLM extraction service with optional cascade.

    Cascade mode (default ON):
      1. Try the primary provider (cheap — e.g. Gemini Flash).
      2. Count missing_attributes in the result.
      3. If missing > threshold → auto-retry with the fallback provider (quality — e.g. Claude Sonnet).
      4. Return whichever result has fewer missing attributes.

    Provider is selected via EXTRACTION_PROVIDER env var.
    Cascade is configured via EXTRACTION_CASCADE_* env vars.
    """

    def __init__(self) -> None:
        # Primary provider
        primary_provider = settings.extraction_provider
        primary_model = settings.extraction_model or _DEFAULT_MODELS.get(primary_provider, "")
        self._primary = _ProviderSpec(
            provider=primary_provider,
            model=primary_model,
            client=self._build_client(primary_provider),
        )

        # Cascade / fallback
        self._cascade_enabled = settings.extraction_cascade_enabled
        self._cascade_threshold = settings.extraction_cascade_missing_threshold
        self._fallback: _ProviderSpec | None = None

        if self._cascade_enabled:
            fb_provider = settings.extraction_cascade_fallback_provider
            fb_model = (
                settings.extraction_cascade_fallback_model
                or _DEFAULT_MODELS.get(fb_provider, "")
            )
            # Only register fallback if it differs from primary
            # Client is built lazily on first use (avoids requiring API key upfront)
            if fb_provider != primary_provider or fb_model != primary_model:
                self._fallback = _ProviderSpec(
                    provider=fb_provider,
                    model=fb_model,
                    client=None,  # lazy — built on first cascade trigger
                )

        self._max_retries = settings.extraction_max_retries

        # Track which provider produced the final result
        self._final_provider = primary_provider
        self._final_model = primary_model
        self._cascade_info: CascadeInfo | None = None

    # --- Public properties ---------------------------------------------------

    @property
    def provider(self) -> str:
        """Return the provider that produced the final result."""
        return self._final_provider

    @property
    def model(self) -> str:
        """Return the model that produced the final result."""
        return self._final_model

    @property
    def cascade_info(self) -> CascadeInfo | None:
        """Return cascade metadata (None if cascade disabled or not triggered)."""
        return self._cascade_info

    # --- Main extraction with cascade ----------------------------------------

    def extract(self, markdown: str, doc_type: str) -> ExtractionResult:
        """Run structured extraction with optional cascade fallback.

        Args:
            markdown: Full markdown text from pdf_service.parse_pdf().
            doc_type: Detected document type (TDS, SDS, RPI, CoA, Brochure, unknown).

        Returns:
            ExtractionResult with all 33 attributes populated or listed as missing.
        """
        system_prompt = self._build_system_prompt(doc_type)
        user_content = (
            f"Extract all chemical product data from this {doc_type} document.\n\n"
            f"---\n\n{markdown}"
        )

        # --- Step 1: Primary extraction ---
        logger.info(
            "Cascade: primary extraction",
            provider=self._primary.provider,
            model=self._primary.model,
            doc_type=doc_type,
            markdown_chars=len(markdown),
        )

        primary_result = self._run_extraction(self._primary, system_prompt, user_content)
        primary_missing = len(primary_result.missing_attributes)

        logger.info(
            "Cascade: primary result",
            provider=self._primary.provider,
            missing=primary_missing,
            threshold=self._cascade_threshold,
        )

        # --- Step 2: Decide if fallback is needed ---
        if (
            self._cascade_enabled
            and self._fallback is not None
            and primary_missing > self._cascade_threshold
        ):
            logger.info(
                "Cascade: fallback triggered",
                reason=f"{primary_missing} missing > threshold {self._cascade_threshold}",
                fallback_provider=self._fallback.provider,
                fallback_model=self._fallback.model,
            )

            try:
                fallback_result = self._run_extraction(
                    self._fallback, system_prompt, user_content
                )
                fallback_missing = len(fallback_result.missing_attributes)

                logger.info(
                    "Cascade: fallback result",
                    provider=self._fallback.provider,
                    missing=fallback_missing,
                )

                # Use whichever result has fewer missing attributes
                if fallback_missing < primary_missing:
                    self._final_provider = self._fallback.provider
                    self._final_model = self._fallback.model
                    final_result = fallback_result
                else:
                    # Fallback didn't improve — keep primary
                    self._final_provider = self._primary.provider
                    self._final_model = self._primary.model
                    final_result = primary_result
                    logger.info(
                        "Cascade: fallback did not improve, keeping primary result",
                        primary_missing=primary_missing,
                        fallback_missing=fallback_missing,
                    )

                self._cascade_info = CascadeInfo(
                    cascade_triggered=True,
                    primary_provider=self._primary.provider,
                    primary_model=self._primary.model,
                    primary_missing_count=primary_missing,
                    fallback_provider=self._fallback.provider,
                    fallback_model=self._fallback.model,
                    fallback_missing_count=fallback_missing,
                    threshold=self._cascade_threshold,
                )

                return final_result

            except Exception as fb_exc:
                # Fallback failed (e.g. missing API key) — keep primary result
                logger.warning(
                    "Cascade: fallback failed, keeping primary result",
                    fallback_provider=self._fallback.provider,
                    error=str(fb_exc),
                )
                self._final_provider = self._primary.provider
                self._final_model = self._primary.model
                self._cascade_info = CascadeInfo(
                    cascade_triggered=True,
                    primary_provider=self._primary.provider,
                    primary_model=self._primary.model,
                    primary_missing_count=primary_missing,
                    fallback_provider=self._fallback.provider,
                    fallback_model=self._fallback.model,
                    fallback_missing_count=None,  # failed
                    threshold=self._cascade_threshold,
                )
                primary_result.extraction_warnings.append(
                    f"Cascade fallback to {self._fallback.provider} failed: {fb_exc}"
                )
                return primary_result

        # --- No fallback needed ---
        self._final_provider = self._primary.provider
        self._final_model = self._primary.model

        if self._cascade_enabled and self._fallback is not None:
            # Cascade was available but not triggered
            self._cascade_info = CascadeInfo(
                cascade_triggered=False,
                primary_provider=self._primary.provider,
                primary_model=self._primary.model,
                primary_missing_count=primary_missing,
                threshold=self._cascade_threshold,
            )

        return primary_result

    # --- Provider client factory ---------------------------------------------

    @staticmethod
    def _build_client(provider: str) -> Any:
        """Build the instructor client for a given provider."""
        if provider == "anthropic":
            import anthropic

            if settings.vertex_credentials_path:
                # Claude via Google Cloud Vertex AI (service account auth)
                import os

                os.environ.setdefault(
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    settings.vertex_credentials_path,
                )
                raw = anthropic.AnthropicVertex(
                    project_id=settings.vertex_project_id,
                    region=settings.vertex_location,
                )
                logger.info(
                    "Built Anthropic client via Vertex AI",
                    project=settings.vertex_project_id,
                    region=settings.vertex_location,
                )
            else:
                # Claude direct via Anthropic API
                raw = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                logger.info("Built Anthropic client via direct API")

            return instructor.from_anthropic(raw)
        elif provider == "google":
            from google import genai

            return instructor.from_genai(
                genai.Client(api_key=settings.google_ai_api_key),
                mode=instructor.Mode.GENAI_TOOLS,
            )
        elif provider == "openai":
            import openai

            return instructor.from_openai(
                openai.OpenAI(api_key=settings.openai_api_key)
            )
        else:
            raise ValueError(f"Unknown extraction provider: {provider}")

    # --- Low-level extraction per provider -----------------------------------

    def _run_extraction(
        self, spec: _ProviderSpec, system_prompt: str, user_content: str
    ) -> ExtractionResult:
        """Run extraction against a specific provider/model."""
        # Lazy client init (for fallback providers)
        if spec.client is None:
            spec.client = self._build_client(spec.provider)

        if spec.provider == "anthropic":
            return spec.client.messages.create(
                model=spec.model,
                max_tokens=8192,
                max_retries=self._max_retries,
                messages=[{"role": "user", "content": user_content}],
                system=system_prompt,
                response_model=ExtractionResult,
            )
        else:
            # OpenAI + Gemini compatible API
            return spec.client.chat.completions.create(
                model=spec.model,
                max_retries=self._max_retries,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_model=ExtractionResult,
            )

    # --- System prompt builder -----------------------------------------------

    @staticmethod
    def _build_system_prompt(doc_type: str) -> str:
        """Compose the full system prompt from base + doc-type-specific sections."""
        doc_specific = _DOC_TYPE_PROMPTS.get(doc_type, _UNKNOWN_PROMPT)
        return f"{_BASE_PROMPT}\n\n{doc_specific}"
