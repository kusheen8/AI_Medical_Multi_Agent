"""
Alert data access repository.

Extends BaseRepository with patient-scoped listing, status queries,
idempotency key lookup, acknowledgement, and delivery receipt management.
"""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.client import AsyncMongoClient
from app.db.exceptions import NotFoundError
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

    async def find_by_idempotency_key(
        self, idempotency_key: str
    ) -> dict[str, Any] | None:
        """Find an alert by its idempotency key.

        Args:
            idempotency_key: The UUID idempotency key.

        Returns:
            The alert document if found, or None.
        """
        return await self._collection.find_one({"idempotency_key": idempotency_key})

    async def acknowledge(
        self, alert_id: str, acknowledged_by: str
    ) -> dict[str, Any]:
        """Acknowledge an alert, stopping retry notifications.

        Args:
            alert_id: The alert ObjectId string.
            acknowledged_by: ID/name of the caregiver acknowledging.

        Returns:
            The updated alert document.

        Raises:
            NotFoundError: If the alert does not exist.
        """
        if not ObjectId.is_valid(alert_id):
            raise NotFoundError(self.COLLECTION, alert_id)

        now = datetime.now(timezone.utc)
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(alert_id)},
            {
                "$set": {
                    "status": "delivered",
                    "acknowledged_at": now,
                    "acknowledged_by": acknowledged_by,
                    "updated_at": now,
                }
            },
            return_document=True,
        )

        if result is None:
            raise NotFoundError(self.COLLECTION, alert_id)

        return result

    async def add_delivery_receipt(
        self, alert_id: str, receipt_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Append a delivery receipt to an alert's receipt array.

        Args:
            alert_id: The alert ObjectId string.
            receipt_data: The receipt document to append.

        Returns:
            The updated alert document.

        Raises:
            NotFoundError: If the alert does not exist.
        """
        if not ObjectId.is_valid(alert_id):
            raise NotFoundError(self.COLLECTION, alert_id)

        now = datetime.now(timezone.utc)
        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(alert_id)},
            {
                "$push": {"delivery_receipts": receipt_data},
                "$set": {"updated_at": now},
            },
            return_document=True,
        )

        if result is None:
            raise NotFoundError(self.COLLECTION, alert_id)

        return result

    async def find_failed(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """Find alerts that have failed or have undelivered channels.

        Returns alerts with overall status 'failed' or alerts
        with any delivery_receipt in 'failed' status.

        Args:
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {
            "$or": [
                {"status": "failed"},
                {"delivery_receipts.status": "failed"},
            ]
        }
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)
