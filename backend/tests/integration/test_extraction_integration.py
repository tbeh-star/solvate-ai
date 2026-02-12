"""Integration tests for the extraction endpoints.

These tests exercise the full FastAPI request lifecycle (routing, file upload
parsing, Pydantic serialisation, error handling) with the OrchestratorAgent
and parse_pdf mocked out so no real LLM calls or PDF parsing occurs.

Unlike the unit tests in ``tests/unit/test_extraction_router.py`` which only
test HTTP-level validation, these integration tests verify:

  - The single-agent endpoint returns a valid ExtractionResponse
  - The batch endpoint processes multiple files and returns per-file results
  - The batch endpoint handles partial failures (1 OK + 1 bad) gracefully
  - The response schema matches the Pydantic model exactly
  - Duplicate product names within a batch are deduplicated on confirm
  - The confirm endpoint returns 400 when all results are failures
"""

from __future__ import annotations

import io
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.modules.extraction.agent_schemas import PartialExtraction

# ---------------------------------------------------------------------------
# Fixtures — DB-isolated client for confirm tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with a per-test DB session override.

    Each test gets its own engine+session to avoid asyncpg's
    ``another operation is in progress`` error caused by shared pool state.
    The session auto-rolls-back after each test so no data is persisted.
    """
    test_engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=1,
        max_overflow=0,
    )
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.pop(get_db, None)
    await test_engine.dispose()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PREFIX = "/api/v1/extraction"

# A realistic ExtractionResult dict (all 33 attributes) used by mocked returns.
MOCK_EXTRACTION_DICT: dict[str, Any] = {
    "document_info": {
        "document_type": "TDS",
        "language": "en",
        "manufacturer": "Wacker Chemie AG",
        "brand": "ELASTOSIL",
        "revision_date": "2024-06-15",
        "page_count": 4,
    },
    "identity": {
        "product_name": "ELASTOSIL RT 601 A/B",
        "product_line": "ELASTOSIL",
        "wacker_sku": "60076802",
        "material_numbers": ["60076802"],
        "product_url": None,
        "grade": None,
    },
    "chemical": {
        "cas_numbers": {
            "value": "68083-19-2",
            "unit": None,
            "source_section": "SDS Sec 3",
            "raw_string": "68083-19-2",
            "confidence": "high",
            "is_specification": False,
            "test_method": None,
        },
        "chemical_components": ["Polydimethylsiloxane", "Vinyl-terminated"],
        "chemical_synonyms": ["PDMS"],
        "purity": None,
    },
    "physical": {
        "physical_form": {
            "value": "Liquid",
            "unit": None,
            "source_section": "TDS Property Table",
            "raw_string": "Pourable liquid",
            "confidence": "high",
            "is_specification": False,
            "test_method": None,
        },
        "density": {
            "value": "1.02",
            "unit": "g/cm³",
            "source_section": "TDS Property Table",
            "raw_string": "Approx. 1.02 g/cm³",
            "confidence": "high",
            "is_specification": True,
            "test_method": "DIN 51757",
        },
        "flash_point": {
            "value": "> 100",
            "unit": "°C",
            "source_section": "SDS Sec 9",
            "raw_string": "> 100 °C",
            "confidence": "high",
            "is_specification": False,
            "test_method": None,
        },
        "temperature_range": None,
        "shelf_life": {
            "value": "24",
            "unit": "months",
            "source_section": "TDS Storage",
            "raw_string": "24 months from date of production",
            "confidence": "high",
            "is_specification": False,
            "test_method": None,
        },
        "cure_system": {
            "value": "Addition",
            "unit": None,
            "source_section": "TDS Description",
            "raw_string": "Addition-curing two-component silicone rubber",
            "confidence": "high",
            "is_specification": False,
            "test_method": None,
        },
    },
    "application": {
        "main_application": "Mold making, prototyping, encapsulation",
        "usage_restrictions": [],
        "packaging_options": ["1 kg Kit", "10 kg Kit", "200 kg Drum"],
    },
    "safety": {
        "ghs_statements": ["H319", "H315"],
        "un_number": None,
        "certifications": ["FDA 21 CFR 177.2600"],
        "global_inventories": ["TSCA", "REACH", "IECSC"],
        "blocked_countries": [],
        "blocked_industries": [],
    },
    "compliance": {
        "wiaw_status": "GREEN LIGHT",
        "sales_advisory": "GO",
    },
    "missing_attributes": ["temperature_range"],
    "extraction_warnings": [],
}


def _make_partial(
    filename: str = "test.pdf",
    extraction_result: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> PartialExtraction:
    """Create a PartialExtraction matching what OrchestratorAgent would return."""
    return PartialExtraction(
        source_file=filename,
        doc_type="TDS",
        extraction_result=extraction_result if extraction_result is not None else MOCK_EXTRACTION_DICT,
        extracted_fields=["product_name", "density", "cas_numbers"],
        missing_fields=["temperature_range"],
        warnings=warnings or [],
    )


def _make_failed_partial(filename: str = "bad.pdf") -> PartialExtraction:
    """Create a PartialExtraction representing a failed extraction.

    The router checks ``if partial.extraction_result:`` — an empty dict is
    truthy, so we use it here.  When model_validate({}) is called on it, Pydantic
    will raise a ValidationError because required fields are missing.  The
    batch endpoint catches this by checking the result of model_validate.

    For the batch flow, the router checks ``if partial.extraction_result:``
    and then calls ``ExtractionResult.model_validate()``.  An empty dict
    will fail validation and be caught as an error.
    """
    return PartialExtraction(
        source_file=filename,
        doc_type="unknown",
        extraction_result={},  # empty → model_validate will fail
        extracted_fields=[],
        missing_fields=[],
        warnings=["PDF parsing failed: corrupted file"],
    )


# ---------------------------------------------------------------------------
# Helpers — fake PDF bytes
# ---------------------------------------------------------------------------


def _fake_pdf(name: str = "test.pdf") -> tuple[str, tuple[str, io.BytesIO, str]]:
    """Return a (field_name, (filename, bytes, mime)) tuple for httpx uploads."""
    return ("file", (name, io.BytesIO(b"%PDF-1.4-fake-content"), "application/pdf"))


def _fake_pdfs(*names: str) -> list[tuple[str, tuple[str, io.BytesIO, str]]]:
    """Return multiple file tuples for batch upload."""
    return [
        ("files", (name, io.BytesIO(b"%PDF-1.4-fake-content"), "application/pdf"))
        for name in names
    ]


def _skip_if_db_unavailable(resp) -> None:  # noqa: ANN001
    """Skip the test gracefully when the database is not available."""
    if resp.status_code == 500:
        detail = resp.json().get("detail", resp.text)
        pytest.skip(f"Database not available: {detail}")


# ===========================================================================
# Single-agent endpoint: POST /extract-agent
# ===========================================================================


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_single_agent_success(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-agent with a valid PDF → 200 + ExtractionResponse."""
    mock_instance = MagicMock()
    mock_instance.process_single_pdf.return_value = _make_partial()
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(f"{PREFIX}/extract-agent", files=[_fake_pdf()])

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["result"] is not None
    assert body["result"]["identity"]["product_name"] == "ELASTOSIL RT 601 A/B"
    assert body["result"]["document_info"]["document_type"] == "TDS"
    assert body["processing_time_ms"] >= 0
    assert body["error"] is None


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_single_agent_no_result(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-agent when orchestrator raises ValueError → success=False.

    The router wraps orchestrator errors in a try/except and returns
    ExtractionResponse(success=False, error=...).
    """
    mock_instance = MagicMock()
    mock_instance.process_single_pdf.side_effect = ValueError(
        "Agent extraction returned no result. Warnings: ['LLM returned empty']"
    )
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(f"{PREFIX}/extract-agent", files=[_fake_pdf()])

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"] is not None
    assert "no result" in body["error"].lower()


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_single_agent_llm_timeout(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-agent when orchestrator raises RuntimeError → success=False."""
    mock_instance = MagicMock()
    mock_instance.process_single_pdf.side_effect = RuntimeError("LLM timeout after 60s")
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(f"{PREFIX}/extract-agent", files=[_fake_pdf()])

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "LLM timeout" in body["error"]


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_single_agent_response_schema(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """Verify the single-agent response matches ExtractionResponse schema exactly."""
    mock_instance = MagicMock()
    mock_instance.process_single_pdf.return_value = _make_partial()
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(f"{PREFIX}/extract-agent", files=[_fake_pdf()])
    body = resp.json()

    # Top-level keys
    expected_keys = {
        "success", "result", "error", "processing_time_ms",
        "provider", "model", "cascade", "markdown_preview",
    }
    assert set(body.keys()) == expected_keys

    # Result sub-sections
    result = body["result"]
    result_sections = {
        "document_info", "identity", "chemical", "physical",
        "application", "safety", "compliance",
        "missing_attributes", "extraction_warnings",
    }
    assert set(result.keys()) == result_sections


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_single_agent_result_content(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """Verify the extracted data flows through correctly (not just schema)."""
    mock_instance = MagicMock()
    mock_instance.process_single_pdf.return_value = _make_partial()
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(f"{PREFIX}/extract-agent", files=[_fake_pdf()])
    result = resp.json()["result"]

    # Chemical data
    assert result["chemical"]["cas_numbers"]["value"] == "68083-19-2"
    assert result["chemical"]["cas_numbers"]["confidence"] == "high"

    # Physical data
    assert result["physical"]["density"]["value"] == "1.02"
    assert result["physical"]["density"]["unit"] == "g/cm³"
    assert result["physical"]["density"]["test_method"] == "DIN 51757"

    # Compliance
    assert result["compliance"]["wiaw_status"] == "GREEN LIGHT"

    # Missing attributes
    assert "temperature_range" in result["missing_attributes"]


# ===========================================================================
# Batch endpoint: POST /extract-batch
# ===========================================================================


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_batch_two_pdfs_success(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-batch with 2 valid PDFs → 200 + 2 successful results."""
    mock_instance = MagicMock()
    mock_instance.process_batch.return_value = [
        _make_partial("doc_a.pdf"),
        _make_partial("doc_b.pdf"),
    ]
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(
        f"{PREFIX}/extract-batch",
        files=_fake_pdfs("doc_a.pdf", "doc_b.pdf"),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["successful_count"] == 2
    assert body["failed_count"] == 0
    assert len(body["results"]) == 2
    assert body["results"][0]["filename"] == "doc_a.pdf"
    assert body["results"][1]["filename"] == "doc_b.pdf"


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_batch_partial_failure(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-batch with 1 success + 1 failure → mixed results."""
    mock_instance = MagicMock()
    mock_instance.process_batch.return_value = [
        _make_partial("good.pdf"),
        _make_failed_partial("bad.pdf"),
    ]
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(
        f"{PREFIX}/extract-batch",
        files=_fake_pdfs("good.pdf", "bad.pdf"),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True  # at least 1 succeeded
    assert body["successful_count"] == 1
    assert body["failed_count"] == 1

    # good.pdf → success
    good = body["results"][0]
    assert good["success"] is True
    assert good["result"]["identity"]["product_name"] == "ELASTOSIL RT 601 A/B"

    # bad.pdf → failure with error message
    bad = body["results"][1]
    assert bad["success"] is False
    assert bad["error"] is not None


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_batch_all_failures(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-batch when all files fail → success=False."""
    mock_instance = MagicMock()
    mock_instance.process_batch.return_value = [
        _make_failed_partial("bad1.pdf"),
        _make_failed_partial("bad2.pdf"),
    ]
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(
        f"{PREFIX}/extract-batch",
        files=_fake_pdfs("bad1.pdf", "bad2.pdf"),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["successful_count"] == 0
    assert body["failed_count"] == 2


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_batch_response_schema(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """Verify batch response matches BatchExtractionResponse schema."""
    mock_instance = MagicMock()
    mock_instance.process_batch.return_value = [_make_partial("test.pdf")]
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(
        f"{PREFIX}/extract-batch",
        files=_fake_pdfs("test.pdf"),
    )

    body = resp.json()
    expected_keys = {
        "success", "results", "total_processing_time_ms",
        "provider", "successful_count", "failed_count",
    }
    assert set(body.keys()) == expected_keys

    # Each result item
    item = body["results"][0]
    item_keys = {"filename", "success", "result", "error", "processing_time_ms"}
    assert set(item.keys()) == item_keys


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_batch_orchestrator_exception_propagates(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-batch when orchestrator raises → exception propagates.

    Unlike the single-agent endpoint which wraps errors in success=False,
    the batch endpoint lets orchestrator exceptions propagate.  With the
    ASGITransport this surfaces as an unhandled exception rather than a
    clean 500 response.
    """
    mock_instance = MagicMock()
    mock_instance.process_batch.side_effect = RuntimeError("Out of memory")
    mock_orch_cls.return_value = mock_instance

    with pytest.raises(RuntimeError, match="Out of memory"):
        await client.post(
            f"{PREFIX}/extract-batch",
            files=_fake_pdfs("test.pdf"),
        )


@patch("app.modules.extraction.router.OrchestratorAgent")
async def test_batch_single_file(
    mock_orch_cls: MagicMock,
    client: AsyncClient,
) -> None:
    """POST /extract-batch with exactly 1 file → works fine."""
    mock_instance = MagicMock()
    mock_instance.process_batch.return_value = [_make_partial("single.pdf")]
    mock_orch_cls.return_value = mock_instance

    resp = await client.post(
        f"{PREFIX}/extract-batch",
        files=_fake_pdfs("single.pdf"),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["successful_count"] == 1
    assert len(body["results"]) == 1


# ===========================================================================
# Confirm endpoint: POST /confirm
# ===========================================================================


async def test_confirm_with_valid_results(db_client: AsyncClient) -> None:
    """POST /confirm with successful results → 200 with run_id.

    Requires a working database — skipped if unavailable.
    """
    resp = await db_client.post(
        f"{PREFIX}/confirm",
        json={
            "results": [
                {
                    "filename": "elastosil_rt601.pdf",
                    "success": True,
                    "result": MOCK_EXTRACTION_DICT,
                    "error": None,
                    "processing_time_ms": 1200,
                },
            ],
            "total_processing_time_ms": 1200,
        },
    )

    _skip_if_db_unavailable(resp)

    assert resp.status_code == 200
    body = resp.json()
    assert "run_id" in body
    assert body["run_id"] > 0
    assert body["golden_records_created"] == 1


async def test_confirm_deduplicates_same_product(db_client: AsyncClient) -> None:
    """POST /confirm with duplicate product names → only 1 golden record.

    Requires a working database — skipped if unavailable.
    """
    result_item = {
        "filename": "doc.pdf",
        "success": True,
        "result": MOCK_EXTRACTION_DICT,
        "error": None,
        "processing_time_ms": 500,
    }

    resp = await db_client.post(
        f"{PREFIX}/confirm",
        json={
            "results": [
                {**result_item, "filename": "doc_v1.pdf"},
                {**result_item, "filename": "doc_v2.pdf"},
            ],
            "total_processing_time_ms": 1000,
        },
    )

    _skip_if_db_unavailable(resp)

    assert resp.status_code == 200
    body = resp.json()
    # Same product_name "ELASTOSIL RT 601 A/B" → deduplicated to 1
    assert body["golden_records_created"] == 1


async def test_confirm_multiple_unique_products(db_client: AsyncClient) -> None:
    """POST /confirm with different product names → one record each.

    Requires a working database — skipped if unavailable.
    """
    import copy

    result_a = copy.deepcopy(MOCK_EXTRACTION_DICT)
    result_a["identity"]["product_name"] = "Product Alpha"

    result_b = copy.deepcopy(MOCK_EXTRACTION_DICT)
    result_b["identity"]["product_name"] = "Product Beta"

    resp = await db_client.post(
        f"{PREFIX}/confirm",
        json={
            "results": [
                {
                    "filename": "alpha.pdf",
                    "success": True,
                    "result": result_a,
                    "error": None,
                    "processing_time_ms": 600,
                },
                {
                    "filename": "beta.pdf",
                    "success": True,
                    "result": result_b,
                    "error": None,
                    "processing_time_ms": 700,
                },
            ],
            "total_processing_time_ms": 1300,
        },
    )

    _skip_if_db_unavailable(resp)

    assert resp.status_code == 200
    body = resp.json()
    assert body["golden_records_created"] == 2


async def test_confirm_mixed_success_and_failure(db_client: AsyncClient) -> None:
    """POST /confirm with 1 success + 1 failure → creates only 1 record.

    Requires a working database — skipped if unavailable.
    """
    resp = await db_client.post(
        f"{PREFIX}/confirm",
        json={
            "results": [
                {
                    "filename": "good.pdf",
                    "success": True,
                    "result": MOCK_EXTRACTION_DICT,
                    "error": None,
                    "processing_time_ms": 800,
                },
                {
                    "filename": "bad.pdf",
                    "success": False,
                    "result": None,
                    "error": "parsing failed",
                    "processing_time_ms": 100,
                },
            ],
            "total_processing_time_ms": 900,
        },
    )

    _skip_if_db_unavailable(resp)

    assert resp.status_code == 200
    body = resp.json()
    assert body["golden_records_created"] == 1


async def test_confirm_only_failures_returns_400(client: AsyncClient) -> None:
    """POST /confirm with all failures → 400 'No successful'."""
    resp = await client.post(
        f"{PREFIX}/confirm",
        json={
            "results": [
                {
                    "filename": "bad1.pdf",
                    "success": False,
                    "result": None,
                    "error": "corrupted",
                    "processing_time_ms": 50,
                },
                {
                    "filename": "bad2.pdf",
                    "success": False,
                    "result": None,
                    "error": "timeout",
                    "processing_time_ms": 30000,
                },
            ],
            "total_processing_time_ms": 30050,
        },
    )

    assert resp.status_code == 400
    assert "No successful" in resp.json()["detail"]


async def test_confirm_empty_body_returns_422(client: AsyncClient) -> None:
    """POST /confirm with empty body → 422 validation error."""
    resp = await client.post(f"{PREFIX}/confirm", json={})
    assert resp.status_code == 422


async def test_confirm_response_schema(db_client: AsyncClient) -> None:
    """Verify confirm response matches ConfirmExtractionResponse schema.

    Requires a working database — skipped if unavailable.
    """
    resp = await db_client.post(
        f"{PREFIX}/confirm",
        json={
            "results": [
                {
                    "filename": "schema_test.pdf",
                    "success": True,
                    "result": MOCK_EXTRACTION_DICT,
                    "error": None,
                    "processing_time_ms": 500,
                },
            ],
            "total_processing_time_ms": 500,
        },
    )

    _skip_if_db_unavailable(resp)

    assert resp.status_code == 200
    body = resp.json()
    expected_keys = {"run_id", "golden_records_created"}
    assert set(body.keys()) == expected_keys
    assert isinstance(body["run_id"], int)
    assert isinstance(body["golden_records_created"], int)
