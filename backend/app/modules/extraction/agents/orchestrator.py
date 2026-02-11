"""M3ndel Agent 5: Pipeline Orchestrator.

Pure Python controller — no LLM calls. Routes documents through the
agent pipeline:

  Single-PDF Pipeline:
    PDF -> Parse -> Classify -> Extract -> (Audit) -> PartialExtraction

  Batch Pipeline:
    For each PDF: Single-PDF Pipeline
    Group by product folder
    For each group: Merge partials -> Golden Record
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import structlog

from app.modules.extraction.agent_schemas import (
    ClassificationResult,
    PartialExtraction,
    ProductGroup,
)
from app.modules.extraction.agents.auditor import AuditorAgent, should_audit
from app.modules.extraction.agents.classifier import ClassifierAgent
from app.modules.extraction.agents.extractors import get_extractor, DocTypeExtractor
from app.modules.extraction.agents.merger import MergerAgent
from app.modules.extraction.cost_tracker import CostTracker
from app.modules.extraction.pdf_service import parse_pdf
from app.modules.extraction.schemas import ExtractionResult

logger = structlog.get_logger()


class OrchestratorAgent:
    """Agent 5: Pipeline controller.

    Coordinates the full extraction pipeline from PDF to Golden Record.
    No LLM calls — pure orchestration logic.
    """

    agent_name = "Orchestrator"

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.cost_tracker = cost_tracker or CostTracker()

        # Agents (lazy-initialized)
        self._classifier: ClassifierAgent | None = None
        self._extractors: dict[str, DocTypeExtractor] = {}
        self._auditor: AuditorAgent | None = None
        self._merger = MergerAgent()

    # ------------------------------------------------------------------
    # Lazy agent initialization
    # ------------------------------------------------------------------

    def _get_classifier(self) -> ClassifierAgent:
        if self._classifier is None:
            self._classifier = ClassifierAgent(
                provider=self.provider,
                model=self.model,
                cost_tracker=self.cost_tracker,
            )
        return self._classifier

    def _get_auditor(self) -> AuditorAgent:
        if self._auditor is None:
            self._auditor = AuditorAgent(
                provider=self.provider,
                model=self.model,
                cost_tracker=self.cost_tracker,
            )
        return self._auditor

    def _get_extractor(self, doc_type: str) -> DocTypeExtractor:
        if doc_type not in self._extractors:
            self._extractors[doc_type] = get_extractor(
                doc_type,
                provider=self.provider,
                model=self.model,
                cost_tracker=self.cost_tracker,
            )
        return self._extractors[doc_type]

    # ------------------------------------------------------------------
    # Single-PDF pipeline
    # ------------------------------------------------------------------

    def process_single_pdf(
        self,
        pdf_path: str | Path,
    ) -> PartialExtraction:
        """Process a single PDF through the full agent pipeline.

        Steps:
          1. Parse PDF to Markdown (PyMuPDF)
          2. Classify document type + brand (Agent 1)
          3. Extract with doc-type-specific agent (Agent 2)
          4. Return PartialExtraction

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            PartialExtraction with extraction result and metadata.
        """
        pdf_path = Path(pdf_path)
        file_name = pdf_path.name

        start = time.time()
        logger.info("Orchestrator: processing PDF", file=file_name)

        # Step 1: Parse PDF
        try:
            pdf_bytes = pdf_path.read_bytes()
            parsed = parse_pdf(pdf_bytes)
        except Exception as e:
            logger.error("Orchestrator: PDF parse failed", file=file_name, error=str(e))
            return PartialExtraction(
                source_file=str(pdf_path),
                doc_type="unknown",
                extraction_result={},
                warnings=[f"PDF parse error: {e}"],
            )

        # Step 2: Classify
        classifier = self._get_classifier()
        classification = classifier.classify(
            markdown=parsed.full_markdown,
            file_name=file_name,
        )

        doc_type = classification.doc_type

        # Step 3: Extract with doc-type-specific agent
        extractor = self._get_extractor(doc_type)
        partial = extractor.extract(
            markdown=parsed.full_markdown,
            doc_type=doc_type,
            file_name=file_name,
        )

        # Enrich the partial with classification metadata
        partial.source_file = str(pdf_path)

        # Step 4: Conditional Audit (Agent 3)
        audit_triggered, audit_reasons = should_audit(partial, doc_type)
        if audit_triggered:
            logger.info(
                "Orchestrator: audit triggered",
                file=file_name,
                doc_type=doc_type,
                reasons=audit_reasons,
            )
            auditor = self._get_auditor()
            audit_result = auditor.audit(
                markdown=parsed.full_markdown,
                partial=partial,
                doc_type=doc_type,
                file_name=file_name,
            )
            partial.audit_result = audit_result

            # Apply corrections if any
            if audit_result.corrections:
                partial = auditor.apply_corrections(partial, audit_result)

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "Orchestrator: PDF processed",
            file=file_name,
            doc_type=doc_type,
            brand=classification.brand,
            confidence=classification.confidence,
            extracted=len(partial.extracted_fields),
            missing=len(partial.missing_fields),
            audited=audit_triggered,
            duration_ms=duration_ms,
        )

        return partial

    # ------------------------------------------------------------------
    # Batch pipeline
    # ------------------------------------------------------------------

    def process_batch(
        self,
        pdf_paths: list[str | Path],
    ) -> list[PartialExtraction]:
        """Process a batch of PDFs sequentially.

        Args:
            pdf_paths: List of paths to PDF files.

        Returns:
            List of PartialExtractions (one per PDF).
        """
        results = []
        total = len(pdf_paths)

        for idx, pdf_path in enumerate(pdf_paths, 1):
            logger.info(f"Orchestrator: batch [{idx}/{total}]", file=Path(pdf_path).name)
            try:
                partial = self.process_single_pdf(pdf_path)
                results.append(partial)
            except Exception as e:
                logger.error(
                    f"Orchestrator: batch [{idx}/{total}] failed",
                    file=Path(pdf_path).name,
                    error=str(e),
                )
                results.append(PartialExtraction(
                    source_file=str(pdf_path),
                    doc_type="unknown",
                    extraction_result={},
                    warnings=[f"Processing error: {e}"],
                ))

        return results

    # ------------------------------------------------------------------
    # Grouping + merging into Golden Records
    # ------------------------------------------------------------------

    @staticmethod
    def group_by_product(
        partials: list[PartialExtraction],
    ) -> list[ProductGroup]:
        """Group partial extractions by product folder.

        Product folder is derived from the PDF path structure:
          02_Input/Wacker/BRAND/PRODUCT_NAME/file.pdf
                                 ^^^^^^^^^^^^
                                 = product folder

        Args:
            partials: List of PartialExtractions from batch processing.

        Returns:
            List of ProductGroups, one per unique product folder.
        """
        groups: dict[str, list[PartialExtraction]] = defaultdict(list)

        for partial in partials:
            path = Path(partial.source_file)
            # Product folder = parent directory of the PDF
            product_folder = str(path.parent)
            groups[product_folder].append(partial)

        product_groups = []
        for folder, group_partials in groups.items():
            # Determine product name and brand from the best partial
            product_name = Path(folder).name
            brand = ""

            # Try to get brand from extraction results
            for p in group_partials:
                if p.extraction_result:
                    doc_info = p.extraction_result.get("document_info", {})
                    if doc_info.get("brand"):
                        brand = doc_info["brand"]
                        break
                    identity = p.extraction_result.get("identity", {})
                    if identity.get("product_name"):
                        product_name = identity["product_name"]

            product_groups.append(ProductGroup(
                product_name=product_name,
                product_folder=folder,
                brand=brand,
                partial_extractions=group_partials,
            ))

        logger.info(
            "Orchestrator: grouped into products",
            total_pdfs=len(partials),
            product_groups=len(product_groups),
        )

        return product_groups

    def merge_to_golden_records(
        self,
        product_groups: list[ProductGroup],
    ) -> list[dict[str, Any]]:
        """Merge each ProductGroup into a Golden Record.

        Args:
            product_groups: List of ProductGroups from group_by_product().

        Returns:
            List of dicts with:
              - product_name: str
              - product_folder: str
              - brand: str
              - golden_record: ExtractionResult | None
              - source_count: int (how many PDFs contributed)
              - error: str | None
        """
        results = []

        for group in product_groups:
            try:
                golden = self._merger.merge(group)
                results.append({
                    "product_name": group.product_name,
                    "product_folder": group.product_folder,
                    "brand": group.brand,
                    "golden_record": golden,
                    "source_count": len(group.partial_extractions),
                    "error": None,
                })
                logger.info(
                    "Golden Record created",
                    product=group.product_name,
                    sources=len(group.partial_extractions),
                    missing=len(golden.missing_attributes),
                )
            except Exception as e:
                logger.error(
                    "Golden Record merge failed",
                    product=group.product_name,
                    error=str(e),
                )
                results.append({
                    "product_name": group.product_name,
                    "product_folder": group.product_folder,
                    "brand": group.brand,
                    "golden_record": None,
                    "source_count": len(group.partial_extractions),
                    "error": str(e),
                })

        return results

    # ------------------------------------------------------------------
    # Full pipeline: batch + group + merge
    # ------------------------------------------------------------------

    def run_full_pipeline(
        self,
        pdf_paths: list[str | Path],
    ) -> dict[str, Any]:
        """Run the complete pipeline: extract all PDFs, group, merge.

        Args:
            pdf_paths: List of all PDF paths to process.

        Returns:
            {
                "partials": list[PartialExtraction],
                "product_groups": list[ProductGroup],
                "golden_records": list[dict],
                "cost_summary": dict,
            }
        """
        start = time.time()

        # Step 1: Extract all PDFs
        partials = self.process_batch(pdf_paths)

        # Step 2: Group by product
        product_groups = self.group_by_product(partials)

        # Step 3: Merge into Golden Records
        golden_records = self.merge_to_golden_records(product_groups)

        elapsed = time.time() - start

        summary = {
            "total_pdfs": len(pdf_paths),
            "successful_extractions": sum(1 for p in partials if p.extraction_result),
            "failed_extractions": sum(1 for p in partials if not p.extraction_result),
            "product_groups": len(product_groups),
            "golden_records": sum(1 for g in golden_records if g["golden_record"]),
            "elapsed_seconds": round(elapsed, 1),
        }

        logger.info("Orchestrator: full pipeline complete", **summary)

        return {
            "partials": partials,
            "product_groups": product_groups,
            "golden_records": golden_records,
            "pipeline_summary": summary,
            "cost_summary": self.cost_tracker.summary(),
        }
