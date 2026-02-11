from __future__ import annotations

from datetime import date, datetime

import httpx
import structlog

from app.core.config import settings
from app.modules.events.schemas import RawArticle, SourceName
from app.modules.events.sources.base import BaseCollector

logger = structlog.get_logger()

# Vertex AI Search replaces the deprecated Google Custom Search JSON API
VERTEX_SEARCH_URL = (
    "https://discoveryengine.googleapis.com/v1/projects/{project_id}"
    "/locations/global/collections/default_collection"
    "/engines/{engine_id}/servingConfigs/default_search:searchLite"
)

# No need for "site:linkedin.com" — the Vertex data store already filters to linkedin.com
DEFAULT_QUERIES = [
    '"distribution agreement" chemical',
    '"authorized distributor" chemical',
    '"acquisition" chemical distribution',
    '"partnership" chemical supplier',
    '"appointed" chemical distributor',
]


class GoogleSearchCollector(BaseCollector):
    """Collects LinkedIn posts via Vertex AI Search (formerly Google CSE)."""

    def __init__(self, queries: list[str] | None = None, max_per_query: int = 10):
        self.queries = queries or DEFAULT_QUERIES
        self.max_per_query = max_per_query

    async def collect(self) -> list[RawArticle]:
        if not settings.vertex_search_engine_id or not settings.vertex_search_project_id:
            logger.warning(
                "google_search_skipped",
                reason="No Vertex AI Search engine ID or project ID configured",
            )
            return []

        if not settings.google_cse_api_key:
            logger.warning(
                "google_search_skipped",
                reason="No API key configured (GOOGLE_CSE_API_KEY)",
            )
            return []

        endpoint = VERTEX_SEARCH_URL.format(
            project_id=settings.vertex_search_project_id,
            engine_id=settings.vertex_search_engine_id,
        )

        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in self.queries:
                try:
                    resp = await client.post(
                        endpoint,
                        params={"key": settings.google_cse_api_key},
                        json={
                            "query": query,
                            "pageSize": min(self.max_per_query, 10),
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    for result in data.get("results", []):
                        struct = result.get("document", {}).get("derivedStructData", {})
                        url = struct.get("link", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)

                        # Extract snippet text
                        snippet = ""
                        snippets_list = struct.get("snippets", [])
                        if snippets_list:
                            snippet = snippets_list[0].get("snippet", "")

                        # Try og:description for richer content (LinkedIn posts)
                        metatags = struct.get("pagemap", {}).get("metatags", [])
                        if metatags:
                            og_desc = metatags[0].get("og:description", "")
                            if og_desc and len(og_desc) > len(snippet):
                                snippet = og_desc

                        articles.append(
                            RawArticle(
                                title=struct.get("title", ""),
                                url=url,
                                snippet=snippet,
                                source_name=SourceName.linkedin_via_google,
                                published_date=_parse_vertex_date(struct),
                            )
                        )
                except Exception:
                    logger.warning("google_search_query_failed", query=query, exc_info=True)
                    continue

        logger.info("google_search_collected", total=len(articles))
        return articles


def _parse_vertex_date(struct: dict) -> date | None:
    """Try to extract a date from Vertex AI Search metadata."""
    metatags = struct.get("pagemap", {}).get("metatags", [])
    if metatags:
        for tag in metatags:
            for key in ("article:published_time", "og:updated_time", "date"):
                val = tag.get(key)
                if val:
                    try:
                        return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
                    except (ValueError, TypeError):
                        continue
    return None
