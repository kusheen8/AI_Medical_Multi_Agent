"""
Injection prevention test suite (D5.9).

Tests that various injection attacks are properly handled:
- NoSQL injection blocked by Pydantic validation
- Path traversal prevented
- XSS payloads treated as plain text (JSON API)
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from tests.conftest import SAMPLE_PATIENT_ID


class TestNoSQLInjection:
    """Test that NoSQL injection payloads are safely handled."""

    def test_operator_injection_in_query_param(self, test_client: TestClient):
        """MongoDB operators in query params should not execute."""
        response = test_client.get('/api/v1/patients?name[$ne]=null')
        # Should return normal paginated response, not injected query
        assert response.status_code in (200, 422)

    def test_operator_in_alert_trigger(self, test_client: TestClient, test_app: Any):
        """MongoDB operators in JSON body should be stored as strings."""
        collection = test_app.state.db_client.get_collection.return_value
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )
        collection.find_one = AsyncMock(return_value=None)

        response = test_client.post("/api/v1/alerts", json={
            "patient_id": SAMPLE_PATIENT_ID,
            "severity": "warning",
            "trigger": '{"$gt": ""}',
            "channels": ["sms"],
        })
        assert response.status_code == 201

    def test_javascript_injection_in_conditions(self, test_client: TestClient, test_app: Any):
        """JavaScript code in conditions should be treated as plain text."""
        collection = test_app.state.db_client.get_collection.return_value
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )

        response = test_client.post("/api/v1/patients", json={
            "name": "Test Patient",
            "dob": "1985-03-15",
            "sex": "M",
            "conditions": ["function(){return true}", 'this.sleep(1000)'],
        })
        # Pydantic treats these as strings — safe
        assert response.status_code == 201


class TestPathTraversal:
    """Test path traversal prevention."""

    def test_dot_dot_slash_in_patient_id(self, test_client: TestClient):
        response = test_client.get("/api/v1/patients/../../etc/passwd")
        assert response.status_code in (404, 422)

    def test_encoded_path_traversal(self, test_client: TestClient):
        response = test_client.get("/api/v1/patients/%2e%2e%2f%2e%2e%2f")
        assert response.status_code in (404, 422)

    def test_null_byte_injection(self, test_client: TestClient):
        from httpx import InvalidURL
        # Null bytes are blocked at the HTTP transport layer (httpx/starlette)
        with pytest.raises(InvalidURL):
            test_client.get("/api/v1/patients/\x00admin")


class TestXSSPrevention:
    """Test XSS payloads are handled safely (JSON API)."""

    def test_script_tag_in_name(self, test_client: TestClient, test_app: Any):
        collection = test_app.state.db_client.get_collection.return_value
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )

        response = test_client.post("/api/v1/patients", json={
            "name": '<script>alert("XSS")</script>',
            "dob": "1985-03-15",
            "sex": "M",
        })
        assert response.status_code == 201
        # JSON API — content type is application/json, not HTML
        assert "application/json" in response.headers.get("content-type", "")

    def test_event_handler_in_name(self, test_client: TestClient, test_app: Any):
        collection = test_app.state.db_client.get_collection.return_value
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )

        response = test_client.post("/api/v1/patients", json={
            "name": 'onmouseover="alert(1)"',
            "dob": "1985-03-15",
            "sex": "M",
        })
        assert response.status_code == 201

    def test_content_type_prevents_xss(self, test_client: TestClient):
        """API responses should have application/json content type."""
        response = test_client.get("/api/v1/patients")
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_x_content_type_options_nosniff(self, test_client: TestClient):
        """X-Content-Type-Options: nosniff prevents MIME type confusion."""
        response = test_client.get("/api/v1/patients")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
