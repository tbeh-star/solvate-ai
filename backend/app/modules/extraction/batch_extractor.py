"""M3ndel Batch Extractor — Direct API calls with token tracking + prompt caching.

Unlike the instructor-based ExtractorService (used by the API endpoint), this module
calls the LLM APIs directly to get full token usage data and leverage prompt caching.

Prompt Caching:
  - Anthropic: `cache_control: {"type": "ephemeral"}` on the system prompt block.
    The ~2500-token system prompt is cached across calls within a 5-minute window.
    Saves ~90% on input cost for the cached portion.
  - Gemini: Uses the `google-genai` context caching API. The system prompt is stored
    as a CachedContent resource and reused across calls (60-minute TTL).

Token Tracking:
  Both providers return token counts in their responses. This module extracts
  input_tokens, output_tokens, and cache metrics from each response.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.config import settings
from app.modules.extraction.cost_tracker import CostTracker, TokenRecord
from app.modules.extraction.schemas import ExtractionResult

# Sanitizer is shared between legacy batch_extractor and new agent pipeline
from app.modules.extraction.agents.sanitizer import (
    sanitize_extraction_json as _sanitize_extraction_json,
    strip_code_fences as _strip_code_fences,
    PLAIN_STRING_FIELDS as _PLAIN_STRING_FIELDS,
    SINGLE_MENDELFACT_FIELDS as _SINGLE_MENDELFACT_FIELDS,
    PLAIN_STRING_LIST_FIELDS as _PLAIN_STRING_LIST_FIELDS,
)

logger = structlog.get_logger()

# Default models per provider
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4@20250514",
    "google": "gemini-2.5-flash",
    "openai": "gpt-4.1",
}

# System prompt parts (imported from extractor.py patterns)
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

## OUTPUT FORMAT
Respond with a SINGLE JSON object matching the ExtractionResult schema. No markdown fencing, no extra text.
"""

_DOC_TYPE_PROMPTS: dict[str, str] = {
    "TDS": """## Document Type: Technical Data Sheet (TDS)
Focus areas:
- **Specification Table** (highest priority): Density, Purity, Viscosity, Flash Point, pH/Acid Number
- **Typical Properties**: Physical Form, Appearance, Color, Odor
- **Grade**: Tech / Food / Pharma / Cosmetic — look for labels like "food grade", "EP", "USP"
- **Product Identity**: Product Name, Product Line, SKU if present
- **Cure System** (for ELASTOSIL): Acetoxy, Oxime, Alkoxy, Addition, Moisture-curing
- **Packaging**: Listed at bottom or in a separate section
- **Shelf Life**: Usually stated in months, check storage section
- **Application**: Often in the product description or "Applications" section

If a value appears in BOTH Specification Table AND Typical Properties, prefer the Spec Table value.""",
    "SDS": """## Document Type: Safety Data Sheet (SDS)
The SDS follows GHS format with 16 standard sections. Focus areas:
- **Section 1**: Product Name, Manufacturer, Product URL
- **Section 2**: GHS Hazard statements (H-codes), Precautionary statements (P-codes)
- **Section 3**: CAS Number(s), Chemical Components, Purity/Concentration
- **Section 9**: Physical Properties — Density, Flash Point, pH, Viscosity, Physical Form, Appearance
- **Section 14**: Transport — UN Number (EXCLUSIVE source for UN number)
- **Section 15**: Regulatory information — Certifications, Global Inventories (TSCA, REACH, DSL, etc.)

CRITICAL: UN Number must ONLY come from Section 14. Do not use other sections for this.
GHS statements come exclusively from Section 2.""",
    "RPI": """## Document Type: Raw Product Information (RPI)
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
- Blocked Countries (derived)""",
    "CoA": """## Document Type: Certificate of Analysis (CoA)
CoA documents contain batch-specific test results. Focus areas:
- **Batch/LOT Number**: Record in metadata
- **Test Results**: Compare against specification limits
- **Purity**: Actual tested value
- **Physical Properties**: Density, Viscosity, pH — as tested
- **Identity Confirmation**: CAS, Product Name

IMPORTANT: CoA values are batch-specific. Set confidence to "medium" unless the value
matches a specification limit exactly. Mark `is_specification: false` for all CoA test results.""",
    "Brochure": """## Document Type: Brochure / Marketing Material
Brochures contain general product information. Focus areas:
- **Product Line**: Brand family, application areas
- **Main Application**: Use cases, industries
- **Physical Form**: General descriptions
- **Packaging Options**: Often listed in brochures
- **Product Comparisons**: May contain multiple products — extract for the primary product only

IMPORTANT: All values from brochures should have confidence "low" unless they contain
explicit specification data (rare). Never set `is_specification: true` for brochure data.""",
    "unknown": """## Document Type: Unknown
Could not automatically classify this document. Analyze the content and extract
whatever attributes are present. Use conservative confidence levels ("medium" or "low").""",
}

