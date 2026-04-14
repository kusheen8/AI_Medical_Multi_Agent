"""
AI Medical Multi-Agent Backend — FastAPI Application Entry Point.

Bootstraps the application with:
- Lifespan context manager for startup/shutdown hooks
- CORS middleware
- Request correlation middleware
- Health check route registration
- Structured logging initialization
- Database client lifecycle management
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes_health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestCorrelationMiddleware
from app.db.client import AsyncMongoClient
from app.services.health_service import HealthService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Startup: initializes logging, connects to MongoDB, creates services.
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

    # ── Middleware ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production (Phase 5)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestCorrelationMiddleware)

    # ── Routes ──
    app.include_router(health_router)

    return app


# Application instance used by `uvicorn app.main:app`
app = create_app()
