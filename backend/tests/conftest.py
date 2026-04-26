"""
Shared test fixtures for the AI Medical Multi-Agent test suite.

Provides:
- test_settings: Deterministic Settings instance (no .env dependency)
- mock_db_client: Mocked AsyncMongoClient
- mock_collection: Reusable mocked Motor collection
- test_app / test_client: FastAPI TestClient with overridden dependencies
- Sample data factories: sample_patient_data, sample_record_data, sample_alert_data
- Phase 3 fixtures: sample_trace_data, sample_task_data, mock_task_queue
- Phase 4 fixtures: mock_notifier, mock_policy_engine, mock_metrics, mock_dlq
- Phase 5 fixtures: auth headers, user data, encryption key
"""

import os
from datetime import date, datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.client import AsyncMongoClient


# ── Deterministic settings ──────────────────────────────────────────────

# Pre-generate a Fernet key for test encryption
_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture
def test_settings() -> Settings:
    """Return a settings instance with deterministic test values."""
    return Settings(
        APP_NAME="test-app",
        APP_VERSION="0.0.1",
        APP_ENV="development",
        LOG_LEVEL="DEBUG",
        GROQ_API_KEY="test-groq-key",
        MONGODB_URI="mongodb://localhost:27017",
        MONGODB_DB_NAME="test_ai_medical",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="medgemma:4b",
        ADMIN_API_KEY="test-admin-key",
        NOTIFICATION_DRY_RUN=True,
        # Phase 5 settings
        JWT_SECRET_KEY="test-jwt-secret-key-for-testing-only",
        FIELD_ENCRYPTION_KEY=_TEST_FERNET_KEY,
        REQUIRE_AUTH=False,
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
    collection.delete_many = AsyncMock()
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
        "GROQ_API_KEY": "test-groq-key",
        "MONGODB_URI": "mongodb://localhost:27017",
    }):
        get_settings.cache_clear()
        from app.main import create_app

        app = create_app()
        app.state.db_client = mock_db_client
        app.state.settings = test_settings
        app.state.health_service = MagicMock()
        # Phase 3: task queue mock
        mock_queue = MagicMock()
        mock_queue.enqueue = AsyncMock(return_value=str(ObjectId()))
        mock_queue.get_task = AsyncMock(return_value=None)
        mock_queue.dequeue = AsyncMock(return_value=None)
        mock_queue.mark_done = AsyncMock()
        mock_queue.mark_failed = AsyncMock()
        mock_queue.recover_pending = AsyncMock(return_value=0)
        mock_queue.pending_count = 0
        app.state.task_queue = mock_queue
        # Phase 4: notification-related mocks
        app.state.caregiver_notifier = MagicMock()
        app.state.caregiver_notifier.dispatch = AsyncMock(return_value=[])
        app.state.policy_engine = MagicMock()
        app.state.policy_engine.evaluate = AsyncMock(return_value=[])
        app.state.metrics_collector = MagicMock()
        app.state.metrics_collector.record_alert_created = MagicMock()
        app.state.metrics_collector.record_delivery_attempt = MagicMock()
        app.state.metrics_collector.set_queue_length = MagicMock()
        app.state.metrics_collector.get_prometheus_format = MagicMock(
            return_value="# test metrics\nalert_created_total 0\n"
        )
        app.state.metrics_collector.get_summary = MagicMock(return_value={
            "alerts": {"total_created": 0},
            "delivery": {},
            "queue": {"length": 0},
            "circuit_breakers": {},
        })
        app.state.dlq_manager = MagicMock()
        app.state.dlq_manager.get_count = AsyncMock(return_value=0)
        app.state.dlq_manager.list_dlq = AsyncMock(return_value={
            "items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0,
        })
        app.state.dlq_manager.get_dlq_item = AsyncMock(return_value=None)
        app.state.dlq_manager.mark_retried = AsyncMock(return_value=True)
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
        "idempotency_key": None,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "created_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
    }


# ── Phase 3 fixtures ───────────────────────────────────────────────────

SAMPLE_TRACE_ID = str(ObjectId())
SAMPLE_TASK_ID = str(ObjectId())


