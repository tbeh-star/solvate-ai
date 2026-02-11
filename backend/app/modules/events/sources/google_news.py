from __future__ import annotations

from datetime import datetime, date

import feedparser
import structlog

from app.modules.events.schemas import RawArticle, SourceName
from app.modules.events.sources.base import BaseCollector

logger = structlog.get_logger()

DEFAULT_QUERIES = [
    "chemical distribution agreement",
    "chemical company acquisition",
    "chemical distributor partnership",
    "BASF distribution agreement",
    "IMCD acquisition",
    "Brenntag partnership",
    "Univar distribution",
    "OQEMA distribution",
    "chemical force majeure",
    "chemical plant shutdown",
]

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"


def _parse_date(entry: dict) -> date | None:
    published = entry.get("published_parsed")
    if published:
        try:
            return datetime(*published[:6]).date()
        except (TypeError, ValueError):
            return None
    return None


class GoogleNewsCollector(BaseCollector):
    """Collects articles from Google News RSS feeds."""

    def __init__(self, queries: list[str] | None = None, max_per_query: int = 10):
        self.queries = queries or DEFAULT_QUERIES
        self.max_per_query = max_per_query

    async def collect(self) -> list[RawArticle]:
        articles: list[RawArticle] = []
        seen_urls: set[str] = set()

        for query in self.queries:
            url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[: self.max_per_query]:
                    link = entry.get("link", "")
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    articles.append(
                        RawArticle(
                            title=entry.get("title", ""),
                            url=link,
                            snippet=entry.get("summary", entry.get("title", "")),
                            source_name=SourceName.google_news,
                            published_date=_parse_date(entry),
                        )
                    )
            except Exception:
                logger.warning("google_news_query_failed", query=query, exc_info=True)
                continue

        logger.info("google_news_collected", total=len(articles))
        return articles
