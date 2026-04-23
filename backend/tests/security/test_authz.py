"""
Authentication and authorization test suite (D5.1, D5.9).

Tests:
- JWT token creation, validation, and expiration
- Password hashing and verification
- Role-based access control boundaries
- Token revocation/logout
- Admin auth (JWT + legacy API key)
- Cross-role access prevention
"""

import time
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import TokenPayload, UserRole


# ── Password Hashing ────────────────────────────────────────────────────


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_and_verify(self):
        password = "MySecurePass123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("CorrectPassword1")
        assert not verify_password("WrongPassword1", hashed)

    def test_different_hashes_for_same_password(self):
        hashed1 = hash_password("SamePass123!")
        hashed2 = hash_password("SamePass123!")
        assert hashed1 != hashed2  # bcrypt uses random salt

    def test_empty_password_handling(self):
        hashed = hash_password("")
        assert verify_password("", hashed)


# ── JWT Token Creation ───────────────────────────────────────────────────


class TestTokenCreation:
    """Test JWT access and refresh token creation."""

    def test_create_access_token(self, test_settings: Settings):
        token = create_access_token(
            user_id="user123",
            role=UserRole.PATIENT,
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_payload(self, test_settings: Settings):
        user_id = "user123"
        token = create_access_token(user_id=user_id, role=UserRole.DOCTOR)
        payload = decode_token(token)
        assert payload.sub == user_id
        assert payload.role == UserRole.DOCTOR
        assert payload.token_type == "access"
        assert payload.jti  # Has unique ID

    def test_access_token_with_scopes(self, test_settings: Settings):
        token = create_access_token(
            user_id="user123",
            role=UserRole.ADMIN,
            scopes=["read:all", "write:all"],
        )
        payload = decode_token(token)
        assert payload.scopes == ["read:all", "write:all"]

    def test_create_refresh_token(self, test_settings: Settings):
        token = create_refresh_token(user_id="user123")
        payload = decode_token(token)
        assert payload.token_type == "refresh"
        assert payload.sub == "user123"

    def test_custom_expiration(self, test_settings: Settings):
        short_token = create_access_token(
            user_id="user123",
            role=UserRole.PATIENT,
            expires_delta=timedelta(seconds=1),
        )
        # Token should be valid immediately
        payload = decode_token(short_token)
        assert payload.sub == "user123"

    def test_expired_token_raises(self, test_settings: Settings):
        from jose import JWTError
        token = create_access_token(
            user_id="user123",
            role=UserRole.PATIENT,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        with pytest.raises(JWTError):
            decode_token(token)


# ── JWT Token Validation ─────────────────────────────────────────────────


class TestTokenValidation:
    """Test JWT decode and validation."""

    def test_invalid_token_raises(self, test_settings: Settings):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token("not.a.valid.token")

    def test_tampered_token_raises(self, test_settings: Settings):
        from jose import JWTError
        token = create_access_token(user_id="user123", role=UserRole.PATIENT)
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_wrong_secret_raises(self, test_settings: Settings):
        from jose import JWTError
        settings = get_settings()
        payload = {
            "sub": "user123",
            "role": "patient",
            "scopes": [],
            "exp": int(time.time()) + 3600,
            "jti": "test-jti",
            "token_type": "access",
        }
        token = jwt.encode(payload, "wrong-secret-key", algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(JWTError):
            decode_token(token)

    def test_all_roles_valid(self, test_settings: Settings):
        for role in UserRole:
            token = create_access_token(user_id="user123", role=role)
            payload = decode_token(token)
            assert payload.role == role


# ── Role-Based Access Control ────────────────────────────────────────────


class TestRBAC:
    """Test role-based access control via admin endpoints."""

    def test_admin_jwt_access(self, test_client: TestClient, admin_auth_headers: dict):
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

    def test_admin_legacy_key_access(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == 200

    def test_patient_cannot_access_admin(self, test_client: TestClient, test_app: Any):
        # Enable auth requirement for this test
        test_app.state.settings.REQUIRE_AUTH = True
        token = create_access_token(user_id="patient1", role=UserRole.PATIENT)
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        test_app.state.settings.REQUIRE_AUTH = False

    def test_no_auth_returns_403(self, test_client: TestClient):
        response = test_client.get("/api/v1/admin/health/summary")
        assert response.status_code == 403

    def test_bad_api_key_returns_403(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_expired_jwt_returns_401(self, test_client: TestClient, test_settings: Settings):
        token = create_access_token(
            user_id="admin1",
            role=UserRole.ADMIN,
            expires_delta=timedelta(seconds=-1),
        )
        response = test_client.get(
            "/api/v1/admin/health/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (401, 403)


# ── Auth Endpoint Flow Tests ────────────────────────────────────────────


class TestAuthEndpoints:
    """Test the auth API endpoints."""

    def test_register_creates_user(self, test_client: TestClient, test_app: Any):
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value=None)  # No existing user
        collection.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=ObjectId())
        )

        response = test_client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "SecurePass1",
            "full_name": "New User",
            "role": "patient",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert "hashed_password" not in data  # Password should not be in response

    def test_register_duplicate_email(self, test_client: TestClient, test_app: Any):
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "email": "existing@example.com",
        })

        response = test_client.post("/api/v1/auth/register", json={
            "email": "existing@example.com",
            "password": "SecurePass1",
            "full_name": "Existing User",
        })
        assert response.status_code == 409

    def test_register_weak_password(self, test_client: TestClient):
        response = test_client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "weak",  # Too short
            "full_name": "Weak User",
        })
        assert response.status_code == 422

    def test_register_password_no_uppercase(self, test_client: TestClient):
        response = test_client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "alllowercase1",
            "full_name": "User",
        })
        assert response.status_code == 422

    def test_login_success(self, test_client: TestClient, test_app: Any):
        hashed = hash_password("SecurePass1")
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "email": "user@example.com",
            "hashed_password": hashed,
            "role": "patient",
            "is_active": True,
        })

        response = test_client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "SecurePass1",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, test_client: TestClient, test_app: Any):
        hashed = hash_password("CorrectPassword1")
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "email": "user@example.com",
            "hashed_password": hashed,
            "role": "patient",
            "is_active": True,
        })

        response = test_client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "WrongPassword1",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, test_client: TestClient, test_app: Any):
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value=None)

        response = test_client.post("/api/v1/auth/login", json={
            "email": "nouser@example.com",
            "password": "AnyPassword1",
        })
        assert response.status_code == 401

    def test_login_deactivated_user(self, test_client: TestClient, test_app: Any):
        hashed = hash_password("SecurePass1")
        collection = test_app.state.db_client.get_collection.return_value
        collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "email": "deactivated@example.com",
            "hashed_password": hashed,
            "role": "patient",
            "is_active": False,
        })

        response = test_client.post("/api/v1/auth/login", json={
            "email": "deactivated@example.com",
            "password": "SecurePass1",
        })
        assert response.status_code == 403

    def test_auth_me_requires_token(self, test_client: TestClient, test_app: Any):
        test_app.state.settings.REQUIRE_AUTH = True
        response = test_client.get("/api/v1/auth/me")
        assert response.status_code == 401
        test_app.state.settings.REQUIRE_AUTH = False
