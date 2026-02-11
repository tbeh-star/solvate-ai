#!/usr/bin/env python3
"""Event collector pipeline.

Collects articles from configured sources, extracts structured events via OpenAI,
deduplicates, stores in PostgreSQL, and syncs to Notion.

Usage:
    python -m scripts.run_event_collector
    python -m scripts.run_event_collector --source google_news
    python -m scripts.run_event_collector --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

import structlog

from app.core.database import async_session
from app.modules.events.dedup import compute_dedup_hash
from app.modules.events.extraction import extract_events_batch
from app.modules.events.notion_sync import NotionEventSync
from app.modules.events.schemas import RawArticle
from app.modules.events.service import (
    create_collector_run,
    create_event,
    dedup_hash_exists,
    finish_collector_run,
    update_notion_page_id,
)
from app.modules.events.sources.google_news import GoogleNewsCollector
from app.modules.events.sources.google_search import GoogleSearchCollector
from app.modules.events.sources.industry_sites import IndustrySitesCollector

logger = structlog.get_logger()

COLLECTORS = {
    "google_news": GoogleNewsCollector,
    "google_search": GoogleSearchCollector,
    "industry_sites": IndustrySitesCollector,
}


async def collect_articles(source: str | None = None) -> list[RawArticle]:
    """Collect raw articles from all or a specific source."""
    articles: list[RawArticle] = []

    if source:
        collector_cls = COLLECTORS.get(source)
        if not collector_cls:
            logger.error("unknown_source", source=source)
            return []
        collector = collector_cls()
        articles = await collector.collect()
    else:
        for name, collector_cls in COLLECTORS.items():
            try:
                collector = collector_cls()
                result = await collector.collect()
                logger.info("source_collected", source=name, count=len(result))
                articles.extend(result)
            except Exception:
                logger.warning("source_failed", source=name, exc_info=True)

    return articles


async def run_pipeline(source: str | None = None, dry_run: bool = False) -> None:
    """Run the full event collection pipeline."""
    started_at = datetime.now()
    source_label = source or "all"
    logger.info("pipeline_started", source=source_label, dry_run=dry_run)

    # Step 1: Collect articles
    articles = await collect_articles(source)
    logger.info("articles_collected", total=len(articles))

    if not articles:
        logger.info("no_articles_found")
        return

    # Step 2: Extract events via OpenAI
    extracted = await extract_events_batch(articles)
    logger.info("events_extracted", relevant=len(extracted))

    if dry_run:
        for article, event in extracted:
            logger.info(
                "dry_run_event",
                title=event.event_title,
                type=event.event_type.value,
                companies=event.companies,
                confidence=event.confidence,
                source_url=article.url,
                is_exclusive=event.is_exclusive,
                exec_quotes_count=len(event.exec_quotes),
            )
        logger.info("dry_run_complete", total_events=len(extracted))
        return

    # Step 3-6: Store in DB and sync to Notion
    async with async_session() as db:
        try:
            run = await create_collector_run(db, source_label, started_at)
            events_new = 0
            notion_sync = NotionEventSync()

            for article, event in extracted:
                dedup = compute_dedup_hash(event)

                if await dedup_hash_exists(db, dedup):
                    logger.debug("event_duplicate_skipped", hash=dedup[:12])
                    continue

                # Store in PostgreSQL
                row = await create_event(db, article, event, dedup)
                events_new += 1

                # Sync to Notion
                notion_page_id = await notion_sync.create_page(
                    event=event,
                    source_url=article.url,
                    source_name=article.source_name.value,
                    pg_id=row.id,
                )
                if notion_page_id:
                    await update_notion_page_id(db, row.id, notion_page_id)

            await finish_collector_run(
                db,
                run.id,
                status="completed",
                events_found=len(extracted),
                events_new=events_new,
            )
            await db.commit()

            logger.info(
                "pipeline_complete",
                events_found=len(extracted),
                events_new=events_new,
            )

        except Exception as e:
            await db.rollback()
            logger.error("pipeline_failed", error=str(e), exc_info=True)
            try:
                async with async_session() as err_db:
                    await finish_collector_run(
                        err_db, run.id, status="failed", error_message=str(e)
                    )
                    await err_db.commit()
            except Exception:
                pass
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run event collector pipeline")
    parser.add_argument(
        "--source",
        choices=list(COLLECTORS.keys()),
        help="Run a specific source only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract but don't store results",
    )
    args = parser.parse_args()

    asyncio.run(run_pipeline(source=args.source, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
