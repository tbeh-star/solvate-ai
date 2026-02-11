from __future__ import annotations

import httpx
import structlog

from app.core.config import settings
from app.modules.events.schemas import ExtractedEvent

logger = structlog.get_logger()

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionEventSync:
    """Syncs events to a Notion database."""

    def __init__(self) -> None:
        self.database_id = settings.notion_events_db_id
        self.headers = {
            "Authorization": f"Bearer {settings.notion_api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def create_page(
        self,
        event: ExtractedEvent,
        source_url: str,
        source_name: str,
        pg_id: int,
    ) -> str | None:
        """Create a Notion page for an event. Returns the Notion page ID."""
        if not self.database_id or not settings.notion_api_key:
            logger.warning("notion_sync_skipped", reason="No Notion API key or DB ID configured")
            return None

        properties = self._build_properties(event, source_url, source_name, pg_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{NOTION_API_URL}/pages",
                    headers=self.headers,
                    json={
                        "parent": {"database_id": self.database_id},
                        "properties": properties,
                    },
                )
                resp.raise_for_status()
                page_id = resp.json()["id"]
                logger.info("notion_page_created", page_id=page_id, event_title=event.event_title)
                return page_id
            except Exception:
                logger.warning("notion_sync_failed", event_title=event.event_title, exc_info=True)
                return None

    def _build_properties(
        self,
        event: ExtractedEvent,
        source_url: str,
        source_name: str,
        pg_id: int,
    ) -> dict:
        props: dict = {
            "Name": {"title": [{"text": {"content": event.event_title[:2000]}}]},
            "Event Type": {"select": {"name": event.event_type.value}},
            "Companies": {
                "rich_text": [
                    {"text": {"content": ", ".join(event.companies)[:2000]}}
                ]
            },
            "Company Roles": {
                "rich_text": [
                    {
                        "text": {
                            "content": ", ".join(
                                f"{role}: {name}" for role, name in event.company_roles.items()
                            )[:2000]
                        }
                    }
                ]
            },
            "Products": {
                "rich_text": [
                    {"text": {"content": ", ".join(event.products)[:2000]}}
                ]
            },
            "Segments": {
                "rich_text": [
                    {"text": {"content": ", ".join(event.segments)[:2000]}}
                ]
            },
            "Regions": {
                "rich_text": [
                    {"text": {"content": ", ".join(event.regions)[:2000]}}
                ]
            },
            "Source": {"url": source_url},
            "Source Name": {"select": {"name": source_name}},
            "Summary": {
                "rich_text": [{"text": {"content": (event.summary or "")[:2000]}}]
            },
            "Confidence": {"number": round(event.confidence * 100)},
            "Status": {"select": {"name": "auto_detected"}},
            "PG ID": {"number": pg_id},
        }

        # Event Date
        if event.event_date:
            props["Event Date"] = {"date": {"start": event.event_date.isoformat()}}

        # Exclusive
        if event.is_exclusive is not None:
            props["Exclusive"] = {"checkbox": event.is_exclusive}

        # Deal Value
        if event.deal_value:
            props["Deal Value"] = {
                "rich_text": [{"text": {"content": event.deal_value[:2000]}}]
            }

        # Deal Duration
        if event.deal_duration:
            props["Deal Duration"] = {
                "rich_text": [{"text": {"content": event.deal_duration[:2000]}}]
            }

        # Effective Date
        if event.effective_date:
            props["Effective Date"] = {
                "date": {"start": event.effective_date.isoformat()}
            }

        # Geographic Scope
        if event.geographic_scope:
            props["Geographic Scope"] = {
                "rich_text": [{"text": {"content": event.geographic_scope[:2000]}}]
            }

        # Exec Quotes
        if event.exec_quotes:
            quotes_text = "\n\n".join(
                f'"{q.quote}" — {q.name}'
                + (f", {q.title}" if q.title else "")
                + (f" ({q.company})" if q.company else "")
                for q in event.exec_quotes
            )
            props["Exec Quotes"] = {
                "rich_text": [{"text": {"content": quotes_text[:2000]}}]
            }

        # Key People
        if event.key_people:
            people_text = ", ".join(
                f"{p.name}"
                + (f" ({p.title})" if p.title else "")
                + (f" @ {p.company}" if p.company else "")
                for p in event.key_people
            )
            props["Key People"] = {
                "rich_text": [{"text": {"content": people_text[:2000]}}]
            }

        # Strategic Rationale
        if event.strategic_rationale:
            props["Strategic Rationale"] = {
                "rich_text": [{"text": {"content": event.strategic_rationale[:2000]}}]
            }

        return props
