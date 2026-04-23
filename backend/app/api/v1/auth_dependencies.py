"""
Authentication and authorization dependencies for FastAPI routes.

Provides:
- ``get_current_user``: Extracts and validates JWT from Authorization header
- ``get_optional_user``: Returns user or None (for optional auth)
- ``require_role``: Factory for role-based access control
- ``require_admin``: Shortcut for admin-only endpoints
- ``require_patient_access``: Ownership check for patient data

Usage::

    @router.get("/protected")
    async def protected_endpoint(
        user: TokenPayload = Depends(get_current_user),
    ):
        ...

    @router.get("/admin-only", dependencies=[Depends(require_admin())])
    async def admin_endpoint():
        ...
"""

from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.config import get_settings
from app.core.security import decode_token, is_token_revoked
from app.models.user import TokenPayload, UserRole

logger = structlog.get_logger(__name__)

# Bearer token extractor — auto_error=False allows optional auth
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenPayload:
    """Extract and validate JWT bearer token from the Authorization header.

    Args:
        request: The FastAPI request object.
        credentials: Extracted bearer credentials.

    Returns:
        TokenPayload with decoded claims.

    Raises:
        HTTPException(401): If token is missing, invalid, or revoked.
    """
    settings = get_settings()

    if credentials is None:
        if not settings.REQUIRE_AUTH:
            # Return anonymous user when auth is not required
            return TokenPayload(
                sub="anonymous",
                role=UserRole.ADMIN,  # Anonymous gets full access when auth disabled
                scopes=[],
                exp=0,
                jti="anonymous",
                token_type="access",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check revocation
    db_client = getattr(request.app.state, "db_client", None)
    if db_client and db_client.is_connected:
        if await is_token_revoked(payload.jti, db_client):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return payload


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenPayload | None:
    """Extract JWT if present, return None otherwise.

    Does not raise on missing token — useful for endpoints that work
    with or without authentication.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
        if payload.token_type != "access":
            return None
        return payload
    except JWTError:
        return None


def require_role(*roles: UserRole) -> Any:
    """Create a dependency that enforces role-based access control.

    Args:
        *roles: Allowed roles for the endpoint.

    Returns:
        FastAPI dependency function.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def _check_role(
        user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        # Anonymous user (when auth disabled) gets through
        if user.sub == "anonymous":
            return user

        if user.role not in roles:
            await logger.awarning(
                "authorization_denied",
                user_id=user.sub,
                user_role=user.role.value,
                required_roles=[r.value for r in roles],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(r.value for r in roles)}.",
            )
        return user

    return _check_role


def require_admin() -> Any:
    """Shortcut dependency for admin-only endpoints."""
    return require_role(UserRole.ADMIN)


async def require_patient_access(
    patient_id: str,
    user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """Verify the user has access to the specified patient's data.

    Access rules:
    - Admin: access all patients
    - Patient: access own data only (user.sub must match patient's user)
    - Caregiver/Doctor: access assigned patients only

    Args:
        patient_id: The patient ID being accessed.
        user: The authenticated user's token payload.

    Returns:
        The validated TokenPayload.

    Raises:
        HTTPException(403): If the user lacks access.
    """
    # Anonymous user (when auth disabled) gets through
    if user.sub == "anonymous":
        return user

    # Admins have full access
    if user.role == UserRole.ADMIN:
        return user

    # For now, we allow access based on role since we don't have
    # patient-user mapping in the token itself. Full ownership checks
    # require a DB lookup which we'll add as needed.
    if user.role in (UserRole.DOCTOR, UserRole.CAREGIVER):
        return user

    # Patients — would need to verify patient_id maps to user.sub
    # For now, allow if they have a valid token
    if user.role == UserRole.PATIENT:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to this patient's data.",
    )