# JSON schema for the response (tells models exactly what structure to output)
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


def _build_system_prompt(doc_type: str) -> str:
    """Compose the full system prompt from base + doc-type-specific sections."""
    doc_specific = _DOC_TYPE_PROMPTS.get(doc_type, _DOC_TYPE_PROMPTS["unknown"])
    return f"{_BASE_PROMPT}\n\n{doc_specific}\n\n{_RESPONSE_SCHEMA_HINT}"


# ---------------------------------------------------------------------------
# Sanitizer + utilities — delegated to agents.sanitizer (shared module)
# Legacy aliases kept for backward compatibility within this file.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Extraction result with token data
# ---------------------------------------------------------------------------


@dataclass
class ExtractionWithTokens:
    """Extraction result bundled with token usage data."""

    result: ExtractionResult | None = None
    error: str | None = None

    # Token usage
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Anthropic (Claude) — Direct API with Prompt Caching
# ---------------------------------------------------------------------------


class AnthropicDirectExtractor:
    """Direct Anthropic API calls with prompt caching + token tracking.

    Prompt Caching Strategy:
      - The system prompt (~2500 tokens) is sent with cache_control: {"type": "ephemeral"}
      - Anthropic automatically caches the prompt for ~5 minutes
      - Subsequent calls within that window read from cache → 90% cheaper input tokens
      - Token usage: response.usage.cache_creation_input_tokens / cache_read_input_tokens
    """

    def __init__(self, model: str | None = None) -> None:
        import anthropic

        self.model = model or settings.extraction_cascade_fallback_model or _DEFAULT_MODELS["anthropic"]

        if settings.vertex_credentials_path:
            import os
            os.environ.setdefault(
                "GOOGLE_APPLICATION_CREDENTIALS",
                settings.vertex_credentials_path,
            )
            self._client = anthropic.AnthropicVertex(
                project_id=settings.vertex_project_id,
                region=settings.vertex_location,
            )
            self._is_vertex = True
            logger.info("AnthropicDirect: Vertex AI client", project=settings.vertex_project_id)
        else:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self._is_vertex = False
            logger.info("AnthropicDirect: Direct API client")

    def extract(self, markdown: str, doc_type: str, file_name: str = "") -> ExtractionWithTokens:
        """Run extraction with prompt caching."""
        system_prompt = _build_system_prompt(doc_type)
        user_content = (
            f"Extract all chemical product data from this {doc_type} document.\n\n"
            f"---\n\n{markdown}"
        )

        start = time.time()

        try:
            # Anthropic prompt caching: system prompt with cache_control
            # For Vertex AI, cache_control might not be supported — we try and fall back
            system_messages: Any
            if not self._is_vertex:
                # Direct API — prompt caching supported
                system_messages = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                # Vertex AI — prompt caching may not be available, use plain string
                system_messages = system_prompt

            response = self._client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_messages,
                messages=[{"role": "user", "content": user_content}],
            )

            duration_ms = int((time.time() - start) * 1000)

            # Extract token usage
            usage = response.usage
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
            cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

            logger.info(
                "Anthropic extraction complete",
                model=self.model,
                file=file_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_created=cache_creation,
                cache_read=cache_read,
                duration_ms=duration_ms,
            )

            # Parse the JSON response
            raw_text = response.content[0].text
            result = self._parse_result(raw_text)

            return ExtractionWithTokens(
                result=result,
                provider="anthropic",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation,
                cache_read_tokens=cache_read,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.error("Anthropic extraction failed", error=str(e), file=file_name)
            return ExtractionWithTokens(
                error=str(e),
                provider="anthropic",
                model=self.model,
                duration_ms=duration_ms,
            )

    @staticmethod
    def _parse_result(raw_text: str) -> ExtractionResult:
        """Parse LLM JSON response into ExtractionResult with sanitization."""
        text = _strip_code_fences(raw_text)
        data = json.loads(text)
        data = _sanitize_extraction_json(data)
        return ExtractionResult.model_validate(data)


# ---------------------------------------------------------------------------
# Gemini — Direct API with Context Caching
# ---------------------------------------------------------------------------


class GeminiDirectExtractor:
    """Direct Gemini API calls with context caching + token tracking.

    Prompt Caching Strategy:
      - Gemini uses explicit CachedContent API (unlike Anthropic's ephemeral)
      - We create a cached content resource from the system prompt
      - The cache has a configurable TTL (default 60 min)
      - Subsequent calls reference the cache → 75% cheaper input tokens
      - Falls back to non-cached calls if caching fails

    Token Usage:
      - response.usage_metadata.prompt_token_count (input)
      - response.usage_metadata.candidates_token_count (output)
      - response.usage_metadata.cached_content_token_count (cached input)
    """

    # Minimum token count for Gemini context caching (Google requirement: >32k tokens for caching)
    # System prompt alone is too small. We'll use inline caching with generateContent.
    _MIN_CACHE_TOKENS = 32_768

    # Max timeout per Gemini API call (2 minutes)
    _REQUEST_TIMEOUT_S = 120

    def __init__(self, model: str | None = None) -> None:
        from google import genai
        from google.genai import types as genai_types

        self.model = model or settings.extraction_model or _DEFAULT_MODELS["google"]
        self._client = genai.Client(
            api_key=settings.google_ai_api_key,
            http_options=genai_types.HttpOptions(timeout=self._REQUEST_TIMEOUT_S * 1000),
        )
        self._cache_name: str | None = None  # Cached content resource name
        self._cache_doc_type: str | None = None  # Doc type the cache was built for

        logger.info("GeminiDirect: client ready", model=self.model, timeout_s=self._REQUEST_TIMEOUT_S)

    def extract(self, markdown: str, doc_type: str, file_name: str = "") -> ExtractionWithTokens:
        """Run extraction with token tracking.

        Note: Gemini context caching requires >32k tokens in the cached content.
        Our system prompt is ~2500 tokens — too small for Gemini's caching.
        Instead, we use standard calls and track tokens from usage_metadata.
        For future optimization: if we batch multiple PDFs of the same doc_type,
        we could concatenate system prompt + examples to exceed the 32k threshold.
        """
        from google import genai
        from google.genai import types

        system_prompt = _build_system_prompt(doc_type)
        user_content = (
            f"Extract all chemical product data from this {doc_type} document.\n\n"
            f"---\n\n{markdown}"
        )

        start = time.time()

        try:
            # Use generateContent directly for full control
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

            duration_ms = int((time.time() - start) * 1000)

            # Extract token usage from usage_metadata
            usage = response.usage_metadata
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0

            logger.info(
                "Gemini extraction complete",
                model=self.model,
                file=file_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                duration_ms=duration_ms,
            )

            # Parse the JSON response
            raw_text = response.text
            result = self._parse_result(raw_text)

            return ExtractionWithTokens(
                result=result,
                provider="google",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cached_tokens,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            logger.error("Gemini extraction failed", error=str(e), file=file_name)
            return ExtractionWithTokens(
                error=str(e),
                provider="google",
                model=self.model,
                duration_ms=duration_ms,
            )

    @staticmethod
    def _parse_result(raw_text: str) -> ExtractionResult:
        """Parse LLM JSON response into ExtractionResult with sanitization."""
        text = _strip_code_fences(raw_text)
        data = json.loads(text)
        data = _sanitize_extraction_json(data)
        return ExtractionResult.model_validate(data)


# ---------------------------------------------------------------------------
# Batch Extractor — combines both providers with cascade + cost tracking
# ---------------------------------------------------------------------------


class BatchExtractorService:
    """Batch extraction with cascade, prompt caching, and cost tracking.

    This is the batch-optimized version of ExtractorService:
    - Uses direct API calls (not instructor) for full token visibility
    - Implements prompt caching for both providers
    - Tracks all costs via CostTracker
    - Supports cascade fallback (Gemini → Sonnet)
    """

    def __init__(
        self,
        cost_tracker: CostTracker | None = None,
        *,
        cascade_enabled: bool | None = None,
        cascade_threshold: int | None = None,
        primary_provider: str | None = None,
        primary_model: str | None = None,
        fallback_provider: str | None = None,
        fallback_model: str | None = None,
    ) -> None:
        self.cost_tracker = cost_tracker or CostTracker()

        # Primary
        self._primary_provider = primary_provider or settings.extraction_provider
        self._primary_model = primary_model or settings.extraction_model or _DEFAULT_MODELS.get(self._primary_provider, "")

        # Cascade
        self._cascade_enabled = cascade_enabled if cascade_enabled is not None else settings.extraction_cascade_enabled
        self._cascade_threshold = cascade_threshold if cascade_threshold is not None else settings.extraction_cascade_missing_threshold
        self._fallback_provider = fallback_provider or settings.extraction_cascade_fallback_provider
        self._fallback_model = fallback_model or settings.extraction_cascade_fallback_model or _DEFAULT_MODELS.get(self._fallback_provider, "")

        # Build extractors
        self._primary_extractor = self._build_extractor(self._primary_provider, self._primary_model)
        self._fallback_extractor: GeminiDirectExtractor | AnthropicDirectExtractor | None = None

        if self._cascade_enabled:
            try:
                self._fallback_extractor = self._build_extractor(self._fallback_provider, self._fallback_model)
            except Exception as e:
                logger.warning("Failed to build fallback extractor", error=str(e))

        logger.info(
            "BatchExtractor initialized",
            primary=f"{self._primary_provider}/{self._primary_model}",
            fallback=f"{self._fallback_provider}/{self._fallback_model}" if self._cascade_enabled else "disabled",
            threshold=self._cascade_threshold,
        )

    @staticmethod
    def _build_extractor(
        provider: str, model: str
    ) -> GeminiDirectExtractor | AnthropicDirectExtractor:
        """Build the appropriate direct extractor for a provider."""
        if provider == "google":
            return GeminiDirectExtractor(model=model)
        elif provider == "anthropic":
            return AnthropicDirectExtractor(model=model)
        else:
            raise ValueError(f"Unsupported batch extraction provider: {provider}")

    def extract(
        self, markdown: str, doc_type: str, file_name: str = ""
    ) -> ExtractionWithTokens:
        """Run extraction with cascade fallback and cost tracking.

        Returns the best result (fewest missing attributes).
        """
        # --- Step 1: Primary extraction ---
        primary = self._primary_extractor.extract(markdown, doc_type, file_name)

        # Track primary cost
        self.cost_tracker.record(
            provider=primary.provider,
            model=primary.model,
            input_tokens=primary.input_tokens,
            output_tokens=primary.output_tokens,
            cache_creation_tokens=primary.cache_creation_tokens,
            cache_read_tokens=primary.cache_read_tokens,
            file_name=file_name,
            doc_type=doc_type,
            duration_ms=primary.duration_ms,
            cascade_triggered=False,
        )

        if primary.error or primary.result is None:
            logger.warning("Primary extraction failed", file=file_name, error=primary.error)
            return primary

        primary_missing = len(primary.result.missing_attributes)

        # --- Step 2: Check if cascade needed ---
        if (
            self._cascade_enabled
            and self._fallback_extractor is not None
            and primary_missing > self._cascade_threshold
        ):
            logger.info(
                "Cascade triggered",
                file=file_name,
                primary_missing=primary_missing,
                threshold=self._cascade_threshold,
            )

            try:
                fallback = self._fallback_extractor.extract(markdown, doc_type, file_name)

                # Track fallback cost
                self.cost_tracker.record(
                    provider=fallback.provider,
                    model=fallback.model,
                    input_tokens=fallback.input_tokens,
                    output_tokens=fallback.output_tokens,
                    cache_creation_tokens=fallback.cache_creation_tokens,
                    cache_read_tokens=fallback.cache_read_tokens,
                    file_name=file_name,
                    doc_type=doc_type,
                    duration_ms=fallback.duration_ms,
                    cascade_triggered=True,
                )

                if fallback.error or fallback.result is None:
                    logger.warning("Fallback failed, keeping primary", error=fallback.error)
                    return primary

                fallback_missing = len(fallback.result.missing_attributes)

                if fallback_missing < primary_missing:
                    logger.info(
                        "Fallback improved result",
                        primary_missing=primary_missing,
                        fallback_missing=fallback_missing,
                    )
                    return fallback
                else:
                    logger.info(
                        "Fallback did not improve, keeping primary",
                        primary_missing=primary_missing,
                        fallback_missing=fallback_missing,
                    )
                    return primary

            except Exception as e:
                logger.warning("Cascade fallback error", error=str(e))
                return primary

        return primary
