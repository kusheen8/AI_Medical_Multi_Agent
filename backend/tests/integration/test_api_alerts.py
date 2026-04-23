"""
Integration tests for alert API endpoints.

Tests alert CRUD, acknowledge flow, webhook processing,
and admin endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from tests.conftest import SAMPLE_ALERT_ID, SAMPLE_PATIENT_ID


# ── Alert CRUD Tests ─────────────────────────────────────────────────────


class TestAlertCreation:
    """Tests for POST /api/v1/alerts."""

    def test_create_alert_success(self, test_client: TestClient, test_app: Any):
        # Mock the insert operation
        alert_id = ObjectId()
        test_app.state.db_client.get_collection.return_value.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=alert_id)
        )
        test_app.state.db_client.get_collection.return_value.find_one = AsyncMock(
            return_value=None  # No idempotency key match
        )

        response = test_client.post("/api/v1/alerts", json={
            "patient_id": SAMPLE_PATIENT_ID,
            "severity": "critical",
            "trigger": "High risk symptoms detected",
            "channels": ["sms", "email"],
        })
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_create_alert_with_idempotency_key(self, test_client: TestClient, test_app: Any):
        alert_id = ObjectId()
        collection_mock = test_app.state.db_client.get_collection.return_value
        collection_mock.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=alert_id)
        )
        collection_mock.find_one = AsyncMock(return_value=None)

        idem_key = str(uuid.uuid4())
        response = test_client.post(
            "/api/v1/alerts",
            json={
                "patient_id": SAMPLE_PATIENT_ID,
                "severity": "critical",
                "trigger": "Emergency symptoms",
                "channels": ["sms"],
            },
            headers={"Idempotency-Key": idem_key},
        )
        assert response.status_code == 201

    def test_create_alert_invalid_patient_id(self, test_client: TestClient):
        response = test_client.post("/api/v1/alerts", json={
            "patient_id": "invalid-id",
            "severity": "critical",
            "trigger": "Test",
            "channels": ["sms"],
        })
        assert response.status_code == 422

    def test_create_alert_missing_trigger(self, test_client: TestClient):
        response = test_client.post("/api/v1/alerts", json={
            "patient_id": SAMPLE_PATIENT_ID,
            "severity": "critical",
            "channels": ["sms"],
        })
        assert response.status_code == 422

    def test_create_alert_empty_channels(self, test_client: TestClient):
        response = test_client.post("/api/v1/alerts", json={
            "patient_id": SAMPLE_PATIENT_ID,
            "severity": "critical",
            "trigger": "Test",
            "channels": [],
        })
        assert response.status_code == 422


class TestAlertRetrieval:
    """Tests for GET /api/v1/alerts/{id}."""

    def test_get_alert_success(self, test_client: TestClient, test_app: Any, sample_alert_doc: dict):
        test_app.state.db_client.get_collection.return_value.find_one = AsyncMock(
            return_value=sample_alert_doc
        )
        response = test_client.get(f"/api/v1/alerts/{SAMPLE_ALERT_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["severity"] == "critical"

    def test_get_alert_invalid_id(self, test_client: TestClient):
        response = test_client.get("/api/v1/alerts/invalid-id")
        assert response.status_code == 422


class TestAlertAcknowledge:
    """Tests for PUT /api/v1/alerts/{id}/acknowledge."""

    def test_acknowledge_success(self, test_client: TestClient, test_app: Any, sample_alert_doc: dict):
        ack_doc = {**sample_alert_doc, "status": "delivered", "acknowledged_by": "caregiver-1"}
        test_app.state.db_client.get_collection.return_value.find_one_and_update = AsyncMock(
            return_value=ack_doc
        )
        response = test_client.put(
            f"/api/v1/alerts/{SAMPLE_ALERT_ID}/acknowledge",
            json={"acknowledged_by": "caregiver-1"},
        )
        assert response.status_code == 200

    def test_acknowledge_invalid_id(self, test_client: TestClient):
        response = test_client.put(
            "/api/v1/alerts/bad-id/acknowledge",
            json={"acknowledged_by": "caregiver-1"},
        )
        assert response.status_code == 422


class TestPatientAlerts:
    """Tests for GET /api/v1/patients/{patient_id}/alerts."""

    def test_list_patient_alerts(self, test_client: TestClient, test_app: Any, sample_alert_doc: dict):
        collection = test_app.state.db_client.get_collection.return_value
        collection.count_documents = AsyncMock(return_value=1)
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        cursor.to_list = AsyncMock(return_value=[sample_alert_doc])
        collection.find = MagicMock(return_value=cursor)

        response = test_client.get(f"/api/v1/patients/{SAMPLE_PATIENT_ID}/alerts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_patient_alerts_invalid_id(self, test_client: TestClient):
        response = test_client.get("/api/v1/patients/bad-id/alerts")
        assert response.status_code == 422


# ── Webhook Tests ────────────────────────────────────────────────────────


class TestWebhooks:
    """Tests for webhook endpoints."""

    def test_sms_webhook(self, test_client: TestClient, test_app: Any, sample_alert_doc: dict):
        test_app.state.db_client.get_collection.return_value.find_one_and_update = AsyncMock(
            return_value=sample_alert_doc
        )
        response = test_client.post("/api/v1/webhooks/sms-status", json={
            "MessageSid": "SM123456",
            "MessageStatus": "delivered",
            "alert_id": SAMPLE_ALERT_ID,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    def test_sms_webhook_no_alert_id(self, test_client: TestClient):
        response = test_client.post("/api/v1/webhooks/sms-status", json={
            "MessageSid": "SM123456",
            "MessageStatus": "delivered",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_email_webhook(self, test_client: TestClient, test_app: Any, sample_alert_doc: dict):
        test_app.state.db_client.get_collection.return_value.find_one_and_update = AsyncMock(
            return_value=sample_alert_doc
        )
        response = test_client.post("/api/v1/webhooks/email-status", json={
            "event": "delivered",
            "alert_id": SAMPLE_ALERT_ID,
        })
        assert response.status_code == 200

    def test_push_webhook(self, test_client: TestClient, test_app: Any, sample_alert_doc: dict):
        test_app.state.db_client.get_collection.return_value.find_one_and_update = AsyncMock(
            return_value=sample_alert_doc
        )
        response = test_client.post("/api/v1/webhooks/push-status", json={
            "status": "delivered",
            "alert_id": SAMPLE_ALERT_ID,
        })
        assert response.status_code == 200


# ── Admin Tests ──────────────────────────────────────────────────────────


class TestAdminEndpoints:
    """Tests for admin dashboard endpoints."""

    def test_health_summary_with_auth(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == 200

    def test_health_summary_no_auth(self, test_client: TestClient):
        response = test_client.get("/api/v1/admin/health/summary")
        assert response.status_code == 403  # No JWT or API key provided

    def test_health_summary_bad_auth(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_failed_alerts_admin(self, test_client: TestClient, test_app: Any):
        collection = test_app.state.db_client.get_collection.return_value
        collection.count_documents = AsyncMock(return_value=0)
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)
        cursor.skip = MagicMock(return_value=cursor)
        cursor.limit = MagicMock(return_value=cursor)
        cursor.to_list = AsyncMock(return_value=[])
        collection.find = MagicMock(return_value=cursor)

        response = test_client.get(
            "/api/v1/admin/alerts/failed",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == 200

    def test_dlq_retry_not_found(self, test_client: TestClient):
        dlq_id = str(ObjectId())
        response = test_client.post(
            f"/api/v1/admin/dlq/retry/{dlq_id}",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == 404


# ── Metrics Endpoint Tests ───────────────────────────────────────────────


class TestMetricsEndpoint:
    """Tests for GET /api/v1/metrics."""

    def test_metrics_prometheus_format(self, test_client: TestClient):
        response = test_client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        assert "alert_created_total" in response.text

    def test_metrics_summary_json(self, test_client: TestClient):
        response = test_client.get("/api/v1/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
