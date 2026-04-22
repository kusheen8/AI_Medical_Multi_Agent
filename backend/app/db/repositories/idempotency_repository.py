"""
Idempotency store repository.

Manages cached request/response pairs in the ``idempotency_store``
MongoDB collection with automatic 24h TTL expiry.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

from app.db.client import AsyncMongoClient

logger = structlog.get_logger(__name__)


class IdempotencyRepository:
    """Repository for idempotency key storage.

    Attributes:
        _db_client: Shared async MongoDB client.
    """

    COLLECTION = "idempotency_store"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        self._db_client = db_client

    @property
    def _collection(self) -> Any:
        """Return the MongoDB collection handle."""
        return self._db_client.get_collection(self.COLLECTION)

    async def get_by_key(self, key: str) -> dict[str, Any] | None:
        """Look up a cached response by idempotency key.

        Args:
            key: The idempotency key (UUID string).

        Returns:
            The cached document if found and not expired, or None.
        """
        doc = await self._collection.find_one({"key": key})
        if doc is None:
            return None

        # Check if expired (TTL index handles cleanup, but double-check)
        expires_at = doc.get("expires_at")
        if expires_at and expires_at < datetime.now(timezone.utc):
            return None

        return doc

    async def store(
        self,
        key: str,
        method: str,
        path: str,
        response_body: dict[str, Any],
        status_code: int,
    ) -> dict[str, Any]:
        """Store a request/response pair for idempotency replay.

        Args:
            key: The idempotency key (UUID string).
            method: HTTP method (POST, PUT).
            path: Request path.
            response_body: The response body to cache.
            status_code: The HTTP status code.

        Returns:
            The inserted document.
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        document = {
            "key": key,
            "method": method,
            "path": path,
            "response_body": response_body,
            "status_code": status_code,
            "created_at": now,
            "expires_at": now + timedelta(hours=24),
        }

        await self._collection.insert_one(document)

        await logger.ainfo(
            "idempotency_stored",
            key=key,
            method=method,
            path=path,
        )

        return document

    async def cleanup_expired(self) -> int:
        """Manually delete expired entries.

        Note: MongoDB TTL index handles automatic cleanup, but this
        method allows on-demand purging.

        Returns:
            Number of expired entries deleted.
        """
        now = datetime.now(timezone.utc)
        result = await self._collection.delete_many({"expires_at": {"$lt": now}})
        count = result.deleted_count

        if count > 0:
            await logger.ainfo("idempotency_cleanup", deleted=count)

        return count
