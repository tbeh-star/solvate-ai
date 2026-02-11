from __future__ import annotations

import json
from abc import ABC, abstractmethod

import structlog

from app.core.config import settings
from app.modules.events.schemas import ExtractedEvent, RawArticle

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are an expert chemical industry analyst specializing in distribution agreements, mergers & acquisitions, partnerships, and supply chain events.

You will receive an article title and snippet. Analyze it and extract structured event data.

Return a JSON object with these fields:
{
  "is_relevant": true/false,  // false if NOT related to chemical industry events
  "event_title": "Short descriptive title",
  "event_type": "distribution_agreement|acquisition|partnership|force_majeure|plant_shutdown|capacity_expansion|regulatory_change|supply_disruption|price_change|other",
  "companies": ["Company A", "Company B"],
  "company_roles": {"supplier": "Company A", "distributor": "Company B"},
  "products": ["Product Name"],
  "segments": ["Coatings", "Personal Care"],
  "regions": ["UK", "Ireland"],
  "event_date": "2024-02-15",  // ISO format or null
  "summary": "2-3 sentence summary of the event",
  "confidence": 0.85,  // 0.0-1.0 how confident you are in the extraction

  // Enriched deal details (null if not available in source text):
  "is_exclusive": true,  // whether the agreement is exclusive, null if unknown
  "deal_value": "$50M",  // reported deal value, null if not mentioned
  "deal_duration": "3 years",  // contract duration, null if not mentioned
  "effective_date": "2024-03-01",  // when the deal takes effect, null if not mentioned
  "geographic_scope": "UK and Ireland",  // specific territory, null if not mentioned
  "exec_quotes": [
    {"name": "John Smith", "title": "CEO", "company": "OQEMA", "quote": "We are thrilled to continue..."}
  ],  // exact quotes from executives, empty array if none
  "key_people": [
    {"name": "Jane Doe", "title": "VP Sales", "company": "BASF"}
  ],  // involved executives mentioned, empty array if none
  "strategic_rationale": "This extends OQEMA's portfolio in specialty amines across the UK market"  // why the deal matters, null if not clear
}

Rules:
- Set is_relevant to false for articles not about chemical/specialty chemical industry events
- For irrelevant articles, still return the full JSON but with empty/null values
- company_roles keys should be: supplier, distributor, acquirer, target, partner, or other descriptive roles
- Only include exec_quotes with EXACT quotes from the source text, never fabricate quotes
- Set null for any enriched field where the information is not available in the source
- Dates should be ISO format (YYYY-MM-DD) or null
- confidence should reflect how much useful data you could extract (0.0-1.0)"""

# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "google": "gemini-2.0-flash",
}


# --- LLM Client abstraction ---


class LLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def extract_json(self, system_prompt: str, user_content: str) -> dict | None:
        """Send a prompt and return parsed JSON response, or None on failure."""
        ...


class OpenAIClient(LLMClient):
    async def extract_json(self, system_prompt: str, user_content: str) -> dict | None:
        from openai import AsyncOpenAI

        model = _resolve_model("openai")
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        return json.loads(content) if content else None


class AnthropicClient(LLMClient):
    async def extract_json(self, system_prompt: str, user_content: str) -> dict | None:
        from anthropic import AsyncAnthropic

        model = _resolve_model("anthropic")
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            temperature=0.1,
        )
        content = response.content[0].text if response.content else None
        if not content:
            return None
        # Strip markdown code fences if present
        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)


class GoogleClient(LLMClient):
    async def extract_json(self, system_prompt: str, user_content: str) -> dict | None:
        from google import genai

        model = _resolve_model("google")
        client = genai.Client(api_key=settings.google_ai_api_key)
        response = await client.aio.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\n{user_content}",
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        content = response.text
        return json.loads(content) if content else None


def _resolve_model(provider: str) -> str:
    """Resolve the model name: use llm_model if set, else provider default."""
    if settings.llm_model:
        return settings.llm_model
    # For openai, fall back to legacy openai_model setting
    if provider == "openai" and settings.openai_model:
        return settings.openai_model
    return DEFAULT_MODELS[provider]


def get_llm_client() -> LLMClient:
    """Factory: return the configured LLM client."""
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        return AnthropicClient()
    if provider == "google":
        return GoogleClient()
    return OpenAIClient()


# --- Extraction functions ---


async def extract_event(article: RawArticle) -> ExtractedEvent | None:
    """Extract a structured event from a single article using the configured LLM."""
    client = get_llm_client()

    user_content = f"Title: {article.title}\nURL: {article.url}\nSnippet: {article.snippet}"
    if article.published_date:
        user_content += f"\nPublished: {article.published_date.isoformat()}"

    try:
        data = await client.extract_json(SYSTEM_PROMPT, user_content)
        if not data:
            return None

        if not data.get("is_relevant", False):
            return None

        return ExtractedEvent.model_validate(data)

    except Exception:
        logger.warning(
            "extraction_failed",
            article_url=article.url,
            provider=settings.llm_provider,
            exc_info=True,
        )
        return None


async def extract_events_batch(
    articles: list[RawArticle],
) -> list[tuple[RawArticle, ExtractedEvent]]:
    """Extract events from a batch of articles. Returns (article, event) pairs for relevant ones."""
    results: list[tuple[RawArticle, ExtractedEvent]] = []

    for article in articles:
        event = await extract_event(article)
        if event is not None:
            results.append((article, event))

    logger.info(
        "extraction_batch_complete",
        total_articles=len(articles),
        relevant_events=len(results),
        provider=settings.llm_provider,
        model=_resolve_model(settings.llm_provider),
    )
    return results
