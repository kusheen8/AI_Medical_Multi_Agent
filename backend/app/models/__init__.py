"""Models package — Pydantic schemas and domain models.

Re-exports all public model classes for convenient imports:
    from app.models import PatientCreate, PatientResponse, RiskLevel, ...
"""

from app.models.alert import (
    AlertCreate,
    AlertInDB,
    AlertResponse,
    AlertSeverity,
    AlertStatus,
    AlertUpdate,
    DeliveryReceipt,
)
from app.models.audit_log import AuditAction, AuditLogEntry, AuditLogResponse
from app.models.common import ErrorDetail, PaginatedResponse, PyObjectId, TimestampMixin
from app.models.medical_record import (
    MedicalRecordCreate,
    MedicalRecordInDB,
    MedicalRecordResponse,
    MedicalRecordUpdate,
    RiskLevel,
)
from app.models.patient import (
    PatientCreate,
    PatientInDB,
    PatientResponse,
    PatientUpdate,
    Sex,
)
from app.models.trace import (
    ReasoningTraceCreate,
    ReasoningTraceInDB,
    ReasoningTraceResponse,
)

__all__ = [
    # Common
    "PyObjectId",
    "TimestampMixin",
    "PaginatedResponse",
    "ErrorDetail",
    # Patient
    "Sex",
    "PatientCreate",
    "PatientUpdate",
    "PatientInDB",
    "PatientResponse",
    # Medical Record
    "RiskLevel",
    "MedicalRecordCreate",
    "MedicalRecordUpdate",
    "MedicalRecordInDB",
    "MedicalRecordResponse",
    # Alert
    "AlertSeverity",
    "AlertStatus",
    "DeliveryReceipt",
    "AlertCreate",
    "AlertUpdate",
    "AlertInDB",
    "AlertResponse",
    # Trace
    "ReasoningTraceCreate",
    "ReasoningTraceInDB",
    "ReasoningTraceResponse",
    # Audit
    "AuditAction",
    "AuditLogEntry",
    "AuditLogResponse",
]
