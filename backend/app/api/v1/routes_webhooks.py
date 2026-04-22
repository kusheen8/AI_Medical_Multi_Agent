"""
Webhook endpoints for notification delivery status updates.

Receives delivery status callbacks from external providers:
- POST /api/v1/webhooks/sms-status   — Twilio delivery webhook
- POST /api/v1/webhooks/email-status — SendGrid delivery webhook
- POST /api/v1/webhooks/push-status  — FCM delivery webhook
"""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_alert_repository
from app.db.repositories.alert_repository import AlertRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


# ── Request Schemas ──────────────────────────────────────────────────────


class SMSWebhookPayload(BaseModel):
    """Twilio SMS delivery status webhook payload."""

    MessageSid: str = Field(description="Twilio message SID.")
    MessageStatus: str = Field(description="Status: queued, sent, delivered, failed, undelivered.")
    To: str = Field(default="", description="Recipient phone number.")
    ErrorCode: str | None = Field(default=None, description="Twilio error code if failed.")
    alert_id: str = Field(default="", description="Associated alert ID.")


class EmailWebhookPayload(BaseModel):
    """SendGrid email delivery status webhook payload."""

    sg_message_id: str = Field(default="", description="SendGrid message ID.")
    event: str = Field(description="Event type: delivered, bounce, dropped, deferred.")
    email: str = Field(default="", description="Recipient email.")
    reason: str = Field(default="", description="Bounce/drop reason.")
    alert_id: str = Field(default="", description="Associated alert ID.")


class PushWebhookPayload(BaseModel):
    """FCM push delivery status webhook payload."""

    message_id: str = Field(default="", description="FCM message ID.")
    status: str = Field(description="Status: delivered, failed.")
    device_token: str = Field(default="", description="Target device token.")
    error: str | None = Field(default=None, description="Error message if failed.")
    alert_id: str = Field(default="", description="Associated alert ID.")


# ── Webhook Signature Validation ─────────────────────────────────────────


def _validate_webhook_signature(
    payload_body: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    """Validate webhook authenticity via HMAC-SHA256 signature.

    Args:
        payload_body: Raw request body bytes.
        signature: Signature from the webhook header.
        secret: Shared signing secret.

    Returns:
        True if signature is valid or if secret is empty (dev mode).
    """
    if not secret:
        # In development, skip validation
        return True
    if not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def _get_webhook_secret(request: Request) -> str:
    """Get the webhook signing secret from app settings."""
    settings = getattr(request.app.state, "settings", None)
    if settings:
        return getattr(settings, "WEBHOOK_SIGNING_SECRET", "")
    return ""


# ── Status Mapping ───────────────────────────────────────────────────────


_SMS_STATUS_MAP: dict[str, str] = {
    "queued": "pending",
    "sent": "sent",
    "delivered": "delivered",
    "failed": "failed",
    "undelivered": "failed",
}

_EMAIL_STATUS_MAP: dict[str, str] = {
    "delivered": "delivered",
    "bounce": "failed",
    "dropped": "failed",
    "deferred": "pending",
    "processed": "sent",
}

_PUSH_STATUS_MAP: dict[str, str] = {
    "delivered": "delivered",
    "failed": "failed",
}


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/sms-status",
    status_code=status.HTTP_200_OK,
    summary="SMS delivery webhook",
    description="Receive Twilio SMS delivery status updates.",
)
async def sms_status_webhook(
    payload: SMSWebhookPayload,
    request: Request,
    alert_repo: AlertRepository = Depends(get_alert_repository),
    x_twilio_signature: str | None = Header(default=None),
) -> dict[str, str]:
    """Process SMS delivery status from Twilio."""
    alert_id = payload.alert_id
    if not alert_id:
        return {"status": "ignored", "reason": "no alert_id"}

    mapped_status = _SMS_STATUS_MAP.get(payload.MessageStatus, "pending")

    receipt_data = {
        "channel": "sms",
        "status": mapped_status,
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "provider_message_id": payload.MessageSid,
        "provider_response_code": int(payload.ErrorCode) if payload.ErrorCode else None,
        "error": f"Error code: {payload.ErrorCode}" if payload.ErrorCode else None,
    }

    try:
        await alert_repo.add_delivery_receipt(alert_id, receipt_data)
        await logger.ainfo(
            "webhook_sms_processed",
            alert_id=alert_id,
            message_sid=payload.MessageSid,
            status=mapped_status,
        )
    except Exception:
        await logger.aerror("webhook_sms_error", alert_id=alert_id, exc_info=True)

    return {"status": "processed"}


@router.post(
    "/email-status",
    status_code=status.HTTP_200_OK,
    summary="Email delivery webhook",
    description="Receive SendGrid email delivery status updates.",
)
async def email_status_webhook(
    payload: EmailWebhookPayload,
    request: Request,
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> dict[str, str]:
    """Process email delivery status from SendGrid."""
    alert_id = payload.alert_id
    if not alert_id:
        return {"status": "ignored", "reason": "no alert_id"}

    mapped_status = _EMAIL_STATUS_MAP.get(payload.event, "pending")

    receipt_data = {
        "channel": "email",
        "status": mapped_status,
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "provider_message_id": payload.sg_message_id,
        "error": payload.reason if payload.reason else None,
    }

    try:
        await alert_repo.add_delivery_receipt(alert_id, receipt_data)
        await logger.ainfo(
            "webhook_email_processed",
            alert_id=alert_id,
            event=payload.event,
            status=mapped_status,
        )
    except Exception:
        await logger.aerror("webhook_email_error", alert_id=alert_id, exc_info=True)

    return {"status": "processed"}


@router.post(
    "/push-status",
    status_code=status.HTTP_200_OK,
    summary="Push delivery webhook",
    description="Receive FCM push delivery status updates.",
)
async def push_status_webhook(
    payload: PushWebhookPayload,
    request: Request,
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> dict[str, str]:
    """Process push delivery status from FCM."""
    alert_id = payload.alert_id
    if not alert_id:
        return {"status": "ignored", "reason": "no alert_id"}

    mapped_status = _PUSH_STATUS_MAP.get(payload.status, "pending")

    receipt_data = {
        "channel": "push",
        "status": mapped_status,
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "provider_message_id": payload.message_id,
        "error": payload.error,
    }

    try:
        await alert_repo.add_delivery_receipt(alert_id, receipt_data)
        await logger.ainfo(
            "webhook_push_processed",
            alert_id=alert_id,
            status=mapped_status,
        )
    except Exception:
        await logger.aerror("webhook_push_error", alert_id=alert_id, exc_info=True)

    return {"status": "processed"}
