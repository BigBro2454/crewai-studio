"""CrewAI Studio – Application settings using pydantic-settings."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "CrewAI Studio"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # ── LLM Providers ────────────────────────────────────────────────────────
    default_llm_provider: Literal["openai", "anthropic", "google"] = "openai"

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = "gemini-3.1-flash-lite"

    # ── Tools ─────────────────────────────────────────────────────────────────
    serper_api_key: str = ""
    browserless_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
