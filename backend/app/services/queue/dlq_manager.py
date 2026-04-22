"""
Dead-letter queue manager for failed notifications.

Stores notifications that have exhausted all retry attempts in a
separate MongoDB collection for admin inspection and manual re-queuing.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from bson import ObjectId

from app.db.client import AsyncMongoClient

logger = structlog.get_logger(__name__)


class DLQManager:
    """Manages the notification dead-letter queue.

    Failed notification attempts are stored here after exhausting
    retries, allowing admins to inspect, diagnose, and manually
    re-queue them.

    Attributes:
        _db_client: Shared async MongoDB client.
    """

    COLLECTION = "notification_dlq"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        self._db_client = db_client

    @property
    def _collection(self) -> Any:
        """Return the MongoDB collection handle."""
        return self._db_client.get_collection(self.COLLECTION)

    async def add_to_dlq(
        self,
        notification_id: str,
        error: str,
        attempts: int,
        alert_id: str = "",
        channel: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a failed notification to the dead-letter queue.

        Args:
            notification_id: Original notification/task ID.
            error: Last error message.
            attempts: Total attempts made.
            alert_id: Associated alert ID.
            channel: Notification channel that failed.
            metadata: Additional context data.

        Returns:
            The DLQ entry ID.
        """
        now = datetime.now(timezone.utc)
        document = {
            "notification_id": notification_id,
            "alert_id": alert_id,
            "channel": channel,
            "error": error,
            "attempts": attempts,
            "metadata": metadata or {},
            "status": "pending",  # pending | retried | discarded
            "created_at": now,
            "updated_at": now,
        }

        result = await self._collection.insert_one(document)
        dlq_id = str(result.inserted_id)

        await logger.awarning(
            "dlq_item_added",
            dlq_id=dlq_id,
            notification_id=notification_id,
            alert_id=alert_id,
            channel=channel,
            attempts=attempts,
            error=error,
        )

        return dlq_id

    async def list_dlq(
        self,
        status: str = "pending",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List dead-letter queue entries with pagination.

        Args:
            status: Filter by status (pending/retried/discarded).
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Paginated result dict with items, total, page, page_size, pages.
        """
        filter_query = {"status": status}
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        skip = (page - 1) * page_size

        total = await self._collection.count_documents(filter_query)
        cursor = (
            self._collection.find(filter_query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items = await cursor.to_list(length=page_size)

        pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    async def get_dlq_item(self, dlq_id: str) -> dict[str, Any] | None:
        """Retrieve a single DLQ entry by ID.

        Args:
            dlq_id: The DLQ entry ObjectId string.

        Returns:
            The DLQ document, or None if not found.
        """
        if not ObjectId.is_valid(dlq_id):
            return None
        return await self._collection.find_one({"_id": ObjectId(dlq_id)})

    async def mark_retried(self, dlq_id: str) -> bool:
        """Mark a DLQ entry as retried.

        Args:
            dlq_id: The DLQ entry ObjectId string.

        Returns:
            True if the entry was found and updated.
        """
        if not ObjectId.is_valid(dlq_id):
            return False

        now = datetime.now(timezone.utc)
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(dlq_id)},
            {"$set": {"status": "retried", "updated_at": now}},
        )

        if result is not None:
            await logger.ainfo("dlq_item_retried", dlq_id=dlq_id)
            return True
        return False

    async def mark_discarded(self, dlq_id: str) -> bool:
        """Mark a DLQ entry as discarded (won't be retried).

        Args:
            dlq_id: The DLQ entry ObjectId string.

        Returns:
            True if the entry was found and updated.
        """
        if not ObjectId.is_valid(dlq_id):
            return False

        now = datetime.now(timezone.utc)
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(dlq_id)},
            {"$set": {"status": "discarded", "updated_at": now}},
        )

        if result is not None:
            await logger.ainfo("dlq_item_discarded", dlq_id=dlq_id)
            return True
        return False

    async def get_count(self, status: str = "pending") -> int:
        """Get the count of DLQ entries by status.

        Args:
            status: Status filter.

        Returns:
            Number of matching entries.
        """
        return await self._collection.count_documents({"status": status})
