"""
Request middleware for cross-cutting concerns.

Provides:
- RequestCorrelationMiddleware: Injects a unique request ID into every request,
  binds it to structlog context, and returns it as X-Request-ID response header.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


logger = structlog.get_logger(__name__)


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a correlation ID to each request.

    - Reads X-Request-ID from incoming headers (allows propagation from upstream).
    - If absent, generates a new UUID4.
    - Binds request_id to structlog context for all downstream log messages.
    - Adds X-Request-ID to the response headers.
    - Logs request start and completion with duration.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Use incoming request ID if provided, otherwise generate one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request_id to structlog context vars (available in all log calls)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        )

        start_time = time.perf_counter()

        await logger.ainfo(
            "request_started",
            client_host=request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await logger.aerror(
                "request_failed",
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        await logger.ainfo(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Attach correlation ID to response
        response.headers["X-Request-ID"] = request_id
        return response
