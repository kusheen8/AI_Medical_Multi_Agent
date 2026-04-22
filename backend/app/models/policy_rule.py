"""
Policy rule domain model and API schemas.

Represents configurable rules for the risk policy engine that determine
when alerts should be triggered based on analysis results.

Condition types:
- risk_threshold: triggers when risk_level meets or exceeds a threshold
- emergency_pattern: triggers on symptom keyword matching
- consecutive_high: triggers when N consecutive records are high-risk
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.common import PyObjectId, TimestampMixin


class ConditionType(str, Enum):
    """Types of conditions that can trigger a policy rule."""

    RISK_THRESHOLD = "risk_threshold"
    EMERGENCY_PATTERN = "emergency_pattern"
    CONSECUTIVE_HIGH = "consecutive_high"


class PolicyAction(str, Enum):
    """Actions taken when a policy rule matches."""

    ALERT = "alert"
    ESCALATE = "escalate"
    INFO = "info"


class RiskTier(str, Enum):
    """Risk tier levels for alert classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Schemas ──────────────────────────────────────────────────────────────


class PolicyRuleCreate(BaseModel):
    """Request schema for creating a new policy rule."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable rule name.",
        json_schema_extra={"example": "Critical Risk Alert"},
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Optional description of what this rule does.",
    )
    condition_type: ConditionType = Field(
        ...,
        description="Type of condition to evaluate.",
        json_schema_extra={"example": "risk_threshold"},
    )
    risk_level: RiskTier = Field(
        ...,
        description="Minimum risk level that triggers this rule.",
        json_schema_extra={"example": "critical"},
    )
    threshold_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Condition-specific parameters.",
        json_schema_extra={
            "example": {"min_risk_level": "critical", "consecutive_count": 3}
        },
    )
    action: PolicyAction = Field(
        ...,
        description="Action to take when rule matches.",
        json_schema_extra={"example": "alert"},
    )
    severity: str = Field(
        default="critical",
        description="Alert severity when this rule triggers.",
        json_schema_extra={"example": "critical"},
    )
    channels: list[str] = Field(
        default_factory=lambda: ["sms", "email"],
        min_length=1,
        description="Notification channels to use.",
        json_schema_extra={"example": ["sms", "email"]},
    )
    enabled: bool = Field(
        default=True,
        description="Whether this rule is active.",
    )
    dry_run: bool = Field(
        default=False,
        description="If true, evaluate but don't trigger alerts.",
    )

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Rule name must not be blank.")
        return stripped


class PolicyRuleUpdate(BaseModel):
    """Request schema for updating a policy rule (partial)."""

    name: str | None = None
    description: str | None = None
    condition_type: ConditionType | None = None
    risk_level: RiskTier | None = None
    threshold_params: dict[str, Any] | None = None
    action: PolicyAction | None = None
    severity: str | None = None
    channels: list[str] | None = None
    enabled: bool | None = None
    dry_run: bool | None = None


class PolicyRuleInDB(TimestampMixin):
    """Internal database representation of a policy rule."""

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    name: str
    description: str = ""
    condition_type: ConditionType
    risk_level: RiskTier
    threshold_params: dict[str, Any] = Field(default_factory=dict)
    action: PolicyAction
    severity: str = "critical"
    channels: list[str] = Field(default_factory=lambda: ["sms", "email"])
    enabled: bool = True
    dry_run: bool = False
    version: int = Field(default=1, description="Rule version for tracking changes.")


class PolicyRuleResponse(BaseModel):
    """API response schema for policy rules."""

    id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439020"})
    name: str
    description: str = ""
    condition_type: ConditionType
    risk_level: RiskTier
    threshold_params: dict[str, Any] = Field(default_factory=dict)
    action: PolicyAction
    severity: str
    channels: list[str]
    enabled: bool
    dry_run: bool
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "PolicyRuleResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            name=doc["name"],
            description=doc.get("description", ""),
            condition_type=doc["condition_type"],
            risk_level=doc["risk_level"],
            threshold_params=doc.get("threshold_params", {}),
            action=doc["action"],
            severity=doc.get("severity", "critical"),
            channels=doc.get("channels", ["sms", "email"]),
            enabled=doc.get("enabled", True),
            dry_run=doc.get("dry_run", False),
            version=doc.get("version", 1),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )


# ── Alert Trigger Result ────────────────────────────────────────────────


class AlertTrigger(BaseModel):
    """Result of a policy evaluation indicating an alert should be created."""

    rule_id: str = Field(description="ID of the policy rule that triggered.")
    rule_name: str = Field(description="Name of the triggering rule.")
    action: PolicyAction
    severity: str
    channels: list[str]
    reason: str = Field(description="Human-readable explanation of why the rule triggered.")
    dry_run: bool = Field(default=False, description="If true, this is a dry-run evaluation.")
