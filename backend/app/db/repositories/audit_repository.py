"""
Audit log data access repository.

Unlike other repositories, the audit repository is **write-only + query**.
No update or delete operations are exposed to enforce immutability of audit
records for compliance purposes.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from bson import ObjectId

from app.db.client import AsyncMongoClient
from app.models.audit_log import AuditAction

logger = structlog.get_logger(__name__)


class AuditRepository:
    """Repository for immutable audit log entries in the ``audit_logs`` collection.

    This repository intentionally does NOT inherit from BaseRepository because
    audit logs must never be updated or deleted through the application layer.
    """

    COLLECTION = "audit_logs"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        self._db_client = db_client

    @property
    def _collection(self) -> Any:
        """Return the Motor collection handle."""
        return self._db_client.get_collection(self.COLLECTION)

    async def log_access(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str | None,
        request_id: str,
        ip_address: str = "unknown",
    ) -> None:
        """Write an immutable audit log entry.

        Args:
            user_id: Who performed the action.
            action: Type of action (read/write/delete).
            resource_type: Type of resource accessed.
            resource_id: Specific document ID (if applicable).
            request_id: Request correlation ID.
            ip_address: Client IP address.
        """
        entry = {
            "user_id": user_id,
            "action": action.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "request_id": request_id,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc),
        }

        await self._collection.insert_one(entry)
        await logger.ainfo(
            "audit_logged",
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    async def query_by_patient_id(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Query audit logs for a specific patient.

        Searches for audit entries where the resource_id matches the patient_id
        or the resource_type is 'patients' and resource_id matches.

        Args:
            patient_id: Patient ObjectId string.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict with ``items``, ``total``, ``page``, ``page_size``, ``pages``.
        """
        filter_query = {"resource_id": patient_id}
        return await self._paginated_query(filter_query, page, page_size)

    async def query_by_user_id(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Query audit logs by the user who performed the action.

        Args:
            user_id: The user identifier.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"user_id": user_id}
        return await self._paginated_query(filter_query, page, page_size)

    async def _paginated_query(
        self,
        filter_query: dict[str, Any],
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Execute a paginated query on the audit logs collection.

        Args:
            filter_query: MongoDB filter dict.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Dict with items, total, page, page_size, pages.
        """
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        skip = (page - 1) * page_size

        total = await self._collection.count_documents(filter_query)
        cursor = (
            self._collection.find(filter_query)
            .sort("timestamp", -1)
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
