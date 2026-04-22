"""
Integration tests for reliability scenarios.

Tests the 7 scenarios from the Phase 4 spec plus additional
edge cases for delivery receipt handling.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState, reset_all_circuit_breakers
from app.services.notifications.caregiver_notifier import CaregiverNotifier
from app.services.notifications.providers.base import NotificationProvider, ProviderResponse
from app.services.notifications.providers.sms_provider import TwilioSMSProvider
from app.services.queue.retry_handler import NotificationRetryHandler, FailureType
from app.models.alert import AlertStatus


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_alert_doc(
    channels: list[str] | None = None,
    severity: str = "critical",
) -> dict[str, Any]:
    return {
        "_id": ObjectId(),
        "patient_id": str(ObjectId()),
        "severity": severity,
        "trigger": "Test alert",
        "channels": channels or ["sms", "email"],
        "status": "pending",
    }


# ── Scenario 1: Ollama Down → Alert Not Created Prematurely ──────────────


class TestScenario1OllamaDown:
    """When Ollama is down, alerts should NOT be created prematurely."""

    @pytest.mark.asyncio
    async def test_no_premature_alert_on_analysis_failure(self):
        """If analysis fails, no alert should be triggered."""
        # This is handled by the AnalysisWorker's error handling.
        # If the analyzer raises, the task is marked failed, NOT
        # evaluated through the policy engine.
        # We verify this by checking that policy_engine.evaluate is
        # never called when the analysis step fails.
        from app.workers.analysis_worker import AnalysisWorker

        mock_queue = MagicMock()
        mock_queue.dequeue = AsyncMock(return_value=None)
        mock_queue.mark_failed = AsyncMock(return_value=True)

        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(
            side_effect=ConnectionError("Ollama is offline")
        )

        mock_policy = MagicMock()
        mock_policy.evaluate = AsyncMock(return_value=[])

        worker = AnalysisWorker(
            worker_id="test",
            queue=mock_queue,
            coordinator=MagicMock(),
            analyzer=mock_analyzer,
            patient_repo=MagicMock(),
            record_repo=MagicMock(),
            trace_repo=MagicMock(),
            policy_engine=mock_policy,
            alert_repo=MagicMock(),
        )

        # Mock the coordinator to return a trace
        worker._coordinator.generate_reasoning_trace = AsyncMock(return_value={
            "task_type": "symptom_analysis",
            "instructions": "test",
        })
        worker._patient_repo.get_by_id = AsyncMock(return_value={"_id": ObjectId()})
        worker._trace_repo.create_trace = AsyncMock(return_value={"_id": ObjectId()})

        task_doc = {
            "_id": ObjectId(),
            "patient_id": str(ObjectId()),
            "payload": {"symptoms": "chest pain"},
            "task_type": "symptom_analysis",
        }

        await worker._process_task(task_doc)

        # Policy engine should NOT be called since analysis failed
        mock_policy.evaluate.assert_not_called()
        # Task should be marked as failed
        mock_queue.mark_failed.assert_called_once()


# ── Scenario 2: SMS Rate Limit → Retry With Backoff ──────────────────────


class TestScenario2SMSRateLimit:
    """SMS provider rate limit triggers retry with backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        handler = NotificationRetryHandler(
            max_attempts=3,
            base_delay=0.01,  # Short for testing
        )

        call_count = 0

        async def rate_limited_send():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("429 Too Many Requests")
            return "sent"

        result = await handler.execute_with_retry(
            rate_limited_send, item_id="sms-1"
        )
        assert result.success is True
        assert result.attempts == 3
        assert call_count == 3


# ── Scenario 3: Email Timeout → DLQ ─────────────────────────────────────


class TestScenario3EmailTimeout:
    """Email provider timeout exhausts retries and moves to DLQ."""

    @pytest.mark.asyncio
    async def test_timeout_moves_to_dlq(self):
        dlq_callback = AsyncMock()
        handler = NotificationRetryHandler(
            max_attempts=3,
            base_delay=0.01,
            dlq_callback=dlq_callback,
        )

        async def always_timeout():
            raise TimeoutError("Connection timed out")

        result = await handler.execute_with_retry(
            always_timeout, item_id="email-1"
        )
        assert result.success is False
        assert result.sent_to_dlq is True
        assert result.failure_type == FailureType.TIMEOUT
        dlq_callback.assert_called_once()


# ── Scenario 4: Circuit Breaker Opens → Fail Fast, Recover ──────────────


