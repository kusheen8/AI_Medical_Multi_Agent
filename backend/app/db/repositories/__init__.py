"""
Base repository providing generic async CRUD operations.

All entity-specific repositories inherit from ``BaseRepository`` and gain
pagination-aware listing, ObjectId conversion, and consistent error handling
for free.  Entity-specific queries are added in subclasses.

Usage::

    class PatientRepository(BaseRepository):
        def __init__(self, db_client):
            super().__init__(db_client, "patients")
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.db.client import AsyncMongoClient
from app.db.exceptions import DuplicateError, NotFoundError, RepositoryError

logger = structlog.get_logger(__name__)


class BaseRepository:
    """Generic async repository with CRUD, pagination, and error handling.

    Attributes:
        _db_client: Shared async MongoDB client.
        _collection_name: MongoDB collection this repository operates on.
    """

    def __init__(self, db_client: AsyncMongoClient, collection_name: str) -> None:
        self._db_client = db_client
        self._collection_name = collection_name

    @property
    def _collection(self) -> Any:
        """Return the Motor collection handle."""
        return self._db_client.get_collection(self._collection_name)

    # ── Create ──────────────────────────────────────────────────────────

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        """Insert a new document.

        Automatically sets ``created_at`` and ``updated_at`` timestamps.

        Args:
            document: Dict representation of the model (no ``_id``).

        Returns:
            The inserted document with ``_id`` populated.

        Raises:
            DuplicateError: If a unique-index violation occurs.
            RepositoryError: On unexpected insertion failures.
        """
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)

        try:
            result = await self._collection.insert_one(document)
            document["_id"] = result.inserted_id
            await logger.ainfo(
                "repo_created",
                collection=self._collection_name,
                id=str(result.inserted_id),
            )
            return document
        except DuplicateKeyError as exc:
            raise DuplicateError(f"Duplicate key in {self._collection_name}: {exc}") from exc
        except Exception as exc:
            raise RepositoryError(f"Insert failed in {self._collection_name}: {exc}") from exc

    # ── Read ────────────────────────────────────────────────────────────

    async def get_by_id(self, doc_id: str) -> dict[str, Any]:
        """Retrieve a single document by its ``_id``.

        Args:
            doc_id: String representation of the MongoDB ObjectId.

        Returns:
            The raw MongoDB document dict.

        Raises:
            NotFoundError: If no document with the given ID exists.
        """
        if not ObjectId.is_valid(doc_id):
            raise NotFoundError(self._collection_name, doc_id)

        doc = await self._collection.find_one({"_id": ObjectId(doc_id)})
        if doc is None:
            raise NotFoundError(self._collection_name, doc_id)
        return doc

    # ── List (paginated) ────────────────────────────────────────────────

    async def list(
        self,
        filter_query: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_field: str = "created_at",
        sort_order: int = -1,
    ) -> dict[str, Any]:
        """List documents with pagination and optional filtering.

        Args:
            filter_query: MongoDB filter dict (default: all documents).
            page: 1-indexed page number.
            page_size: Number of documents per page (max 100).
            sort_field: Field to sort by.
            sort_order: 1 for ascending, -1 for descending.

        Returns:
            Dict with ``items``, ``total``, ``page``, ``page_size``, ``pages``.
        """
        filter_query = filter_query or {}
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        skip = (page - 1) * page_size

        total = await self._collection.count_documents(filter_query)
        cursor = (
            self._collection.find(filter_query)
            .sort(sort_field, sort_order)
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

    # ── Update ──────────────────────────────────────────────────────────

    async def update(self, doc_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        """Update a document by ID (partial update via ``$set``).

        Automatically refreshes ``updated_at``.

        Args:
            doc_id: String ObjectId of the document to update.
            update_data: Dict of fields to update (only non-None values).

        Returns:
            The updated document.

        Raises:
            NotFoundError: If the document does not exist.
        """
        if not ObjectId.is_valid(doc_id):
            raise NotFoundError(self._collection_name, doc_id)

        # Remove None values — only update provided fields
        update_fields = {k: v for k, v in update_data.items() if v is not None}
        if not update_fields:
            return await self.get_by_id(doc_id)

        update_fields["updated_at"] = datetime.now(timezone.utc)

        result = await self._collection.find_one_and_update(
            {"_id": ObjectId(doc_id)},
            {"$set": update_fields},
            return_document=True,  # Return the updated document
        )

        if result is None:
            raise NotFoundError(self._collection_name, doc_id)

        await logger.ainfo(
            "repo_updated",
            collection=self._collection_name,
            id=doc_id,
            fields=list(update_fields.keys()),
        )
        return result

    # ── Delete ──────────────────────────────────────────────────────────

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID.

        Args:
            doc_id: String ObjectId of the document to delete.

        Returns:
            True if the document was deleted.

        Raises:
            NotFoundError: If the document does not exist.
        """
        if not ObjectId.is_valid(doc_id):
            raise NotFoundError(self._collection_name, doc_id)

        result = await self._collection.delete_one({"_id": ObjectId(doc_id)})
        if result.deleted_count == 0:
            raise NotFoundError(self._collection_name, doc_id)

        await logger.ainfo(
            "repo_deleted",
            collection=self._collection_name,
            id=doc_id,
        )
        return True
