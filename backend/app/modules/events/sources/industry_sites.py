from __future__ import annotations

import httpx
import structlog
from bs4 import BeautifulSoup

from app.modules.events.schemas import RawArticle, SourceName
from app.modules.events.sources.base import BaseCollector

logger = structlog.get_logger()

# Newsroom URLs for key chemical companies
INDUSTRY_SOURCES: list[dict] = [
    {
        "name": "Brenntag Corporate",
        "url": "https://corporate.brenntag.com/en/media/news/",
        "selector": ".news-card",
        "title_selector": ".news-card--body--link span",
        "snippet_selector": ".news-card--body--text",
        "link_selector": ".news-card--body--link",
        "base_url": "https://corporate.brenntag.com",
    },
    {
        "name": "Brenntag US",
        "url": "https://www.brenntag.com/en-us/media/news/",
        "selector": ".news-card",
        "title_selector": ".news-card--body--link span",
        "snippet_selector": ".news-card--body--text",
        "link_selector": ".news-card--body--link",
        "base_url": "https://www.brenntag.com",
    },
    {
        "name": "Univar Solutions",
        "url": "https://news.univarsolutions.com/",
        "selector": "li.wd_item",
        "title_selector": ".wd_title a",
        "snippet_selector": ".wd_summary p",
        "link_selector": ".wd_title a",
        "base_url": "https://news.univarsolutions.com",
    },
    {
        "name": "ChemAnalyst",
        "url": "https://www.chemanalyst.com/NewsAndDeals/NewsHome",
        "selector": ".card, .news-card, article",
        "title_selector": "h3, h4, h5, .card-title, a",
        "snippet_selector": "p, .card-text",
        "link_selector": "a",
        "base_url": "https://www.chemanalyst.com",
    },
]


class IndustrySitesCollector(BaseCollector):
    """Scrapes newsroom pages of key chemical industry companies."""

    def __init__(self, sources: list[dict] | None = None, max_per_source: int = 15):
        self.sources = sources or INDUSTRY_SOURCES
        self.max_per_source = max_per_source

    async def collect(self) -> list[RawArticle]:
        articles: list[RawArticle] = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            for source in self.sources:
                try:
                    articles.extend(
                        await self._scrape_source(client, source)
                    )
                except Exception:
                    logger.warning(
                        "industry_site_failed",
                        source=source["name"],
                        exc_info=True,
                    )

        logger.info("industry_sites_collected", total=len(articles))
        return articles

    async def _scrape_source(
        self, client: httpx.AsyncClient, source: dict
    ) -> list[RawArticle]:
        resp = await client.get(source["url"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles: list[RawArticle] = []
        elements = soup.select(source["selector"])[: self.max_per_source]
        base_url = source.get("base_url", "/".join(source["url"].split("/")[:3]))

        for el in elements:
            title_el = el.select_one(source["title_selector"])
            snippet_el = el.select_one(source["snippet_selector"])

            title = title_el.get_text(strip=True) if title_el else el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else title

            # Find link: use link_selector if provided, else try the element itself
            href = ""
            link_selector = source.get("link_selector")
            if link_selector:
                link_el = el.select_one(link_selector)
                if link_el:
                    href = link_el.get("href", "")
            if not href:
                href = el.get("href", "")
                # Also check for nested <a> tags
                if not href:
                    a_tag = el.select_one("a[href]")
                    if a_tag:
                        href = a_tag.get("href", "")

            # Resolve relative URLs
            if href and not href.startswith("http"):
                href = f"{base_url}{href}" if href.startswith("/") else f"{base_url}/{href}"

            if not title or not href:
                continue

            articles.append(
                RawArticle(
                    title=title,
                    url=href,
                    snippet=snippet[:500],
                    source_name=SourceName.company_website,
                    published_date=None,
                )
            )

        return articles
