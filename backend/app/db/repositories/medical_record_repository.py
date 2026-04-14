"""
Medical record data access repository.

Extends BaseRepository with patient-scoped listing and risk-level queries.
"""

from typing import Any

from app.db.client import AsyncMongoClient
from app.db.repositories import BaseRepository


class MedicalRecordRepository(BaseRepository):
    """Repository for medical record documents in the ``medical_records`` collection."""

    COLLECTION = "medical_records"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        super().__init__(db_client, self.COLLECTION)

    async def list_by_patient_id(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List medical records belonging to a specific patient.

        Args:
            patient_id: The patient's ObjectId string.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"patient_id": patient_id}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)

    async def find_by_risk_level(
        self,
        risk_level: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Find medical records by risk classification.

        Args:
            risk_level: One of low, medium, high, critical.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"risk_level": risk_level}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)
