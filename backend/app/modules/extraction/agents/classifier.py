"""M3ndel Agent 1: Document Classifier.

Classifies PDFs by doc-type (TDS/SDS/RPI/CoA/Brochure) and detects
the Wacker brand using LLM analysis of the first 2 pages + filename hints.

Replaces the regex-based `pdf_service.detect_document_type()` which has
~40% misclassification rate for TDS documents.
"""

from __future__ import annotations

import structlog

from app.modules.extraction.agent_schemas import ClassificationResult
from app.modules.extraction.agents.base import BaseAgent
from app.modules.extraction.cost_tracker import CostTracker

logger = structlog.get_logger()

# Max chars from document to send to classifier (~first 2 pages)
_MAX_CONTENT_CHARS = 4000


class ClassifierAgent(BaseAgent):
    """Agent 1: Document type + brand classification via LLM.

    Uses the first ~2 pages of the document markdown plus the filename
    as input to a focused classification prompt (~300 tokens).

    Much more accurate than regex-based detection, especially for TDS
    documents that don't contain "Technical Data Sheet" in the header.
    """

    agent_name = "Classifier"

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        super().__init__(provider=provider, model=model, cost_tracker=cost_tracker)
        self._system_prompt = self.load_prompt("classifier.txt")

    def classify(
        self,
        markdown: str,
        file_name: str = "",
    ) -> ClassificationResult:
        """Classify a document by type and brand.

        Args:
            markdown: Full document markdown (will be truncated to first ~2 pages).
            file_name: Original filename — used as classification hint.

        Returns:
            ClassificationResult with doc_type, brand, product_name, confidence, reasoning.
        """
        # Truncate to first ~2 pages for cost efficiency
        content_sample = markdown[:_MAX_CONTENT_CHARS]

        user_content = (
            f"Filename: {file_name}\n\n"
            f"--- Document Content (first 2 pages) ---\n\n"
            f"{content_sample}"
        )

        try:
            result = self.call_llm(
                system_prompt=self._system_prompt,
                user_content=user_content,
                response_json=True,
                file_name=file_name,
                doc_type="classification",
            )

            data = result["content"]

            # Validate and create ClassificationResult
            classification = ClassificationResult.model_validate(data)

            logger.info(
                "Document classified",
                file=file_name,
                doc_type=classification.doc_type,
                brand=classification.brand,
                confidence=classification.confidence,
                reasoning=classification.reasoning[:80],
            )

            return classification

        except Exception as e:
            logger.error(
                "Classification failed, falling back to 'unknown'",
                file=file_name,
                error=str(e),
            )
            return ClassificationResult(
                doc_type="unknown",
                brand=None,
                product_name=None,
                confidence=0.0,
                reasoning=f"Classification error: {e}",
            )
