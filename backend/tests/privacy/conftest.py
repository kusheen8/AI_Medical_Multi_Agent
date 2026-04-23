"""Privacy test configuration — ensures get_settings() returns test values."""

import os
from unittest.mock import patch

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _patch_settings_env():
    """Ensure env vars exist so get_settings() works in unit tests."""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "test-gemini-key",
        "MONGODB_URI": "mongodb://localhost:27017",
    }):
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
