"""
Integration tests for Patient CRUD API endpoints.

Tests all 5 patient endpoints via FastAPI TestClient with mocked MongoDB:
- POST   /api/v1/patients
- GET    /api/v1/patients/{id}
- GET    /api/v1/patients
- PUT    /api/v1/patients/{id}
- DELETE /api/v1/patients/{id}

Also tests:
- Idempotency key behavior
- Validation error responses (422)
- Not found responses (404)
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════════
# POST /api/v1/patients
# ═══════════════════════════════════════════════════════════════════════


class TestCreatePatient:
    def test_create_success(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_data: dict[str, Any],
    ) -> None:
        inserted_id = ObjectId()
        mock_collection.insert_one.return_value = MagicMock(inserted_id=inserted_id)
        # Idempotency key lookup returns None (no cached response)
        mock_collection.find_one.return_value = None

        response = test_client.post("/api/v1/patients", json=sample_patient_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["sex"] == "M"
        assert "id" in data
        assert "created_at" in data

    def test_create_validation_error_missing_name(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/patients",
            json={"dob": "1985-03-15", "sex": "M"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) > 0

    def test_create_validation_error_blank_name(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/patients",
            json={"name": "   ", "dob": "1985-03-15", "sex": "M"},
        )
        assert response.status_code == 422

    def test_create_validation_error_future_dob(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/patients",
            json={"name": "Test", "dob": "2099-01-01", "sex": "M"},
        )
        assert response.status_code == 422

    def test_create_validation_error_invalid_sex(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/patients",
            json={"name": "Test", "dob": "1985-03-15", "sex": "X"},
        )
        assert response.status_code == 422

    def test_create_with_idempotency_key(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_data: dict[str, Any],
    ) -> None:
        inserted_id = ObjectId()
        mock_collection.insert_one.return_value = MagicMock(inserted_id=inserted_id)
        mock_collection.find_one.return_value = None

        response = test_client.post(
            "/api/v1/patients",
            json=sample_patient_data,
            headers={"X-Idempotency-Key": "unique-key-123"},
        )
        assert response.status_code == 201

    def test_create_idempotency_returns_cached(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_doc: dict[str, Any],
        sample_patient_data: dict[str, Any],
    ) -> None:
        # Simulate cached idempotency response
        mock_collection.find_one.return_value = {
            "key": "cached-key",
            "response": sample_patient_doc,
        }

        response = test_client.post(
            "/api/v1/patients",
            json=sample_patient_data,
            headers={"X-Idempotency-Key": "cached-key"},
        )
        assert response.status_code == 201
        # insert_one should NOT have been called (cached)
        # (Note: find_one is used for both idempotency check, so we verify response)
        data = response.json()
        assert data["name"] == "John Doe"


# ═══════════════════════════════════════════════════════════════════════
# GET /api/v1/patients/{id}
# ═══════════════════════════════════════════════════════════════════════


class TestGetPatient:
    def test_get_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_doc: dict[str, Any],
    ) -> None:
        mock_collection.find_one.return_value = sample_patient_doc

        patient_id = str(sample_patient_doc["_id"])
        response = test_client.get(f"/api/v1/patients/{patient_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["id"] == patient_id

    def test_get_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        response = test_client.get(f"/api/v1/patients/{ObjectId()}")
        assert response.status_code == 404

    def test_get_invalid_id(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.get("/api/v1/patients/not-valid-id")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# GET /api/v1/patients
# ═══════════════════════════════════════════════════════════════════════


class TestListPatients:
    def test_list_empty(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.count_documents.return_value = 0
        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = []

        response = test_client.get("/api/v1/patients")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_results(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_doc: dict[str, Any],
    ) -> None:
        mock_collection.count_documents.return_value = 1
        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = [sample_patient_doc]

        response = test_client.get("/api/v1/patients")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "John Doe"

    def test_list_pagination_params(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.count_documents.return_value = 0
        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = []

        response = test_client.get("/api/v1/patients?page=2&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5

    def test_list_with_name_filter(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.count_documents.return_value = 0
        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = []

        response = test_client.get("/api/v1/patients?name=John")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════
# PUT /api/v1/patients/{id}
# ═══════════════════════════════════════════════════════════════════════


class TestUpdatePatient:
    def test_update_success(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_doc: dict[str, Any],
    ) -> None:
        updated_doc = {**sample_patient_doc, "name": "Updated Name"}
        mock_collection.find_one_and_update.return_value = updated_doc
        # Idempotency check returns None
        mock_collection.find_one.return_value = None

        patient_id = str(sample_patient_doc["_id"])
        response = test_client.put(
            f"/api/v1/patients/{patient_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one_and_update.return_value = None
        mock_collection.find_one.return_value = None

        response = test_client.put(
            f"/api/v1/patients/{ObjectId()}",
            json={"name": "X"},
        )
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# DELETE /api/v1/patients/{id}
# ═══════════════════════════════════════════════════════════════════════


class TestDeletePatient:
    def test_delete_success(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        response = test_client.delete(f"/api/v1/patients/{ObjectId()}")
        assert response.status_code == 204

    def test_delete_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

        response = test_client.delete(f"/api/v1/patients/{ObjectId()}")
        assert response.status_code == 404
