"""
Alert domain model and API schemas.

Represents caregiver notifications triggered by medical analysis results.

Validation rules:
- patient_id: required, valid ObjectId
- severity: enum (warning, error, critical)
- status: enum (pending, sent, delivered, failed)
- trigger: required, non-empty description
- channels: required, non-empty list of notification channels
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.common import PyObjectId, TimestampMixin


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Delivery lifecycle status for alerts."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryReceipt(BaseModel):
    """Record of a delivery attempt for a specific channel."""

    channel: str = Field(description="Notification channel (e.g., sms, email, push).")
    status: AlertStatus = Field(description="Delivery status for this channel.")
    attempted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the delivery was attempted.",
    )
    error: str | None = Field(default=None, description="Error message if delivery failed.")


class AlertCreate(BaseModel):
    """Request schema for creating a new alert."""

    patient_id: str = Field(
        ...,
        description="ID of the patient this alert is for.",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    severity: AlertSeverity = Field(
        ...,
        description="Alert severity level.",
        json_schema_extra={"example": "critical"},
    )
    trigger: str = Field(
        ...,
        min_length=1,
        description="What triggered this alert.",
        json_schema_extra={"example": "High risk cardiac symptoms detected"},
    )
    channels: list[str] = Field(
        ...,
        min_length=1,
        description="Notification channels to use.",
        json_schema_extra={"example": ["sms", "email"]},
    )

    @field_validator("patient_id")
    @classmethod
    def patient_id_valid_objectid(cls, v: str) -> str:
        from bson import ObjectId

        if not ObjectId.is_valid(v):
            raise ValueError("patient_id must be a valid ObjectId string.")
        return v

    @field_validator("trigger")
    @classmethod
    def trigger_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Trigger must not be blank.")
        return stripped


class AlertUpdate(BaseModel):
    """Request schema for updating an alert (partial)."""

    severity: AlertSeverity | None = None
    status: AlertStatus | None = None
    delivery_receipts: list[DeliveryReceipt] | None = None


class AlertInDB(TimestampMixin):
    """Internal database representation of an alert."""

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    patient_id: str
    severity: AlertSeverity
    trigger: str
    channels: list[str]
    status: AlertStatus = AlertStatus.PENDING
    delivery_receipts: list[DeliveryReceipt] = Field(default_factory=list)


class AlertResponse(BaseModel):
    """API response schema for alerts."""

    id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439013"})
    patient_id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439011"})
    severity: AlertSeverity = Field(json_schema_extra={"example": "critical"})
    trigger: str = Field(json_schema_extra={"example": "High risk cardiac symptoms detected"})
    channels: list[str] = Field(json_schema_extra={"example": ["sms", "email"]})
    status: AlertStatus = Field(json_schema_extra={"example": "pending"})
    delivery_receipts: list[DeliveryReceipt] = Field(default_factory=list)
    created_at: datetime = Field(json_schema_extra={"example": "2026-03-01T12:00:00Z"})
    updated_at: datetime = Field(json_schema_extra={"example": "2026-03-01T12:00:00Z"})

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "AlertResponse":
        """Construct response from a raw MongoDB document."""
        receipts = [
            DeliveryReceipt(**r) for r in doc.get("delivery_receipts", [])
        ]
        return cls(
            id=str(doc["_id"]),
            patient_id=doc["patient_id"],
            severity=doc["severity"],
            trigger=doc["trigger"],
            channels=doc.get("channels", []),
            status=doc.get("status", AlertStatus.PENDING),
            delivery_receipts=receipts,
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )
