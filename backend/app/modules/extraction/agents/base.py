"""M3ndel BaseAgent — Shared LLM call logic, JSON parsing, cost tracking.

Consolidates the duplicated LLM-call patterns from batch_extractor.py into
a reusable base class for all agents.

Providers supported:
  - google (Gemini Flash / Pro)
  - anthropic (Claude Sonnet / Opus via direct API or Vertex AI)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings
from app.modules.extraction.agents.sanitizer import strip_code_fences
from app.modules.extraction.cost_tracker import CostTracker

logger = structlog.get_logger()

# Default models per provider
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4@20250514",
    "google": "gemini-2.5-flash",
    "openai": "gpt-4.1",
}

# Directory where prompt templates live
_PROMPTS_DIR = Path(__file__).parent / "prompts"


class BaseAgent:
    """Base class for all M3ndel agents.

    Provides:
      - LLM client initialization (Gemini / Anthropic)
      - Unified call_llm() with token tracking
      - Prompt loading from prompts/ directory
      - JSON parsing with code-fence stripping
      - Cost tracking integration
    """

    agent_name: str = "base"

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.provider = provider or settings.extraction_provider
        self.model = model or settings.extraction_model or DEFAULT_MODELS.get(self.provider, "")
        self.cost_tracker = cost_tracker

        # Lazy-initialized clients
        self._gemini_client: Any = None
        self._anthropic_client: Any = None
        self._is_vertex = False

        logger.info(
            f"{self.agent_name} initialized",
            provider=self.provider,
            model=self.model,
        )

    # ------------------------------------------------------------------
    # Prompt loading
    # ------------------------------------------------------------------

    @staticmethod
    def load_prompt(filename: str) -> str:
        """Load a prompt template from the prompts/ directory."""
        path = _PROMPTS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    # ------------------------------------------------------------------
    # LLM client builders (lazy)
    # ------------------------------------------------------------------

    def _get_gemini_client(self) -> Any:
        """Get or create the Gemini client."""
        if self._gemini_client is None:
            from google import genai
            from google.genai import types as genai_types

            self._gemini_client = genai.Client(
                api_key=settings.google_ai_api_key,
                http_options=genai_types.HttpOptions(timeout=120_000),
            )
        return self._gemini_client

    def _get_anthropic_client(self) -> Any:
        """Get or create the Anthropic client (direct or Vertex AI)."""
        if self._anthropic_client is None:
            import anthropic

            if settings.vertex_credentials_path:
                import os
                os.environ.setdefault(
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    settings.vertex_credentials_path,
                )
                self._anthropic_client = anthropic.AnthropicVertex(
                    project_id=settings.vertex_project_id,
                    region=settings.vertex_location,
                )
                self._is_vertex = True
            else:
                self._anthropic_client = anthropic.Anthropic(
                    api_key=settings.anthropic_api_key,
                )
                self._is_vertex = False

        return self._anthropic_client

    # ------------------------------------------------------------------
    # Unified LLM call
    # ------------------------------------------------------------------

    def call_llm(
        self,
        system_prompt: str,
        user_content: str,
        *,
        response_json: bool = True,
        file_name: str = "",
        doc_type: str = "",
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Call the configured LLM provider and return parsed result + metadata.

        Returns:
            {
                "content": str | dict,  # Raw text or parsed JSON
                "input_tokens": int,
                "output_tokens": int,
                "cache_creation_tokens": int,
                "cache_read_tokens": int,
                "duration_ms": int,
                "provider": str,
                "model": str,
            }
        """
        if self.provider == "google":
            return self._call_gemini(
                system_prompt, user_content,
                response_json=response_json,
                file_name=file_name,
                doc_type=doc_type,
                temperature=temperature,
            )
        elif self.provider == "anthropic":
            return self._call_anthropic(
                system_prompt, user_content,
                file_name=file_name,
                doc_type=doc_type,
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _call_gemini(
        self,
        system_prompt: str,
        user_content: str,
        *,
        response_json: bool = True,
        file_name: str = "",
        doc_type: str = "",
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Call Gemini and return structured result."""
        from google.genai import types

        client = self._get_gemini_client()
        start = time.time()

        config_kwargs: dict[str, Any] = {
            "system_instruction": system_prompt,
            "temperature": temperature,
        }
        if response_json:
            config_kwargs["response_mime_type"] = "application/json"

        response = client.models.generate_content(
            model=self.model,
            contents=user_content,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        duration_ms = int((time.time() - start) * 1000)
        usage = response.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0

        raw_text = response.text

        logger.info(
            f"{self.agent_name} Gemini call",
            file=file_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
        )

        # Track cost
        if self.cost_tracker:
            self.cost_tracker.record(
                provider="google",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cached_tokens,
                file_name=file_name,
                doc_type=doc_type,
                duration_ms=duration_ms,
            )

        # Parse if JSON expected
        content: str | dict = raw_text
        if response_json:
            content = self.parse_json(raw_text)

        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_tokens": 0,
            "cache_read_tokens": cached_tokens,
            "duration_ms": duration_ms,
            "provider": "google",
            "model": self.model,
        }

    def _call_anthropic(
        self,
        system_prompt: str,
        user_content: str,
        *,
        file_name: str = "",
        doc_type: str = "",
    ) -> dict[str, Any]:
        """Call Anthropic (direct or Vertex) and return structured result."""
        client = self._get_anthropic_client()
        start = time.time()

        # Prompt caching for direct API
        if not self._is_vertex:
            system_messages: Any = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_messages = system_prompt

        response = client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_messages,
            messages=[{"role": "user", "content": user_content}],
        )

        duration_ms = int((time.time() - start) * 1000)
        usage = response.usage
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

        raw_text = response.content[0].text

        logger.info(
            f"{self.agent_name} Anthropic call",
            file=file_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_created=cache_creation,
            cache_read=cache_read,
            duration_ms=duration_ms,
        )

        # Track cost
        if self.cost_tracker:
            self.cost_tracker.record(
                provider="anthropic",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation,
                cache_read_tokens=cache_read,
                file_name=file_name,
                doc_type=doc_type,
                duration_ms=duration_ms,
            )

        # Parse JSON
        content: str | dict = self.parse_json(raw_text)

        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
            "duration_ms": duration_ms,
            "provider": "anthropic",
            "model": self.model,
        }

    # ------------------------------------------------------------------
    # JSON parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_json(raw_text: str) -> dict:
        """Parse LLM output as JSON, stripping code fences if present."""
        text = strip_code_fences(raw_text)
        return json.loads(text)
