"""
Unit tests for core/config.py — Settings loading and validation.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


# Minimal valid environment for Settings
VALID_ENV = {
    "GEMINI_API_KEY": "test-api-key-123",
    "MONGODB_URI": "mongodb://localhost:27017",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "medgemma:4b",
}


class TestSettings:
    """Tests for the Settings class."""

    def test_settings_loads_from_env(self) -> None:
        """Settings should load all required values from environment."""
        with patch.dict(os.environ, VALID_ENV, clear=False):
            settings = Settings()  # type: ignore[call-arg]

        assert settings.GEMINI_API_KEY == "test-api-key-123"
        assert settings.MONGODB_URI == "mongodb://localhost:27017"
        assert settings.OLLAMA_BASE_URL == "http://localhost:11434"
        assert settings.OLLAMA_MODEL == "medgemma:4b"

    def test_settings_defaults(self) -> None:
        """Settings should apply correct defaults for optional fields."""
        with patch.dict(os.environ, VALID_ENV, clear=False):
            settings = Settings()  # type: ignore[call-arg]

        assert settings.APP_NAME == "AI Medical Multi-Agent"
        assert settings.APP_VERSION == "0.1.0"
        assert settings.APP_ENV == "development"
        assert settings.LOG_LEVEL == "INFO"
        assert settings.MONGODB_DB_NAME == "ai_medical"
        assert settings.MONGODB_MIN_POOL_SIZE == 1
        assert settings.MONGODB_MAX_POOL_SIZE == 10

    def test_settings_missing_gemini_key_raises(self) -> None:
        """Settings should fail validation when GEMINI_API_KEY is missing."""
        env = {k: v for k, v in VALID_ENV.items() if k != "GEMINI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()  # type: ignore[call-arg]
        assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_settings_missing_mongodb_uri_raises(self) -> None:
        """Settings should fail validation when MONGODB_URI is missing."""
        env = {k: v for k, v in VALID_ENV.items() if k != "MONGODB_URI"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()  # type: ignore[call-arg]
        assert "MONGODB_URI" in str(exc_info.value)

    def test_settings_custom_values(self) -> None:
        """Settings should accept custom values for optional fields."""
        custom_env = {
            **VALID_ENV,
            "APP_ENV": "production",
            "LOG_LEVEL": "DEBUG",
            "MONGODB_DB_NAME": "custom_db",
            "MONGODB_MIN_POOL_SIZE": "5",
            "MONGODB_MAX_POOL_SIZE": "50",
        }
        with patch.dict(os.environ, custom_env, clear=False):
            settings = Settings()  # type: ignore[call-arg]

        assert settings.APP_ENV == "production"
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.MONGODB_DB_NAME == "custom_db"
        assert settings.MONGODB_MIN_POOL_SIZE == 5
        assert settings.MONGODB_MAX_POOL_SIZE == 50

    def test_is_production_property(self) -> None:
        """is_production should return True only in production mode."""
        env_prod = {**VALID_ENV, "APP_ENV": "production"}
        with patch.dict(os.environ, env_prod, clear=False):
            settings = Settings()  # type: ignore[call-arg]
        assert settings.is_production is True
        assert settings.is_development is False

    def test_is_development_property(self) -> None:
        """is_development should return True only in development mode."""
        with patch.dict(os.environ, VALID_ENV, clear=False):
            settings = Settings()  # type: ignore[call-arg]
        assert settings.is_development is True
        assert settings.is_production is False

    def test_invalid_app_env_raises(self) -> None:
        """Settings should reject invalid APP_ENV values."""
        env = {**VALID_ENV, "APP_ENV": "invalid_env"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValidationError):
                Settings()  # type: ignore[call-arg]

    def test_invalid_log_level_raises(self) -> None:
        """Settings should reject invalid LOG_LEVEL values."""
        env = {**VALID_ENV, "LOG_LEVEL": "VERBOSE"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValidationError):
                Settings()  # type: ignore[call-arg]


class TestGetSettings:
    """Tests for the get_settings() singleton function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """get_settings() should return a Settings instance."""
        get_settings.cache_clear()
        with patch.dict(os.environ, VALID_ENV, clear=False):
            settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_caches(self) -> None:
        """get_settings() should return the same instance on repeated calls."""
        get_settings.cache_clear()
        with patch.dict(os.environ, VALID_ENV, clear=False):
            s1 = get_settings()
            s2 = get_settings()
        assert s1 is s2
        get_settings.cache_clear()
