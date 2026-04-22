"""
Analysis API endpoints for symptom analysis and history summarization.

Provides three endpoints:
- POST /api/v1/analyze/symptoms — enqueue symptom analysis (202 Accepted)
- POST /api/v1/analyze/history  — enqueue history summarization (202 Accepted)
- GET  /api/v1/analysis/{task_id} — poll task status

All endpoints return immediately with a task_id.  Actual processing
happens asynchronously via background workers.
"""

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_db_client, get_patient_repository
from app.db.client import AsyncMongoClient
from app.db.repositories.patient_repository import PatientRepository
from app.services.queue.task_queue import TaskQueue
from app.services.queue.task_schema import TaskCreate, TaskPriority, TaskResponse, TaskType

router = APIRouter(prefix="/api/v1", tags=["analysis"])


# ── Request Schemas ──────────────────────────────────────────────────────


class SymptomAnalysisRequest(BaseModel):
    """Request body for symptom analysis."""

    patient_id: str = Field(
        ...,
        description="Patient ID to analyze symptoms for.",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    symptoms: str = Field(
        ...,
        min_length=1,
        description="Free-text symptom description.",
        json_schema_extra={"example": "Chest pain, shortness of breath, dizziness"},
    )
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Task priority (0=urgent, 3=low).",
    )


class HistoryAnalysisRequest(BaseModel):
    """Request body for history summarization."""

    patient_id: str = Field(
        ...,
        description="Patient ID to summarize history for.",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"},
    )
    date_range: dict[str, str] | None = Field(
        default=None,
        description="Optional date range (start/end in ISO format).",
        json_schema_extra={"example": {"start": "2025-01-01", "end": "2026-01-01"}},
    )
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Task priority (0=urgent, 3=low).",
    )


class TaskAcceptedResponse(BaseModel):
    """Response returned when a task is accepted (202)."""

    task_id: str = Field(
        description="Unique task identifier for polling.",
        json_schema_extra={"example": "507f1f77bcf86cd799439016"},
    )
    status: str = Field(
        default="queued",
        description="Initial task status.",
    )
    message: str = Field(
        default="Task accepted for processing.",
        description="Human-readable status message.",
    )


# ── Dependency helpers ───────────────────────────────────────────────────


def get_task_queue(request: Request) -> TaskQueue:
    """Extract the TaskQueue from app state."""
    return request.app.state.task_queue


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/analyze/symptoms",
    response_model=TaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit symptom analysis",
    description="Enqueue a symptom analysis task. Returns immediately with a task_id.",
)
async def analyze_symptoms(
    body: SymptomAnalysisRequest,
    patient_repo: PatientRepository = Depends(get_patient_repository),
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskAcceptedResponse:
    """Submit a symptom analysis request.

    Validates the patient exists, then enqueues the task for
    asynchronous processing by the analysis worker.
    """
    # Validate patient exists
    if not ObjectId.is_valid(body.patient_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid patient_id format.",
        )

    try:
        await patient_repo.get_by_id(body.patient_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id '{body.patient_id}' not found.",
        )

    # Enqueue task
    task = TaskCreate(
        task_type=TaskType.SYMPTOM_ANALYSIS,
        patient_id=body.patient_id,
        payload={"symptoms": body.symptoms},
        priority=body.priority,
    )
    task_id = await task_queue.enqueue(task)

    return TaskAcceptedResponse(
        task_id=task_id,
        status="queued",
        message="Symptom analysis task accepted for processing.",
    )


@router.post(
    "/analyze/history",
    response_model=TaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit history summarization",
    description="Enqueue a history summarization task. Returns immediately with a task_id.",
)
async def analyze_history(
    body: HistoryAnalysisRequest,
    patient_repo: PatientRepository = Depends(get_patient_repository),
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskAcceptedResponse:
    """Submit a history summarization request.

    Validates the patient exists, then enqueues the task for
    asynchronous processing by the summarization worker.
    """
    # Validate patient exists
    if not ObjectId.is_valid(body.patient_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid patient_id format.",
        )

    try:
        await patient_repo.get_by_id(body.patient_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id '{body.patient_id}' not found.",
        )

    # Build payload
    payload: dict[str, Any] = {}
    if body.date_range:
        payload["date_range"] = body.date_range

    # Enqueue task
    task = TaskCreate(
        task_type=TaskType.HISTORY_SUMMARIZATION,
        patient_id=body.patient_id,
        payload=payload,
        priority=body.priority,
    )
    task_id = await task_queue.enqueue(task)

    return TaskAcceptedResponse(
        task_id=task_id,
        status="queued",
        message="History summarization task accepted for processing.",
    )


@router.get(
    "/analysis/{task_id}",
    response_model=TaskResponse,
    summary="Poll task status",
    description="Check the status of a previously submitted analysis task.",
)
async def get_analysis_status(
    task_id: str,
    task_queue: TaskQueue = Depends(get_task_queue),
) -> TaskResponse:
    """Get the current status of an analysis task.

    Returns the task status, result (if completed), or error (if failed).
    """
    if not ObjectId.is_valid(task_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid task_id format.",
        )

    task_doc = await task_queue.get_task(task_id)
    if task_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found.",
        )

    return TaskResponse.from_mongo(task_doc)