@pytest.fixture
def sample_trace_data() -> dict[str, Any]:
    """Return a valid reasoning trace creation payload."""
    return {
        "task_type": "symptom_analysis",
        "instructions": "Analyze cardiovascular symptoms and assess risk.",
        "allowed_data_classes": ["vitals", "symptoms", "medications"],
        "origin": "gemini_coordinator",
        "expires_at": datetime(2026, 4, 2, 13, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_trace_doc() -> dict[str, Any]:
    """Return a reasoning trace document as it would appear in MongoDB."""
    return {
        "_id": ObjectId(SAMPLE_TRACE_ID),
        "task_type": "symptom_analysis",
        "instructions": "Analyze cardiovascular symptoms and assess risk.",
        "allowed_data_classes": ["vitals", "symptoms", "medications"],
        "origin": "gemini_coordinator",
        "task_id": SAMPLE_TASK_ID,
        "patient_id": SAMPLE_PATIENT_ID,
        "expires_at": datetime(2026, 4, 2, 13, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2026, 4, 1, 13, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 1, 13, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """Return a valid task creation payload."""
    return {
        "task_type": "symptom_analysis",
        "patient_id": SAMPLE_PATIENT_ID,
        "payload": {"symptoms": "Chest pain, shortness of breath"},
    }


@pytest.fixture
def sample_task_doc() -> dict[str, Any]:
    """Return a task document as it would appear in MongoDB."""
    return {
        "_id": ObjectId(SAMPLE_TASK_ID),
        "task_type": "symptom_analysis",
        "patient_id": SAMPLE_PATIENT_ID,
        "payload": {"symptoms": "Chest pain, shortness of breath"},
        "status": "queued",
        "priority": 2,
        "retries": 0,
        "max_retries": 3,
        "result": None,
        "error": None,
        "trace_id": None,
        "created_at": datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc),
    }


# ── Phase 4 fixtures ───────────────────────────────────────────────────


SAMPLE_POLICY_RULE_ID = str(ObjectId())
SAMPLE_DLQ_ID = str(ObjectId())


@pytest.fixture
def sample_policy_rule_doc() -> dict[str, Any]:
    """Return a policy rule document as it would appear in MongoDB."""
    return {
        "_id": ObjectId(SAMPLE_POLICY_RULE_ID),
        "name": "Critical Risk Emergency Alert",
        "description": "Immediate alert for critical risk assessments.",
        "condition_type": "risk_threshold",
        "risk_level": "critical",
        "threshold_params": {"min_risk_level": "critical"},
        "action": "escalate",
        "severity": "critical",
        "channels": ["sms", "email", "push"],
        "enabled": True,
        "dry_run": False,
        "version": 1,
        "created_at": datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_dlq_doc() -> dict[str, Any]:
    """Return a DLQ entry document."""
    return {
        "_id": ObjectId(SAMPLE_DLQ_ID),
        "notification_id": str(ObjectId()),
        "alert_id": SAMPLE_ALERT_ID,
        "channel": "sms",
        "error": "Connection timeout",
        "attempts": 3,
        "status": "pending",
        "metadata": {},
        "created_at": datetime(2026, 4, 1, 15, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 4, 1, 15, 0, 0, tzinfo=timezone.utc),
    }


# ── Phase 5 fixtures ───────────────────────────────────────────────────

SAMPLE_USER_ID = str(ObjectId())


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Return a valid user registration payload."""
    return {
        "email": "test@example.com",
        "password": "TestPass123",
        "full_name": "Test User",
        "role": "patient",
    }


@pytest.fixture
def sample_admin_user_data() -> dict[str, Any]:
    """Return an admin user registration payload."""
    return {
        "email": "admin@example.com",
        "password": "AdminPass123",
        "full_name": "Admin User",
        "role": "admin",
    }


@pytest.fixture
def auth_headers(test_settings: Settings) -> dict[str, str]:
    """Generate JWT auth headers for a test patient user."""
    from app.core.security import create_access_token
    from app.models.user import UserRole

    token = create_access_token(
        user_id=SAMPLE_USER_ID,
        role=UserRole.PATIENT,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_settings: Settings) -> dict[str, str]:
    """Generate JWT auth headers for an admin user."""
    from app.core.security import create_access_token
    from app.models.user import UserRole

    token = create_access_token(
        user_id=SAMPLE_USER_ID,
        role=UserRole.ADMIN,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def doctor_auth_headers(test_settings: Settings) -> dict[str, str]:
    """Generate JWT auth headers for a doctor user."""
    from app.core.security import create_access_token
    from app.models.user import UserRole

    token = create_access_token(
        user_id=SAMPLE_USER_ID,
        role=UserRole.DOCTOR,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset rate limiter state between tests."""
    from app.core.rate_limiter import reset_rate_limiter
    reset_rate_limiter()
    yield
    reset_rate_limiter()


@pytest.fixture(autouse=True)
def _reset_encryption():
    """Reset field encryptor singleton between tests."""
    from app.core.encryption import reset_field_encryptor
    reset_field_encryptor()
    yield
    reset_field_encryptor()

