"""
Integration tests for Medical Record API endpoints.

Tests all 4 record endpoints via FastAPI TestClient with mocked MongoDB:
- POST /api/v1/records
- GET  /api/v1/records/{id}
- GET  /api/v1/patients/{patient_id}/records
- PUT  /api/v1/records/{id}

Also tests:
- Patient existence validation on create
- Risk level enum validation
- Not found responses (404)
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════════
# POST /api/v1/records
# ═══════════════════════════════════════════════════════════════════════


class TestCreateRecord:
    def test_create_success(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_record_data: dict[str, Any],
        sample_patient_doc: dict[str, Any],
    ) -> None:
        inserted_id = ObjectId()
        # find_one: first call for patient lookup, succeeds
        mock_collection.find_one.return_value = sample_patient_doc
        mock_collection.insert_one.return_value = MagicMock(inserted_id=inserted_id)

        response = test_client.post("/api/v1/records", json=sample_record_data)

        assert response.status_code == 201
        data = response.json()
        assert data["symptoms"] == "Chest pain, shortness of breath"
        assert "id" in data

    def test_create_patient_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        # Patient lookup returns None
        mock_collection.find_one.return_value = None

        response = test_client.post(
            "/api/v1/records",
            json={
                "patient_id": str(ObjectId()),
                "symptoms": "Headache",
            },
        )
        assert response.status_code == 422
        assert "does not exist" in response.json()["detail"]

    def test_create_invalid_patient_id(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/records",
            json={
                "patient_id": "not-a-valid-id",
                "symptoms": "Pain",
            },
        )
        assert response.status_code == 422

    def test_create_empty_symptoms(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/records",
            json={
                "patient_id": str(ObjectId()),
                "symptoms": "   ",
            },
        )
        assert response.status_code == 422

    def test_create_with_risk_level(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_doc: dict[str, Any],
    ) -> None:
        mock_collection.find_one.return_value = sample_patient_doc
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())

        response = test_client.post(
            "/api/v1/records",
            json={
                "patient_id": str(sample_patient_doc["_id"]),
                "symptoms": "Headache",
                "risk_level": "low",
            },
        )
        assert response.status_code == 201

    def test_create_invalid_risk_level(
        self,
        test_client: TestClient,
    ) -> None:
        response = test_client.post(
            "/api/v1/records",
            json={
                "patient_id": str(ObjectId()),
                "symptoms": "Pain",
                "risk_level": "extreme",
            },
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# GET /api/v1/records/{id}
# ═══════════════════════════════════════════════════════════════════════


class TestGetRecord:
    def test_get_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_record_doc: dict[str, Any],
    ) -> None:
        mock_collection.find_one.return_value = sample_record_doc

        record_id = str(sample_record_doc["_id"])
        response = test_client.get(f"/api/v1/records/{record_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["symptoms"] == "Chest pain, shortness of breath"
        assert data["risk_level"] == "high"

    def test_get_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        response = test_client.get(f"/api/v1/records/{ObjectId()}")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# GET /api/v1/patients/{patient_id}/records
# ═══════════════════════════════════════════════════════════════════════


class TestListPatientRecords:
    def test_list_empty(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_patient_doc: dict[str, Any],
    ) -> None:
        # First find_one for patient existence check
        mock_collection.find_one.return_value = sample_patient_doc
        mock_collection.count_documents.return_value = 0
        cursor = mock_collection.find.return_value
        cursor.to_list.return_value = []

        patient_id = str(sample_patient_doc["_id"])
        response = test_client.get(f"/api/v1/patients/{patient_id}/records")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_patient_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        response = test_client.get(f"/api/v1/patients/{ObjectId()}/records")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# PUT /api/v1/records/{id}
# ═══════════════════════════════════════════════════════════════════════


class TestUpdateRecord:
    def test_update_success(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_record_doc: dict[str, Any],
    ) -> None:
        updated_doc = {**sample_record_doc, "risk_level": "critical"}
        mock_collection.find_one_and_update.return_value = updated_doc

        record_id = str(sample_record_doc["_id"])
        response = test_client.put(
            f"/api/v1/records/{record_id}",
            json={"risk_level": "critical"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "critical"

    def test_update_not_found(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one_and_update.return_value = None

        response = test_client.put(
            f"/api/v1/records/{ObjectId()}",
            json={"risk_level": "low"},
        )
        assert response.status_code == 404

    def test_update_add_analysis(
        self,
        test_client: TestClient,
        mock_collection: MagicMock,
        sample_record_doc: dict[str, Any],
    ) -> None:
        updated = {
            **sample_record_doc,
            "analysis_result": "New analysis",
        }
        mock_collection.find_one_and_update.return_value = updated

        record_id = str(sample_record_doc["_id"])
        response = test_client.put(
            f"/api/v1/records/{record_id}",
            json={"analysis_result": "New analysis"},
        )

        assert response.status_code == 200
        assert response.json()["analysis_result"] == "New analysis"
