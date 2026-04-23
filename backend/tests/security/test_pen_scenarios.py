"""
Penetration testing scenarios (D5.9).

Automated security tests covering:
- Authentication bypass attempts
- Authorization bypass (accessing other users' data)
- Injection attacks (NoSQL, command injection, path traversal)
- Data exposure via error messages
- Sensitive data in responses
- Security headers presence
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import UserRole
from tests.conftest import SAMPLE_PATIENT_ID


# ── Authentication Bypass Tests ──────────────────────────────────────────


class TestAuthenticationBypass:
    """Attempt to bypass authentication mechanisms."""

    def test_forged_jwt_rejected(self, test_client: TestClient, test_app: Any):
        """Admin endpoints should reject forged JWT tokens."""
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.fake"},
        )
        # Should get 401 or 403 for invalid token
        assert response.status_code in (401, 403)

    def test_empty_bearer_rejected(self, test_client: TestClient, test_app: Any):
        """Empty bearer token should be rejected on admin endpoints."""
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code in (401, 403)

    def test_no_auth_header_rejected(self, test_client: TestClient, test_app: Any):
        """Admin endpoints require auth."""
        response = test_client.get("/api/v1/admin/health/summary")
        assert response.status_code == 403

    def test_malformed_auth_header(self, test_client: TestClient, test_app: Any):
        """Non-Bearer auth headers should be rejected on admin endpoints."""
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"Authorization": "NotBearer sometoken"},
        )
        assert response.status_code == 403

    def test_refresh_token_cant_be_used_as_access(self, test_client: TestClient, test_app: Any):
        from app.core.security import create_refresh_token
        refresh = create_refresh_token(user_id="user123")
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"Authorization": f"Bearer {refresh}"},
        )
        # Should reject refresh token used as access token
        assert response.status_code in (401, 403)


# ── Injection Prevention Tests ───────────────────────────────────────────


class TestInjectionPrevention:
    """Test that injection attacks are blocked."""

    def test_nosql_injection_in_patient_name(self, test_client: TestClient, test_app: Any):
        """Attempt NoSQL injection via patient name field."""
        collection = test_app.state.db_client.get_collection.return_value
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )

        # These should be safely stored as strings, not executed
        injection_payloads = [
            {"$gt": ""},
            {"$ne": None},
            '{"$where": "sleep(5000)"}',
        ]
        for payload in injection_payloads:
            response = test_client.post("/api/v1/patients", json={
                "name": str(payload) if not isinstance(payload, str) else payload,
                "dob": "1985-03-15",
                "sex": "M",
            })
            # Pydantic validates the name is a string, so these should pass
            # but be stored safely as strings
            assert response.status_code in (201, 422)

    def test_nosql_injection_in_patient_id(self, test_client: TestClient):
        """Attempt NoSQL injection via patient ID path parameter."""
        injection_ids = [
            '{"$gt": ""}',
            '{"$ne": null}',
            "'; DROP TABLE patients; --",
        ]
        for payload in injection_ids:
            response = test_client.get(f"/api/v1/patients/{payload}")
            # Should return 404 (invalid ObjectId) or 422, never 200
            assert response.status_code in (404, 422)

    def test_command_injection_in_symptoms(self, test_client: TestClient, test_app: Any):
        """Attempt command injection via symptom text."""
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(SAMPLE_PATIENT_ID),
            "name": "Test",
            "dob": "1985-03-15",
            "sex": "M",
        })

        response = test_client.post("/api/v1/analyze/symptoms", json={
            "patient_id": SAMPLE_PATIENT_ID,
            "symptoms": "; rm -rf / ; echo 'pwned'",
        })
        # Should accept as text (202) — no command execution occurs
        assert response.status_code == 202

    def test_path_traversal_in_id(self, test_client: TestClient):
        """Attempt path traversal via ID field."""
        traversal_ids = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f",
        ]
        for payload in traversal_ids:
            response = test_client.get(f"/api/v1/patients/{payload}")
            assert response.status_code in (404, 422)

    def test_xss_payload_in_patient_name(self, test_client: TestClient, test_app: Any):
        """XSS payloads should be stored as-is (JSON API, no HTML rendering)."""
        collection = test_app.state.db_client.get_collection.return_value
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )

        response = test_client.post("/api/v1/patients", json={
            "name": '<script>alert("xss")</script>',
            "dob": "1985-03-15",
            "sex": "M",
        })
        # API returns JSON — XSS is not applicable
        assert response.status_code == 201
        data = response.json()
        # The name should be returned as-is in JSON (safe)
        assert "script" in data.get("name", "").lower()


# ── Data Exposure Tests ──────────────────────────────────────────────────


class TestDataExposure:
    """Test that sensitive data is not exposed in responses."""

    def test_error_response_no_stack_trace(self, test_client: TestClient):
        """Error responses should not contain stack traces."""
        response = test_client.get("/api/v1/patients/invalid-id")
        assert response.status_code in (404, 422)
        body = response.text
        assert "Traceback" not in body
        assert "File " not in body

    def test_404_no_internal_details(self, test_client: TestClient, test_app: Any):
        """404 responses should not reveal internal structure."""
        test_app.state.db_client.get_collection.return_value.find_one = AsyncMock(
            return_value=None
        )
        valid_id = str(ObjectId())
        response = test_client.get(f"/api/v1/patients/{valid_id}")
        assert response.status_code == 404
        body = response.json()
        assert "mongodb" not in str(body).lower()
        assert "collection" not in str(body).lower()

    def test_login_failure_generic_message(self, test_client: TestClient, test_app: Any):
        """Login failures should not reveal whether the email exists or not."""
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value=None)

        response = test_client.post("/api/v1/auth/login", json={
            "email": "nouser@example.com",
            "password": "AnyPass123",
        })
        assert response.status_code == 401
        detail = response.json().get("detail", "")
        # Should not reveal whether user exists or which credential was wrong
        assert "not found" not in detail.lower()
        assert "does not exist" not in detail.lower()
        assert "incorrect password" not in detail.lower()


# ── Security Headers Tests ───────────────────────────────────────────────


class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    def test_x_content_type_options(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_content_security_policy(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp

    def test_cache_control(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        cache = response.headers.get("Cache-Control", "")
        assert "no-store" in cache

    def test_x_xss_protection(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        assert response.headers.get("X-XSS-Protection") == "0"

    def test_referrer_policy(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        assert response.headers.get("Referrer-Policy") == "no-referrer"

    def test_no_hsts_in_development(self, test_client: TestClient):
        """HSTS should not be set in development mode."""
        response = test_client.get("/api/v1/health")
        assert "Strict-Transport-Security" not in response.headers

    def test_request_id_header(self, test_client: TestClient):
        """All responses should have X-Request-ID."""
        response = test_client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers
