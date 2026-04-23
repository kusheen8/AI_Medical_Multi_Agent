"""
Security headers middleware for HTTPS/TLS hardening.

Adds security headers to all API responses:
- Strict-Transport-Security (HSTS) — production only
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy
- Cache-Control: no-store (for API responses with sensitive data)
- X-XSS-Protection: 0 (modern browsers use CSP instead)
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses.

    In production mode, also adds HSTS header to enforce HTTPS.

    Args:
        app_env: Application environment ('development', 'staging', 'production').
    """

    def __init__(self, app: any, app_env: str = "development") -> None:  # type: ignore[valid-type]
        super().__init__(app)
        self._app_env = app_env

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # HSTS — only in production/staging (requires HTTPS)
        if self._app_env in ("production", "staging"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Content Security Policy (API-appropriate)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )

        # Disable caching for API responses (may contain sensitive data)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        # X-XSS-Protection — set to 0 per modern best practice
        # (CSP is the proper defense; this header can introduce vulnerabilities)
        response.headers["X-XSS-Protection"] = "0"

        # Referrer Policy — don't leak URLs
        response.headers["Referrer-Policy"] = "no-referrer"

        # Permissions Policy — restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        return response
