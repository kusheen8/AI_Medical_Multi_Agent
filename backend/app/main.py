"""
AI Medical Multi-Agent Backend — FastAPI Application Entry Point.

Bootstraps the application with:
- Lifespan context manager for startup/shutdown hooks
- CORS middleware (restricted origins)
- Security headers middleware (Phase 5)
- Rate limiting middleware (Phase 5)
- Request correlation middleware
- Audit logging middleware
- Health check route registration
- Patient and Medical Record CRUD route registration
- Audit trail route registration
- Analysis endpoint registration
- Alert, Webhook, Metrics, and Admin route registration (Phase 4)
- Authentication route registration (Phase 5)
- Worker pool lifecycle management
- Task queue initialization and crash recovery
- Risk policy engine and notification service initialization (Phase 4)
- Circuit breaker and metrics collector setup (Phase 4)
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
from app.api.v1.routes_admin import router as admin_router
from app.api.v1.routes_alerts import router as alerts_router
from app.api.v1.routes_analysis import router as analysis_router
from app.api.v1.routes_audit import router as audit_router
from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_health import router as health_router
from app.api.v1.routes_metrics import router as metrics_router
from app.api.v1.routes_patients import router as patients_router
from app.api.v1.routes_records import router as records_router
from app.api.v1.routes_webhooks import router as webhooks_router
from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestCorrelationMiddleware
from app.core.rate_limiter import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.tracing import setup_tracing
from app.db.client import AsyncMongoClient
from app.db.repositories.alert_repository import AlertRepository
from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.patient_repository import PatientRepository
from app.db.repositories.policy_repository import PolicyRepository
from app.db.repositories.trace_repository import TraceRepository
from app.services.circuit_breaker import get_circuit_breaker
from app.services.coordinator.groq_coordinator import GroqCoordinator
from app.services.health_service import HealthService
from app.services.local_agents.medical_analyzer import MedicalAnalyzer
from app.services.local_agents.history_summarizer import HistorySummarizer
from app.services.local_agents.ollama_client import OllamaClient
from app.services.metrics import MetricsCollector
from app.services.notifications.caregiver_notifier import CaregiverNotifier
from app.services.notifications.providers.email_provider import SendGridEmailProvider
from app.services.notifications.providers.push_provider import FCMPushProvider
from app.services.notifications.providers.sms_provider import TwilioSMSProvider
from app.services.privacy_filter import PrivacyFilter
from app.services.queue.dlq_manager import DLQManager
from app.services.queue.task_queue import TaskQueue
from app.services.risk_policy.policy_engine import PolicyEngine
from app.workers.analysis_worker import AnalysisWorker
from app.workers.summarization_worker import SummarizationWorker

logger = structlog.get_logger(__name__)


async def _create_indexes(db_client: AsyncMongoClient) -> None:
    """Create MongoDB indexes for optimal query performance.

    Indexes:
    - medical_records.patient_id: speeds up patient-scoped record lookups
    - alerts.patient_id: speeds up patient-scoped alert lookups
    - alerts.idempotency_key: enables idempotency deduplication
    - alerts.status: speeds up status-based queries
    - audit_logs.resource_id: speeds up audit trail queries by patient
    - audit_logs.user_id: speeds up audit trail queries by user
    - audit_logs.timestamp: speeds up time-range audit queries
    - idempotency_keys.key: unique index for deduplication
    - idempotency_keys.created_at: TTL index for auto-expiry (24h)
    - idempotency_store.key: unique index for request deduplication
    - idempotency_store.expires_at: TTL index for auto-expiry
    - reasoning_traces.task_id: speeds up trace lookups by task
    - reasoning_traces.patient_id: speeds up patient-scoped trace queries
    - reasoning_traces.expires_at: TTL index for auto-expiry
    - tasks.status: speeds up queue polling
    - tasks.created_at: speeds up task ordering
    - policy_rules.name: unique rule names
    - policy_rules.enabled: speeds up active rule queries
    - notification_dlq.status: speeds up DLQ queries
    """
    try:
        # Medical records index
        records_col = db_client.get_collection("medical_records")
        await records_col.create_index("patient_id")

        # Alerts indexes (Phase 4)
        alerts_col = db_client.get_collection("alerts")
        await alerts_col.create_index("patient_id")
        await alerts_col.create_index("idempotency_key", sparse=True)
        await alerts_col.create_index("status")

        # Audit log indexes
        audit_col = db_client.get_collection("audit_logs")
        await audit_col.create_index("resource_id")
        await audit_col.create_index("user_id")
        await audit_col.create_index("timestamp")

        # Idempotency key indexes (legacy)
        idem_col = db_client.get_collection("idempotency_keys")
        await idem_col.create_index("key", unique=True)
        await idem_col.create_index("created_at", expireAfterSeconds=86400)  # 24h TTL

        # Idempotency store indexes (Phase 4)
        idem_store_col = db_client.get_collection("idempotency_store")
        await idem_store_col.create_index("key", unique=True)
        await idem_store_col.create_index("expires_at", expireAfterSeconds=0)

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

        # Policy rules indexes (Phase 4)
        policy_col = db_client.get_collection("policy_rules")
        await policy_col.create_index("name", unique=True)
        await policy_col.create_index("enabled")

        # Notification DLQ indexes (Phase 4)
        dlq_col = db_client.get_collection("notification_dlq")
        await dlq_col.create_index("status")
        await dlq_col.create_index("created_at")

        # User indexes (Phase 5)
        users_col = db_client.get_collection("users")
        await users_col.create_index("email", unique=True)

        # Token blacklist indexes (Phase 5)
        blacklist_col = db_client.get_collection("token_blacklist")
        await blacklist_col.create_index("jti", unique=True)
        await blacklist_col.create_index("expires_at", expireAfterSeconds=0)

        await logger.ainfo("mongodb_indexes_created")
    except Exception:
        await logger.awarning("mongodb_index_creation_failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Startup: initializes logging, connects to MongoDB, creates services,
             indexes, task queue, worker pool, and Phase 4 reliability services.
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
    app.state.settings = settings
    app.state.health_service = HealthService(settings=settings, db_client=db_client)

    # ── Phase 3: Initialize pipeline services ──
    privacy_filter = PrivacyFilter()
    coordinator = GroqCoordinator(settings=settings, privacy_filter=privacy_filter)
    ollama_client = OllamaClient(settings=settings)

    # Repositories
    patient_repo = PatientRepository(db_client)
    record_repo = MedicalRecordRepository(db_client)
    trace_repo = TraceRepository(db_client)
    alert_repo = AlertRepository(db_client)
    policy_repo = PolicyRepository(db_client)

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

    # ── Phase 4: Initialize reliability services ──

    # Metrics collector
    metrics_collector = MetricsCollector()
    app.state.metrics_collector = metrics_collector

    # Circuit breakers for notification providers
    dry_run = settings.notification_dry_run_effective
    cb_threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
    cb_timeout = settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT

    sms_cb = get_circuit_breaker("twilio", cb_threshold, cb_timeout)
    email_cb = get_circuit_breaker("sendgrid", cb_threshold, cb_timeout)
    push_cb = get_circuit_breaker("fcm", cb_threshold, cb_timeout)
    get_circuit_breaker("ollama", cb_threshold, cb_timeout)  # Register Ollama CB

    # Notification providers
    sms_provider = TwilioSMSProvider(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        from_number=settings.TWILIO_FROM_NUMBER,
        dry_run=dry_run,
    )
    email_provider = SendGridEmailProvider(
        api_key=settings.SENDGRID_API_KEY,
        from_email=settings.SENDGRID_FROM_EMAIL,
        dry_run=dry_run,
    )
    push_provider = FCMPushProvider(
        server_key=settings.FCM_SERVER_KEY,
        dry_run=dry_run,
    )

    # Caregiver notifier
    notifier = CaregiverNotifier(
        providers={"sms": sms_provider, "email": email_provider, "push": push_provider},
        circuit_breakers={"sms": sms_cb, "email": email_cb, "push": push_cb},
    )
    app.state.caregiver_notifier = notifier

    # DLQ Manager
    dlq_manager = DLQManager(db_client)
    app.state.dlq_manager = dlq_manager

    # Risk policy engine
    policy_engine = PolicyEngine(
        policy_repo=policy_repo,
        record_repo=record_repo,
        global_dry_run=dry_run,
    )
    app.state.policy_engine = policy_engine

    # Seed default policies (if none exist)
    try:
        await policy_engine.seed_default_policies()
    except Exception:
        await logger.awarning("policy_seed_failed", exc_info=True)

    await logger.ainfo(
        "phase4_services_initialized",
        notification_dry_run=dry_run,
        circuit_breaker_threshold=cb_threshold,
        circuit_breaker_timeout=cb_timeout,
    )

    # ── Start worker pool ──
    worker_tasks: list[asyncio.Task[None]] = []
    workers: list[AnalysisWorker | SummarizationWorker] = []

    # Analysis workers (with Phase 4 alert hooks)
    for i in range(settings.WORKER_CONCURRENCY):
        worker = AnalysisWorker(
            worker_id=f"analysis-{i}",
            queue=task_queue,
            coordinator=coordinator,
            analyzer=analyzer,
            patient_repo=patient_repo,
            record_repo=record_repo,
            trace_repo=trace_repo,
            policy_engine=policy_engine,
            notifier=notifier,
            alert_repo=alert_repo,
            metrics=metrics_collector,
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
    # CORS — restricted origins (Phase 5 hardening)
    cors_origins = settings.cors_origins_list if settings.is_production else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID",
                       "X-Idempotency-Key", "X-Admin-Key", "Idempotency-Key"],
    )
    # Security headers (Phase 5)
    app.add_middleware(SecurityHeadersMiddleware, app_env=settings.APP_ENV)
    # Rate limiting (Phase 5)
    app.add_middleware(
        RateLimitMiddleware,
        login_limit=settings.RATE_LIMIT_LOGIN,
        api_limit=settings.RATE_LIMIT_API,
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
    # Phase 4 routers
    app.include_router(alerts_router)
    app.include_router(webhooks_router)
    app.include_router(metrics_router)
    app.include_router(admin_router)
    # Phase 5 routers
    app.include_router(auth_router)

    # ── Phase 5: Distributed Tracing ──
    setup_tracing(app)

    return app


# Application instance used by `uvicorn app.main:app`
app = create_app()
