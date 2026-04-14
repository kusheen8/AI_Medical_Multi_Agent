"""
Medical record domain model and API schemas.

Represents a single symptom submission / analysis result linked to a patient.

Validation rules:
- patient_id: required, valid ObjectId
- symptoms: required, non-empty text
- risk_level: enum (low, medium, high, critical)
- entities, analysis_result: optional (populated by agent pipeline)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.common import PyObjectId, TimestampMixin


class RiskLevel(str, Enum):
    """Risk classification levels for medical records."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MedicalRecordCreate(BaseModel):
    """Request schema for creating a new medical record."""

    patient_id: str = Field(
        ...,
        description="ID of the patient this record belongs to.",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    symptoms: str = Field(
        ...,
        min_length=1,
        description="Free-text symptom description.",
        json_schema_extra={"example": "Chest pain, shortness of breath"},
    )
    entities: dict[str, Any] | None = Field(
        default=None,
        description="Extracted medical entities (populated by analyzer).",
        json_schema_extra={"example": {"symptom1": "chest pain", "severity": "high"}},
    )
    analysis_result: str | None = Field(
        default=None,
        description="Analysis output from the medical agent pipeline.",
    )
    risk_level: RiskLevel | None = Field(
        default=None,
        description="Risk classification (populated by analyzer).",
    )

    @field_validator("symptoms")
    @classmethod
    def symptoms_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Symptoms field must not be blank.")
        return stripped

    @field_validator("patient_id")
    @classmethod
    def patient_id_valid_objectid(cls, v: str) -> str:
        from bson import ObjectId

        if not ObjectId.is_valid(v):
            raise ValueError("patient_id must be a valid ObjectId string.")
        return v


class MedicalRecordUpdate(BaseModel):
    """Request schema for updating a medical record (partial)."""

    symptoms: str | None = Field(None, min_length=1)
    entities: dict[str, Any] | None = None
    analysis_result: str | None = None
    risk_level: RiskLevel | None = None

    @field_validator("symptoms")
    @classmethod
    def symptoms_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Symptoms field must not be blank.")
            return stripped
        return v


class MedicalRecordInDB(TimestampMixin):
    """Internal database representation of a medical record."""

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    patient_id: str
    symptoms: str
    entities: dict[str, Any] | None = None
    analysis_result: str | None = None
    risk_level: RiskLevel | None = None


class MedicalRecordResponse(BaseModel):
    """API response schema for medical records."""

    id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439012"})
    patient_id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439011"})
    symptoms: str = Field(json_schema_extra={"example": "Chest pain, shortness of breath"})
    entities: dict[str, Any] | None = Field(
        default=None,
        json_schema_extra={"example": {"symptom1": "chest pain", "severity": "high"}},
    )
    analysis_result: str | None = Field(
        default=None,
        json_schema_extra={"example": "Possible cardiac issue; recommend EKG"},
    )
    risk_level: RiskLevel | None = Field(
        default=None,
        json_schema_extra={"example": "high"},
    )
    created_at: datetime = Field(json_schema_extra={"example": "2026-03-01T11:00:00Z"})
    updated_at: datetime = Field(json_schema_extra={"example": "2026-03-01T11:30:00Z"})

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "MedicalRecordResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            patient_id=doc["patient_id"],
            symptoms=doc["symptoms"],
            entities=doc.get("entities"),
            analysis_result=doc.get("analysis_result"),
            risk_level=doc.get("risk_level"),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )
