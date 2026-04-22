"""
Idempotency middleware for preventing duplicate write operations.

Intercepts POST/PUT requests with an ``Idempotency-Key`` header and
returns cached responses for previously executed requests.

Usage:
    Include ``idempotency_dependency`` in POST/PUT endpoints:

        @router.post("/alerts")
        async def create_alert(
            ...,
            idem_repo: IdempotencyRepository = Depends(get_idempotency_repo),
        ):
            cached = await check_idempotency(request, idem_repo)
            if cached:
                return cached
            ...  # process normally
            await store_idempotency(request, idem_repo, response_data, status_code)
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.db.repositories.idempotency_repository import IdempotencyRepository

logger = structlog.get_logger(__name__)


def validate_idempotency_key(key: str | None) -> str | None:
    """Validate that an idempotency key is a valid UUID format.

    Args:
        key: The raw header value.

    Returns:
        The validated key string, or None if invalid/absent.
    """
    if key is None:
        return None
    try:
        uuid.UUID(key)
        return key
    except ValueError:
        return None


async def check_idempotency(
    idempotency_key: str,
    repo: IdempotencyRepository,
) -> dict[str, Any] | None:
    """Check if a request with this idempotency key has already been processed.

    Args:
        idempotency_key: The validated idempotency key.
        repo: The idempotency store repository.

    Returns:
        The cached response dict if found, or None.
    """
    cached = await repo.get_by_key(idempotency_key)
    if cached is not None:
        await logger.ainfo(
            "idempotency_cache_hit",
            key=idempotency_key,
            method=cached.get("method", ""),
            path=cached.get("path", ""),
        )
        return cached.get("response_body")
    return None


async def store_idempotency(
    idempotency_key: str,
    repo: IdempotencyRepository,
    method: str,
    path: str,
    response_body: dict[str, Any],
    status_code: int,
) -> None:
    """Store a request/response pair for idempotency replay.

    Args:
        idempotency_key: The validated idempotency key.
        repo: The idempotency store repository.
        method: HTTP method (POST, PUT).
        path: Request path.
        response_body: The response body to cache.
        status_code: The HTTP status code.
    """
    await repo.store(
        key=idempotency_key,
        method=method,
        path=path,
        response_body=response_body,
        status_code=status_code,
    )
    await logger.ainfo(
        "idempotency_stored",
        key=idempotency_key,
        method=method,
        path=path,
        status_code=status_code,
    )
