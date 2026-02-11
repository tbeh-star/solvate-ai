"""M3ndel Agent 4: Golden Record Merger.

Combines multiple partial extractions (TDS + SDS + RPI + CoA + Brochure)
for the same product into a single Golden Record using the Truth Hierarchy.

This agent is PURELY PROGRAMMATIC — no LLM calls needed.

Truth Hierarchy (priority):
  TDS(5) > CoA(4) > SDS(3) > RPI(2) > Brochure(1) > unknown(0)

Merge Strategy:
  - Scalar fields: Take the value from the highest-priority source.
  - Union fields (certifications, inventories, etc.): Combine from all sources.
  - Conflicts: Log as warning, keep highest-priority value.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import structlog

from app.modules.extraction.agent_schemas import (
    DOC_TYPE_PRIORITY,
    UNION_MERGE_FIELDS,
    PartialExtraction,
    ProductGroup,
)
from app.modules.extraction.agents.sanitizer import (
    PLAIN_STRING_FIELDS,
    PLAIN_STRING_LIST_FIELDS,
    SINGLE_MENDELFACT_FIELDS,
)
from app.modules.extraction.schemas import ExtractionResult

logger = structlog.get_logger()


class MergerAgent:
    """Agent 4: Merges partial extractions into Golden Records.

    No LLM calls — pure Python logic based on Truth Hierarchy.
    """

    agent_name = "Merger"

    def merge(self, group: ProductGroup) -> ExtractionResult:
        """Merge a ProductGroup into a single Golden Record.

        Args:
            group: A ProductGroup containing partial extractions from
                   multiple document types for the same product.

        Returns:
            A merged ExtractionResult (Golden Record).
        """
        partials = group.partial_extractions

        if not partials:
            logger.warning("Merger: no partials to merge", product=group.product_name)
            raise ValueError(f"No partial extractions for {group.product_name}")

        if len(partials) == 1:
            # Single document — just return its extraction result
            logger.info(
                "Merger: single partial, no merge needed",
                product=group.product_name,
                doc_type=partials[0].doc_type,
            )
            return ExtractionResult.model_validate(partials[0].extraction_result)

        # Sort by priority (highest first)
        sorted_partials = sorted(
            partials,
            key=lambda p: DOC_TYPE_PRIORITY.get(p.doc_type, 0),
            reverse=True,
        )

        logger.info(
            "Merger: merging partials",
            product=group.product_name,
            sources=[f"{p.doc_type}({p.source_file})" for p in sorted_partials],
        )

        # Start with the highest-priority extraction as the base
        merged = deepcopy(sorted_partials[0].extraction_result)
        merge_warnings: list[str] = []

        # Merge in lower-priority partials
        for partial in sorted_partials[1:]:
            if not partial.extraction_result:
                continue

            source_data = partial.extraction_result
            source_type = partial.doc_type
            source_priority = DOC_TYPE_PRIORITY.get(source_type, 0)

            self._merge_section(
                merged, source_data, "document_info",
                source_type, source_priority, merge_warnings,
            )
            self._merge_section(
                merged, source_data, "identity",
                source_type, source_priority, merge_warnings,
            )
            self._merge_section(
                merged, source_data, "chemical",
                source_type, source_priority, merge_warnings,
            )
            self._merge_section(
                merged, source_data, "physical",
                source_type, source_priority, merge_warnings,
            )
            self._merge_section(
                merged, source_data, "application",
                source_type, source_priority, merge_warnings,
            )
            self._merge_section(
                merged, source_data, "safety",
                source_type, source_priority, merge_warnings,
            )
            self._merge_section(
                merged, source_data, "compliance",
                source_type, source_priority, merge_warnings,
            )

        # Rebuild missing_attributes: only those missing from ALL sources
        all_missing = self._compute_missing(sorted_partials)
        merged["missing_attributes"] = sorted(all_missing)

        # Combine extraction_warnings from all sources + merge conflicts
        all_warnings = set()
        for p in sorted_partials:
            for w in p.warnings:
                all_warnings.add(w)
        all_warnings.update(merge_warnings)
        merged["extraction_warnings"] = sorted(all_warnings)

        logger.info(
            "Merger: Golden Record created",
            product=group.product_name,
            sources=len(sorted_partials),
            missing=len(all_missing),
            warnings=len(all_warnings),
        )

        return ExtractionResult.model_validate(merged)

    def _merge_section(
        self,
        target: dict,
        source: dict,
        section: str,
        source_type: str,
        source_priority: int,
        warnings: list[str],
    ) -> None:
        """Merge a single section from source into target.

        Uses Truth Hierarchy: only fill in null/empty fields from lower-priority sources.
        Union fields are always combined.
        """
        target_section = target.get(section, {})
        source_section = source.get(section, {})

        if not isinstance(target_section, dict) or not isinstance(source_section, dict):
            return

        for key, source_val in source_section.items():
            if source_val is None:
                continue

            target_val = target_section.get(key)

            # Union-merge fields: combine lists from all sources
            if key in UNION_MERGE_FIELDS:
                if isinstance(source_val, list) and isinstance(target_val, list):
                    # Add items not already present
                    existing = set(str(v) for v in target_val)
                    for item in source_val:
                        if str(item) not in existing:
                            target_val.append(item)
                            existing.add(str(item))
                elif isinstance(source_val, list) and (target_val is None or target_val == []):
                    target_section[key] = source_val
                continue

            # Plain string fields: fill if target is empty
            if key in PLAIN_STRING_FIELDS:
                if not target_val and source_val:
                    target_section[key] = source_val
                continue

            # Plain string list fields: fill if target is empty
            if key in PLAIN_STRING_LIST_FIELDS:
                if (not target_val or target_val == []) and source_val:
                    target_section[key] = source_val
                continue

            # MendelFact fields (single): fill if target is null
            if key in SINGLE_MENDELFACT_FIELDS or key == "cas_numbers":
                if target_val is None and source_val is not None:
                    target_section[key] = source_val
                elif (
                    target_val is not None
                    and source_val is not None
                    and isinstance(target_val, dict)
                    and isinstance(source_val, dict)
                ):
                    # Both have values — check for conflict
                    t_value = target_val.get("value")
                    s_value = source_val.get("value")
                    if t_value and s_value and str(t_value) != str(s_value):
                        warnings.append(
                            f"Conflict in {section}.{key}: "
                            f"keeping '{t_value}' (higher priority), "
                            f"discarding '{s_value}' from {source_type}"
                        )
                continue

            # Generic: fill null with any non-null value
            if target_val is None and source_val is not None:
                target_section[key] = source_val

        target[section] = target_section

    @staticmethod
    def _compute_missing(partials: list[PartialExtraction]) -> set[str]:
        """Compute which attributes are missing from ALL partial extractions.

        An attribute is only "missing" in the Golden Record if no single
        source document provided it.
        """
        if not partials:
            return set()

        # Start with all fields missing
        all_fields_missing = set(partials[0].missing_fields)

        # Intersect with missing fields from each partial
        for partial in partials[1:]:
            all_fields_missing &= set(partial.missing_fields)

        return all_fields_missing
