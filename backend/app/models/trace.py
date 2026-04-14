"""
Reasoning trace domain model and API schemas.

Represents the de-identified instructions sent from the cloud coordinator
to local agents. These traces contain NO raw PHI — only task metadata,
allowed data classifications, and expiration policies.

Fields:
- task_type: classification of the task (e.g., "symptom_analysis")
- instructions: coordinator-generated reasoning instructions
- allowed_data_classes: data categories the local agent may access
- origin: which agent generated this trace
- expires_at: when the trace should be considered stale
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.models.common import PyObjectId, TimestampMixin


class ReasoningTraceCreate(BaseModel):
    """Request schema for creating a reasoning trace."""

    task_type: str = Field(
        ...,
        min_length=1,
        description="Type of task (e.g., symptom_analysis, history_summary).",
        json_schema_extra={"example": "symptom_analysis"},
    )
    instructions: str = Field(
        ...,
        min_length=1,
        description="Coordinator-generated reasoning instructions (no PHI).",
        json_schema_extra={"example": "Analyze symptoms for cardiac risk indicators."},
    )
    allowed_data_classes: list[str] = Field(
        default_factory=list,
        description="Data categories the local agent may access.",
        json_schema_extra={"example": ["vitals", "symptoms", "medications"]},
    )
    origin: str = Field(
        ...,
        min_length=1,
        description="Agent that generated this trace.",
        json_schema_extra={"example": "gemini_coordinator"},
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When this trace expires (UTC). Null = no expiry.",
    )


class ReasoningTraceInDB(TimestampMixin):
    """Internal database representation of a reasoning trace."""

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    task_type: str
    instructions: str
    allowed_data_classes: list[str] = Field(default_factory=list)
    origin: str
    expires_at: datetime | None = None


class ReasoningTraceResponse(BaseModel):
    """API response schema for reasoning traces."""

    id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439014"})
    task_type: str = Field(json_schema_extra={"example": "symptom_analysis"})
    instructions: str = Field(
        json_schema_extra={"example": "Analyze symptoms for cardiac risk indicators."},
    )
    allowed_data_classes: list[str] = Field(
        json_schema_extra={"example": ["vitals", "symptoms", "medications"]},
    )
    origin: str = Field(json_schema_extra={"example": "gemini_coordinator"})
    expires_at: datetime | None = None
    created_at: datetime = Field(json_schema_extra={"example": "2026-03-01T13:00:00Z"})
    updated_at: datetime = Field(json_schema_extra={"example": "2026-03-01T13:00:00Z"})

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "ReasoningTraceResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            task_type=doc["task_type"],
            instructions=doc["instructions"],
            allowed_data_classes=doc.get("allowed_data_classes", []),
            origin=doc["origin"],
            expires_at=doc.get("expires_at"),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )
