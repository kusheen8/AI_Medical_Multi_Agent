"""
Alert data access repository.

Extends BaseRepository with patient-scoped listing and status queries.
"""

from typing import Any

from app.db.client import AsyncMongoClient
from app.db.repositories import BaseRepository


class AlertRepository(BaseRepository):
    """Repository for alert documents in the ``alerts`` collection."""

    COLLECTION = "alerts"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        super().__init__(db_client, self.COLLECTION)

    async def list_by_patient_id(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List alerts for a specific patient.

        Args:
            patient_id: The patient's ObjectId string.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"patient_id": patient_id}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)

    async def find_by_status(
        self,
        status: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Find alerts by delivery status.

        Args:
            status: One of pending, sent, delivered, failed.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"status": status}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)
