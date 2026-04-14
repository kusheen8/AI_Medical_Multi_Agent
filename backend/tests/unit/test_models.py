"""
Unit tests for domain models.

Validates:
- Model construction with valid/invalid inputs
- Field constraints (name length, DOB, enums)
- ObjectId serialization/deserialization
- Enum validation (RiskLevel, AlertSeverity, AlertStatus, Sex)
- Response.from_mongo factory methods
"""

from datetime import date, datetime, timezone

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models.alert import AlertCreate, AlertResponse, AlertSeverity, AlertStatus
from app.models.audit_log import AuditAction, AuditLogEntry
from app.models.common import PaginatedResponse, PyObjectId
from app.models.medical_record import MedicalRecordCreate, MedicalRecordResponse, RiskLevel
from app.models.patient import PatientCreate, PatientResponse, PatientUpdate, Sex
from app.models.trace import ReasoningTraceCreate, ReasoningTraceResponse


# ═══════════════════════════════════════════════════════════════════════
# PyObjectId
# ═══════════════════════════════════════════════════════════════════════


class TestPyObjectId:
    def test_from_string(self) -> None:
        oid = str(ObjectId())
        result = PyObjectId.validate(oid)
        assert str(result) == oid

    def test_from_objectid(self) -> None:
        oid = ObjectId()
        result = PyObjectId.validate(oid)
        assert str(result) == str(oid)

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PyObjectId.validate("not-an-objectid")

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PyObjectId.validate(12345)


# ═══════════════════════════════════════════════════════════════════════
# Patient Models
# ═══════════════════════════════════════════════════════════════════════


class TestPatientCreate:
    def test_valid_patient(self) -> None:
        patient = PatientCreate(
            name="John Doe", dob=date(1985, 3, 15), sex=Sex.MALE
        )
        assert patient.name == "John Doe"
        assert patient.dob == date(1985, 3, 15)
        assert patient.sex == Sex.MALE
        assert patient.conditions == []
        assert patient.medications == []
        assert patient.allergies == []

    def test_valid_patient_with_all_fields(self) -> None:
        patient = PatientCreate(
            name="Jane Doe",
            dob=date(1990, 7, 20),
            sex=Sex.FEMALE,
            conditions=["asthma"],
            medications=["inhaler"],
            allergies=["peanuts"],
        )
        assert patient.conditions == ["asthma"]

    def test_name_required(self) -> None:
        with pytest.raises(ValidationError):
            PatientCreate(dob=date(1985, 3, 15), sex=Sex.MALE)  # type: ignore

    def test_name_blank_rejected(self) -> None:
        with pytest.raises(ValidationError, match="blank"):
            PatientCreate(name="   ", dob=date(1985, 3, 15), sex=Sex.MALE)

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            PatientCreate(name="A" * 256, dob=date(1985, 3, 15), sex=Sex.MALE)

    def test_name_max_length(self) -> None:
        patient = PatientCreate(name="A" * 255, dob=date(1985, 3, 15), sex=Sex.MALE)
        assert len(patient.name) == 255

    def test_dob_future_rejected(self) -> None:
        with pytest.raises(ValidationError, match="future"):
            PatientCreate(
                name="John Doe", dob=date(2099, 1, 1), sex=Sex.MALE
            )

    def test_invalid_sex_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PatientCreate(name="John", dob=date(1985, 3, 15), sex="X")  # type: ignore

    def test_name_stripped(self) -> None:
        patient = PatientCreate(
            name="  Jane Doe  ", dob=date(1985, 3, 15), sex=Sex.FEMALE
        )
        assert patient.name == "Jane Doe"


class TestPatientUpdate:
    def test_all_none_valid(self) -> None:
        update = PatientUpdate()
        assert update.name is None
        assert update.dob is None

    def test_partial_update(self) -> None:
        update = PatientUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.dob is None

    def test_blank_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="blank"):
            PatientUpdate(name="   ")

    def test_future_dob_rejected(self) -> None:
        with pytest.raises(ValidationError, match="future"):
            PatientUpdate(dob=date(2099, 1, 1))


