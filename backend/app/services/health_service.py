"""
Health check service for verifying external dependency connectivity.

Checks MongoDB, Ollama, and Gemini API status with latency measurement.
Results are cached with a configurable TTL to avoid excessive calls.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
import structlog

from app.core.config import Settings
from app.db.client import AsyncMongoClient

logger = structlog.get_logger(__name__)

# Cache TTL in seconds
_CACHE_TTL_SECONDS = 10.0


class DependencyStatus(str, Enum):
    """Status of an individual dependency."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class DependencyCheck:
    """Result of a single dependency health check."""
    name: str
    status: DependencyStatus
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
        }
        if self.details:
            result["details"] = self.details
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class HealthCheckResult:
    """Aggregated health check result for all dependencies."""
    status: str  # "ok" | "degraded" | "unhealthy"
    dependencies: list[DependencyCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "status": self.status,
            "dependencies": [d.to_dict() for d in self.dependencies],
        }


class HealthService:
    """Service for checking application dependency health.

    Caches results for _CACHE_TTL_SECONDS to avoid hammering external services
    during health probe storms (e.g., Kubernetes liveness probes).
    """

    def __init__(self, settings: Settings, db_client: AsyncMongoClient) -> None:
        self._settings = settings
        self._db_client = db_client
        self._cache: HealthCheckResult | None = None
        self._cache_timestamp: float = 0.0

    async def check_all(self) -> HealthCheckResult:
        """Run all dependency checks, returning cached result if fresh.

        Returns:
            HealthCheckResult with aggregated status and per-dependency details.
        """
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_timestamp) < _CACHE_TTL_SECONDS:
            return self._cache

        checks = await self._run_all_checks()
        result = self._aggregate(checks)

        self._cache = result
        self._cache_timestamp = now
        return result

    async def _run_all_checks(self) -> list[DependencyCheck]:
        """Execute all individual dependency checks."""
        checks: list[DependencyCheck] = []

        checks.append(await self._check_mongodb())
        checks.append(await self._check_ollama())
        checks.append(await self._check_gemini())

        return checks

    async def _check_mongodb(self) -> DependencyCheck:
        """Check MongoDB connectivity by issuing a ping command."""
        start = time.perf_counter()
        try:
            result = await self._db_client.ping()
            latency = (time.perf_counter() - start) * 1000
            return DependencyCheck(
                name="mongodb",
                status=DependencyStatus.HEALTHY,
                latency_ms=latency,
                details={"ping": result.get("ok", 0)},
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            await logger.awarning("health_check_mongodb_failed", error=str(exc))
            return DependencyCheck(
                name="mongodb",
                status=DependencyStatus.UNHEALTHY,
                latency_ms=latency,
                error=str(exc),
            )

    async def _check_ollama(self) -> DependencyCheck:
        """Check Ollama API connectivity and model availability."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._settings.OLLAMA_BASE_URL}/api/tags")
            latency = (time.perf_counter() - start) * 1000

            if resp.status_code != 200:
                return DependencyCheck(
                    name="ollama",
                    status=DependencyStatus.UNHEALTHY,
                    latency_ms=latency,
                    error=f"HTTP {resp.status_code}",
                )

            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            model_available = any(
                self._settings.OLLAMA_MODEL in m for m in models
            )

            return DependencyCheck(
                name="ollama",
                status=DependencyStatus.HEALTHY if model_available else DependencyStatus.DEGRADED,
                latency_ms=latency,
                details={
                    "model_requested": self._settings.OLLAMA_MODEL,
                    "model_available": model_available,
                    "models_found": len(models),
                },
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            await logger.awarning("health_check_ollama_failed", error=str(exc))
            return DependencyCheck(
                name="ollama",
                status=DependencyStatus.UNHEALTHY,
                latency_ms=latency,
                error=str(exc),
            )

    async def _check_gemini(self) -> DependencyCheck:
        """Check Gemini API connectivity by listing models.

        Uses a lightweight models.list call to verify API key validity
        without consuming generation quota.
        """
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": self._settings.GEMINI_API_KEY},
                )
            latency = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                return DependencyCheck(
                    name="gemini",
                    status=DependencyStatus.HEALTHY,
                    latency_ms=latency,
                    details={"authenticated": True},
                )
            elif resp.status_code == 403:
                return DependencyCheck(
                    name="gemini",
                    status=DependencyStatus.UNHEALTHY,
                    latency_ms=latency,
                    error="Invalid API key or insufficient permissions",
                )
            else:
                return DependencyCheck(
                    name="gemini",
                    status=DependencyStatus.DEGRADED,
                    latency_ms=latency,
                    error=f"HTTP {resp.status_code}",
                )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            await logger.awarning("health_check_gemini_failed", error=str(exc))
            return DependencyCheck(
                name="gemini",
                status=DependencyStatus.UNHEALTHY,
                latency_ms=latency,
                error=str(exc),
            )

    @staticmethod
    def _aggregate(checks: list[DependencyCheck]) -> HealthCheckResult:
        """Determine overall status from individual dependency checks.

        - All healthy → "ok"
        - Any unhealthy → "unhealthy"
        - Otherwise → "degraded"
        """
        statuses = {c.status for c in checks}
        if statuses == {DependencyStatus.HEALTHY}:
            overall = "ok"
        elif DependencyStatus.UNHEALTHY in statuses:
            overall = "unhealthy"
        else:
            overall = "degraded"

        return HealthCheckResult(status=overall, dependencies=checks)
