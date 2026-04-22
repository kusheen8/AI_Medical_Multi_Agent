"""
AI Medical Multi-Agent Backend — FastAPI Application Entry Point.

Bootstraps the application with:
- Lifespan context manager for startup/shutdown hooks
- CORS middleware
- Request correlation middleware
- Audit logging middleware
- Health check route registration
- Patient and Medical Record CRUD route registration
- Audit trail route registration
- Analysis endpoint registration
- Worker pool lifecycle management
- Task queue initialization and crash recovery
- Global error handlers
- Structured logging initialization
- Database client lifecycle management
- MongoDB index creation on startup
"""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.error_handlers import register_error_handlers
from app.api.v1.routes_analysis import router as analysis_router
from app.api.v1.routes_audit import router as audit_router
from app.api.v1.routes_health import router as health_router
from app.api.v1.routes_patients import router as patients_router
from app.api.v1.routes_records import router as records_router
from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestCorrelationMiddleware
from app.db.client import AsyncMongoClient
from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.patient_repository import PatientRepository
from app.db.repositories.trace_repository import TraceRepository
from app.services.coordinator.gemini_coordinator import GeminiCoordinator
from app.services.health_service import HealthService
from app.services.local_agents.medical_analyzer import MedicalAnalyzer
from app.services.local_agents.history_summarizer import HistorySummarizer
from app.services.local_agents.ollama_client import OllamaClient
from app.services.privacy_filter import PrivacyFilter
from app.services.queue.task_queue import TaskQueue
from app.workers.analysis_worker import AnalysisWorker
from app.workers.summarization_worker import SummarizationWorker

logger = structlog.get_logger(__name__)


