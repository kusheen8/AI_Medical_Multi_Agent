"""
Authentication API endpoints.

Provides:
- POST /api/v1/auth/register — User registration
- POST /api/v1/auth/login    — Email/password login → token pair
- POST /api/v1/auth/refresh  — Refresh token → new access token
- POST /api/v1/auth/logout   — Revoke current token
- GET  /api/v1/auth/me       — Current user info
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError

from app.api.v1.auth_dependencies import get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    revoke_token,
    verify_password,
)
from app.db.repositories.user_repository import UserRepository
from app.models.user import (
    LoginRequest,
    TokenPair,
    TokenPayload,
    UserCreate,
    UserResponse,
    UserRole,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Dependency helpers ───────────────────────────────────────────────────


def _get_user_repo(request: Request) -> UserRepository:
    """Build a UserRepository from the shared DB client."""
    return UserRepository(request.app.state.db_client)


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Non-patient roles require admin privileges.",
)
async def register_user(
    body: UserCreate,
    request: Request,
    user_repo: UserRepository = Depends(_get_user_repo),
    current_user: TokenPayload = Depends(get_current_user),
) -> UserResponse:
    """Register a new user.

    Non-patient roles (caregiver, doctor, admin) can only be created
    by an admin user.
    """
    # Non-patient roles require admin
    if body.role != UserRole.PATIENT and current_user.sub != "anonymous":
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create non-patient user accounts.",
            )

    # Check for existing user
    existing = await user_repo.find_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # Create user document
    user_doc = {
        "email": body.email.lower(),
        "hashed_password": hash_password(body.password),
        "full_name": body.full_name,
        "role": body.role.value,
        "patient_id": body.patient_id,
        "assigned_patient_ids": body.assigned_patient_ids,
        "is_active": True,
    }

    created = await user_repo.create_user(user_doc)
    await logger.ainfo("user_registered", user_id=str(created["_id"]), role=body.role.value)

    return UserResponse.from_mongo(created)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login with email and password",
    description="Authenticate with email/password credentials. Returns JWT token pair.",
)
async def login(
    body: LoginRequest,
    user_repo: UserRepository = Depends(_get_user_repo),
) -> TokenPair:
    """Authenticate user and return access + refresh tokens."""
    settings = get_settings()

    # Find user by email
    user = await user_repo.find_by_email(body.email)
    if user is None:
        await logger.awarning("login_failed", reason="user_not_found", email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Verify password
    if not verify_password(body.password, user["hashed_password"]):
        await logger.awarning("login_failed", reason="invalid_password", email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Check active status
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    user_id = str(user["_id"])
    role = UserRole(user["role"])

    access_token = create_access_token(user_id=user_id, role=role)
    refresh_token = create_refresh_token(user_id=user_id)

    await logger.ainfo("login_successful", user_id=user_id, role=role.value)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token pair.",
)
async def refresh_token(
    request: Request,
    user_repo: UserRepository = Depends(_get_user_repo),
) -> TokenPair:
    """Exchange a refresh token for new access + refresh tokens."""
    settings = get_settings()

    # Extract refresh token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )

    token_str = auth_header.removeprefix("Bearer ").strip()

    try:
        payload = decode_token(token_str)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    if payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Refresh token required.",
        )

    # Look up user
    user = await user_repo.get_by_id(payload.sub)
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    user_id = str(user["_id"])
    role = UserRole(user["role"])

    # Revoke old refresh token
    db_client = request.app.state.db_client
    await revoke_token(payload.jti, payload.exp, db_client)

    # Issue new pair
    new_access = create_access_token(user_id=user_id, role=role)
    new_refresh = create_refresh_token(user_id=user_id)

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout / revoke token",
    description="Revoke the current access token.",
)
async def logout(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
) -> None:
    """Revoke the current access token by adding its JTI to the blacklist."""
    if current_user.sub == "anonymous":
        return

    db_client = request.app.state.db_client
    await revoke_token(current_user.jti, current_user.exp, db_client)
    await logger.ainfo("user_logged_out", user_id=current_user.sub)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user info",
    description="Return the profile of the currently authenticated user.",
)
async def get_me(
    current_user: TokenPayload = Depends(get_current_user),
    user_repo: UserRepository = Depends(_get_user_repo),
) -> UserResponse:
    """Return the current user's profile."""
    if current_user.sub == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user = await user_repo.get_by_id(current_user.sub)
    return UserResponse.from_mongo(user)
