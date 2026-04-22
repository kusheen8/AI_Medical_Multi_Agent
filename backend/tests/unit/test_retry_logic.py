"""
Unit tests for retry logic and DLQ manager.

Tests exponential backoff timing, DLQ after max attempts,
per-failure-type strategies, and idempotency on retry.
"""

import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.services.queue.retry_handler import (
    FailureType,
    NotificationRetryHandler,
    RetryResult,
    _NON_RETRYABLE,
    _RATE_LIMIT_MULTIPLIER,
)


# ── Delay Calculation Tests ──────────────────────────────────────────────


class TestDelayCalculation:
    """Tests for exponential backoff delay calculation."""

    def test_first_attempt_delay(self):
        handler = NotificationRetryHandler(base_delay=5.0, multiplier=2.0)
        assert handler.get_delay(0) == 5.0

    def test_second_attempt_delay(self):
        handler = NotificationRetryHandler(base_delay=5.0, multiplier=2.0)
        assert handler.get_delay(1) == 10.0

    def test_third_attempt_delay(self):
        handler = NotificationRetryHandler(base_delay=5.0, multiplier=2.0)
        assert handler.get_delay(2) == 20.0

    def test_rate_limit_extended_delay(self):
        handler = NotificationRetryHandler(base_delay=5.0, multiplier=2.0)
        normal_delay = handler.get_delay(0)
        rate_limit_delay = handler.get_delay(0, FailureType.RATE_LIMIT)
        assert rate_limit_delay == normal_delay * _RATE_LIMIT_MULTIPLIER


# ── Retryability Tests ───────────────────────────────────────────────────


class TestRetryability:
    """Tests for failure type retryability."""

    def test_timeout_is_retryable(self):
        handler = NotificationRetryHandler()
        assert handler.is_retryable(FailureType.TIMEOUT) is True

    def test_network_error_is_retryable(self):
        handler = NotificationRetryHandler()
        assert handler.is_retryable(FailureType.NETWORK_ERROR) is True

    def test_rate_limit_is_retryable(self):
        handler = NotificationRetryHandler()
        assert handler.is_retryable(FailureType.RATE_LIMIT) is True

    def test_auth_error_is_not_retryable(self):
        handler = NotificationRetryHandler()
        assert handler.is_retryable(FailureType.AUTH_ERROR) is False

    def test_invalid_recipient_is_not_retryable(self):
        handler = NotificationRetryHandler()
        assert handler.is_retryable(FailureType.INVALID_RECIPIENT) is False

    def test_provider_error_is_retryable(self):
        handler = NotificationRetryHandler()
        assert handler.is_retryable(FailureType.PROVIDER_ERROR) is True


# ── Execute with Retry Tests ─────────────────────────────────────────────


class TestExecuteWithRetry:
    """Tests for the retry execution logic."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        handler = NotificationRetryHandler(max_attempts=3, base_delay=0.01)
        operation = AsyncMock(return_value="success")
        result = await handler.execute_with_retry(operation, item_id="test-1")
        assert result.success is True
        assert result.attempts == 1
        assert result.result == "success"

    @pytest.mark.asyncio
    async def test_success_on_second_attempt(self):
        handler = NotificationRetryHandler(max_attempts=3, base_delay=0.01)
        operation = AsyncMock(
            side_effect=[TimeoutError("timeout"), "success"]
        )
        result = await handler.execute_with_retry(operation, item_id="test-2")
        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_all_attempts_fail_to_dlq(self):
        dlq_callback = AsyncMock()
        handler = NotificationRetryHandler(
            max_attempts=3, base_delay=0.01, dlq_callback=dlq_callback
        )
        operation = AsyncMock(side_effect=RuntimeError("always fails"))
        result = await handler.execute_with_retry(operation, item_id="test-3")
        assert result.success is False
        assert result.attempts == 3
        assert result.sent_to_dlq is True
        dlq_callback.assert_called_once_with("test-3", "always fails", 3)

    @pytest.mark.asyncio
    async def test_non_retryable_aborts_immediately(self):
        handler = NotificationRetryHandler(max_attempts=3, base_delay=0.01)
        operation = AsyncMock(side_effect=RuntimeError("auth error 401"))
        result = await handler.execute_with_retry(operation, item_id="test-4")
        assert result.success is False
        assert result.attempts < 3  # Should not exhaust all attempts
        assert result.failure_type == FailureType.AUTH_ERROR

    @pytest.mark.asyncio
    async def test_no_dlq_callback(self):
        handler = NotificationRetryHandler(max_attempts=2, base_delay=0.01)
        operation = AsyncMock(side_effect=RuntimeError("fail"))
        result = await handler.execute_with_retry(operation, item_id="test-5")
        assert result.success is False
        assert result.sent_to_dlq is False  # No callback configured


# ── Error Classification Tests ───────────────────────────────────────────


class TestErrorClassification:
    """Tests for automatic error classification."""

    def test_timeout_classification(self):
        handler = NotificationRetryHandler()
        ft = handler._classify_error(TimeoutError("Connection timed out"))
        assert ft == FailureType.TIMEOUT

    def test_rate_limit_classification(self):
        handler = NotificationRetryHandler()
        ft = handler._classify_error(RuntimeError("429 Too Many Requests"))
        assert ft == FailureType.RATE_LIMIT

    def test_auth_classification(self):
        handler = NotificationRetryHandler()
        ft = handler._classify_error(RuntimeError("401 Unauthorized"))
        assert ft == FailureType.AUTH_ERROR

    def test_network_classification(self):
        handler = NotificationRetryHandler()
        ft = handler._classify_error(ConnectionError("DNS resolution failed"))
        assert ft == FailureType.NETWORK_ERROR

    def test_provider_error_classification(self):
        handler = NotificationRetryHandler()
        ft = handler._classify_error(RuntimeError("503 Service Unavailable"))
        assert ft == FailureType.PROVIDER_ERROR

    def test_unknown_classification(self):
        handler = NotificationRetryHandler()
        ft = handler._classify_error(RuntimeError("Something weird happened"))
        assert ft == FailureType.UNKNOWN
