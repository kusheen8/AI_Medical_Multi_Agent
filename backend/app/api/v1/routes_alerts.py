"""
Alert management API endpoints.

Provides the full alert lifecycle:
- POST   /api/v1/alerts                     — Create alert (with idempotency)
- GET    /api/v1/alerts/failed              — List undelivered alerts
- GET    /api/v1/alerts/{id}                — Retrieve alert details
- GET    /api/v1/alerts/{id}/delivery-status — Delivery receipts
- PUT    /api/v1/alerts/{id}/acknowledge    — Acknowledge alert
- GET    /api/v1/patients/{patient_id}/alerts — Patient's alerts (paginated)
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_alert_repository
from app.core.idempotency import check_idempotency, store_idempotency, validate_idempotency_key
from app.db.repositories.alert_repository import AlertRepository
from app.db.repositories.idempotency_repository import IdempotencyRepository
from app.models.alert import AlertCreate, AlertResponse, AlertStatus, DeliveryReceipt

router = APIRouter(prefix="/api/v1", tags=["alerts"])


# ── Request/Response Schemas ─────────────────────────────────────────────


class AlertAcknowledgeRequest(BaseModel):
    """Request body for acknowledging an alert."""

    acknowledged_by: str = Field(
        ...,
        min_length=1,
        description="ID or name of the caregiver acknowledging.",
        json_schema_extra={"example": "caregiver-jane-doe"},
    )


class AlertCreateResponse(BaseModel):
    """Response for alert creation."""

    id: str = Field(json_schema_extra={"example": "507f1f77bcf86cd799439013"})
    created_at: datetime
    status: str = "pending"


class DeliveryStatusResponse(BaseModel):
    """Response for delivery status queries."""

    alert_id: str
    delivery_receipts: list[DeliveryReceipt]


# ── Dependency Helpers ───────────────────────────────────────────────────


def get_idempotency_repo(request: Request) -> IdempotencyRepository:
    """Extract the IdempotencyRepository from app state."""
    return IdempotencyRepository(request.app.state.db_client)


def get_notifier(request: Request) -> Any:
    """Extract the CaregiverNotifier from app state."""
    return getattr(request.app.state, "caregiver_notifier", None)


def get_metrics(request: Request) -> Any:
    """Extract the MetricsCollector from app state."""
    return getattr(request.app.state, "metrics_collector", None)


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/alerts",
    response_model=AlertCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create alert",
    description="Create a new caregiver alert with optional idempotency key.",
)
async def create_alert(
    body: AlertCreate,
    request: Request,
    alert_repo: AlertRepository = Depends(get_alert_repository),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        description="UUID to prevent duplicate alert creation.",
    ),
) -> AlertCreateResponse:
    """Create a new alert and optionally dispatch notifications."""
    # Idempotency check
    validated_key = validate_idempotency_key(idempotency_key)
    if validated_key:
        idem_repo = get_idempotency_repo(request)
        cached = await check_idempotency(validated_key, idem_repo)
        if cached is not None:
            return AlertCreateResponse(**cached)

    # Check for existing alert with same idempotency key in alerts collection
    if validated_key:
        existing = await alert_repo.find_by_idempotency_key(validated_key)
        if existing:
            return AlertCreateResponse(
                id=str(existing["_id"]),
                created_at=existing.get("created_at", datetime.now(timezone.utc)),
                status=existing.get("status", "pending"),
            )

    # Create the alert document
    now = datetime.now(timezone.utc)
    alert_doc: dict[str, Any] = {
        "patient_id": body.patient_id,
        "severity": body.severity.value,
        "trigger": body.trigger,
        "channels": body.channels,
        "status": AlertStatus.PENDING.value,
        "delivery_receipts": [],
        "idempotency_key": validated_key,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "created_at": now,
        "updated_at": now,
    }

    created = await alert_repo.create(alert_doc)
    alert_id = str(created["_id"])

    # Record metrics
    metrics = get_metrics(request)
    if metrics:
        metrics.record_alert_created(body.severity.value)

    # Dispatch notifications (non-blocking)
    notifier = get_notifier(request)
    if notifier:
        try:
            patient_context = {"age": "unknown", "risk_tier": body.severity.value}
            receipts = await notifier.dispatch(
                alert_doc={**alert_doc, "_id": created["_id"]},
                patient_context=patient_context,
            )
            # Store delivery receipts
            for receipt in receipts:
                await alert_repo.add_delivery_receipt(alert_id, {
                    "channel": receipt.channel,
                    "status": receipt.status.value,
                    "attempted_at": receipt.attempted_at.isoformat() if receipt.attempted_at else now.isoformat(),
                    "error": receipt.error,
                    "provider_response_code": getattr(receipt, "provider_response_code", None),
                    "provider_message_id": getattr(receipt, "provider_message_id", None),
                    "retry_count": 0,
                })
            # Update overall status based on receipts
            any_sent = any(r.status == AlertStatus.SENT for r in receipts)
            all_failed = all(r.status == AlertStatus.FAILED for r in receipts)
            if any_sent:
                await alert_repo.update(alert_id, {"status": AlertStatus.SENT.value})
            elif all_failed:
                await alert_repo.update(alert_id, {"status": AlertStatus.FAILED.value})
        except Exception:
            pass  # Alert is created even if dispatch fails; retry will handle it

    response_data = {
        "id": alert_id,
        "created_at": now.isoformat(),
        "status": "pending",
    }

    # Store idempotency response
    if validated_key:
        idem_repo = get_idempotency_repo(request)
        await store_idempotency(
            validated_key, idem_repo, "POST", "/api/v1/alerts", response_data, 201
        )

    return AlertCreateResponse(id=alert_id, created_at=now, status="pending")


@router.get(
    "/alerts/failed",
    response_model=list[AlertResponse],
    summary="List failed alerts",
    description="List alerts that failed delivery.",
)
async def list_failed_alerts(
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> list[AlertResponse]:
    """List all alerts with failed delivery status."""
    result = await alert_repo.find_by_status(AlertStatus.FAILED.value)
    items = result.get("items", [])
    return [AlertResponse.from_mongo(doc) for doc in items]


@router.get(
    "/alerts/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert details",
    description="Retrieve details for a specific alert.",
)
async def get_alert(
    alert_id: str,
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> AlertResponse:
    """Get a single alert by ID."""
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid alert_id format.",
        )

    doc = await alert_repo.get_by_id(alert_id)
    return AlertResponse.from_mongo(doc)


@router.get(
    "/alerts/{alert_id}/delivery-status",
    response_model=DeliveryStatusResponse,
    summary="Get delivery status",
    description="Retrieve delivery receipts for all channels of an alert.",
)
async def get_delivery_status(
    alert_id: str,
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> DeliveryStatusResponse:
    """Get delivery status for each channel of an alert."""
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid alert_id format.",
        )

    doc = await alert_repo.get_by_id(alert_id)
    receipts = [
        DeliveryReceipt(**r) for r in doc.get("delivery_receipts", [])
    ]
    return DeliveryStatusResponse(alert_id=alert_id, delivery_receipts=receipts)


@router.put(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge alert",
    description="Acknowledge an alert by a caregiver, stopping retry notifications.",
)
async def acknowledge_alert(
    alert_id: str,
    body: AlertAcknowledgeRequest,
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> AlertResponse:
    """Acknowledge an alert — stops retry notifications."""
    if not ObjectId.is_valid(alert_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid alert_id format.",
        )

    doc = await alert_repo.acknowledge(alert_id, body.acknowledged_by)
    return AlertResponse.from_mongo(doc)


@router.get(
    "/patients/{patient_id}/alerts",
    response_model=list[AlertResponse],
    summary="List patient alerts",
    description="List all alerts for a specific patient (paginated).",
)
async def list_patient_alerts(
    patient_id: str,
    page: int = 1,
    page_size: int = 20,
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> list[AlertResponse]:
    """List alerts for a patient with pagination."""
    if not ObjectId.is_valid(patient_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid patient_id format.",
        )

    result = await alert_repo.list_by_patient_id(patient_id, page, page_size)
    items = result.get("items", [])
    return [AlertResponse.from_mongo(doc) for doc in items]
