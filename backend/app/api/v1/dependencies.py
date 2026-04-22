"""
FastAPI dependency injection helpers for API v1 routes.

Provides repository instances via ``Depends()`` by extracting the
shared ``db_client`` from ``request.app.state`` (set during lifespan).
"""

from typing import Any

from fastapi import Request

from app.db.client import AsyncMongoClient
from app.db.repositories.alert_repository import AlertRepository
from app.db.repositories.audit_repository import AuditRepository
from app.db.repositories.idempotency_repository import IdempotencyRepository
from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.patient_repository import PatientRepository
from app.db.repositories.policy_repository import PolicyRepository
from app.db.repositories.trace_repository import TraceRepository
from app.services.queue.task_queue import TaskQueue


def get_db_client(request: Request) -> AsyncMongoClient:
    """Extract the shared AsyncMongoClient from app state."""
    return request.app.state.db_client


def get_patient_repository(request: Request) -> PatientRepository:
    """Build a PatientRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return PatientRepository(db_client)


def get_medical_record_repository(request: Request) -> MedicalRecordRepository:
    """Build a MedicalRecordRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return MedicalRecordRepository(db_client)


def get_alert_repository(request: Request) -> AlertRepository:
    """Build an AlertRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return AlertRepository(db_client)


def get_audit_repository(request: Request) -> AuditRepository:
    """Build an AuditRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return AuditRepository(db_client)


def get_trace_repository(request: Request) -> TraceRepository:
    """Build a TraceRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return TraceRepository(db_client)


def get_task_queue(request: Request) -> TaskQueue:
    """Extract the TaskQueue from app state."""
    return request.app.state.task_queue


def get_policy_repository(request: Request) -> PolicyRepository:
    """Build a PolicyRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return PolicyRepository(db_client)


def get_idempotency_repository(request: Request) -> IdempotencyRepository:
    """Build an IdempotencyRepository using the shared DB client."""
    db_client: AsyncMongoClient = request.app.state.db_client
    return IdempotencyRepository(db_client)


def get_policy_engine(request: Request) -> Any:
    """Extract the PolicyEngine from app state."""
    return request.app.state.policy_engine


def get_caregiver_notifier(request: Request) -> Any:
    """Extract the CaregiverNotifier from app state."""
    return request.app.state.caregiver_notifier


def get_metrics_collector(request: Request) -> Any:
    """Extract the MetricsCollector from app state."""
    return request.app.state.metrics_collector


def get_dlq_manager(request: Request) -> Any:
    """Extract the DLQManager from app state."""
    return request.app.state.dlq_manager
