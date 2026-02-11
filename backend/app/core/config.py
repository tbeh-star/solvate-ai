from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Price Intelligence"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://pi:pi@localhost:5432/price_intelligence"

    # Auth0
    auth0_domain: str = "auth.priceintelligence.io"
    auth0_audience: str = "https://api.priceintelligence.io"
    auth0_issuer: str = ""

    # LLM (multi-provider: openai | anthropic | google)
    llm_provider: str = "openai"
    llm_model: str = ""  # auto-defaults per provider if empty
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # legacy, used if llm_model is empty + provider=openai
    openai_fallback_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""

    # M3ndel Extraction (provider: anthropic | openai | google)
    extraction_provider: str = "google"  # Primary: Gemini (20x cheaper)
    extraction_model: str = ""  # auto-defaults per provider if empty
    extraction_max_retries: int = 2
    extraction_max_file_size_mb: int = 20

    # M3ndel Cascade: auto-fallback to quality model when primary misses too many fields
    extraction_cascade_enabled: bool = True
    extraction_cascade_fallback_provider: str = "anthropic"
    extraction_cascade_fallback_model: str = "claude-sonnet-4@20250514"  # Sonnet 4 via Vertex AI (15k quota)
    extraction_cascade_missing_threshold: int = 10  # fallback if > N of 33 attributes missing

    # Vertex AI — Anthropic Claude via Google Cloud
    vertex_project_id: str = ""              # GCP project, e.g. "m3ndel-lab"
    vertex_location: str = "europe-west1"    # GCP region
    vertex_credentials_path: str = ""        # path to service-account JSON

    # Email
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    mail_username: str = ""
    mail_password: str = ""

    # Notion
    notion_api_key: str = ""
    notion_events_db_id: str = ""

    # Google Custom Search (for LinkedIn monitoring)
    google_cse_api_key: str = ""
    google_cse_id: str = ""

    # Vertex AI Search (replaces Google CSE)
    vertex_search_engine_id: str = ""
    vertex_search_project_id: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def auth0_issuer_url(self) -> str:
        if self.auth0_issuer:
            return self.auth0_issuer
        return f"https://{self.auth0_domain}/"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
