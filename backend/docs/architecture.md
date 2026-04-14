# Architecture Overview — Phase 1: Foundation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                                                             │
│  ┌──────────┐  ┌────────────┐  ┌───────────────────────┐   │
│  │  CORS    │→ │ Correlation│→ │  API Router           │   │
│  │Middleware│  │ Middleware  │  │  /api/v1/health       │   │
│  └──────────┘  └────────────┘  │  /api/v1/health/deps  │   │
│                                └───────────────────────┘   │
│                                          │                  │
│                                          ▼                  │
│                                ┌──────────────────┐         │
│                                │  HealthService   │         │
│                                │  (cached, 10s)   │         │
│                                └──────────────────┘         │
│                                   │    │    │               │
│                              ┌────┘    │    └────┐          │
│                              ▼         ▼         ▼          │
│                          MongoDB    Ollama    Gemini         │
│                          (Motor)    (HTTP)    (HTTP)         │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

### `app/core/` — Cross-Cutting Concerns

| Module | Purpose |
|--------|---------|
| `config.py` | Pydantic `BaseSettings` for type-safe environment config |
| `logging.py` | `structlog` setup: JSON in production, console in development |
| `middleware.py` | Request correlation ID injection and request lifecycle logging |

### `app/db/` — Data Access Layer

| Module | Purpose |
|--------|---------|
| `client.py` | `AsyncMongoClient` wrapper over Motor with connection pooling |

**Migration Path:** Motor is deprecated (removal May 2026). The abstraction in `client.py` isolates all Motor-specific code. When migrating to PyMongo async, only `client.py` needs changes — no dependent code breaks.

### `app/api/v1/` — HTTP API Layer

| Module | Purpose |
|--------|---------|
| `routes_health.py` | Liveness probe (`/health`) and dependency checks (`/health/dependencies`) |

### `app/services/` — Business Logic

| Module | Purpose |
|--------|---------|
| `health_service.py` | Dependency health probing with TTL-based caching |

### `app/models/` — Domain Models (Phase 2)

Reserved for Pydantic domain schemas (Patient, MedicalRecord, Alert).

---

## Configuration Flow

```
.env file
   │
   ▼
Pydantic BaseSettings (core/config.py)
   │
   ├─→ Settings validated at import time
   ├─→ lru_cache singleton via get_settings()
   │
   ▼
Used by: main.py, db/client.py, services/health_service.py
```

**Required variables:**
- `GEMINI_API_KEY` — Cloud LLM authentication
- `MONGODB_URI` — Database connection string

**Optional with defaults:**
- `APP_ENV` (development), `LOG_LEVEL` (INFO), `MONGODB_DB_NAME` (ai_medical)
- `OLLAMA_BASE_URL` (http://localhost:11434), `OLLAMA_MODEL` (medgemma:4b)

---

## Logging Architecture

```
Application Code
   │
   ├─ structlog.get_logger() → BoundLogger
   │     │
   │     ▼
   │  Context Vars (request_id, method, path)
   │     │
   │     ▼
   │  Processors: timestamps, log level, unicode
   │     │
   │     ▼
   │  Renderer: JSON (prod) / Console (dev)
   │     │
   │     ▼
   │  stdlib logging → stdout
   │
   └─ Third-party loggers (uvicorn, motor) → WARNING+
```

---

## Application Lifecycle

```
uvicorn starts
   │
   ▼
create_app()
   ├─ Load settings (validated)
   ├─ Create FastAPI instance
   ├─ Add middleware (CORS → Correlation)
   └─ Register routers
   │
   ▼
lifespan() startup
   ├─ Initialize structured logging
   ├─ Connect to MongoDB (graceful failure)
   ├─ Create HealthService
   └─ Store on app.state
   │
   ▼
Serving requests...
   │
   ▼
lifespan() shutdown
   ├─ Disconnect MongoDB
   └─ Log shutdown
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **structlog** | JSON-native structured logging, context variable binding, async-safe |
| **Motor with abstraction** | Current async driver; wrapper enables seamless PyMongo async migration |
| **Pydantic BaseSettings** | Type-safe config, `.env` loading, fail-fast validation |
| **Health check caching** | 10s TTL prevents probe storms from overwhelming external services |
| **Lifespan context manager** | Modern FastAPI pattern (replaces deprecated on_event) |
| **Request correlation IDs** | Essential for distributed tracing; propagated via X-Request-ID header |
