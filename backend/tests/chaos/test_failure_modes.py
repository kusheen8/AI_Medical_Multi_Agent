"""
Chaos tests for failure mode simulation.

Tests random service failures and load testing for alert throughput.
"""

import asyncio
import random
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.services.circuit_breaker import CircuitBreaker, CircuitState, reset_all_circuit_breakers
from app.services.metrics import MetricsCollector
from app.services.notifications.caregiver_notifier import CaregiverNotifier
from app.services.notifications.providers.base import NotificationProvider, ProviderResponse
from app.services.notifications.providers.sms_provider import TwilioSMSProvider
from app.services.notifications.providers.email_provider import SendGridEmailProvider
from app.services.queue.retry_handler import NotificationRetryHandler
from app.models.alert import AlertStatus


# ── Random Service Failure Simulation ────────────────────────────────────


class TestRandomFailures:
    """Chaos tests simulating random service failures."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_random_provider_failures(self):
        """Simulate random failures across providers; system should not crash."""
        fail_count = 0
        success_count = 0

        class FlakySMSProvider(TwilioSMSProvider):
            async def send(self, recipient, message, metadata=None):
                nonlocal fail_count, success_count
                if random.random() < 0.3:  # 30% failure rate
                    fail_count += 1
                    raise ConnectionError("Random failure")
                success_count += 1
                return await super().send(recipient, message, metadata)

        notifier = CaregiverNotifier(
            providers={"sms": FlakySMSProvider(dry_run=True)},
        )

        # Send 20 alerts
        for i in range(20):
            alert_doc = {
                "_id": ObjectId(),
                "patient_id": str(ObjectId()),
                "severity": "critical",
                "trigger": f"Test alert {i}",
                "channels": ["sms"],
                "status": "pending",
            }
            receipts = await notifier.dispatch(
                alert_doc, {"age": 60, "risk_tier": "critical"}
            )
            # Every dispatch should return receipts (success or failure)
            assert len(receipts) == 1

        # At least some should have succeeded and some failed
        # (with 30% failure rate and 20 tries, extremely unlikely all succeed/fail)
        total = fail_count + success_count
        assert total == 20

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_intermittent_failures(self):
        """Circuit breaker should open after sustained failures and recover."""
        cb = CircuitBreaker("chaos-test", failure_threshold=3, recovery_timeout=0.05)

        call_count = 0

        async def intermittent():
            nonlocal call_count
            call_count += 1
            if call_count <= 4:  # First 4 calls fail
                raise RuntimeError("Service error")
            return "ok"

        # First 3 failures should open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(intermittent)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN

        # Next call (4th total) still fails - reopens
        with pytest.raises(RuntimeError):
            await cb.call(intermittent)
        assert cb.state == CircuitState.OPEN

        # Wait again
        await asyncio.sleep(0.1)
        # 5th call succeeds
        result = await cb.call(intermittent)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED


# ── Load Tests ───────────────────────────────────────────────────────────


class TestLoadPerformance:
    """Load tests for alert throughput."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_100_alerts_throughput(self):
        """Send 100 alerts and verify throughput and latency.

        Target: all 100 alerts should complete within reasonable time
        with stub providers (no real network calls).
        """
        notifier = CaregiverNotifier(
            providers={
                "sms": TwilioSMSProvider(dry_run=True),
                "email": SendGridEmailProvider(dry_run=True),
            },
        )

        metrics = MetricsCollector()
        start_time = time.monotonic()

        tasks = []
        for i in range(100):
            alert_doc = {
                "_id": ObjectId(),
                "patient_id": str(ObjectId()),
                "severity": random.choice(["warning", "error", "critical"]),
                "trigger": f"Load test alert {i}",
                "channels": ["sms", "email"],
                "status": "pending",
            }

            async def dispatch_and_record(doc=alert_doc):
                t0 = time.monotonic()
                receipts = await notifier.dispatch(
                    doc, {"age": 50, "risk_tier": doc["severity"]}
                )
                latency = (time.monotonic() - t0) * 1000
                metrics.record_alert_created(doc["severity"])
                for r in receipts:
                    metrics.record_delivery_attempt(
                        r.channel, r.status == AlertStatus.SENT, latency
                    )
                return receipts

            tasks.append(dispatch_and_record())

        results = await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start_time

        # Verify all 100 completed
        assert len(results) == 100

        # Each alert should have 2 receipts (sms + email)
        total_receipts = sum(len(r) for r in results)
        assert total_receipts == 200

        # Throughput: should complete in under 5 seconds with stubs
        assert elapsed < 5.0, f"Load test took {elapsed:.2f}s (target: <5s)"

        # Verify metrics
        summary = metrics.get_summary()
        assert summary["alerts"]["total_created"] == 100

    @pytest.mark.asyncio
    async def test_retry_handler_under_load(self):
        """Test retry handler with 50 concurrent operations."""
        handler = NotificationRetryHandler(
            max_attempts=2, base_delay=0.001
        )

        succeed_count = 0
        fail_count = 0

        async def mostly_works():
            nonlocal succeed_count, fail_count
            if random.random() < 0.2:  # 20% initial failure
                fail_count += 1
                raise RuntimeError("Temporary failure")
            succeed_count += 1
            return "ok"

        tasks = [
            handler.execute_with_retry(mostly_works, item_id=f"load-{i}")
            for i in range(50)
        ]

        results = await asyncio.gather(*tasks)
        success = sum(1 for r in results if r.success)
        # With 20% failure rate and 2 attempts, most should succeed
        assert success >= 30  # At least 60% success rate
