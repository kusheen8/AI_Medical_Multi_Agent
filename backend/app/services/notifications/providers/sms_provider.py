"""
Twilio SMS notification provider (stub implementation).

Implements the NotificationProvider interface for SMS delivery via Twilio.
Currently a stub that logs messages without making real API calls.
Replace the ``send`` method body with actual Twilio SDK calls when ready.
"""

import uuid
from typing import Any

import structlog

from app.services.notifications.providers.base import NotificationProvider, ProviderResponse

logger = structlog.get_logger(__name__)


class TwilioSMSProvider(NotificationProvider):
    """SMS notification provider using Twilio API.

    Attributes:
        _account_sid: Twilio account SID.
        _auth_token: Twilio auth token.
        _from_number: Sender phone number.
        _dry_run: If True, log but don't send.
    """

    def __init__(
        self,
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = "",
        dry_run: bool = True,
    ) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number
        self._dry_run = dry_run

    @property
    def channel_name(self) -> str:
        return "sms"

    async def send(
        self,
        recipient: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Send an SMS message via Twilio (stub).

        In production, this would use the Twilio REST API:
        ``POST https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json``

        Args:
            recipient: Destination phone number (E.164 format).
            message: SMS body text.
            metadata: Optional additional parameters.

        Returns:
            ProviderResponse with simulated success.
        """
        message_id = f"SM{uuid.uuid4().hex[:32]}"

        await logger.ainfo(
            "sms_send_stub",
            recipient=recipient,
            message_length=len(message),
            message_id=message_id,
            dry_run=self._dry_run,
        )

        # Stub: always return success
        return ProviderResponse(
            success=True,
            provider_message_id=message_id,
            status_code=201,
            metadata={"channel": "sms", "provider": "twilio"},
        )

    async def health_check(self) -> bool:
        """Check Twilio API connectivity (stub: always True)."""
        return True
