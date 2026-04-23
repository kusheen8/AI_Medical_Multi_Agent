"""
In-memory sliding window rate limiter middleware.

Provides per-IP rate limiting with configurable limits per endpoint category.
Uses a sliding window algorithm with in-memory storage (suitable for
single-instance deployments; use Redis for multi-instance).

Rate limit categories:
- Login endpoints (``/api/v1/auth/login``): stricter limit
- General API endpoints: higher limit for authenticated users
"""

import time
from collections import defaultdict
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger(__name__)

# Sliding window storage: {key: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)


def _cleanup_expired(key: str, window_seconds: float = 60.0) -> None:
    """Remove timestamps outside the sliding window."""
    cutoff = time.monotonic() - window_seconds
    _request_log[key] = [t for t in _request_log[key] if t > cutoff]


def reset_rate_limiter() -> None:
    """Reset all rate limit state (for testing)."""
    _request_log.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter middleware.

    Configuration:
        login_limit: Max requests per minute for login endpoint.
        api_limit: Max requests per minute for general API endpoints.

    Rate limit info is returned in response headers:
        X-RateLimit-Limit: Maximum requests allowed
        X-RateLimit-Remaining: Remaining requests in window
        X-RateLimit-Reset: Seconds until window resets
    """

    def __init__(
        self,
        app: Any,
        login_limit: int = 100,
        api_limit: int = 1000,
    ) -> None:
        super().__init__(app)
        self._login_limit = login_limit
        self._api_limit = api_limit
        self._window_seconds = 60.0

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip rate limiting for health checks and metrics
        if path in ("/api/v1/health", "/api/v1/health/dependencies", "/api/v1/metrics"):
            return await call_next(request)

        # Determine limit and key
        client_ip = request.client.host if request.client else "unknown"

        if path == "/api/v1/auth/login":
            limit = self._login_limit
            key = f"login:{client_ip}"
        elif path.startswith("/api/"):
            limit = self._api_limit
            # Use user ID from auth header if available, else IP
            key = f"api:{client_ip}"
        else:
            return await call_next(request)

        # Check rate limit
        now = time.monotonic()
        _cleanup_expired(key, self._window_seconds)

        current_count = len(_request_log[key])

        if current_count >= limit:
            retry_after = int(self._window_seconds - (now - _request_log[key][0]))
            retry_after = max(retry_after, 1)

            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=path,
                limit=limit,
                current_count=current_count,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        # Record request
        _request_log[key].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, limit - len(_request_log[key]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
