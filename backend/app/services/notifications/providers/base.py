"""
Abstract base class for notification providers.

All notification channel adapters (SMS, Email, Push) implement this
interface, allowing the CaregiverNotifier to route messages uniformly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    """Result of a notification provider send attempt.

    Attributes:
        success: Whether the message was accepted by the provider.
        provider_message_id: Message ID assigned by the provider (for tracking).
        status_code: HTTP status code from the provider API.
        error: Error message if the send failed.
        metadata: Additional provider-specific response data.
    """

    success: bool
    provider_message_id: str = ""
    status_code: int = 200
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationProvider(ABC):
    """Abstract notification provider interface.

    Subclasses implement the ``send`` method for a specific channel
    (SMS via Twilio, Email via SendGrid, Push via FCM).
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the channel identifier (e.g., 'sms', 'email', 'push')."""
        ...

    @abstractmethod
    async def send(
        self,
        recipient: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Send a notification to the recipient.

        Args:
            recipient: Destination address (phone number, email, device token).
            message: Notification message body.
            metadata: Optional provider-specific parameters.

        Returns:
            ProviderResponse with success/failure details.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the provider is currently reachable.

        Returns:
            True if the provider API is responsive.
        """
        return True
