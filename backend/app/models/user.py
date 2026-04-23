"""
User and authentication domain models.

Defines the data structures for user accounts and JWT tokens:
- UserRole: Role-based access control enum
- UserCreate: Registration request schema
- UserInDB: Internal database representation (with hashed password)
- UserResponse: API response schema (no password)
- TokenPayload: Decoded JWT claims
- TokenPair: Login response with access + refresh tokens
- LoginRequest: Email/password login schema
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.common import PyObjectId, TimestampMixin


class UserRole(str, Enum):
    """Roles for role-based access control (RBAC)."""

    PATIENT = "patient"
    CAREGIVER = "caregiver"
    DOCTOR = "doctor"
    ADMIN = "admin"


class UserCreate(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(
        ...,
        description="User email address (used as login identifier).",
        json_schema_extra={"example": "user@example.com"},
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters).",
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full name of the user.",
        json_schema_extra={"example": "Jane Smith"},
    )
    role: UserRole = Field(
        default=UserRole.PATIENT,
        description="User role for access control.",
    )
    patient_id: str | None = Field(
        default=None,
        description="Associated patient ID (for patient/caregiver roles).",
    )
    assigned_patient_ids: list[str] = Field(
        default_factory=list,
        description="Patient IDs this user is authorized to access (for caregivers/doctors).",
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserInDB(TimestampMixin):
    """Internal database representation of a user."""

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    email: str
    hashed_password: str
    full_name: str
    role: UserRole
    patient_id: str | None = None
    assigned_patient_ids: list[str] = Field(default_factory=list)
    is_active: bool = True

    def to_response(self) -> "UserResponse":
        """Convert DB model to API response (strips password)."""
        return UserResponse(
            id=str(self.id),
            email=self.email,
            full_name=self.full_name,
            role=self.role,
            patient_id=self.patient_id,
            assigned_patient_ids=self.assigned_patient_ids,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class UserResponse(BaseModel):
    """API response schema for user data (no password)."""

    id: str = Field(description="User ID.")
    email: str
    full_name: str
    role: UserRole
    patient_id: str | None = None
    assigned_patient_ids: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "UserResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            email=doc["email"],
            full_name=doc["full_name"],
            role=doc["role"],
            patient_id=doc.get("patient_id"),
            assigned_patient_ids=doc.get("assigned_patient_ids", []),
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )


class LoginRequest(BaseModel):
    """Email/password login request."""

    email: EmailStr = Field(
        ...,
        description="User email address.",
        json_schema_extra={"example": "user@example.com"},
    )
    password: str = Field(
        ...,
        description="User password.",
    )


class TokenPayload(BaseModel):
    """Decoded JWT token claims."""

    sub: str = Field(description="User ID (subject).")
    role: UserRole = Field(description="User role.")
    scopes: list[str] = Field(default_factory=list, description="Permission scopes.")
    exp: int = Field(description="Expiration timestamp (Unix epoch).")
    jti: str = Field(description="Unique token ID for revocation.")
    token_type: str = Field(default="access", description="Token type (access/refresh).")


class TokenPair(BaseModel):
    """Login response containing access and refresh tokens."""

    access_token: str = Field(description="Short-lived JWT access token.")
    refresh_token: str = Field(description="Long-lived JWT refresh token.")
    token_type: str = Field(default="bearer", description="Token type.")
    expires_in: int = Field(description="Access token TTL in seconds.")
