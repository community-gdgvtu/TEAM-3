"""Runtime configuration.

Values are read from the environment (see ``.env.example``). No secrets are
committed; missing values fall back to safe defaults so the app always boots.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="URBAN_",
        extra="ignore",
    )

    app_name: str = "URBAN Policy Digital Twin"
    version: str = "0.1.0"
    environment: str = "development"

    # Comma-separated list of allowed CORS origins for the frontend.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM key is optional at boot. Code paths that need it must degrade to a
    # rule-based fallback when it is absent (see AGENT_LOOP.md). Never hardcode.
    llm_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


settings = Settings()
