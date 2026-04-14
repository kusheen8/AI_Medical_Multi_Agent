"""
Patient data access repository.

Extends BaseRepository with patient-specific queries such as
name search and condition-based filtering.
"""

from typing import Any

from app.db.client import AsyncMongoClient
from app.db.repositories import BaseRepository


class PatientRepository(BaseRepository):
    """Repository for patient documents in the ``patients`` collection."""

    COLLECTION = "patients"

    def __init__(self, db_client: AsyncMongoClient) -> None:
        super().__init__(db_client, self.COLLECTION)

    async def search_by_name(
        self,
        name: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Search patients by name (case-insensitive partial match).

        Args:
            name: Search string to match against patient names.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"name": {"$regex": name, "$options": "i"}}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)

    async def find_by_conditions(
        self,
        conditions: list[str],
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Find patients who have any of the given medical conditions.

        Args:
            conditions: List of condition names to match.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Paginated result dict.
        """
        filter_query = {"conditions": {"$in": conditions}}
        return await self.list(filter_query=filter_query, page=page, page_size=page_size)