async def _create_indexes(db_client: AsyncMongoClient) -> None:
    """Create MongoDB indexes for optimal query performance.

    Indexes:
    - medical_records.patient_id: speeds up patient-scoped record lookups
    - alerts.patient_id: speeds up patient-scoped alert lookups
    - audit_logs.resource_id: speeds up audit trail queries by patient
    - audit_logs.user_id: speeds up audit trail queries by user
    - audit_logs.timestamp: speeds up time-range audit queries
    - idempotency_keys.key: unique index for deduplication
    - idempotency_keys.created_at: TTL index for auto-expiry (24h)
    - reasoning_traces.task_id: speeds up trace lookups by task
    - reasoning_traces.patient_id: speeds up patient-scoped trace queries
    - reasoning_traces.expires_at: TTL index for auto-expiry
    - tasks.status: speeds up queue polling
    - tasks.created_at: speeds up task ordering
    """
    try:
        # Medical records index
        records_col = db_client.get_collection("medical_records")
        await records_col.create_index("patient_id")

        # Alerts index
        alerts_col = db_client.get_collection("alerts")
        await alerts_col.create_index("patient_id")

        # Audit log indexes
        audit_col = db_client.get_collection("audit_logs")
        await audit_col.create_index("resource_id")
        await audit_col.create_index("user_id")
        await audit_col.create_index("timestamp")

        # Idempotency key indexes
        idem_col = db_client.get_collection("idempotency_keys")
        await idem_col.create_index("key", unique=True)
        await idem_col.create_index("created_at", expireAfterSeconds=86400)  # 24h TTL

        # Reasoning trace indexes (Phase 3)
        traces_col = db_client.get_collection("reasoning_traces")
        await traces_col.create_index("task_id")
        await traces_col.create_index("patient_id")
        await traces_col.create_index("expires_at", expireAfterSeconds=0)  # TTL based on expires_at

        # Task queue indexes (Phase 3)
        tasks_col = db_client.get_collection("tasks")
        await tasks_col.create_index("status")
        await tasks_col.create_index("created_at")
        await tasks_col.create_index([("status", 1), ("priority", 1), ("created_at", 1)])

        await logger.ainfo("mongodb_indexes_created")
    except Exception:
        await logger.awarning("mongodb_index_creation_failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Startup: initializes logging, connects to MongoDB, creates services,
             indexes, task queue, and worker pool.
    Shutdown: gracefully stops workers, drains queue, disconnects from MongoDB.
    """
    settings = get_settings()

    # ── Startup ──
    setup_logging(log_level=settings.LOG_LEVEL, app_env=settings.APP_ENV)
    await logger.ainfo(
        "app_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )

    # Initialize database client
    db_client = AsyncMongoClient(settings)
    try:
        await db_client.connect()
        await _create_indexes(db_client)
    except Exception:
        await logger.aerror(
            "app_startup_db_failed",
            msg="Could not connect to MongoDB. Health checks will report unhealthy.",
        )

    # Store shared state on app instance
    app.state.db_client = db_client
    app.state.health_service = HealthService(settings=settings, db_client=db_client)

    # ── Phase 3: Initialize pipeline services ──
    privacy_filter = PrivacyFilter()
    coordinator = GeminiCoordinator(settings=settings, privacy_filter=privacy_filter)
    ollama_client = OllamaClient(settings=settings)

    # Repositories
    patient_repo = PatientRepository(db_client)
    record_repo = MedicalRecordRepository(db_client)
    trace_repo = TraceRepository(db_client)

    # Local agents
    analyzer = MedicalAnalyzer(ollama_client=ollama_client)
    summarizer = HistorySummarizer(
        ollama_client=ollama_client,
        record_repository=record_repo,
    )

    # Task queue
    task_queue = TaskQueue(db_client)
    app.state.task_queue = task_queue

    # Recover any tasks stuck in processing from a previous crash
    try:
        recovered = await task_queue.recover_pending()
        if recovered:
            await logger.ainfo("tasks_recovered_on_startup", count=recovered)
    except Exception:
        await logger.awarning("task_recovery_failed", exc_info=True)

    # ── Start worker pool ──
    worker_tasks: list[asyncio.Task[None]] = []
    workers: list[AnalysisWorker | SummarizationWorker] = []

    # Analysis workers
    for i in range(settings.WORKER_CONCURRENCY):
        worker = AnalysisWorker(
            worker_id=f"analysis-{i}",
            queue=task_queue,
            coordinator=coordinator,
            analyzer=analyzer,
            patient_repo=patient_repo,
            record_repo=record_repo,
            trace_repo=trace_repo,
        )
        workers.append(worker)
        worker_tasks.append(asyncio.create_task(worker.start()))

    # Summarization worker (1 instance)
    summary_worker = SummarizationWorker(
        worker_id="summarization-0",
        queue=task_queue,
        coordinator=coordinator,
        summarizer=summarizer,
        patient_repo=patient_repo,
        trace_repo=trace_repo,
    )
    workers.append(summary_worker)
    worker_tasks.append(asyncio.create_task(summary_worker.start()))

    await logger.ainfo(
        "worker_pool_started",
        analysis_workers=settings.WORKER_CONCURRENCY,
        summarization_workers=1,
    )

    await logger.ainfo("app_started")

    yield

    # ── Shutdown ──
    await logger.ainfo("app_shutting_down")

    # Stop all workers gracefully
    for worker in workers:
        await worker.stop()

    # Cancel worker tasks and wait for them to finish
    for task in worker_tasks:
        task.cancel()

    await asyncio.gather(*worker_tasks, return_exceptions=True)
    await logger.ainfo("worker_pool_stopped")

    await db_client.disconnect()
    await logger.ainfo("app_shutdown_complete")


def create_app() -> FastAPI:
    """Factory function for creating the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI Medical Multi-Agent backend providing hybrid cloud/local "
            "medical analysis with PHI boundary enforcement."
        ),
        lifespan=lifespan,
    )

    # ── Middleware (order matters: outermost runs first) ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production (Phase 5)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestCorrelationMiddleware)

    # ── Error Handlers ──
    register_error_handlers(app)

    # ── Routes ──
    app.include_router(health_router)
    app.include_router(patients_router)
    app.include_router(records_router)
    app.include_router(audit_router)
    app.include_router(analysis_router)

    return app


# Application instance used by `uvicorn app.main:app`
app = create_app()