class TestPatientResponse:
    def test_from_mongo(self) -> None:
        doc = {
            "_id": ObjectId(),
            "name": "John Doe",
            "dob": "1985-03-15",
            "sex": "M",
            "conditions": ["diabetes"],
            "medications": ["metformin"],
            "allergies": ["penicillin"],
            "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        }
        response = PatientResponse.from_mongo(doc)
        assert response.id == str(doc["_id"])
        assert response.name == "John Doe"
        assert response.conditions == ["diabetes"]

    def test_from_mongo_minimal(self) -> None:
        doc = {
            "_id": ObjectId(),
            "name": "Jane",
            "dob": "1990-01-01",
            "sex": "F",
        }
        response = PatientResponse.from_mongo(doc)
        assert response.conditions == []
        assert response.medications == []
        assert response.allergies == []


# ═══════════════════════════════════════════════════════════════════════
# Medical Record Models
# ═══════════════════════════════════════════════════════════════════════


class TestMedicalRecordCreate:
    def test_valid_record(self) -> None:
        record = MedicalRecordCreate(
            patient_id=str(ObjectId()),
            symptoms="Headache and nausea",
        )
        assert record.symptoms == "Headache and nausea"

    def test_symptoms_required(self) -> None:
        with pytest.raises(ValidationError):
            MedicalRecordCreate(patient_id=str(ObjectId()))  # type: ignore

    def test_symptoms_blank_rejected(self) -> None:
        with pytest.raises(ValidationError, match="blank"):
            MedicalRecordCreate(patient_id=str(ObjectId()), symptoms="   ")

    def test_invalid_patient_id(self) -> None:
        with pytest.raises(ValidationError, match="valid ObjectId"):
            MedicalRecordCreate(patient_id="not-valid", symptoms="pain")

    def test_with_risk_level(self) -> None:
        record = MedicalRecordCreate(
            patient_id=str(ObjectId()),
            symptoms="Chest pain",
            risk_level=RiskLevel.HIGH,
        )
        assert record.risk_level == RiskLevel.HIGH

    def test_invalid_risk_level(self) -> None:
        with pytest.raises(ValidationError):
            MedicalRecordCreate(
                patient_id=str(ObjectId()),
                symptoms="Pain",
                risk_level="extreme",  # type: ignore
            )


class TestRiskLevel:
    def test_valid_values(self) -> None:
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_all_members(self) -> None:
        assert len(RiskLevel) == 4


class TestMedicalRecordResponse:
    def test_from_mongo(self) -> None:
        doc = {
            "_id": ObjectId(),
            "patient_id": str(ObjectId()),
            "symptoms": "Fever",
            "entities": {"temp": "102F"},
            "analysis_result": "Likely infection",
            "risk_level": "medium",
            "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        }
        response = MedicalRecordResponse.from_mongo(doc)
        assert response.risk_level == RiskLevel.MEDIUM
        assert response.entities == {"temp": "102F"}


# ═══════════════════════════════════════════════════════════════════════
# Alert Models
# ═══════════════════════════════════════════════════════════════════════


class TestAlertCreate:
    def test_valid_alert(self) -> None:
        alert = AlertCreate(
            patient_id=str(ObjectId()),
            severity=AlertSeverity.CRITICAL,
            trigger="High risk detected",
            channels=["sms"],
        )
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.channels == ["sms"]

    def test_trigger_blank_rejected(self) -> None:
        with pytest.raises(ValidationError, match="blank"):
            AlertCreate(
                patient_id=str(ObjectId()),
                severity=AlertSeverity.WARNING,
                trigger="   ",
                channels=["email"],
            )

    def test_channels_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AlertCreate(
                patient_id=str(ObjectId()),
                severity=AlertSeverity.ERROR,
                trigger="Something happened",
                channels=[],
            )

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            AlertCreate(
                patient_id=str(ObjectId()),
                severity="info",  # type: ignore
                trigger="Test",
                channels=["sms"],
            )

    def test_invalid_patient_id(self) -> None:
        with pytest.raises(ValidationError, match="valid ObjectId"):
            AlertCreate(
                patient_id="bad-id",
                severity=AlertSeverity.WARNING,
                trigger="Test",
                channels=["sms"],
            )


class TestAlertSeverityEnum:
    def test_valid_values(self) -> None:
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_all_members(self) -> None:
        assert len(AlertSeverity) == 3


class TestAlertStatusEnum:
    def test_valid_values(self) -> None:
        assert AlertStatus.PENDING.value == "pending"
        assert AlertStatus.SENT.value == "sent"
        assert AlertStatus.DELIVERED.value == "delivered"
        assert AlertStatus.FAILED.value == "failed"


class TestAlertResponse:
    def test_from_mongo(self) -> None:
        doc = {
            "_id": ObjectId(),
            "patient_id": str(ObjectId()),
            "severity": "critical",
            "trigger": "Test trigger",
            "channels": ["sms", "email"],
            "status": "pending",
            "delivery_receipts": [],
            "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        }
        response = AlertResponse.from_mongo(doc)
        assert response.severity == AlertSeverity.CRITICAL
        assert response.status == AlertStatus.PENDING


# ═══════════════════════════════════════════════════════════════════════
# Reasoning Trace Models
# ═══════════════════════════════════════════════════════════════════════


class TestReasoningTraceCreate:
    def test_valid_trace(self) -> None:
        trace = ReasoningTraceCreate(
            task_type="symptom_analysis",
            instructions="Analyze for cardiac risk",
            origin="gemini_coordinator",
        )
        assert trace.task_type == "symptom_analysis"
        assert trace.allowed_data_classes == []

    def test_with_data_classes(self) -> None:
        trace = ReasoningTraceCreate(
            task_type="history_summary",
            instructions="Summarize patient history",
            allowed_data_classes=["vitals", "symptoms"],
            origin="gemini_coordinator",
        )
        assert trace.allowed_data_classes == ["vitals", "symptoms"]


class TestReasoningTraceResponse:
    def test_from_mongo(self) -> None:
        doc = {
            "_id": ObjectId(),
            "task_type": "symptom_analysis",
            "instructions": "Analyze",
            "allowed_data_classes": ["vitals"],
            "origin": "gemini_coordinator",
            "expires_at": None,
            "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        }
        response = ReasoningTraceResponse.from_mongo(doc)
        assert response.task_type == "symptom_analysis"
        assert response.origin == "gemini_coordinator"


# ═══════════════════════════════════════════════════════════════════════
# Audit Log Models
# ═══════════════════════════════════════════════════════════════════════


class TestAuditLogEntry:
    def test_valid_entry(self) -> None:
        entry = AuditLogEntry(
            user_id="anonymous",
            action=AuditAction.READ,
            resource_type="patients",
            request_id="abc-123",
        )
        assert entry.action == AuditAction.READ
        assert entry.resource_id is None

    def test_with_resource_id(self) -> None:
        entry = AuditLogEntry(
            user_id="user1",
            action=AuditAction.WRITE,
            resource_type="records",
            resource_id="507f1f77bcf86cd799439011",
            request_id="def-456",
            ip_address="192.168.1.1",
        )
        assert entry.resource_id == "507f1f77bcf86cd799439011"
        assert entry.ip_address == "192.168.1.1"


class TestAuditAction:
    def test_valid_values(self) -> None:
        assert AuditAction.READ.value == "read"
        assert AuditAction.WRITE.value == "write"
        assert AuditAction.DELETE.value == "delete"


# ═══════════════════════════════════════════════════════════════════════
# PaginatedResponse
# ═══════════════════════════════════════════════════════════════════════


class TestPaginatedResponse:
    def test_valid_paginated(self) -> None:
        resp = PaginatedResponse[str](
            items=["a", "b"],
            total=10,
            page=1,
            page_size=20,
            pages=1,
        )
        assert resp.items == ["a", "b"]
        assert resp.total == 10

    def test_invalid_page(self) -> None:
        with pytest.raises(ValidationError):
            PaginatedResponse[str](
                items=[], total=0, page=0, page_size=20, pages=0
            )

    def test_invalid_page_size(self) -> None:
        with pytest.raises(ValidationError):
            PaginatedResponse[str](
                items=[], total=0, page=1, page_size=101, pages=0
            )
