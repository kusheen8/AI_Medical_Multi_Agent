"""
Unit tests for the notification service.

Tests CaregiverNotifier dispatch routing, PHI sanitization,
provider adapters, and channel selection by severity.
"""

import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from app.models.alert import AlertStatus
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, reset_all_circuit_breakers
from app.services.notifications.caregiver_notifier import CaregiverNotifier
from app.services.notifications.providers.base import NotificationProvider, ProviderResponse
from app.services.notifications.providers.sms_provider import TwilioSMSProvider
from app.services.notifications.providers.email_provider import SendGridEmailProvider
from app.services.notifications.providers.push_provider import FCMPushProvider


# ── Provider Tests ───────────────────────────────────────────────────────


class TestTwilioSMSProvider:
    """Tests for SMS provider stub."""

    @pytest.mark.asyncio
    async def test_send_returns_success(self):
        provider = TwilioSMSProvider(dry_run=True)
        resp = await provider.send("+1234567890", "Test message")
        assert resp.success is True
        assert resp.provider_message_id.startswith("SM")
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_channel_name(self):
        provider = TwilioSMSProvider()
        assert provider.channel_name == "sms"

    @pytest.mark.asyncio
    async def test_health_check(self):
        provider = TwilioSMSProvider()
        assert await provider.health_check() is True


class TestSendGridEmailProvider:
    """Tests for email provider stub."""

    @pytest.mark.asyncio
    async def test_send_returns_success(self):
        provider = SendGridEmailProvider(dry_run=True)
        resp = await provider.send("test@example.com", "Test email body")
        assert resp.success is True
        assert resp.provider_message_id.startswith("SG")
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_channel_name(self):
        provider = SendGridEmailProvider()
        assert provider.channel_name == "email"


class TestFCMPushProvider:
    """Tests for push provider stub."""

    @pytest.mark.asyncio
    async def test_send_returns_success(self):
        provider = FCMPushProvider(dry_run=True)
        resp = await provider.send("device-token-123", "Test push")
        assert resp.success is True
        assert resp.provider_message_id.startswith("FCM")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_channel_name(self):
        provider = FCMPushProvider()
        assert provider.channel_name == "push"


# ── CaregiverNotifier Tests ─────────────────────────────────────────────


class TestCaregiverNotifier:
    """Tests for the notification orchestrator."""

    def setup_method(self):
        reset_all_circuit_breakers()

    def _make_alert_doc(
        self,
        channels: list[str] | None = None,
        severity: str = "critical",
    ) -> dict[str, Any]:
        return {
            "_id": ObjectId(),
            "patient_id": str(ObjectId()),
            "severity": severity,
            "trigger": "High risk detected",
            "channels": channels or ["sms", "email"],
            "status": "pending",
        }

    def _make_context(self) -> dict[str, Any]:
        return {"age": 65, "risk_tier": "critical"}

    @pytest.mark.asyncio
    async def test_dispatch_to_all_channels(self):
        notifier = CaregiverNotifier(
            providers={
                "sms": TwilioSMSProvider(dry_run=True),
                "email": SendGridEmailProvider(dry_run=True),
            },
        )
        alert = self._make_alert_doc(channels=["sms", "email"])
        receipts = await notifier.dispatch(alert, self._make_context())
        assert len(receipts) == 2
        assert all(r.status == AlertStatus.SENT for r in receipts)

    @pytest.mark.asyncio
    async def test_dispatch_with_missing_provider(self):
        notifier = CaregiverNotifier(providers={"sms": TwilioSMSProvider(dry_run=True)})
        alert = self._make_alert_doc(channels=["sms", "push"])
        receipts = await notifier.dispatch(alert, self._make_context())
        assert len(receipts) == 2
        sms_receipt = [r for r in receipts if r.channel == "sms"][0]
        push_receipt = [r for r in receipts if r.channel == "push"][0]
        assert sms_receipt.status == AlertStatus.SENT
        assert push_receipt.status == AlertStatus.FAILED
        assert "No provider" in push_receipt.error

    @pytest.mark.asyncio
    async def test_dispatch_with_circuit_breaker_open(self):
        # Manually create an open circuit breaker
        cb = CircuitBreaker("sms-test", failure_threshold=1, recovery_timeout=60)
        # Force open
        cb._state = CircuitBreaker.__init__  # Reset
        cb = CircuitBreaker("sms-test", failure_threshold=1, recovery_timeout=60)
        try:
            await cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        # Now should be open
        assert cb.state.value == "open"

        notifier = CaregiverNotifier(
            providers={"sms": TwilioSMSProvider(dry_run=True)},
            circuit_breakers={"sms": cb},
        )
        alert = self._make_alert_doc(channels=["sms"])
        receipts = await notifier.dispatch(alert, self._make_context())
        assert len(receipts) == 1
        assert receipts[0].status == AlertStatus.FAILED
        assert "circuit breaker" in receipts[0].error.lower()

    @pytest.mark.asyncio
    async def test_dispatch_with_provider_exception(self):
        """Provider raises exception → receipt shows failed."""
        mock_provider = MagicMock(spec=NotificationProvider)
        mock_provider.channel_name = "sms"
        mock_provider.send = AsyncMock(side_effect=ConnectionError("Network down"))

        notifier = CaregiverNotifier(providers={"sms": mock_provider})
        alert = self._make_alert_doc(channels=["sms"])
        receipts = await notifier.dispatch(alert, self._make_context())
        assert len(receipts) == 1
        assert receipts[0].status == AlertStatus.FAILED
        assert "Network down" in receipts[0].error


# ── PHI Sanitization Tests ───────────────────────────────────────────────


class TestPHISanitization:
    """Tests ensuring no PHI is sent to external providers."""

    @pytest.mark.asyncio
    async def test_message_contains_no_patient_name(self):
        notifier = CaregiverNotifier(
            providers={"email": SendGridEmailProvider(dry_run=True)}
        )
        # Build message directly
        message = notifier._build_message(
            severity="critical",
            trigger="High risk detected",
            patient_context={"age": 45, "risk_tier": "critical"},
        )
        assert "John" not in message
        assert "Doe" not in message
        assert "critical" in message.lower()
        assert "45" in message

    @pytest.mark.asyncio
    async def test_message_contains_no_medical_details(self):
        notifier = CaregiverNotifier(providers={})
        message = notifier._build_message(
            severity="warning",
            trigger="Medium risk assessment",
            patient_context={"age": 30, "risk_tier": "medium"},
        )
        # Should not contain specific medical data
        assert "diabetes" not in message.lower()
        assert "metformin" not in message.lower()
