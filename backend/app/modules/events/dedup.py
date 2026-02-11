from __future__ import annotations

import hashlib

from app.modules.events.schemas import ExtractedEvent


def compute_dedup_hash(event: ExtractedEvent) -> str:
    """Compute a SHA-256 dedup hash from event_type + sorted companies + event_date.

    This prevents storing the same event found from multiple sources.
    """
    parts = [
        event.event_type.value,
        "|".join(sorted(c.lower().strip() for c in event.companies)),
        event.event_date.isoformat() if event.event_date else "unknown",
    ]
    key = "::".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()
