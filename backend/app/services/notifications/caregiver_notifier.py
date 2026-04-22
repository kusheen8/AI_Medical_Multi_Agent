"""
Caregiver notification service — orchestrates alert dispatch.

Routes alert notifications to the appropriate channels (SMS, Email, Push)
based on alert severity and patient preferences.  Enforces PHI boundary
by never sending raw patient data to external providers.

All provider calls are wrapped with the circuit breaker for resilience.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

from app.models.alert import DeliveryReceipt, AlertStatus
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.services.notifications.providers.base import NotificationProvider, ProviderResponse

logger = structlog.get_logger(__name__)


class CaregiverNotifier:
    """Orchestrates notification dispatch across multiple channels.

    Attributes:
        _providers: Mapping of channel name to provider instance.
        _circuit_breakers: Mapping of channel name to circuit breaker.
    """

    def __init__(
        self,
        providers: dict[str, NotificationProvider],
        circuit_breakers: dict[str, CircuitBreaker] | None = None,
    ) -> None:
        self._providers = providers
        self._circuit_breakers = circuit_breakers or {}

    async def dispatch(
        self,
        alert_doc: dict[str, Any],
        patient_context: dict[str, Any],
        caregiver_contacts: dict[str, str] | None = None,
    ) -> list[DeliveryReceipt]:
        """Dispatch notifications for an alert across configured channels.

        Args:
            alert_doc: The alert document (contains severity, channels, trigger).
            patient_context: De-identified patient context (age, risk tier ONLY — no PHI).
            caregiver_contacts: Mapping of channel → recipient address.
                Example: {"sms": "+1234567890", "email": "care@example.com"}

        Returns:
            List of DeliveryReceipt for each channel attempted.
        """
        channels = alert_doc.get("channels", [])
        severity = alert_doc.get("severity", "warning")
        trigger = alert_doc.get("trigger", "Medical alert triggered")
        alert_id = str(alert_doc.get("_id", ""))
        contacts = caregiver_contacts or {}

        # Build sanitized message (no PHI)
        message = self._build_message(severity, trigger, patient_context)

        receipts: list[DeliveryReceipt] = []

        for channel in channels:
            provider = self._providers.get(channel)
            if provider is None:
                await logger.awarning(
                    "notification_provider_not_found",
                    channel=channel,
                    alert_id=alert_id,
                )
                receipts.append(DeliveryReceipt(
                    channel=channel,
                    status=AlertStatus.FAILED,
                    error=f"No provider configured for channel '{channel}'",
                ))
                continue

            recipient = contacts.get(channel, f"default-{channel}-recipient")

            receipt = await self._send_via_channel(
                provider=provider,
                channel=channel,
                recipient=recipient,
                message=message,
                alert_id=alert_id,
                metadata={"severity": severity, "alert_id": alert_id},
            )
            receipts.append(receipt)

        await logger.ainfo(
            "notification_dispatch_complete",
            alert_id=alert_id,
            channels=channels,
            success_count=sum(1 for r in receipts if r.status == AlertStatus.SENT),
            fail_count=sum(1 for r in receipts if r.status == AlertStatus.FAILED),
        )

        return receipts

    async def _send_via_channel(
        self,
        provider: NotificationProvider,
        channel: str,
        recipient: str,
        message: str,
        alert_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryReceipt:
        """Send a notification through a single channel with circuit breaker.

        Args:
            provider: The notification provider to use.
            channel: Channel name for logging/receipt.
            recipient: Destination address.
            message: Sanitized message body.
            alert_id: Alert ID for correlation.
            metadata: Additional send metadata.

        Returns:
            DeliveryReceipt for this channel.
        """
        cb = self._circuit_breakers.get(channel)
        now = datetime.now(timezone.utc)

        try:
            if cb is not None:
                response: ProviderResponse = await cb.call(
                    provider.send, recipient, message, metadata
                )
            else:
                response = await provider.send(recipient, message, metadata)

            if response.success:
                return DeliveryReceipt(
                    channel=channel,
                    status=AlertStatus.SENT,
                    attempted_at=now,
                    provider_response_code=response.status_code,
                    provider_message_id=response.provider_message_id,
                )
            else:
                return DeliveryReceipt(
                    channel=channel,
                    status=AlertStatus.FAILED,
                    attempted_at=now,
                    error=response.error or "Provider returned failure",
                    provider_response_code=response.status_code,
                )

        except CircuitBreakerOpen:
            await logger.awarning(
                "notification_circuit_breaker_open",
                channel=channel,
                alert_id=alert_id,
            )
            return DeliveryReceipt(
                channel=channel,
                status=AlertStatus.FAILED,
                attempted_at=now,
                error=f"Circuit breaker open for {channel}",
            )
        except Exception as exc:
            await logger.aerror(
                "notification_send_error",
                channel=channel,
                alert_id=alert_id,
                error=str(exc),
                exc_info=True,
            )
            return DeliveryReceipt(
                channel=channel,
                status=AlertStatus.FAILED,
                attempted_at=now,
                error=str(exc),
            )

    def _build_message(
        self,
        severity: str,
        trigger: str,
        patient_context: dict[str, Any],
    ) -> str:
        """Build a sanitized notification message without PHI.

        Args:
            severity: Alert severity level.
            trigger: What triggered the alert.
            patient_context: De-identified context (age, risk tier only).

        Returns:
            Sanitized message string safe for external providers.
        """
        age = patient_context.get("age", "unknown")
        risk_tier = patient_context.get("risk_tier", severity)

        severity_label = severity.upper()

        return (
            f"[{severity_label} ALERT] Medical attention may be required.\n\n"
            f"Risk Level: {risk_tier}\n"
            f"Patient Age: {age}\n"
            f"Reason: {trigger}\n\n"
            f"Please review the patient's status in the care portal. "
            f"This alert was generated automatically by the medical analysis system."
        )
