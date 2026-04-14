"""
Patient domain model and API schemas.

Defines the data structures for patient records including:
- PatientCreate: Request schema for creating a new patient
- PatientUpdate: Request schema for partial updates
- PatientInDB: Internal database representation
- PatientResponse: API response schema

Validation rules:
- name: required, 1–255 characters
- dob: required, ISO 8601 date string
- sex: enum (M, F, Other)
- conditions, medications, allergies: optional string lists
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.common import PyObjectId, TimestampMixin


class Sex(str, Enum):
    """Biological sex options for patient records."""

    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"


class PatientCreate(BaseModel):
    """Request schema for creating a new patient."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full name of the patient.",
        json_schema_extra={"example": "John Doe"},
    )
    dob: date = Field(
        ...,
        description="Date of birth in ISO 8601 format (YYYY-MM-DD).",
        json_schema_extra={"example": "1985-03-15"},
    )
    sex: Sex = Field(
        ...,
        description="Biological sex.",
        json_schema_extra={"example": "M"},
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Known medical conditions.",
        json_schema_extra={"example": ["diabetes", "hypertension"]},
    )
    medications: list[str] = Field(
        default_factory=list,
        description="Current medications.",
        json_schema_extra={"example": ["metformin", "lisinopril"]},
    )
    allergies: list[str] = Field(
        default_factory=list,
        description="Known allergies.",
        json_schema_extra={"example": ["penicillin"]},
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Patient name must not be blank.")
        return stripped

    @field_validator("dob")
    @classmethod
    def dob_must_be_past(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return v


class PatientUpdate(BaseModel):
    """Request schema for updating a patient (partial — all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    dob: date | None = None
    sex: Sex | None = None
    conditions: list[str] | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Patient name must not be blank.")
            return stripped
        return v

    @field_validator("dob")
    @classmethod
    def dob_must_be_past(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return v


class PatientInDB(TimestampMixin):
    """Internal database representation of a patient record.

    The ``id`` field is aliased from ``_id`` for MongoDB compatibility.
    """

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    name: str
    dob: date
    sex: Sex
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)

    def to_response(self) -> "PatientResponse":
        """Convert DB model to API response."""
        return PatientResponse(
            id=str(self.id),
            name=self.name,
            dob=self.dob,
            sex=self.sex,
            conditions=self.conditions,
            medications=self.medications,
            allergies=self.allergies,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class PatientResponse(BaseModel):
    """API response schema for patient data."""

    id: str = Field(description="Patient ID.", json_schema_extra={"example": "507f1f77bcf86cd799439011"})
    name: str = Field(json_schema_extra={"example": "John Doe"})
    dob: date = Field(json_schema_extra={"example": "1985-03-15"})
    sex: Sex = Field(json_schema_extra={"example": "M"})
    conditions: list[str] = Field(json_schema_extra={"example": ["diabetes", "hypertension"]})
    medications: list[str] = Field(json_schema_extra={"example": ["metformin", "lisinopril"]})
    allergies: list[str] = Field(json_schema_extra={"example": ["penicillin"]})
    created_at: datetime = Field(json_schema_extra={"example": "2026-03-01T10:00:00Z"})
    updated_at: datetime = Field(json_schema_extra={"example": "2026-03-01T10:00:00Z"})

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "PatientResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            name=doc["name"],
            dob=doc["dob"],
            sex=doc["sex"],
            conditions=doc.get("conditions", []),
            medications=doc.get("medications", []),
            allergies=doc.get("allergies", []),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )
