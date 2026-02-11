from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.events.schemas import RawArticle


class BaseCollector(ABC):
    """Abstract base class for event source collectors."""

    @abstractmethod
    async def collect(self) -> list[RawArticle]:
        """Collect raw articles from the source. Returns a list of RawArticle."""
        ...
