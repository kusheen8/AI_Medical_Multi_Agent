"""
Audit logging middleware for PHI access tracking.

Intercepts all requests to ``/api/v1/patients/**`` and ``/api/v1/records/**``
endpoints and writes immutable audit log entries to MongoDB.

Security:
- Request bodies are NEVER logged (PHI protection).
- Only request metadata (method, path, resource ID, request ID) is captured.
- user_id defaults to "anonymous" until Phase 5 auth is implemented.
"""

import re

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.db.repositories.audit_repository import AuditRepository
from app.models.audit_log import AuditAction

logger = structlog.get_logger(__name__)

# Paths that trigger audit logging
_AUDIT_PATTERNS = [
    re.compile(r"^/api/v1/patients"),
    re.compile(r"^/api/v1/records"),
]

# Map HTTP methods to audit actions
_METHOD_TO_ACTION = {
    "GET": AuditAction.READ,
    "POST": AuditAction.WRITE,
    "PUT": AuditAction.WRITE,
    "PATCH": AuditAction.WRITE,
    "DELETE": AuditAction.DELETE,
}

# Pattern to extract resource ID from paths like /api/v1/patients/{id}
_RESOURCE_ID_PATTERN = re.compile(
    r"^/api/v1/(patients|records)/([a-f0-9]{24})(?:/.*)?$"
)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs PHI access to the audit_logs collection.

    Writes audit entries for every request matching patient/record endpoints.
    Runs AFTER the request is processed (so we know the status code).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Only audit matching paths
        should_audit = any(pattern.match(path) for pattern in _AUDIT_PATTERNS)

        response = await call_next(request)

        if should_audit and response.status_code < 500:
            try:
                await self._write_audit_entry(request, path)
            except Exception:
                # Audit logging failures must never break the request
                await logger.awarning(
                    "audit_logging_failed",
                    path=path,
                    exc_info=True,
                )

        return response

    async def _write_audit_entry(self, request: Request, path: str) -> None:
        """Extract metadata and write an audit log entry."""
        # Determine action from HTTP method
        action = _METHOD_TO_ACTION.get(request.method, AuditAction.READ)

        # Extract resource type and ID from the path
        resource_type = "unknown"
        resource_id = None

        id_match = _RESOURCE_ID_PATTERN.match(path)
        if id_match:
            resource_type = id_match.group(1)
            resource_id = id_match.group(2)
        elif "/patients" in path:
            resource_type = "patients"
        elif "/records" in path:
            resource_type = "records"

        # Get request_id from context (set by RequestCorrelationMiddleware)
        request_id = request.headers.get("X-Request-ID", "unknown")

        # Get client IP
        ip_address = request.client.host if request.client else "unknown"

        # user_id placeholder — will be replaced by auth in Phase 5
        user_id = "anonymous"

        # Get audit repository from app state
        db_client = request.app.state.db_client
        if not db_client.is_connected:
            return

        audit_repo = AuditRepository(db_client)
        await audit_repo.log_access(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
        )
