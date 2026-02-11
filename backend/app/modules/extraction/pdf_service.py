"""M3ndel PDF Parsing Service — PyMuPDF text + table extraction to Markdown."""

from __future__ import annotations

import re
from typing import Literal

import fitz  # PyMuPDF
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

DocType = Literal["TDS", "SDS", "RPI", "CoA", "Brochure", "unknown"]


# ---------------------------------------------------------------------------
# Data models for parsed output
# ---------------------------------------------------------------------------


class PageContent(BaseModel):
    """Extracted content for a single PDF page."""

    page_number: int
    text: str
    tables_markdown: list[str] = []


class ParsedDocument(BaseModel):
    """Complete parsed PDF output."""

    full_markdown: str
    pages: list[PageContent]
    doc_type: DocType
    page_count: int
    metadata: dict = {}


# ---------------------------------------------------------------------------
# Document type detection heuristics
# ---------------------------------------------------------------------------

_DOC_TYPE_PATTERNS: list[tuple[DocType, list[str]]] = [
    (
        "SDS",
        [
            r"safety\s+data\s+sheet",
            r"sicherheitsdatenblatt",
            r"SECTION\s+1[\s:.]+IDENTIFICATION",
            r"SECTION\s+1[\s:.]+Identification\s+of\s+the\s+substance",
        ],
    ),
    (
        "TDS",
        [
            r"technical\s+data\s+sheet",
            r"technisches\s+datenblatt",
            r"typical\s+properties",
            r"specification\s+data",
            r"product\s+data\s+sheet",
        ],
    ),
    (
        "RPI",
        [
            r"raw\s+product\s+information",
            r"global\s+chemical\s+inventor",
            r"regulatory\s+product\s+information",
        ],
    ),
    (
        "CoA",
        [
            r"certificate\s+of\s+analysis",
            r"analysenzertifikat",
            r"batch[\s-]+no",
            r"lot[\s-]+no",
        ],
    ),
]


def detect_document_type(text: str) -> DocType:
    """Classify a PDF by scanning the first ~3000 chars for keyword patterns."""
    sample = text[:3000].lower()
    for doc_type, patterns in _DOC_TYPE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, sample, re.IGNORECASE):
                return doc_type
    return "Brochure" if len(text) > 200 else "unknown"


# ---------------------------------------------------------------------------
# Brand detection
# ---------------------------------------------------------------------------

_BRANDS = [
    "ELASTOSIL",
    "FERMOPURE",
    "GENIOSIL",
    "BELSIL",
    "POWERSIL",
    "VINNAPAS",
    "WACKER",
]


def detect_brand(text: str) -> str | None:
    """Return the first Wacker brand name found in the text."""
    sample = text[:5000].upper()
    for brand in _BRANDS:
        if brand in sample:
            return brand
    return None


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------


def parse_pdf(pdf_bytes: bytes) -> ParsedDocument:
    """Extract text and tables from a PDF, returning structured Markdown.

    Strategy (Markdown-First):
      1. Extract text layer per page via PyMuPDF.
      2. Identify table objects and convert to Markdown tables.
      3. Combine text blocks and tables into a single Markdown string.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PageContent] = []
    markdown_parts: list[str] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        # --- Text extraction ---
        text = page.get_text("text") or ""

        # --- Table extraction ---
        tables_md: list[str] = []
        try:
            tables = page.find_tables()
            for table in tables:
                md = table.to_markdown()
                if md and md.strip():
                    tables_md.append(md.strip())
        except Exception:
            logger.warning("Table extraction failed", page=page_num, exc_info=True)

        # --- Compose page markdown ---
        page_md = f"## Page {page_num}\n\n{text.strip()}"
        if tables_md:
            page_md += "\n\n### Tables\n\n" + "\n\n".join(tables_md)

        pages.append(PageContent(page_number=page_num, text=text, tables_markdown=tables_md))
        markdown_parts.append(page_md)

    full_text = "\n".join(p.text for p in pages)
    full_markdown = "\n\n---\n\n".join(markdown_parts)

    doc_type = detect_document_type(full_text)
    brand = detect_brand(full_text)

    metadata: dict = {}
    if brand:
        metadata["brand"] = brand

    # Try to extract PDF metadata
    pdf_meta = doc.metadata or {}
    if pdf_meta.get("title"):
        metadata["pdf_title"] = pdf_meta["title"]
    if pdf_meta.get("creationDate"):
        metadata["creation_date"] = pdf_meta["creationDate"]

    doc.close()

    logger.info(
        "PDF parsed",
        pages=len(pages),
        doc_type=doc_type,
        brand=brand,
        chars=len(full_markdown),
    )

    return ParsedDocument(
        full_markdown=full_markdown,
        pages=pages,
        doc_type=doc_type,
        page_count=len(pages),
        metadata=metadata,
    )
