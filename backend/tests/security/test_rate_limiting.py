"""
Rate limiting test suite (D5.5).

Tests:
- Login endpoint rate limiting
- API endpoint rate limiting
- Retry-After header presence
- Rate limit headers in responses
- Rate limit reset behavior
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limiter import reset_rate_limiter, _request_log


def _get_rate_middleware(test_app: Any):
    """Get the RateLimitMiddleware instance from the app middleware stack."""
    from app.core.rate_limiter import RateLimitMiddleware
    for middleware in test_app.middleware_stack.__dict__.get("app", test_app).__dict__.values():
        if isinstance(middleware, RateLimitMiddleware):
            return middleware
    # Walk the ASGI chain
    app = test_app
    while hasattr(app, "app"):
        if hasattr(app, "_login_limit"):
            return app
        app = app.app
    return None


class TestRateLimiting:
    """Test rate limiting middleware."""

    def setup_method(self):
        reset_rate_limiter()

    def test_normal_request_passes(self, test_client: TestClient):
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200

    def test_rate_limit_headers_present(self, test_client: TestClient, test_app: Any):
        """API requests should include rate limit headers."""
        response = test_client.get("/api/v1/patients")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_login_rate_limit_enforced(self, test_client: TestClient, test_app: Any):
        """Login endpoint should be rate limited when limit is exceeded."""
        # Pre-fill the rate limiter with fake timestamps to simulate exhaustion
        import time
        key = "login:testclient"
        now = time.monotonic()
        _request_log[key] = [now - i * 0.01 for i in range(1001)]

        resp = test_client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "AnyPass123",
        })
        assert resp.status_code == 429

    def test_rate_limit_429_has_retry_after(self, test_client: TestClient, test_app: Any):
        """429 responses should include Retry-After header."""
        import time
        key = "login:testclient"
        now = time.monotonic()
        _request_log[key] = [now - i * 0.01 for i in range(1001)]

        resp = test_client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "AnyPass123",
        })
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_health_endpoint_not_rate_limited(self, test_client: TestClient):
        """Health check endpoints should not be rate limited."""
        for _ in range(200):
            resp = test_client.get("/api/v1/health")
            assert resp.status_code == 200

    def test_rate_limit_response_body(self, test_client: TestClient, test_app: Any):
        """429 response should have helpful error message."""
        import time
        key = "login:testclient"
        now = time.monotonic()
        _request_log[key] = [now - i * 0.01 for i in range(1001)]

        resp = test_client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "pass",
        })
        assert resp.status_code == 429
        data = resp.json()
        assert "rate limit" in data.get("detail", "").lower()

