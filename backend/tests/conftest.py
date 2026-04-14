"""
Shared test fixtures for the AI Medical Multi-Agent test suite.

Provides:
- test_settings: Deterministic Settings instance (no .env dependency)
- mock_db_client: Mocked AsyncMongoClient
- mock_collection: Reusable mocked Motor collection
- test_app / test_client: FastAPI TestClient with overridden dependencies
- Sample data factories: sample_patient_data, sample_record_data, sample_alert_data
"""

import os
from datetime import date, datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.client import AsyncMongoClient


# ── Deterministic settings ──────────────────────────────────────────────


@pytest.fixture
def test_settings() -> Settings:
    """Return a settings instance with deterministic test values."""
    return Settings(
        APP_NAME="test-app",
        APP_VERSION="0.0.1",
        APP_ENV="development",
        LOG_LEVEL="DEBUG",
        GEMINI_API_KEY="test-gemini-key",
        MONGODB_URI="mongodb://localhost:27017",
        MONGODB_DB_NAME="test_ai_medical",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="medgemma:4b",
    )


# ── Mock MongoDB client ────────────────────────────────────────────────


@pytest.fixture
def mock_collection() -> MagicMock:
    """Create a mock Motor collection with common async methods stubbed."""
    collection = MagicMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find_one_and_update = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.count_documents = AsyncMock(return_value=0)
    collection.create_index = AsyncMock()

    # find() returns a chainable cursor mock
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])
    collection.find = MagicMock(return_value=cursor)

    return collection


@pytest.fixture
def mock_db_client(mock_collection: MagicMock) -> MagicMock:
    """Create a mocked AsyncMongoClient that returns the mock collection."""
    client = MagicMock(spec=AsyncMongoClient)
    client.is_connected = True
    client.get_collection = MagicMock(return_value=mock_collection)
    client.get_database = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.ping = AsyncMock(return_value={"ok": 1.0})
    return client


# ── Test app & client ───────────────────────────────────────────────────


@pytest.fixture
def test_app(mock_db_client: MagicMock, test_settings: Settings) -> Any:
    """Create a FastAPI test app with mocked dependencies."""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "test-gemini-key",
        "MONGODB_URI": "mongodb://localhost:27017",
    }):
        get_settings.cache_clear()
        from app.main import create_app

        app = create_app()
        app.state.db_client = mock_db_client
        app.state.health_service = MagicMock()
        return app


@pytest.fixture
def test_client(test_app: Any) -> TestClient:
    """Create a TestClient from the test app."""
    return TestClient(test_app, raise_server_exceptions=False)


# ── Sample data factories ──────────────────────────────────────────────

SAMPLE_OBJECT_ID = str(ObjectId())
SAMPLE_PATIENT_ID = str(ObjectId())
SAMPLE_RECORD_ID = str(ObjectId())
SAMPLE_ALERT_ID = str(ObjectId())


@pytest.fixture
def sample_patient_data() -> dict[str, Any]:
    """Return a valid patient creation payload."""
    return {
        "name": "John Doe",
        "dob": "1985-03-15",
        "sex": "M",
        "conditions": ["diabetes", "hypertension"],
        "medications": ["metformin", "lisinopril"],
        "allergies": ["penicillin"],
    }


@pytest.fixture
def sample_patient_doc() -> dict[str, Any]:
    """Return a patient document as it would appear in MongoDB."""
    return {
        "_id": ObjectId(SAMPLE_PATIENT_ID),
        "name": "John Doe",
        "dob": "1985-03-15",
        "sex": "M",
        "conditions": ["diabetes", "hypertension"],
        "medications": ["metformin", "lisinopril"],
        "allergies": ["penicillin"],
        "created_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_record_data() -> dict[str, Any]:
    """Return a valid medical record creation payload."""
    return {
        "patient_id": SAMPLE_PATIENT_ID,
        "symptoms": "Chest pain, shortness of breath",
    }


@pytest.fixture
def sample_record_doc() -> dict[str, Any]:
    """Return a medical record document as it would appear in MongoDB."""
    return {
        "_id": ObjectId(SAMPLE_RECORD_ID),
        "patient_id": SAMPLE_PATIENT_ID,
        "symptoms": "Chest pain, shortness of breath",
        "entities": {"symptom1": "chest pain", "severity": "high"},
        "analysis_result": "Possible cardiac issue; recommend EKG",
        "risk_level": "high",
        "created_at": datetime(2026, 3, 1, 11, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, 11, 30, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_alert_data() -> dict[str, Any]:
    """Return a valid alert creation payload."""
    return {
        "patient_id": SAMPLE_PATIENT_ID,
        "severity": "critical",
        "trigger": "High risk cardiac symptoms detected",
        "channels": ["sms", "email"],
    }


@pytest.fixture
def sample_alert_doc() -> dict[str, Any]:
    """Return an alert document as it would appear in MongoDB."""
    return {
        "_id": ObjectId(SAMPLE_ALERT_ID),
        "patient_id": SAMPLE_PATIENT_ID,
        "severity": "critical",
        "trigger": "High risk cardiac symptoms detected",
        "channels": ["sms", "email"],
        "status": "pending",
        "delivery_receipts": [],
        "created_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
    }
