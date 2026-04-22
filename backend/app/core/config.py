"""
Configuration management using Pydantic BaseSettings.

Loads settings from environment variables and .env files with type validation.
All required variables are validated at startup — missing values cause immediate failure.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required variables will raise ValidationError at startup if missing,
    ensuring fail-fast behavior for misconfigured deployments.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──
    APP_NAME: str = "AI Medical Multi-Agent"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Cloud LLM (required) ──
    GEMINI_API_KEY: str

    # ── Database (required) ──
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "ai_medical"
    MONGODB_MIN_POOL_SIZE: int = 1
    MONGODB_MAX_POOL_SIZE: int = 10

    # ── Local LLM via Ollama (required) ──
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "medgemma:4b"
    OLLAMA_TIMEOUT: int = 30

    # ── Cloud Coordinator ──
    GEMINI_MODEL: str = "gemini-1.5-flash"
    COORDINATOR_TIMEOUT: int = 5

    # ── Worker Pool ──
    WORKER_CONCURRENCY: int = 2

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Uses lru_cache to ensure settings are loaded only once.
    Call get_settings.cache_clear() in tests to reset.
    """
    return Settings()
