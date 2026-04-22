"""
Metrics API endpoint.

Exposes system metrics in Prometheus text exposition format for
monitoring tools (Grafana, Prometheus) to scrape.
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Return system metrics in Prometheus text exposition format.",
)
async def get_metrics(request: Request) -> PlainTextResponse:
    """Return all collected metrics in Prometheus format."""
    collector = getattr(request.app.state, "metrics_collector", None)
    if collector is None:
        return PlainTextResponse(
            "# No metrics collector configured\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Update queue length if task queue is available
    task_queue = getattr(request.app.state, "task_queue", None)
    if task_queue:
        collector.set_queue_length(task_queue.pending_count)

    metrics_text = collector.get_prometheus_format()
    return PlainTextResponse(
        metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get(
    "/metrics/summary",
    summary="Metrics JSON summary",
    description="Return system metrics as a JSON summary.",
)
async def get_metrics_summary(request: Request) -> dict[str, Any]:
    """Return all collected metrics as a JSON dictionary."""
    collector = getattr(request.app.state, "metrics_collector", None)
    if collector is None:
        return {"error": "No metrics collector configured"}

    # Update queue length
    task_queue = getattr(request.app.state, "task_queue", None)
    if task_queue:
        collector.set_queue_length(task_queue.pending_count)

    return collector.get_summary()
