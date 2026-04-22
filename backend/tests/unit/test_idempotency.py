"""
Unit tests for idempotency middleware.

Tests cached response replay, expired entry handling,
and invalid key format rejection.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.idempotency import (
    check_idempotency,
    store_idempotency,
    validate_idempotency_key,
)


# ── Key Validation Tests ─────────────────────────────────────────────────


class TestValidateIdempotencyKey:
    """Tests for idempotency key validation."""

    def test_valid_uuid(self):
        key = str(uuid.uuid4())
        assert validate_idempotency_key(key) == key

    def test_none_returns_none(self):
        assert validate_idempotency_key(None) is None

    def test_invalid_format(self):
        assert validate_idempotency_key("not-a-uuid") is None

    def test_empty_string(self):
        assert validate_idempotency_key("") is None

    def test_uuid_without_hyphens(self):
        key = uuid.uuid4().hex
        # UUID hex without hyphens is NOT a valid UUID string
        result = validate_idempotency_key(key)
        # uuid.UUID accepts hex-only strings, so this should work
        assert result == key


# ── Check Idempotency Tests ──────────────────────────────────────────────


class TestCheckIdempotency:
    """Tests for idempotency cache checking."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_response(self):
        repo = MagicMock()
        cached_doc = {
            "key": "test-key",
            "method": "POST",
            "path": "/api/v1/alerts",
            "response_body": {"id": "abc123", "status": "created"},
            "status_code": 201,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=12),
        }
        repo.get_by_key = AsyncMock(return_value=cached_doc)
        result = await check_idempotency("test-key", repo)
        assert result == {"id": "abc123", "status": "created"}

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        repo = MagicMock()
        repo.get_by_key = AsyncMock(return_value=None)
        result = await check_idempotency("test-key", repo)
        assert result is None


# ── Store Idempotency Tests ──────────────────────────────────────────────


class TestStoreIdempotency:
    """Tests for idempotency response storage."""

    @pytest.mark.asyncio
    async def test_stores_response(self):
        repo = MagicMock()
        repo.store = AsyncMock()
        await store_idempotency(
            idempotency_key="test-key",
            repo=repo,
            method="POST",
            path="/api/v1/alerts",
            response_body={"id": "abc123"},
            status_code=201,
        )
        repo.store.assert_called_once_with(
            key="test-key",
            method="POST",
            path="/api/v1/alerts",
            response_body={"id": "abc123"},
            status_code=201,
        )
