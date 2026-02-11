"""M3ndel Cost Tracker — Token counting & cost estimation per LLM provider.

Tracks input/output/cached tokens and computes costs in USD.
Supports Gemini Flash, Gemini Pro, Claude Sonnet, Claude Opus, GPT-4o etc.

Usage:
    tracker = CostTracker()
    tracker.record("google", "gemini-2.5-flash", input_tokens=5000, output_tokens=800)
    tracker.record("anthropic", "claude-sonnet-4@20250514",
                   input_tokens=5000, output_tokens=800,
                   cache_creation_tokens=4000, cache_read_tokens=3500)
    print(tracker.summary())
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pricing per 1M tokens (USD) — updated 2025-06
# ---------------------------------------------------------------------------

# Format: (input_per_1M, output_per_1M, cache_write_per_1M, cache_read_per_1M)
# cache_write = surcharge for first write to cache, cache_read = reading from cache
# Set cache prices to 0.0 if provider doesn't support caching

_PRICING: dict[str, tuple[float, float, float, float]] = {
    # Gemini Flash 2.5 — context caching supported
    "gemini-2.5-flash": (0.15, 0.60, 0.0375, 0.0375),
    "gemini-2.0-flash": (0.10, 0.40, 0.025, 0.025),
    "gemini-1.5-flash": (0.075, 0.30, 0.01875, 0.01875),
    # Gemini Pro
    "gemini-2.5-pro": (1.25, 10.00, 0.3125, 0.3125),
    "gemini-1.5-pro": (1.25, 5.00, 0.3125, 0.3125),
    # Claude Sonnet (Vertex AI pricing = same as direct API)
    "claude-sonnet-4@20250514": (3.00, 15.00, 3.75, 0.30),
    "claude-sonnet-4-20250514": (3.00, 15.00, 3.75, 0.30),
    "claude-3-5-sonnet-v2@20241022": (3.00, 15.00, 3.75, 0.30),
    "claude-3-5-sonnet@20241022": (3.00, 15.00, 3.75, 0.30),
    # Claude Opus
    "claude-opus-4@20250514": (15.00, 75.00, 18.75, 1.50),
    # Claude Haiku
    "claude-3-5-haiku@20241022": (0.80, 4.00, 1.00, 0.08),
    # OpenAI
    "gpt-4o": (2.50, 10.00, 0.0, 1.25),
    "gpt-4o-mini": (0.15, 0.60, 0.0, 0.075),
    "gpt-4.1": (2.00, 8.00, 0.0, 0.50),
    "gpt-4.1-mini": (0.40, 1.60, 0.0, 0.10),
    "gpt-4.1-nano": (0.10, 0.40, 0.0, 0.025),
}

# Fallback pricing for unknown models (conservative estimate)
_FALLBACK_PRICING = (3.00, 15.00, 3.75, 0.30)


def _get_pricing(model: str) -> tuple[float, float, float, float]:
    """Look up pricing for a model, with fuzzy matching."""
    if model in _PRICING:
        return _PRICING[model]
    # Try partial match (e.g. "gemini-2.5-flash-001" → "gemini-2.5-flash")
    for key in _PRICING:
        if key in model or model in key:
            return _PRICING[key]
    logger.warning("Unknown model pricing, using fallback", model=model)
    return _FALLBACK_PRICING


# ---------------------------------------------------------------------------
# Token record per extraction
# ---------------------------------------------------------------------------


@dataclass
class TokenRecord:
    """Token usage for a single extraction call."""

    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0  # Anthropic: tokens written to cache
    cache_read_tokens: int = 0      # Anthropic: tokens read from cache
    total_tokens: int = 0
    cost_usd: float = 0.0
    file_name: str = ""
    doc_type: str = ""
    duration_ms: int = 0
    cascade_triggered: bool = False
    timestamp: float = field(default_factory=time.time)

    def compute_cost(self) -> None:
        """Compute USD cost from token counts."""
        input_price, output_price, cache_write_price, cache_read_price = _get_pricing(self.model)

        self.total_tokens = (
            self.input_tokens + self.output_tokens
            + self.cache_creation_tokens + self.cache_read_tokens
        )

        self.cost_usd = (
            (self.input_tokens / 1_000_000) * input_price
            + (self.output_tokens / 1_000_000) * output_price
            + (self.cache_creation_tokens / 1_000_000) * cache_write_price
            + (self.cache_read_tokens / 1_000_000) * cache_read_price
        )


# ---------------------------------------------------------------------------
# Cost Tracker — aggregates across batch
# ---------------------------------------------------------------------------


@dataclass
class ProviderStats:
    """Aggregated stats for one provider."""

    provider: str
    model: str
    call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    cache_hit_rate: float = 0.0  # percentage of reads from cache


class CostTracker:
    """Tracks token usage and costs across a batch of extractions."""

    def __init__(self) -> None:
        self.records: list[TokenRecord] = []
        self._start_time = time.time()

    def record(
        self,
        provider: str,
        model: str,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        file_name: str = "",
        doc_type: str = "",
        duration_ms: int = 0,
        cascade_triggered: bool = False,
    ) -> TokenRecord:
        """Record a single extraction's token usage."""
        rec = TokenRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            file_name=file_name,
            doc_type=doc_type,
            duration_ms=duration_ms,
            cascade_triggered=cascade_triggered,
        )
        rec.compute_cost()
        self.records.append(rec)

        logger.info(
            "Cost tracked",
            provider=provider,
            model=model,
            file=file_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read=cache_read_tokens,
            cost_usd=f"${rec.cost_usd:.4f}",
        )

        return rec

    def _stats_by_provider(self) -> dict[str, ProviderStats]:
        """Aggregate stats grouped by provider+model."""
        stats: dict[str, ProviderStats] = {}

        for rec in self.records:
            key = f"{rec.provider}/{rec.model}"
            if key not in stats:
                stats[key] = ProviderStats(provider=rec.provider, model=rec.model)

            s = stats[key]
            s.call_count += 1
            s.total_input_tokens += rec.input_tokens
            s.total_output_tokens += rec.output_tokens
            s.total_cache_creation_tokens += rec.cache_creation_tokens
            s.total_cache_read_tokens += rec.cache_read_tokens
            s.total_tokens += rec.total_tokens
            s.total_cost_usd += rec.cost_usd
            s.total_duration_ms += rec.duration_ms

        # Compute cache hit rates
        for s in stats.values():
            total_cache = s.total_cache_creation_tokens + s.total_cache_read_tokens
            if total_cache > 0:
                s.cache_hit_rate = s.total_cache_read_tokens / total_cache * 100

        return stats

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of all costs."""
        elapsed = time.time() - self._start_time
        stats = self._stats_by_provider()

        total_cost = sum(r.cost_usd for r in self.records)
        total_tokens = sum(r.total_tokens for r in self.records)
        cascade_count = sum(1 for r in self.records if r.cascade_triggered)

        provider_summaries = {}
        for key, s in stats.items():
            provider_summaries[key] = {
                "calls": s.call_count,
                "input_tokens": s.total_input_tokens,
                "output_tokens": s.total_output_tokens,
                "cache_creation_tokens": s.total_cache_creation_tokens,
                "cache_read_tokens": s.total_cache_read_tokens,
                "total_tokens": s.total_tokens,
                "cost_usd": round(s.total_cost_usd, 4),
                "avg_cost_per_call": round(s.total_cost_usd / max(s.call_count, 1), 4),
                "avg_duration_ms": round(s.total_duration_ms / max(s.call_count, 1)),
                "cache_hit_rate_pct": round(s.cache_hit_rate, 1),
            }

        return {
            "total_extractions": len(self.records),
            "cascade_triggered_count": cascade_count,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_pdf": round(total_cost / max(len(self.records), 1), 4),
            "elapsed_seconds": round(elapsed, 1),
            "providers": provider_summaries,
        }

    def summary_text(self) -> str:
        """Return a human-readable summary string."""
        s = self.summary()
        lines = [
            "=" * 60,
            "  M3NDEL BATCH EXTRACTION — COST REPORT",
            "=" * 60,
            f"  Total PDFs:       {s['total_extractions']}",
            f"  Cascades:         {s['cascade_triggered_count']}",
            f"  Total Tokens:     {s['total_tokens']:,}",
            f"  Total Cost:       ${s['total_cost_usd']:.4f}",
            f"  Avg Cost/PDF:     ${s['avg_cost_per_pdf']:.4f}",
            f"  Elapsed:          {s['elapsed_seconds']}s",
            "-" * 60,
        ]

        for key, ps in s["providers"].items():
            lines.extend([
                f"  Provider: {key}",
                f"    Calls:          {ps['calls']}",
                f"    Input Tokens:   {ps['input_tokens']:,}",
                f"    Output Tokens:  {ps['output_tokens']:,}",
                f"    Cache Created:  {ps['cache_creation_tokens']:,}",
                f"    Cache Read:     {ps['cache_read_tokens']:,}",
                f"    Cache Hit Rate: {ps['cache_hit_rate_pct']}%",
                f"    Total Cost:     ${ps['cost_usd']:.4f}",
                f"    Avg Cost/Call:  ${ps['avg_cost_per_call']:.4f}",
                f"    Avg Duration:   {ps['avg_duration_ms']}ms",
                "-" * 60,
            ])

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_records_list(self) -> list[dict[str, Any]]:
        """Return list of dicts for CSV/JSON export."""
        return [
            {
                "file_name": r.file_name,
                "doc_type": r.doc_type,
                "provider": r.provider,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cache_creation_tokens": r.cache_creation_tokens,
                "cache_read_tokens": r.cache_read_tokens,
                "total_tokens": r.total_tokens,
                "cost_usd": round(r.cost_usd, 6),
                "duration_ms": r.duration_ms,
                "cascade_triggered": r.cascade_triggered,
                "timestamp": r.timestamp,
            }
            for r in self.records
        ]
