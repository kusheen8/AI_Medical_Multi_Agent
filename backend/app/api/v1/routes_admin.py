"""
Admin dashboard API endpoints.

Provides operational visibility for system administrators:
- GET  /api/v1/admin/health/summary  — Overall system status
- GET  /api/v1/admin/alerts/failed   — Failed alerts awaiting retry
- GET  /api/v1/admin/queue/tasks     — Active queue tasks
- POST /api/v1/admin/dlq/retry/{id}  — Manually retry a DLQ item

All endpoints require ``X-Admin-Key`` header for authentication (Phase 5
will upgrade this to JWT/RBAC).
"""

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.v1.dependencies import get_alert_repository
from app.db.repositories.alert_repository import AlertRepository
from app.models.alert import AlertResponse, AlertStatus

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Admin Auth Dependency ────────────────────────────────────────────────


async def verify_admin_key(
    request: Request,
    x_admin_key: str = Header(
        ...,
        alias="X-Admin-Key",
        description="Admin API key for authentication.",
    ),
) -> str:
    """Verify the admin API key.

    Phase 5 will replace this with proper JWT/RBAC authentication.

    Returns:
        The validated admin key.
    """
    settings = getattr(request.app.state, "settings", None)
    expected_key = ""
    if settings:
        expected_key = getattr(settings, "ADMIN_API_KEY", "")

    if not expected_key or x_admin_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key.",
        )
    return x_admin_key


# ── Endpoints ────────────────────────────────────────────────────────────


@router.get(
    "/health/summary",
    summary="System health summary",
    description="Overall system status including queue, circuit breakers, and delivery rates.",
    dependencies=[Depends(verify_admin_key)],
)
async def admin_health_summary(request: Request) -> dict[str, Any]:
    """Return comprehensive system health summary."""
    result: dict[str, Any] = {}

    # Metrics summary
    metrics = getattr(request.app.state, "metrics_collector", None)
    if metrics:
        task_queue = getattr(request.app.state, "task_queue", None)
        if task_queue:
            metrics.set_queue_length(task_queue.pending_count)
        result["metrics"] = metrics.get_summary()

    # Health service
    health_service = getattr(request.app.state, "health_service", None)
    if health_service:
        try:
            health = await health_service.check_all()
            result["dependencies"] = health.to_dict()
        except Exception:
            result["dependencies"] = {"status": "error", "msg": "Health check failed"}

    # DLQ count
    dlq = getattr(request.app.state, "dlq_manager", None)
    if dlq:
        try:
            dlq_count = await dlq.get_count()
            result["dlq"] = {"pending_count": dlq_count}
        except Exception:
            result["dlq"] = {"pending_count": -1, "error": "Failed to query DLQ"}

    return result


@router.get(
    "/alerts/failed",
    response_model=list[AlertResponse],
    summary="Failed alerts",
    description="List alerts that failed delivery awaiting retry.",
    dependencies=[Depends(verify_admin_key)],
)
async def admin_failed_alerts(
    alert_repo: AlertRepository = Depends(get_alert_repository),
) -> list[AlertResponse]:
    """List failed alerts for admin review."""
    result = await alert_repo.find_by_status(AlertStatus.FAILED.value)
    items = result.get("items", [])
    return [AlertResponse.from_mongo(doc) for doc in items]


@router.get(
    "/queue/tasks",
    summary="Active queue tasks",
    description="List tasks currently in the queue.",
    dependencies=[Depends(verify_admin_key)],
)
async def admin_queue_tasks(
    request: Request,
    status_filter: str = "queued",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List active queue tasks for admin visibility."""
    task_queue = getattr(request.app.state, "task_queue", None)
    if task_queue is None:
        return {"items": [], "total": 0, "pending_count": 0}

    # Query tasks from MongoDB directly
    db_client = getattr(request.app.state, "db_client", None)
    if db_client is None:
        return {"items": [], "total": 0, "pending_count": task_queue.pending_count}

    collection = db_client.get_collection("tasks")
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    skip = (page - 1) * page_size

    filter_query = {"status": status_filter}
    total = await collection.count_documents(filter_query)
    cursor = (
        collection.find(filter_query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(length=page_size)

    # Serialize ObjectIds
    for item in items:
        item["_id"] = str(item["_id"])

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pending_count": task_queue.pending_count,
    }


@router.post(
    "/dlq/retry/{dlq_id}",
    summary="Retry DLQ item",
    description="Manually re-queue a dead-letter queue item for retry.",
    dependencies=[Depends(verify_admin_key)],
)
async def admin_retry_dlq(
    dlq_id: str,
    request: Request,
) -> dict[str, Any]:
    """Manually retry a DLQ item."""
    if not ObjectId.is_valid(dlq_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid dlq_id format.",
        )

    dlq = getattr(request.app.state, "dlq_manager", None)
    if dlq is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DLQ manager not available.",
        )

    item = await dlq.get_dlq_item(dlq_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DLQ item '{dlq_id}' not found.",
        )

    # Mark as retried
    await dlq.mark_retried(dlq_id)

    return {
        "status": "retried",
        "dlq_id": dlq_id,
        "alert_id": item.get("alert_id", ""),
        "channel": item.get("channel", ""),
    }
