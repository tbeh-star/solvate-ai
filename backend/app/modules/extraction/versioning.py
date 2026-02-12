"""Versioning & region resolution for Golden Records.

Determines the region (EU, US, JP, CN, KR, GLOBAL) from an ExtractionResult
and assigns auto-incrementing version numbers per (product_name, region).
"""

from __future__ import annotations

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.extraction.models import GoldenRecord
from app.modules.extraction.schemas import ExtractionResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Region resolution
# ---------------------------------------------------------------------------

# SDS language → default region mapping.
# Wacker Chemie HQ is in Germany, so EN/DE/FR SDSs are EU versions by default.
_LANG_TO_REGION: dict[str, str] = {
    "en": "EU",
    "de": "EU",
    "fr": "EU",
    "es": "EU",
    "it": "EU",
    "pt": "EU",
    "nl": "EU",
    "pl": "EU",
    "ja": "JP",
    "zh": "CN",
    "ko": "KR",
}

# Document types that are not region-specific
_GLOBAL_DOC_TYPES = {"TDS", "CoA", "Brochure", "RPI"}


def resolve_region(result: ExtractionResult) -> str:
    """Determine the geographic region for a Golden Record.

    Logic:
      1. TDS, CoA, Brochure, RPI → always "GLOBAL" (not region-specific)
      2. SDS → derive from language + optional inventory override
      3. Fallback → "GLOBAL"

    The inventory override catches the case where an English-language SDS
    references only TSCA (US) and not REACH (EU), indicating it's a US version.
    """
    doc_type = result.document_info.document_type

    # Step 1: Non-regional document types → GLOBAL
    if doc_type in _GLOBAL_DOC_TYPES:
        return "GLOBAL"

    # Step 2: SDS → language-based region
    if doc_type == "SDS":
        lang = (result.document_info.language or "en").lower()[:2]
        region = _LANG_TO_REGION.get(lang, "GLOBAL")

        # Step 2b: Inventory-based override for US detection
        # If the SDS mentions TSCA but NOT REACH, it's likely a US version
        inventories = result.safety.global_inventories if result.safety else []
        if inventories:
            inv_text = " ".join(inv.upper() for inv in inventories)
            has_tsca = "TSCA" in inv_text
            has_reach = "REACH" in inv_text
            if has_tsca and not has_reach:
                region = "US"

        return region

    # Step 3: Unknown doc type → GLOBAL
    return "GLOBAL"


# ---------------------------------------------------------------------------
# Version assignment
# ---------------------------------------------------------------------------


async def assign_version(
    db: AsyncSession,
    product_name: str,
    region: str,
) -> tuple[int, list[int]]:
    """Determine next version number and mark older versions as not-latest.

    Returns:
        (new_version, list_of_obsoleted_record_ids)
    """
    # 1. Find the current max version for this product+region
    max_version_query = (
        select(func.max(GoldenRecord.version))
        .where(GoldenRecord.product_name == product_name)
        .where(GoldenRecord.region == region)
    )
    max_version = (await db.execute(max_version_query)).scalar_one_or_none()
    new_version = (max_version or 0) + 1

    # 2. Mark all existing latest records as obsolete
    obsoleted_ids_query = (
        select(GoldenRecord.id)
        .where(GoldenRecord.product_name == product_name)
        .where(GoldenRecord.region == region)
        .where(GoldenRecord.is_latest == True)  # noqa: E712
    )
    obsoleted_result = await db.execute(obsoleted_ids_query)
    obsoleted_ids = [row[0] for row in obsoleted_result.all()]

    if obsoleted_ids:
        await db.execute(
            update(GoldenRecord)
            .where(GoldenRecord.id.in_(obsoleted_ids))
            .values(is_latest=False)
        )
        logger.info(
            "Obsoleted previous versions",
            product_name=product_name,
            region=region,
            obsoleted_ids=obsoleted_ids,
            new_version=new_version,
        )

    return new_version, obsoleted_ids
