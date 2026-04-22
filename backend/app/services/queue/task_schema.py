"""
Task schema models for the internal async queue.

Defines the lifecycle states, task types, and Pydantic models used
for enqueuing, persisting, and reporting on background analysis tasks.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.common import PyObjectId, TimestampMixin


class TaskStatus(str, Enum):
    """Lifecycle states for queued tasks."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class TaskType(str, Enum):
    """Supported analysis task types."""

    SYMPTOM_ANALYSIS = "symptom_analysis"
    HISTORY_SUMMARIZATION = "history_summarization"


class TaskPriority(int, Enum):
    """Task priority levels (lower number = higher priority)."""

    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskCreate(BaseModel):
    """Request schema for creating a new task."""

    task_type: TaskType = Field(
        ...,
        description="Type of analysis task.",
        json_schema_extra={"example": "symptom_analysis"},
    )
    patient_id: str = Field(
        ...,
        description="Patient ID this task relates to.",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific payload (symptoms text, date range, etc.).",
    )
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Task priority — urgent tasks are processed first.",
    )


class TaskInDB(TimestampMixin):
    """Internal database representation of a queued task."""

    model_config = {"populate_by_name": True}

    id: PyObjectId = Field(alias="_id", description="MongoDB document ID.")
    task_type: TaskType
    patient_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.NORMAL
    retries: int = Field(default=0, ge=0, description="Number of retry attempts so far.")
    max_retries: int = Field(default=3, description="Maximum retry attempts before DLQ.")
    result: dict[str, Any] | None = Field(
        default=None,
        description="Task result (populated on completion).",
    )
    error: str | None = Field(
        default=None,
        description="Error message (populated on failure).",
    )
    trace_id: str | None = Field(
        default=None,
        description="ID of the associated reasoning trace.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="When this task expires (UTC).",
    )


class TaskResponse(BaseModel):
    """API response schema for task status queries."""

    id: str = Field(
        description="Task ID.",
        json_schema_extra={"example": "507f1f77bcf86cd799439016"},
    )
    task_type: TaskType = Field(
        json_schema_extra={"example": "symptom_analysis"},
    )
    patient_id: str = Field(
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    status: TaskStatus = Field(
        json_schema_extra={"example": "queued"},
    )
    priority: TaskPriority = Field(
        json_schema_extra={"example": 2},
    )
    retries: int = Field(
        json_schema_extra={"example": 0},
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="Task result — present only when status is 'completed'.",
    )
    error: str | None = Field(
        default=None,
        description="Error details — present only when status is 'failed' or 'dead_letter'.",
    )
    trace_id: str | None = Field(
        default=None,
        description="Associated reasoning trace ID.",
    )
    created_at: datetime = Field(
        json_schema_extra={"example": "2026-03-01T13:00:00Z"},
    )
    updated_at: datetime = Field(
        json_schema_extra={"example": "2026-03-01T13:05:00Z"},
    )

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "TaskResponse":
        """Construct response from a raw MongoDB document."""
        return cls(
            id=str(doc["_id"]),
            task_type=doc["task_type"],
            patient_id=doc["patient_id"],
            status=doc["status"],
            priority=doc.get("priority", TaskPriority.NORMAL),
            retries=doc.get("retries", 0),
            result=doc.get("result"),
            error=doc.get("error"),
            trace_id=doc.get("trace_id"),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        )
