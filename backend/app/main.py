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
- Global error handlers
- Structured logging initialization
- Database client lifecycle management
- MongoDB index creation on startup
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.error_handlers import register_error_handlers
from app.api.v1.routes_audit import router as audit_router
from app.api.v1.routes_health import router as health_router
from app.api.v1.routes_patients import router as patients_router
from app.api.v1.routes_records import router as records_router
from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestCorrelationMiddleware
from app.db.client import AsyncMongoClient
from app.services.health_service import HealthService

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

        await logger.ainfo("mongodb_indexes_created")
    except Exception:
        await logger.awarning("mongodb_index_creation_failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Startup: initializes logging, connects to MongoDB, creates services and indexes.
    Shutdown: gracefully disconnects from MongoDB.
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

    await logger.ainfo("app_started")

    yield

    # ── Shutdown ──
    await logger.ainfo("app_shutting_down")
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

    return app


# Application instance used by `uvicorn app.main:app`
app = create_app()
