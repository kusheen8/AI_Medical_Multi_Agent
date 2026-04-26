"""
End-to-end integration tests for the hybrid analysis pipeline.

Tests the full flow with mocked LLMs (Gemini + Ollama) but real
FastAPI routing and request handling:
1. POST /analyze/symptoms → 202 with task_id
2. Poll GET /analysis/{task_id} → status progression
3. Verify PHI boundary: no raw PHI in coordinator calls
4. Error cases: patient not found, invalid input

Note: These tests use a TestClient with mocked DB and LLM services.
Real MongoDB and Ollama integration is tested separately.
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db.client import AsyncMongoClient
from app.services.queue.task_queue import TaskQueue
from app.services.queue.task_schema import TaskStatus


# ── Fixtures ─────────────────────────────────────────────────────────────


SAMPLE_PATIENT_ID = str(ObjectId())
SAMPLE_TASK_ID = str(ObjectId())


@pytest.fixture
def mock_collection() -> MagicMock:
    collection = MagicMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find_one_and_update = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.count_documents = AsyncMock(return_value=0)
    collection.create_index = AsyncMock()

    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])
    collection.find = MagicMock(return_value=cursor)

    return collection


@pytest.fixture
def mock_db_client(mock_collection: MagicMock) -> MagicMock:
    client = MagicMock(spec=AsyncMongoClient)
    client.is_connected = True
    client.get_collection = MagicMock(return_value=mock_collection)
    client.get_database = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.ping = AsyncMock(return_value={"ok": 1.0})
    return client


@pytest.fixture
def mock_task_queue(mock_db_client: MagicMock) -> MagicMock:
    """Create a mocked TaskQueue."""
    queue = MagicMock(spec=TaskQueue)
    queue.enqueue = AsyncMock(return_value=SAMPLE_TASK_ID)
    queue.get_task = AsyncMock()
    queue.dequeue = AsyncMock(return_value=None)
    queue.mark_done = AsyncMock()
    queue.mark_failed = AsyncMock()
    queue.recover_pending = AsyncMock(return_value=0)
    queue.pending_count = 0
    return queue


@pytest.fixture
def integration_app(mock_db_client: MagicMock, mock_task_queue: MagicMock) -> any:
    """Create a test app with mocked dependencies for integration testing."""
    with patch.dict(os.environ, {
        "GROQ_API_KEY": "test-groq-key",
        "MONGODB_URI": "mongodb://localhost:27017",
    }):
        get_settings.cache_clear()
        from app.main import create_app

        app = create_app()
        app.state.db_client = mock_db_client
        app.state.health_service = MagicMock()
        app.state.task_queue = mock_task_queue
        return app


@pytest.fixture
def client(integration_app: any) -> TestClient:
    return TestClient(integration_app, raise_server_exceptions=False)


# ── Symptom Analysis Endpoint Tests ──────────────────────────────────────


class TestSymptomAnalysisEndpoint:
    """Integration tests for POST /api/v1/analyze/symptoms."""

    def test_submit_analysis_returns_202(
        self, client: TestClient, mock_collection: MagicMock,
    ) -> None:
        # Mock patient exists
        mock_collection.find_one.return_value = {
            "_id": ObjectId(SAMPLE_PATIENT_ID),
            "name": "John Doe",
            "dob": "1985-03-15",
            "sex": "M",
            "conditions": ["diabetes"],
            "medications": ["metformin"],
            "allergies": [],
        }

        response = client.post(
            "/api/v1/analyze/symptoms",
            json={
                "patient_id": SAMPLE_PATIENT_ID,
                "symptoms": "Chest pain and shortness of breath",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_submit_analysis_patient_not_found(
        self, client: TestClient, mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        response = client.post(
            "/api/v1/analyze/symptoms",
            json={
                "patient_id": SAMPLE_PATIENT_ID,
                "symptoms": "Headache",
            },
        )

        assert response.status_code == 404

    def test_submit_analysis_invalid_patient_id(
        self, client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/analyze/symptoms",
            json={
                "patient_id": "invalid-id",
                "symptoms": "Headache",
            },
        )

        assert response.status_code == 422

    def test_submit_analysis_empty_symptoms(
        self, client: TestClient,
    ) -> None:
        response = client.post(
            "/api/v1/analyze/symptoms",
            json={
                "patient_id": SAMPLE_PATIENT_ID,
                "symptoms": "",
            },
        )

        assert response.status_code == 422


# ── History Analysis Endpoint Tests ──────────────────────────────────────


class TestHistoryAnalysisEndpoint:
    """Integration tests for POST /api/v1/analyze/history."""

    def test_submit_history_returns_202(
        self, client: TestClient, mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = {
            "_id": ObjectId(SAMPLE_PATIENT_ID),
            "name": "Jane Smith",
            "dob": "1990-06-20",
            "sex": "F",
            "conditions": [],
            "medications": [],
            "allergies": [],
        }

        response = client.post(
            "/api/v1/analyze/history",
            json={
                "patient_id": SAMPLE_PATIENT_ID,
                "date_range": {"start": "2025-01-01", "end": "2026-01-01"},
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_submit_history_no_date_range(
        self, client: TestClient, mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = {
            "_id": ObjectId(SAMPLE_PATIENT_ID),
            "name": "Test Patient",
            "dob": "1985-01-01",
            "sex": "M",
            "conditions": [],
            "medications": [],
            "allergies": [],
        }

        response = client.post(
            "/api/v1/analyze/history",
            json={
                "patient_id": SAMPLE_PATIENT_ID,
            },
        )

        assert response.status_code == 202


# ── Task Polling Endpoint Tests ──────────────────────────────────────────


class TestTaskPollingEndpoint:
    """Integration tests for GET /api/v1/analysis/{task_id}."""

    def test_poll_queued_task(
        self, client: TestClient, mock_task_queue: MagicMock,
    ) -> None:
        now = datetime.now(timezone.utc)
        mock_task_queue.get_task.return_value = {
            "_id": ObjectId(SAMPLE_TASK_ID),
            "task_type": "symptom_analysis",
            "patient_id": SAMPLE_PATIENT_ID,
            "status": "queued",
            "priority": 2,
            "retries": 0,
            "result": None,
            "error": None,
            "trace_id": None,
            "created_at": now,
            "updated_at": now,
        }

        response = client.get(f"/api/v1/analysis/{SAMPLE_TASK_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["result"] is None

    def test_poll_completed_task(
        self, client: TestClient, mock_task_queue: MagicMock,
    ) -> None:
        now = datetime.now(timezone.utc)
        mock_task_queue.get_task.return_value = {
            "_id": ObjectId(SAMPLE_TASK_ID),
            "task_type": "symptom_analysis",
            "patient_id": SAMPLE_PATIENT_ID,
            "status": "completed",
            "priority": 2,
            "retries": 0,
            "result": {
                "entities": {"chest_pain": "acute"},
                "risk_level": "high",
                "recommendations": ["ECG"],
                "analysis_text": "Elevated cardiac risk.",
            },
            "error": None,
            "trace_id": "trace123",
            "created_at": now,
            "updated_at": now,
        }

        response = client.get(f"/api/v1/analysis/{SAMPLE_TASK_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["risk_level"] == "high"
        assert data["trace_id"] == "trace123"

    def test_poll_failed_task(
        self, client: TestClient, mock_task_queue: MagicMock,
    ) -> None:
        now = datetime.now(timezone.utc)
        mock_task_queue.get_task.return_value = {
            "_id": ObjectId(SAMPLE_TASK_ID),
            "task_type": "symptom_analysis",
            "patient_id": SAMPLE_PATIENT_ID,
            "status": "failed",
            "priority": 2,
            "retries": 2,
            "result": None,
            "error": "Ollama unavailable",
            "trace_id": None,
            "created_at": now,
            "updated_at": now,
        }

        response = client.get(f"/api/v1/analysis/{SAMPLE_TASK_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "Ollama" in data["error"]

    def test_poll_task_not_found(
        self, client: TestClient, mock_task_queue: MagicMock,
    ) -> None:
        mock_task_queue.get_task.return_value = None

        response = client.get(f"/api/v1/analysis/{str(ObjectId())}")

        assert response.status_code == 404

    def test_poll_invalid_task_id(
        self, client: TestClient,
    ) -> None:
        response = client.get("/api/v1/analysis/invalid-id")

        assert response.status_code == 422


# ── PHI Boundary Verification ───────────────────────────────────────────


class TestPHIBoundary:
    """Verify that no raw PHI reaches cloud API calls."""

    def test_de_identified_context_has_no_phi(self) -> None:
        """Verify that PrivacyFilter strips all patient identifiers."""
        from app.services.privacy_filter import PrivacyFilter

        privacy_filter = PrivacyFilter()

        patient_doc = {
            "name": "John Doe",
            "dob": "1985-03-15",
            "sex": "M",
            "conditions": ["diabetes", "hypertension"],
            "medications": ["metformin", "lisinopril"],
            "allergies": ["penicillin"],
        }

        context = privacy_filter.prepare_coordinator_context(
            patient_doc=patient_doc,
            symptoms="Chest pain, shortness of breath, dizziness",
        )

        context_str = json.dumps(context)

        # No raw PHI
        assert "John Doe" not in context_str
        assert "1985-03-15" not in context_str
        assert "chest pain" not in context_str.lower()
        assert "shortness of breath" not in context_str.lower()

        # Has de-identified data
        assert context["age_bracket"] in ("40-49",)
        assert "endocrine" in context["condition_categories"]
        assert "cardiovascular" in context["condition_categories"]

    def test_phi_scanner_catches_leaked_data(self) -> None:
        """Verify PHIScanner detects common PHI patterns."""
        from app.core.privacy import PHIScanner

        scanner = PHIScanner()

        # Should detect SSN
        assert scanner.contains_phi("SSN: 123-45-6789")

        # Should detect email
        assert scanner.contains_phi("Email: patient@example.com")

        # Should detect names
        assert scanner.contains_phi("Patient John Doe was admitted")

        # Should NOT flag de-identified data
        assert not scanner.contains_phi(
            "age_bracket: 40-49, categories: endocrine, cardiovascular"
        )
