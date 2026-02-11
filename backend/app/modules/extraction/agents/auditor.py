"""M3ndel Agent 3: Quality Auditor.

Cross-checks extracted data against source document to catch errors.

Triggered CONDITIONALLY — not every PDF gets audited. Trigger criteria:
  - >3 fields with confidence "low"
  - CAS number missing for SDS or RPI documents
  - >3 extraction warnings
  - Any hallucination indicators

The Auditor receives the extraction result AND the source markdown,
then verifies values against the actual text.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.modules.extraction.agent_schemas import (
    AuditCorrection,
    AuditResult,
    PartialExtraction,
)
from app.modules.extraction.agents.base import BaseAgent
from app.modules.extraction.cost_tracker import CostTracker

logger = structlog.get_logger()

# Fields that should trigger an audit if missing from specific doc types
CRITICAL_FIELDS_BY_DOC_TYPE: dict[str, set[str]] = {
    "SDS": {"cas_numbers", "ghs_statements", "un_number", "flash_point"},
    "RPI": {"cas_numbers", "global_inventories", "certifications"},
    "TDS": {"density", "grade", "physical_form"},
    "CoA": {"cas_numbers", "purity"},
}

# Max source markdown length sent to auditor (to control token cost)
_MAX_SOURCE_CHARS = 8000


def should_audit(
    partial: PartialExtraction,
    doc_type: str,
) -> tuple[bool, list[str]]:
    """Determine if a PartialExtraction should be audited.

    Returns:
        (should_audit, reasons) — whether to audit and why.
    """
    reasons: list[str] = []

    # Skip if extraction failed entirely
    if not partial.extraction_result:
        return False, []

    # Count low-confidence MendelFact fields
    low_conf_count = _count_low_confidence(partial.extraction_result)
    if low_conf_count >= 3:
        reasons.append(f"{low_conf_count} low-confidence fields")

    # Check for missing critical fields
    critical_fields = CRITICAL_FIELDS_BY_DOC_TYPE.get(doc_type, set())
    missing_critical = critical_fields & set(partial.missing_fields)
    if missing_critical:
        reasons.append(f"missing critical fields: {', '.join(sorted(missing_critical))}")

    # Check warnings count
    if len(partial.warnings) >= 3:
        reasons.append(f"{len(partial.warnings)} extraction warnings")

    # Check for potential hallucination indicators
    hallucination_flags = _check_hallucination_indicators(partial.extraction_result)
    if hallucination_flags:
        reasons.extend(hallucination_flags)

    return len(reasons) > 0, reasons


def _count_low_confidence(extraction_result: dict) -> int:
    """Count MendelFact fields with confidence='low'."""
    count = 0
    for section_key in ("identity", "chemical", "physical", "application", "safety", "compliance"):
        section = extraction_result.get(section_key, {})
        if not isinstance(section, dict):
            continue
        for field_val in section.values():
            if isinstance(field_val, dict) and field_val.get("confidence") == "low":
                count += 1
    return count


def _check_hallucination_indicators(extraction_result: dict) -> list[str]:
    """Check for common hallucination patterns in extracted data."""
    flags: list[str] = []

    # Check CAS number format (should be XXXXX-XX-X pattern)
    chemical = extraction_result.get("chemical", {})
    cas = chemical.get("cas_numbers") if isinstance(chemical, dict) else None
    if isinstance(cas, dict) and cas.get("value"):
        cas_val = str(cas["value"])
        # Basic CAS format check: digits-digits-digit(s)
        import re
        cas_parts = [c.strip() for c in cas_val.split(",")]
        for part in cas_parts:
            if part and not re.match(r"^\d{2,7}-\d{2}-\d$", part.strip()):
                flags.append(f"suspicious CAS format: '{part}'")

    # Check UN number format (should be UN followed by 4 digits)
    safety = extraction_result.get("safety", {})
    un = safety.get("un_number") if isinstance(safety, dict) else None
    if isinstance(un, dict) and un.get("value"):
        un_val = str(un["value"]).strip().upper()
        import re
        if not re.match(r"^(UN\s?)?\d{4}$", un_val):
            flags.append(f"suspicious UN number: '{un_val}'")

    # Check GHS statement format
    ghs = safety.get("ghs_statements", []) if isinstance(safety, dict) else []
    if isinstance(ghs, list):
        import re
        for stmt in ghs[:5]:  # Check first 5
            s = str(stmt).strip()
            if s and not re.match(r"^[HPE]\d{3}", s):
                flags.append(f"suspicious GHS format: '{s}'")
                break  # One is enough to trigger

    return flags


class AuditorAgent(BaseAgent):
    """Agent 3: Quality Auditor.

    Cross-checks extraction results against source document.
    Only called conditionally when trigger criteria are met.
    """

    agent_name = "Auditor"

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        super().__init__(provider=provider, model=model, cost_tracker=cost_tracker)
        base_prompt = self.load_prompt("auditor.txt")
        self._system_prompt = base_prompt

    def audit(
        self,
        markdown: str,
        partial: PartialExtraction,
        doc_type: str,
        file_name: str = "",
    ) -> AuditResult:
        """Audit an extraction result against its source document.

        Args:
            markdown: Full document markdown content.
            partial: The PartialExtraction to audit.
            doc_type: Document type (TDS, SDS, etc.).
            file_name: Original filename for logging.

        Returns:
            AuditResult with corrections, confidence, and flagged issues.
        """
        # Truncate source to control costs
        source_text = markdown[:_MAX_SOURCE_CHARS]
        if len(markdown) > _MAX_SOURCE_CHARS:
            source_text += f"\n\n[... truncated, {len(markdown)} total chars ...]"

        # Build the extraction summary for the LLM
        extraction_json = json.dumps(partial.extraction_result, indent=2, default=str)

        user_content = (
            f"## Document Type: {doc_type}\n"
            f"## File: {file_name}\n\n"
            f"## Extracted Data\n```json\n{extraction_json}\n```\n\n"
            f"## Source Document\n---\n{source_text}\n---\n\n"
            f"Cross-check the extracted data against the source document. "
            f"Report any errors, mismatches, or hallucinated values."
        )

        try:
            result = self.call_llm(
                system_prompt=self._system_prompt,
                user_content=user_content,
                response_json=True,
                file_name=file_name,
                doc_type=doc_type,
            )

            raw_data = result["content"]

            # Parse corrections
            corrections = []
            for c in raw_data.get("corrections", []):
                # LLM may return full MendelFact dicts instead of plain strings
                orig = c.get("original_value")
                if isinstance(orig, dict):
                    orig = str(orig.get("value", orig))
                elif orig is not None:
                    orig = str(orig)

                corrected = c.get("corrected_value")
                if isinstance(corrected, dict):
                    corrected = str(corrected.get("value", corrected))
                elif corrected is not None:
                    corrected = str(corrected)

                corrections.append(AuditCorrection(
                    field_name=c.get("field_name", "unknown"),
                    original_value=orig,
                    corrected_value=corrected,
                    reason=c.get("reason", ""),
                    source_quote=c.get("source_quote"),
                ))

            audit_result = AuditResult(
                corrections=corrections,
                overall_confidence=float(raw_data.get("overall_confidence", 0.5)),
                flagged_issues=raw_data.get("flagged_issues", []),
                pass_audit=bool(raw_data.get("pass_audit", True)),
            )

            logger.info(
                "Auditor: audit complete",
                file=file_name,
                doc_type=doc_type,
                corrections=len(corrections),
                confidence=audit_result.overall_confidence,
                pass_audit=audit_result.pass_audit,
                flagged=len(audit_result.flagged_issues),
            )

            return audit_result

        except Exception as e:
            logger.error(
                "Auditor: audit failed",
                file=file_name,
                doc_type=doc_type,
                error=str(e),
            )
            # Return a "pass" result on failure (don't block the pipeline)
            return AuditResult(
                corrections=[],
                overall_confidence=0.5,
                flagged_issues=[f"Audit error: {e}"],
                pass_audit=True,
            )

    def apply_corrections(
        self,
        partial: PartialExtraction,
        audit_result: AuditResult,
    ) -> PartialExtraction:
        """Apply audit corrections to a PartialExtraction.

        Only applies corrections where:
          - The field exists in the extraction result
          - The corrected_value is not None (removal not auto-applied)

        Args:
            partial: Original PartialExtraction.
            audit_result: Audit results with corrections.

        Returns:
            Updated PartialExtraction with corrections applied.
        """
        if not audit_result.corrections:
            return partial

        extraction = partial.extraction_result.copy()
        applied = 0

        for correction in audit_result.corrections:
            # Parse field path: "section.field" -> section_key, field_key
            parts = correction.field_name.split(".", 1)
            if len(parts) == 2:
                section_key, field_key = parts
            else:
                # Try to find the field in any section
                field_key = parts[0]
                section_key = self._find_section_for_field(extraction, field_key)
                if not section_key:
                    continue

            section = extraction.get(section_key, {})
            if not isinstance(section, dict):
                continue

            if field_key not in section:
                continue

            # Apply the correction
            current_val = section[field_key]
            new_val = correction.corrected_value

            if new_val is None:
                # Don't auto-remove values — flag for human review instead
                partial.warnings.append(
                    f"Audit: {correction.field_name} may be incorrect "
                    f"(reason: {correction.reason})"
                )
                continue

            if isinstance(current_val, dict) and "value" in current_val:
                # MendelFact field — update just the value
                current_val["value"] = new_val
                current_val["confidence"] = "medium"  # Downgrade confidence after correction
                applied += 1
            elif isinstance(current_val, str):
                # Plain string field
                section[field_key] = new_val
                applied += 1

            extraction[section_key] = section

        if applied > 0:
            partial.extraction_result = extraction
            partial.warnings.append(f"Audit: {applied} corrections applied")
            logger.info(
                "Auditor: corrections applied",
                file=partial.source_file,
                applied=applied,
                total=len(audit_result.corrections),
            )

        return partial

    @staticmethod
    def _find_section_for_field(extraction: dict, field_key: str) -> str | None:
        """Find which section a field belongs to."""
        for section_key in ("identity", "chemical", "physical", "application",
                            "safety", "compliance", "document_info"):
            section = extraction.get(section_key, {})
            if isinstance(section, dict) and field_key in section:
                return section_key
        return None