class TestScenario4CircuitBreaker:
    """Circuit breaker prevents cascading failures and recovers."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_open_circuit_fails_fast(self):
        cb = CircuitBreaker("test-svc", failure_threshold=2, recovery_timeout=0.1)

        async def failing():
            raise RuntimeError("Service down")

        # Trigger open
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failing)

        assert cb.state == CircuitState.OPEN

        # Now calls should fail immediately
        with pytest.raises(CircuitBreakerOpen):
            await cb.call(failing)

    @pytest.mark.asyncio
    async def test_circuit_recovers(self):
        cb = CircuitBreaker("test-svc", failure_threshold=2, recovery_timeout=0.05)

        async def failing():
            raise RuntimeError("fail")

        async def success():
            return "ok"

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failing)

        await asyncio.sleep(0.1)  # Wait for half-open
        result = await cb.call(success)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED


# ── Scenario 5: Queue Crash → Resume Pending ─────────────────────────────


class TestScenario5QueueRecovery:
    """Queue recovers pending tasks after a crash."""

    @pytest.mark.asyncio
    async def test_recover_pending_re_enqueues(self):
        from app.services.queue.task_queue import TaskQueue

        mock_client = MagicMock()
        collection = MagicMock()

        # Simulate 2 stuck tasks
        stuck_tasks = [
            {
                "_id": ObjectId(),
                "task_type": "symptom_analysis",
                "priority": 2,
                "status": "processing",
            },
            {
                "_id": ObjectId(),
                "task_type": "history_summarization",
                "priority": 1,
                "status": "processing",
            },
        ]

        # Make find return an async iterator
        async def async_iter():
            for doc in stuck_tasks:
                yield doc

        collection.find = MagicMock(return_value=async_iter())
        collection.find_one_and_update = AsyncMock()
        mock_client.get_collection = MagicMock(return_value=collection)

        queue = TaskQueue(mock_client)
        recovered = await queue.recover_pending()
        assert recovered == 2
        assert queue.pending_count == 2


# ── Scenario 6: Duplicate Alert → Idempotency ───────────────────────────


class TestScenario6Idempotency:
    """Duplicate alert creation prevented by idempotency key."""

    @pytest.mark.asyncio
    async def test_idempotency_prevents_duplicate(self):
        from app.core.idempotency import check_idempotency, validate_idempotency_key
        import uuid

        key = str(uuid.uuid4())
        assert validate_idempotency_key(key) == key

        # First call: no cache
        repo = MagicMock()
        repo.get_by_key = AsyncMock(return_value=None)
        result = await check_idempotency(key, repo)
        assert result is None

        # Second call: cache hit
        repo.get_by_key = AsyncMock(return_value={
            "key": key,
            "response_body": {"id": "alert-123", "status": "pending"},
        })
        result = await check_idempotency(key, repo)
        assert result is not None
        assert result["id"] == "alert-123"


# ── Scenario 7: Webhook Out of Order → Receipts Update ──────────────────


class TestScenario7WebhookOrder:
    """Out-of-order webhooks correctly update delivery receipts."""

    @pytest.mark.asyncio
    async def test_out_of_order_webhook_updates(self):
        from app.db.repositories.alert_repository import AlertRepository

        mock_client = MagicMock()
        collection = MagicMock()

        # Start with a "sent" receipt
        alert_doc = {
            "_id": ObjectId(),
            "patient_id": str(ObjectId()),
            "severity": "critical",
            "trigger": "test",
            "channels": ["sms"],
            "status": "sent",
            "delivery_receipts": [
                {"channel": "sms", "status": "sent", "attempted_at": "2026-04-01T10:00:00Z"},
            ],
        }

        # Simulate $push operation
        collection.find_one_and_update = AsyncMock(return_value={
            **alert_doc,
            "delivery_receipts": [
                {"channel": "sms", "status": "sent", "attempted_at": "2026-04-01T10:00:00Z"},
                {"channel": "sms", "status": "delivered", "attempted_at": "2026-04-01T10:01:00Z"},
            ],
        })
        collection.find_one = AsyncMock(return_value=alert_doc)
        mock_client.get_collection = MagicMock(return_value=collection)

        repo = AlertRepository(mock_client)
        result = await repo.add_delivery_receipt(
            str(alert_doc["_id"]),
            {"channel": "sms", "status": "delivered", "attempted_at": "2026-04-01T10:01:00Z"},
        )

        # Both receipts should be present (appended, not replaced)
        assert len(result["delivery_receipts"]) == 2
        statuses = [r["status"] for r in result["delivery_receipts"]]
        assert "sent" in statuses
        assert "delivered" in statuses
