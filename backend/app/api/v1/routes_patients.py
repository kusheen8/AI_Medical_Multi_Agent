"""
Patient CRUD API endpoints.

Provides:
- POST   /api/v1/patients          — Create patient (201)
- GET    /api/v1/patients/{id}     — Retrieve patient (200 / 404)
- GET    /api/v1/patients          — List patients (paginated)
- PUT    /api/v1/patients/{id}     — Update patient (200 / 404)
- DELETE /api/v1/patients/{id}     — Delete patient (204 / 404)

Supports optional idempotency via ``X-Idempotency-Key`` header on POST/PUT.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.v1.dependencies import get_patient_repository
from app.db.repositories.patient_repository import PatientRepository
from app.models.patient import PatientCreate, PatientResponse, PatientUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


async def _handle_idempotency(
    repo: PatientRepository,
    key: str,
) -> dict[str, Any] | None:
    """Check if an idempotency key has already been used.

    Returns the cached response document if found, else None.
    """
    collection = repo._db_client.get_collection("idempotency_keys")
    existing = await collection.find_one({"key": key})
    if existing:
        return existing.get("response")
    return None


async def _store_idempotency(
    repo: PatientRepository,
    key: str,
    response_doc: dict[str, Any],
) -> None:
    """Store an idempotency key with its response for deduplication."""
    collection = repo._db_client.get_collection("idempotency_keys")
    await collection.insert_one(
        {
            "key": key,
            "response": response_doc,
            "created_at": datetime.now(timezone.utc),
        }
    )


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
    description="Register a new patient record. Supports optional idempotency via X-Idempotency-Key header.",
)
async def create_patient(
    patient: PatientCreate,
    repo: PatientRepository = Depends(get_patient_repository),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> PatientResponse:
    """Create a new patient record."""
    # Check idempotency
    if x_idempotency_key:
        cached = await _handle_idempotency(repo, x_idempotency_key)
        if cached:
            await logger.ainfo("idempotency_hit", key=x_idempotency_key)
            return PatientResponse.from_mongo(cached)

    doc = patient.model_dump()
    # Convert date to string for MongoDB storage
    doc["dob"] = doc["dob"].isoformat()
    created = await repo.create(doc)

    # Store idempotency key
    if x_idempotency_key:
        await _store_idempotency(repo, x_idempotency_key, created)

    return PatientResponse.from_mongo(created)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Retrieve a patient by ID",
    description="Returns the patient record or 404 if not found.",
)
async def get_patient(
    patient_id: str,
    repo: PatientRepository = Depends(get_patient_repository),
) -> PatientResponse:
    """Retrieve a single patient by ID."""
    doc = await repo.get_by_id(patient_id)
    return PatientResponse.from_mongo(doc)


@router.get(
    "",
    summary="List all patients",
    description="Returns a paginated list of patients. Supports optional name search.",
)
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    name: str | None = Query(None, description="Filter by name (partial match)"),
    repo: PatientRepository = Depends(get_patient_repository),
) -> dict[str, Any]:
    """List patients with optional name search and pagination."""
    if name:
        result = await repo.search_by_name(name, page=page, page_size=page_size)
    else:
        result = await repo.list(page=page, page_size=page_size)

    result["items"] = [
        PatientResponse.from_mongo(doc).model_dump() for doc in result["items"]
    ]
    return result


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update a patient",
    description="Partially update a patient record. Only provided fields are changed.",
)
async def update_patient(
    patient_id: str,
    update: PatientUpdate,
    repo: PatientRepository = Depends(get_patient_repository),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> PatientResponse:
    """Update an existing patient record."""
    # Check idempotency
    if x_idempotency_key:
        cached = await _handle_idempotency(repo, x_idempotency_key)
        if cached:
            return PatientResponse.from_mongo(cached)

    update_data = update.model_dump(exclude_unset=True)
    # Convert date to string if present
    if "dob" in update_data and update_data["dob"] is not None:
        update_data["dob"] = update_data["dob"].isoformat()

    updated = await repo.update(patient_id, update_data)

    # Store idempotency key
    if x_idempotency_key:
        await _store_idempotency(repo, x_idempotency_key, updated)

    return PatientResponse.from_mongo(updated)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a patient",
    description="Permanently delete a patient record. Returns 204 on success, 404 if not found.",
)
async def delete_patient(
    patient_id: str,
    repo: PatientRepository = Depends(get_patient_repository),
) -> Response:
    """Delete a patient by ID."""
    await repo.delete(patient_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
