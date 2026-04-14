"""
Unit tests for repository CRUD operations.

Tests use mocked MongoDB collections to verify:
- Create / Read / Update / Delete operations
- Pagination logic
- Error handling (NotFoundError, DuplicateError)
- Patient-specific queries (search_by_name, find_by_conditions)
- Record-specific queries (list_by_patient_id, find_by_risk_level)
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.db.exceptions import DuplicateError, NotFoundError
from app.db.repositories.patient_repository import PatientRepository
from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.alert_repository import AlertRepository
from app.db.repositories.audit_repository import AuditRepository


# ═══════════════════════════════════════════════════════════════════════
# Base CRUD — via PatientRepository
# ═══════════════════════════════════════════════════════════════════════


class TestBaseRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_success(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        inserted_id = ObjectId()
        mock_collection.insert_one.return_value = MagicMock(inserted_id=inserted_id)

        doc = {"name": "John Doe", "dob": "1985-03-15"}
        result = await repo.create(doc)

        assert result["_id"] == inserted_id
        assert "created_at" in result
        assert "updated_at" in result
        mock_collection.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_raises(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.insert_one.side_effect = DuplicateKeyError("dup key")

        with pytest.raises(DuplicateError):
            await repo.create({"name": "Dup"})

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        doc: dict[str, Any] = {"name": "Test"}
        await repo.create(doc)

        assert isinstance(doc["created_at"], datetime)
        assert isinstance(doc["updated_at"], datetime)


class TestBaseRepositoryGetById:
    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        oid = ObjectId()
        mock_collection.find_one.return_value = {"_id": oid, "name": "Jane"}

        result = await repo.get_by_id(str(oid))
        assert result["name"] == "Jane"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.find_one.return_value = None

        with pytest.raises(NotFoundError):
            await repo.get_by_id(str(ObjectId()))

    @pytest.mark.asyncio
    async def test_get_by_id_invalid_id(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)

        with pytest.raises(NotFoundError):
            await repo.get_by_id("not-a-valid-id")


class TestBaseRepositoryList:
    @pytest.mark.asyncio
    async def test_list_empty(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.list()
        assert result["items"] == []
        assert result["total"] == 0
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_list_with_items(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.count_documents.return_value = 2

        items = [
            {"_id": ObjectId(), "name": "A"},
            {"_id": ObjectId(), "name": "B"},
        ]
        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = items

        result = await repo.list()
        assert result["total"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.count_documents.return_value = 50

        result = await repo.list(page=2, page_size=10)
        assert result["page"] == 2
        assert result["page_size"] == 10
        assert result["pages"] == 5

    @pytest.mark.asyncio
    async def test_list_page_size_capped(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.list(page_size=200)
        assert result["page_size"] == 100  # capped at max


class TestBaseRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_success(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        oid = ObjectId()
        updated_doc = {"_id": oid, "name": "Updated"}
        mock_collection.find_one_and_update.return_value = updated_doc

        result = await repo.update(str(oid), {"name": "Updated"})
        assert result["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.find_one_and_update.return_value = None

        with pytest.raises(NotFoundError):
            await repo.update(str(ObjectId()), {"name": "X"})

    @pytest.mark.asyncio
    async def test_update_empty_data_returns_existing(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        oid = ObjectId()
        existing = {"_id": oid, "name": "Existing"}
        mock_collection.find_one.return_value = existing

        # All values are None → no actual update needed
        result = await repo.update(str(oid), {"name": None})
        assert result["name"] == "Existing"


class TestBaseRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_success(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        result = await repo.delete(str(ObjectId()))
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

        with pytest.raises(NotFoundError):
            await repo.delete(str(ObjectId()))

    @pytest.mark.asyncio
    async def test_delete_invalid_id(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)

        with pytest.raises(NotFoundError):
            await repo.delete("bad-id")


# ═══════════════════════════════════════════════════════════════════════
# Patient-specific queries
# ═══════════════════════════════════════════════════════════════════════


class TestPatientRepository:
    @pytest.mark.asyncio
    async def test_search_by_name(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.count_documents.return_value = 1

        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = [{"_id": ObjectId(), "name": "John"}]

        result = await repo.search_by_name("John")
        assert result["total"] == 1
        # Verify regex filter was used
        call_args = mock_collection.find.call_args
        assert "$regex" in str(call_args)

    @pytest.mark.asyncio
    async def test_find_by_conditions(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = PatientRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.find_by_conditions(["diabetes"])
        assert result["total"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Medical Record repository
# ═══════════════════════════════════════════════════════════════════════


class TestMedicalRecordRepository:
    @pytest.mark.asyncio
    async def test_list_by_patient_id(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = MedicalRecordRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.list_by_patient_id(str(ObjectId()))
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_find_by_risk_level(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = MedicalRecordRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.find_by_risk_level("high")
        assert result["total"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Alert repository
# ═══════════════════════════════════════════════════════════════════════


class TestAlertRepository:
    @pytest.mark.asyncio
    async def test_list_by_patient_id(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = AlertRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.list_by_patient_id(str(ObjectId()))
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_find_by_status(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = AlertRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.find_by_status("pending")
        assert result["total"] == 0


# ═══════════════════════════════════════════════════════════════════════
# Audit repository
# ═══════════════════════════════════════════════════════════════════════


class TestAuditRepository:
    @pytest.mark.asyncio
    async def test_log_access(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = AuditRepository(mock_db_client)

        from app.models.audit_log import AuditAction

        await repo.log_access(
            user_id="anonymous",
            action=AuditAction.READ,
            resource_type="patients",
            resource_id=str(ObjectId()),
            request_id="req-123",
        )
        mock_collection.insert_one.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_by_patient_id(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = AuditRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.query_by_patient_id(str(ObjectId()))
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_query_by_user_id(
        self, mock_db_client: MagicMock, mock_collection: MagicMock
    ) -> None:
        repo = AuditRepository(mock_db_client)
        mock_collection.count_documents.return_value = 0

        result = await repo.query_by_user_id("anonymous")
        assert result["total"] == 0
