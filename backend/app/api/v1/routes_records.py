"""
Medical record API endpoints.

Provides:
- POST /api/v1/records                         — Create record (201, validates patient exists)
- GET  /api/v1/records/{id}                    — Retrieve record (200 / 404)
- GET  /api/v1/patients/{patient_id}/records   — List records by patient (paginated)
- PUT  /api/v1/records/{id}                    — Update record (200 / 404)
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.dependencies import get_medical_record_repository, get_patient_repository
from app.db.exceptions import NotFoundError
from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.patient_repository import PatientRepository
from app.models.medical_record import (
    MedicalRecordCreate,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["records"])


@router.post(
    "/api/v1/records",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new medical record",
    description="Create a medical record linked to an existing patient. Validates patient_id exists.",
)
async def create_record(
    record: MedicalRecordCreate,
    record_repo: MedicalRecordRepository = Depends(get_medical_record_repository),
    patient_repo: PatientRepository = Depends(get_patient_repository),
) -> MedicalRecordResponse:
    """Create a new medical record, validating patient existence first."""
    # Verify patient exists
    try:
        await patient_repo.get_by_id(record.patient_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Patient with id '{record.patient_id}' does not exist.",
        )

    doc = record.model_dump()
    # Convert risk_level enum to string value for MongoDB
    if doc.get("risk_level") is not None:
        doc["risk_level"] = doc["risk_level"].value if hasattr(doc["risk_level"], "value") else doc["risk_level"]

    created = await record_repo.create(doc)
    return MedicalRecordResponse.from_mongo(created)


@router.get(
    "/api/v1/records/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Retrieve a medical record by ID",
    description="Returns the medical record or 404 if not found.",
)
async def get_record(
    record_id: str,
    record_repo: MedicalRecordRepository = Depends(get_medical_record_repository),
) -> MedicalRecordResponse:
    """Retrieve a single medical record by ID."""
    doc = await record_repo.get_by_id(record_id)
    return MedicalRecordResponse.from_mongo(doc)


@router.get(
    "/api/v1/patients/{patient_id}/records",
    summary="List medical records for a patient",
    description="Returns a paginated list of medical records for the specified patient.",
)
async def list_patient_records(
    patient_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    record_repo: MedicalRecordRepository = Depends(get_medical_record_repository),
    patient_repo: PatientRepository = Depends(get_patient_repository),
) -> dict[str, Any]:
    """List medical records belonging to a specific patient."""
    # Verify patient exists
    try:
        await patient_repo.get_by_id(patient_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id '{patient_id}' does not exist.",
        )

    result = await record_repo.list_by_patient_id(patient_id, page=page, page_size=page_size)
    result["items"] = [
        MedicalRecordResponse.from_mongo(doc).model_dump() for doc in result["items"]
    ]
    return result


@router.put(
    "/api/v1/records/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Update a medical record",
    description="Partially update a medical record (e.g., add analysis_result or risk_level).",
)
async def update_record(
    record_id: str,
    update: MedicalRecordUpdate,
    record_repo: MedicalRecordRepository = Depends(get_medical_record_repository),
) -> MedicalRecordResponse:
    """Update an existing medical record."""
    update_data = update.model_dump(exclude_unset=True)
    # Convert risk_level enum to string value for MongoDB
    if "risk_level" in update_data and update_data["risk_level"] is not None:
        update_data["risk_level"] = (
            update_data["risk_level"].value
            if hasattr(update_data["risk_level"], "value")
            else update_data["risk_level"]
        )

    updated = await record_repo.update(record_id, update_data)
    return MedicalRecordResponse.from_mongo(updated)
