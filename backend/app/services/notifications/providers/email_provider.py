"""
SendGrid email notification provider (stub implementation).

Implements the NotificationProvider interface for email delivery via SendGrid.
Currently a stub that logs messages without making real API calls.
"""

import uuid
from typing import Any

import structlog

from app.services.notifications.providers.base import NotificationProvider, ProviderResponse

logger = structlog.get_logger(__name__)


class SendGridEmailProvider(NotificationProvider):
    """Email notification provider using SendGrid API.

    Attributes:
        _api_key: SendGrid API key.
        _from_email: Sender email address.
        _dry_run: If True, log but don't send.
    """

    def __init__(
        self,
        api_key: str = "",
        from_email: str = "",
        dry_run: bool = True,
    ) -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._dry_run = dry_run

    @property
    def channel_name(self) -> str:
        return "email"

    async def send(
        self,
        recipient: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Send an email via SendGrid (stub).

        Args:
            recipient: Destination email address.
            message: Email body text.
            metadata: Optional parameters (subject, html_body, etc.).

        Returns:
            ProviderResponse with simulated success.
        """
        message_id = f"SG{uuid.uuid4().hex[:32]}"
        subject = (metadata or {}).get("subject", "Medical Alert Notification")

        await logger.ainfo(
            "email_send_stub",
            recipient=recipient,
            subject=subject,
            message_length=len(message),
            message_id=message_id,
            dry_run=self._dry_run,
        )

        return ProviderResponse(
            success=True,
            provider_message_id=message_id,
            status_code=202,
            metadata={"channel": "email", "provider": "sendgrid"},
        )

    async def health_check(self) -> bool:
        """Check SendGrid API connectivity (stub: always True)."""
        return True
