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
    GROQ_API_KEY: str

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
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    COORDINATOR_TIMEOUT: int = 5

    # ── Worker Pool ──
    WORKER_CONCURRENCY: int = 2

    # ── Notification Providers (Phase 4) ──
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = ""
    FCM_SERVER_KEY: str = ""

    # ── Webhook & Security (Phase 4) ──
    WEBHOOK_SIGNING_SECRET: str = ""
    ADMIN_API_KEY: str = "dev-admin-key"

    # ── Notification Behavior (Phase 4) ──
    NOTIFICATION_DRY_RUN: bool = True

    # ── Alert Retry Config (Phase 4) ──
    ALERT_RETRY_MAX_ATTEMPTS: int = 3
    ALERT_RETRY_BASE_DELAY: float = 5.0
    ALERT_RETRY_MULTIPLIER: float = 2.0

    # ── Circuit Breaker Config (Phase 4) ──
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: float = 30.0

    # ── Phase 5: Authentication & Authorization ──
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REQUIRE_AUTH: bool = False  # Set True in production to enforce auth

    # ── Phase 5: CORS ──
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # ── Phase 5: Rate Limiting ──
    RATE_LIMIT_LOGIN: int = 100  # requests per minute per IP
    RATE_LIMIT_API: int = 1000   # requests per minute per authenticated user

    # ── Phase 5: Field Encryption ──
    FIELD_ENCRYPTION_KEY: str = ""  # Fernet key; generate via Fernet.generate_key()

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    @property
    def notification_dry_run_effective(self) -> bool:
        """Resolve effective dry-run state (always True in dev unless overridden)."""
        if self.is_development:
            return True
        return self.NOTIFICATION_DRY_RUN


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Uses lru_cache to ensure settings are loaded only once.
    Call get_settings.cache_clear() in tests to reset.
    """
    return Settings()
