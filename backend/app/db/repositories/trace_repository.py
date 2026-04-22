"""
Reasoning trace data access repository.

Extends BaseRepository with trace-specific queries such as
task_id lookup, patient-scoped listing, and status filtering.

Traces are **immutable** once created — no update method is exposed.
This ensures audit-trail integrity for compliance.
"""

from datetime import datetime, timezone
from typing import Any

from app.db.client import AsyncMongoClient
from app.db.repositories import BaseRepository


class TraceRepository(BaseRepository):
    """Repository for reasoning trace documents in the ``reasoning_traces`` collection."""

    COLLECTION = "reasoning_traces"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        super().__init__(db_client, self.COLLECTION)

    async def create_trace(self, document: dict[str, Any]) -> dict[str, Any]:
        """Insert a new reasoning trace (immutable after creation).

        Args:
            document: Dict representation of the trace (no ``_id``).

        Returns:
            The inserted document with ``_id`` populated.
        """
        return await self.create(document)

    async def get_by_task_id(self, task_id: str) -> dict[str, Any] | None:
        """Find a trace by its associated task_id.

        Args:
            task_id: The task identifier linked to this trace.

        Returns:
            The trace document, or None if not found.
        """
        return await self._collection.find_one({"task_id": task_id})

    async def list_by_patient_id(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List traces associated with a specific patient.

        Args:
            patient_id: The patient's ObjectId string.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"patient_id": patient_id}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)

    async def list_by_status(
        self,
        status: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List traces by execution status.

        Args:
            status: Trace status to filter by.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"status": status}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)

    async def list_expired(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List traces that have passed their expiration time.

        Args:
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict of expired traces.
        """
        now = datetime.now(timezone.utc)
        filter_query = {
            "expires_at": {"$ne": None, "$lte": now},
        }
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)
