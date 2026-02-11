"""M3ndel Sanitizer — Post-processing of LLM extraction output.

Fixes common LLM output errors before Pydantic validation:
  1. Plain-string fields wrapped in MendelFact-like dicts
  2. List items wrapped in MendelFact-like dicts
  3. cas_numbers returned as null or list of dicts
  4. List fields returned as null instead of []
  5. document_type as full name instead of short code
  6. cas_numbers as list of MendelFacts → join into single MendelFact
  7. main_application as list → join into single string
  8. Single MendelFact fields returned as list → take first element

This module is shared between the legacy batch_extractor and the new agent pipeline.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Field-type constants (define which fields expect which shape)
# ---------------------------------------------------------------------------

# Fields that should be plain strings (not MendelFact objects)
PLAIN_STRING_FIELDS = {
    # identity
    "product_name", "product_line", "wacker_sku", "product_url",
    # document_info
    "language", "manufacturer", "brand", "revision_date",
    # application
    "main_application",
    # compliance
    "wiaw_status", "sales_advisory",
}

# Fields that should be a single MendelFact (not a list of MendelFacts)
SINGLE_MENDELFACT_FIELDS = {
    "grade", "purity", "physical_form", "density", "flash_point",
    "temperature_range", "shelf_life", "cure_system", "un_number",
}

# Fields that should be lists of plain strings
PLAIN_STRING_LIST_FIELDS = {
    "material_numbers", "chemical_components", "chemical_synonyms",
    "usage_restrictions", "packaging_options",
    "ghs_statements", "certifications", "global_inventories",
    "blocked_countries", "blocked_industries",
    "missing_attributes", "extraction_warnings",
}

# Map full document type names to short codes
DOC_TYPE_MAP = {
    "technical data sheet": "TDS",
    "safety data sheet": "SDS",
    "raw product information": "RPI",
    "regulatory product information": "RPI",
    "certificate of analysis": "CoA",
    "brochure": "Brochure",
}


# ---------------------------------------------------------------------------
# Helper: strip markdown code fences from LLM output
# ---------------------------------------------------------------------------

def strip_code_fences(raw_text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM response."""
    text = raw_text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# Core sanitizer
# ---------------------------------------------------------------------------

def sanitize_extraction_json(data: dict) -> dict:
    """Fix common LLM output errors before Pydantic validation.

    Common issues fixed:
    1. LLM wraps plain-string fields in MendelFact-like objects
       e.g. {"product_name": {"value": "X", "source_section": "..."}}
       -> should be: {"product_name": "X"}

    2. LLM wraps list items in MendelFact-like objects
       e.g. {"chemical_components": [{"value": "X", ...}]}
       -> should be: {"chemical_components": ["X"]}

    3. cas_numbers is null when not found
       -> should be a MendelFact with value=null

    4. List fields returned as null -> should be []

    5. document_type as full name -> must be short code (TDS, SDS, RPI, CoA, Brochure, unknown)

    6. cas_numbers as list (SDS with multiple CAS) -> join into single MendelFact

    7. main_application as list -> join into single string

    8. Single MendelFact fields returned as list -> take first element
    """

    def unwrap_value(obj: Any) -> str | None:
        """Extract the plain value from a MendelFact-like dict."""
        if isinstance(obj, dict) and "value" in obj:
            return str(obj["value"]) if obj["value"] is not None else None
        if isinstance(obj, str):
            return obj
        return str(obj) if obj is not None else None

    def fix_dict(d: dict, depth: int = 0) -> dict:
        """Recursively fix nested dicts."""
        if depth > 5:  # prevent infinite recursion
            return d

        result = {}
        for key, val in d.items():
            # Fix document_type full name -> short code
            if key == "document_type" and isinstance(val, str):
                mapped = DOC_TYPE_MAP.get(val.lower().strip())
                result[key] = mapped if mapped else val
                continue

            # Fix plain string fields wrapped in MendelFact or wrapped in list
            if key in PLAIN_STRING_FIELDS:
                if isinstance(val, dict) and "value" in val:
                    result[key] = unwrap_value(val)
                elif isinstance(val, list):
                    # LLM wrapped a plain string field in a list of MendelFact dicts
                    # e.g. main_application: [{"value": "X", ...}, {"value": "Y", ...}]
                    # -> join values into a single string
                    parts = []
                    for item in val:
                        v = unwrap_value(item) if isinstance(item, dict) else (str(item) if item else None)
                        if v:
                            parts.append(v)
                    result[key] = "; ".join(parts) if parts else None
                else:
                    result[key] = val

            # Fix single MendelFact fields returned as list -> take first element
            elif key in SINGLE_MENDELFACT_FIELDS:
                if isinstance(val, list) and len(val) > 0:
                    # LLM returned a list of MendelFacts -> take the first one
                    result[key] = val[0] if isinstance(val[0], dict) else val
                else:
                    result[key] = val

            # Fix list-of-string fields with wrapped items or null -> []
            elif key in PLAIN_STRING_LIST_FIELDS:
                if val is None:
                    # LLM returned null for a list field -> default to empty list
                    result[key] = []
                elif isinstance(val, list):
                    cleaned = []
                    for item in val:
                        if item is None:
                            continue
                        if isinstance(item, dict):
                            # Dict with "value" key -> extract it
                            if "value" in item:
                                v = str(item["value"]) if item["value"] is not None else None
                            # Dict with "name" key (e.g. chemical_components as objects)
                            elif "name" in item:
                                v = str(item["name"])
                            else:
                                # Generic dict -> stringify it
                                v = "; ".join(f"{k}: {v}" for k, v in item.items() if v is not None)
                            if v:
                                cleaned.append(v)
                        elif isinstance(item, str):
                            cleaned.append(item)
                        else:
                            cleaned.append(str(item))
                    result[key] = cleaned
                else:
                    result[key] = val

            # Fix cas_numbers edge cases
            elif key == "cas_numbers":
                if val is None:
                    # null -> proper MendelFact placeholder
                    result[key] = {
                        "value": None,
                        "source_section": "not found",
                        "raw_string": "CAS number not found in document",
                        "confidence": "low",
                        "is_specification": False,
                    }
                elif isinstance(val, list):
                    # LLM returned a list of MendelFact-like dicts (SDS with multiple CAS)
                    # -> join CAS numbers into a single MendelFact with comma-separated value
                    cas_values = []
                    first_item = val[0] if val else {}
                    for item in val:
                        if isinstance(item, dict) and "value" in item and item["value"]:
                            cas_values.append(str(item["value"]))
                        elif isinstance(item, str):
                            cas_values.append(item)
                    if cas_values:
                        result[key] = {
                            "value": ", ".join(cas_values),
                            "source_section": first_item.get("source_section", "Section 3") if isinstance(first_item, dict) else "Section 3",
                            "raw_string": ", ".join(cas_values),
                            "confidence": first_item.get("confidence", "high") if isinstance(first_item, dict) else "high",
                            "is_specification": True,
                            "test_method": None,
                        }
                    else:
                        result[key] = {
                            "value": None,
                            "source_section": "not found",
                            "raw_string": "CAS number not found in document",
                            "confidence": "low",
                            "is_specification": False,
                        }
                else:
                    result[key] = val

            # Recurse into nested dicts
            elif isinstance(val, dict):
                result[key] = fix_dict(val, depth + 1)

            # Recurse into nested lists of dicts
            elif isinstance(val, list):
                result[key] = [
                    fix_dict(item, depth + 1) if isinstance(item, dict) else item
                    for item in val
                ]

            else:
                result[key] = val

        return result

    return fix_dict(data)
