"""Application settings, loaded from environment variables / .env.

Kept deliberately small: only what the current stubs and health endpoint need.
Add fields here as real tool integrations grow beyond their public,
no-key-required defaults.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CURIE_", env_file=".env", extra="ignore")

    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"

    host: str = "0.0.0.0"
    port: int = 8000

    # Comma-separated extra allowed CORS origins for the deployed frontend
    # (e.g. "https://curie.vercel.app"). Local dev origins are always allowed
    # regardless of this setting — see curie/backend/api/app.py.
    cors_origins: str = ""

    http_timeout_seconds: float = 20.0

    esm_atlas_base_url: str = "https://api.esmatlas.com"
    uniprot_base_url: str = "https://rest.uniprot.org"
    iedb_base_url: str = "https://query-api.iedb.org"
    europe_pmc_base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    # Bare GEMINI_API_KEY / GEMINI_MODEL (no CURIE_ prefix), matching the
    # variable names every other Gemini-based tool expects. Entirely
    # optional: curie's graph runs fully deterministically without it — see
    # curie/agent/nodes/research_planner.py and gemini_synthesis.py.
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")


def get_settings() -> Settings:
    return Settings()
