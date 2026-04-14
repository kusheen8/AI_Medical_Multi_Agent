"""
Audit log domain model for PHI access tracking.

Every read/write/delete of patient or medical record data is logged here
for compliance and forensic review.  Audit logs are **immutable** — once
written, they cannot be updated or deleted through the application layer.

Fields:
- user_id: Who performed the action (placeholder until Phase 5 auth)
- action: read / write / delete
- resource_type: patients / records / alerts
- resource_id: The specific document accessed
- request_id: Correlation ID from the request middleware
- ip_address: Client IP address
- timestamp: When the access occurred
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.common import PyObjectId


class AuditAction(str, Enum):
    """Types of actions tracked in audit logs."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class AuditLogEntry(BaseModel):
    """Schema for writing audit log entries to MongoDB.

    This model is write-only from the application's perspective.
    No update or delete operations should be exposed.
    """

    model_config = {"populate_by_name": True}

    id: PyObjectId | None = Field(default=None, alias="_id")
    user_id: str = Field(
        description="User who performed the action ('anonymous' until auth is implemented).",
    )
    action: AuditAction = Field(description="Type of action performed.")
    resource_type: str = Field(
        description="Type of resource accessed (e.g., 'patients', 'records').",
    )
    resource_id: str | None = Field(
        default=None,
        description="Specific document ID accessed (if applicable).",
    )
    request_id: str = Field(
        description="Correlation ID from request middleware.",
    )
    ip_address: str = Field(
        default="unknown",
        description="Client IP address.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the action.",
    )


class AuditLogResponse(BaseModel):
    """API response schema for audit log queries."""

    id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439015"})
    user_id: str = Field(json_schema_extra={"example": "anonymous"})
    action: AuditAction = Field(json_schema_extra={"example": "read"})
    resource_type: str = Field(json_schema_extra={"example": "patients"})
    resource_id: str | None = Field(json_schema_extra={"example": "507f1f77bcf86cd799439011"})
    request_id: str = Field(json_schema_extra={"example": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"})
    ip_address: str = Field(json_schema_extra={"example": "127.0.0.1"})
    timestamp: datetime = Field(json_schema_extra={"example": "2026-03-01T10:00:00Z"})

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "AuditLogResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            action=doc["action"],
            resource_type=doc["resource_type"],
            resource_id=doc.get("resource_id"),
            request_id=doc["request_id"],
            ip_address=doc.get("ip_address", "unknown"),
            timestamp=doc.get("timestamp", datetime.now(timezone.utc)),
        )
