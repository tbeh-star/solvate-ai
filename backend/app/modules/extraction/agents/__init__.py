"""M3ndel Multi-Agent Extraction Engine.

5-agent architecture for structured chemical product data extraction:
  Agent 1 — Classifier:   LLM-based doc-type + brand detection
  Agent 2 — Extractors:   Doc-type-specific sub-agents (TDS/SDS/RPI/CoA/Brochure)
  Agent 3 — Auditor:      Quality cross-check (conditional)
  Agent 4 — Merger:       Golden Record builder (programmatic)
  Agent 5 — Orchestrator: Pipeline controller (no LLM)
"""
