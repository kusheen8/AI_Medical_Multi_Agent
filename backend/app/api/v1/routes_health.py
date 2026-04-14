"""
Health check API endpoints.

Provides:
- GET /api/v1/health          — Simple liveness probe
- GET /api/v1/health/dependencies — Detailed dependency status
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get(
    "",
    summary="Liveness probe",
    description="Returns 200 OK if the service is running.",
    response_description="Service status",
)
async def health_check() -> dict[str, str]:
    """Simple liveness check — confirms the FastAPI process is up."""
    return {"status": "ok"}


@router.get(
    "/dependencies",
    summary="Dependency health check",
    description="Returns detailed connectivity status for MongoDB, Ollama, and Gemini API.",
    response_description="Per-dependency health status with latency",
)
async def health_dependencies(request: Request) -> JSONResponse:
    """Detailed health check for all external dependencies.

    Returns:
        200 if all dependencies are healthy.
        503 if any dependency is unhealthy or degraded.
    """
    health_service = request.app.state.health_service
    result = await health_service.check_all()

    status_code = 200 if result.status == "ok" else 503
    return JSONResponse(content=result.to_dict(), status_code=status_code)
