"""
Audit query API endpoint for compliance review.

Provides:
- GET /api/v1/audit/patient/{patient_id} — Paginated audit trail for a patient
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_audit_repository
from app.db.repositories.audit_repository import AuditRepository
from app.models.audit_log import AuditLogResponse

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get(
    "/patient/{patient_id}",
    summary="Query audit trail for a patient",
    description="Returns a paginated list of all access events for the specified patient.",
)
async def get_patient_audit_trail(
    patient_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> dict[str, Any]:
    """Query audit logs for a specific patient."""
    result = await audit_repo.query_by_patient_id(
        patient_id, page=page, page_size=page_size
    )
    result["items"] = [
        AuditLogResponse.from_mongo(doc).model_dump() for doc in result["items"]
    ]
    return result
