"""
Firebase Cloud Messaging push notification provider (stub implementation).

Implements the NotificationProvider interface for push delivery via FCM.
Currently a stub that logs messages without making real API calls.
"""

import uuid
from typing import Any

import structlog

from app.services.notifications.providers.base import NotificationProvider, ProviderResponse

logger = structlog.get_logger(__name__)


class FCMPushProvider(NotificationProvider):
    """Push notification provider using Firebase Cloud Messaging.

    Attributes:
        _server_key: FCM server key.
        _dry_run: If True, log but don't send.
    """

    def __init__(
        self,
        server_key: str = "",
        dry_run: bool = True,
    ) -> None:
        self._server_key = server_key
        self._dry_run = dry_run

    @property
    def channel_name(self) -> str:
        return "push"

    async def send(
        self,
        recipient: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Send a push notification via FCM (stub).

        Args:
            recipient: Device registration token.
            message: Notification body text.
            metadata: Optional parameters (title, data payload, etc.).

        Returns:
            ProviderResponse with simulated success.
        """
        message_id = f"FCM{uuid.uuid4().hex[:30]}"
        title = (metadata or {}).get("title", "Medical Alert")

        await logger.ainfo(
            "push_send_stub",
            recipient=recipient[:20] + "..." if len(recipient) > 20 else recipient,
            title=title,
            message_length=len(message),
            message_id=message_id,
            dry_run=self._dry_run,
        )

        return ProviderResponse(
            success=True,
            provider_message_id=message_id,
            status_code=200,
            metadata={"channel": "push", "provider": "fcm"},
        )

    async def health_check(self) -> bool:
        """Check FCM API connectivity (stub: always True)."""
        return True
