"""
JWT authentication and password hashing utilities.

Provides:
- ``create_access_token`` / ``create_refresh_token``: Generate JWTs
- ``decode_token``: Validate and decode JWTs
- ``hash_password`` / ``verify_password``: bcrypt password operations
- ``revoke_token`` / ``is_token_revoked``: Token blacklist via MongoDB

Security notes:
- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 7 days (configurable)
- Token revocation stored in MongoDB with TTL index
- Password hashed with bcrypt (passlib)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.user import TokenPayload, UserRole

logger = structlog.get_logger(__name__)

# Password hashing context
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password.

    Returns:
        The bcrypt hash string.
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash.

    Args:
        plain_password: The plaintext password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches.
    """
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    role: UserRole,
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived JWT access token.

    Args:
        user_id: The user's MongoDB ObjectId string.
        role: The user's role.
        scopes: Permission scopes.
        expires_delta: Custom TTL (defaults to config value).

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role.value,
        "scopes": scopes or [],
        "exp": now + expires_delta,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived JWT refresh token.

    Args:
        user_id: The user's MongoDB ObjectId string.
        expires_delta: Custom TTL (defaults to config value).

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "exp": now + expires_delta,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: The encoded JWT string.

    Returns:
        TokenPayload with decoded claims.

    Raises:
        JWTError: If the token is invalid, expired, or malformed.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayload(
            sub=payload["sub"],
            role=UserRole(payload.get("role", "patient")),
            scopes=payload.get("scopes", []),
            exp=payload["exp"],
            jti=payload["jti"],
            token_type=payload.get("token_type", "access"),
        )
    except JWTError:
        raise


async def revoke_token(jti: str, exp: int, db_client: Any) -> None:
    """Add a token to the revocation blacklist.

    Stores the token's JTI in MongoDB with a TTL matching the token's
    expiration time, so entries auto-expire.

    Args:
        jti: The token's unique identifier.
        exp: The token's expiration timestamp (Unix epoch).
        db_client: AsyncMongoClient instance.
    """
    collection = db_client.get_collection("token_blacklist")
    await collection.insert_one({
        "jti": jti,
        "revoked_at": datetime.now(timezone.utc),
        "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc),
    })
    await logger.ainfo("token_revoked", jti=jti)


async def is_token_revoked(jti: str, db_client: Any) -> bool:
    """Check if a token has been revoked.

    Args:
        jti: The token's unique identifier.
        db_client: AsyncMongoClient instance.

    Returns:
        True if the token is in the blacklist.
    """
    collection = db_client.get_collection("token_blacklist")
    doc = await collection.find_one({"jti": jti})
    return doc is not None
