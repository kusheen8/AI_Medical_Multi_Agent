---
title: "Phase 3: Hybrid Agent Pipeline"
phase: 3
duration: "Weeks 5-6"
dependencies: ["PHASE_1_FOUNDATION.md", "PHASE_2_CORE_DOMAIN.md"]
tags: ["orchestration", "cloud-llm", "local-llm", "queue", "privacy"]
---

# Phase 3: Hybrid Agent Pipeline

## Phase Overview

**Duration:** Weeks 5-6  
**Objective:** Implement the core hybrid pipeline—Cloud LLM reasoning + Local LLM execution against PHI  
**Entry Criteria:** Phase 2 complete; Patient/Record CRUD endpoints working; Audit logging active  
**Exit Criteria:** End-to-end symptom analysis works; no raw PHI in cloud logs; async queue executes tasks reliably

---

## Goals

- ✓ Implement Cloud Coordinator Reasoning Trace generation (Gemini, non-PHI only)
- ✓ Implement Local Medical Analyzer execution (Ollama + MedGemma, against PHI)
- ✓ Implement Local History Summarizer execution (Ollama + MedGemma, longitudinal analysis)
- ✓ Build internal async queue for task decoupling
- ✓ Implement worker processes for task execution
- ✓ Enforce PHI boundary: no sensitive data to cloud, all PHI processing local
- ✓ Add response sanitization before cloud transmission

---

## Deliverables

### D3.1: Cloud Coordinator Service
**Description:** Gemini-based reasoning trace generation (non-sensitive only)  
**Acceptance Criteria:**
- [ ] `services/coordinator/gemini_coordinator.py` implements coordinator interface
- [ ] Accepts: task_type (symptom_analysis, history_summarization), de-identified context, intent
- [ ] Returns: ReasoningTrace with instructions, allowed_data_classes, expires_at
- [ ] Enforces: no raw PHI in prompts; only metadata (age, conditions enum, risk tier)
- [ ] Error handling: timeout (5s), rate limiting, retry logic
- [ ] Uses `google-genai` SDK (not deprecated packages)
- [ ] Prompts stored in version-controlled prompt library
- [ ] Supports prompt caching for repeated patterns

**Artifacts:**
- `backend/app/services/coordinator/gemini_coordinator.py`
- `backend/app/services/coordinator/prompts.py` (prompt templates)
- Type hints and interface contract
- Unit tests with mocked Gemini responses

---

### D3.2: Reasoning Trace Storage
**Description:** Schema and repository for trace management  
**Acceptance Criteria:**
- [ ] ReasoningTrace model in `models/trace.py` with all required fields
- [ ] `db/repositories/trace_repository.py` implements CRUD + expiration management
- [ ] Traces stored in MongoDB with TTL index (auto-delete after expires_at)
- [ ] Traces are immutable once created (audit trail)
- [ ] Query traces by task_id, patient_id, status
- [ ] Serialize traces to JSON for queue messages

**Artifacts:**
- `backend/app/models/trace.py` (complete definition)
- `backend/app/db/repositories/trace_repository.py`
- TTL index configuration in database initialization

---

### D3.3: Local Medical Analyzer
**Description:** Ollama + MedGemma execution engine for symptom analysis  
**Acceptance Criteria:**
- [ ] `services/local_agents/medical_analyzer.py` implements execution interface
- [ ] Input: ReasoningTrace, MedicalRecord with symptoms, Patient context
- [ ] Process:
  1. Fetch PHI-complete patient data from DB (local only)
  2. Execute trace instructions against symptoms and history
  3. Invoke MedGemma via Ollama for clinical analysis
  4. Parse structured output (entities, risk_level, recommendations)
- [ ] Output: AnalysisResult with structured clinical insights
- [ ] Error handling: model unavailability, malformed output, timeouts (30s max)
- [ ] Logging: trace execution steps, model latency, token usage

**Artifacts:**
- `backend/app/services/local_agents/medical_analyzer.py`
- `backend/app/services/local_agents/ollama_client.py` (wrapper)
- Output schema definition
- Prompt templates for MedGemma

---

### D3.4: Local History Summarizer
**Description:** Ollama + MedGemma for longitudinal trend analysis  
**Acceptance Criteria:**
- [ ] `services/local_agents/history_summarizer.py` implements summarization interface
- [ ] Input: Patient ID, date range, ReasoningTrace
- [ ] Process:
  1. Query historical records for patient (local DB)
  2. Aggregate temporal pattern (trends in symptoms, risk over time)
  3. Execute trace instructions to generate summary narrative
  4. Invoke MedGemma for clinical interpretation
- [ ] Output: TimelineSummary with key events, patterns, clinical context
- [ ] Error handling: insufficient data, model errors, timeouts
- [ ] Performance: handle 6-12 months of records efficiently (pagination)

**Artifacts:**
- `backend/app/services/local_agents/history_summarizer.py`
- Query optimization for longitudinal data
- Sample output examples

---

### D3.5: Internal Async Queue
**Description:** Decoupling API latency from model execution latency  
**Acceptance Criteria:**
- [ ] `services/queue/task_queue.py` implements async queue interface
- [ ] Task schema: task_id, task_type, payload (trace + patient context), status, created_at, expires_at
- [ ] Queue operations: enqueue(), dequeue(), mark_done(), mark_failed()
- [ ] In-memory queue (Phase 3); upgrade path to Celery/RabbitMQ documented
- [ ] Dead-letter queue for failed tasks (max retries: 3)
- [ ] Priority support: urgent tasks (alerts) processed first
- [ ] Task persistence: save to MongoDB for durability and replay

**Artifacts:**
- `backend/app/services/queue/task_queue.py`
- `backend/app/services/queue/task_schema.py`
- Task lifecycle documentation

---

### D3.6: Worker Processes
**Description:** Background task executors  
**Acceptance Criteria:**
- [ ] `workers/analysis_worker.py` polls queue for analysis tasks
  - Dequeues task
  - Fetches trace and patient context
  - Invokes medical analyzers
  - Stores result in MedicalRecord
  - Updates task status (done/failed)
- [ ] `workers/summarization_worker.py` for history summarization tasks
- [ ] Worker concurrency: 2-4 workers (configurable)
- [ ] Error handling: retry logic, exponential backoff, DLQ
- [ ] Graceful shutdown: complete in-flight tasks before terminating
- [ ] Observability: worker logs include task_id, latency, outcome

**Artifacts:**
- `backend/app/workers/analysis_worker.py`
- `backend/app/workers/summarization_worker.py`
- Worker pool management in `main.py`
- Startup/shutdown hooks

---

### D3.7: Symptom Analysis API Endpoint
**Description:** Public-facing symptom analysis trigger  
**Acceptance Criteria:**
- [ ] `POST /api/v1/analyze/symptoms` accepts patient_id and symptoms text
- [ ] Request validation: patient exists, symptoms non-empty
- [ ] Response (P95 latency ≤1.5s):
  - Returns task_id immediately (202 Accepted)
  - Task execution happens async in background
- [ ] Polling endpoint: `GET /api/v1/analysis/{task_id}` returns current status
- [ ] Status: queued, processing, completed (with result), failed (with error)
- [ ] Privacy enforcement: Coordinator receives de-identified context only

**Artifacts:**
- `backend/app/api/v1/routes_analysis.py` (updated with analysis endpoints)
- Request/response schemas with examples
- Integration tests end-to-end

---

### D3.8: History Summarization API Endpoint
**Description:** Public-facing longitudinal analysis trigger  
**Acceptance Criteria:**
- [ ] `POST /api/v1/analyze/history` accepts patient_id, date_range
- [ ] Response (202 Accepted): returns task_id
- [ ] Polling: `GET /api/v1/analysis/{task_id}` for status
- [ ] Privacy enforcement: same PHI boundary as symptom analysis

**Artifacts:**
- `backend/app/api/v1/routes_analysis.py` (endpoints)
- Request/response schemas

---

### D3.9: PHI Boundary Enforcement
**Description:** Middleware and validators to prevent PHI leakage  
**Acceptance Criteria:**
- [ ] `core/privacy.py` implements privacy middleware
- [ ] Before cloud API calls: scan request payload, redact any known PHI patterns
- [ ] Detector for: names, identifiers, specific medical entity values
- [ ] Block calls that would send raw PHI; log and alert
- [ ] Response sanitization: strip PHI before returning to frontend (if needed)
- [ ] Unit tests: verify redaction on realistic examples
- [ ] Privacy policy documentation (what is redacted, why)

**Artifacts:**
- `backend/app/core/privacy.py` (middleware + validators)
- `backend/app/services/privacy_filter.py` (redaction logic)
- Privacy tests: test_privacy_redaction.py

---

### D3.10: End-to-End Integration Tests
**Description:** Verify hybrid flow with real services  
**Acceptance Criteria:**
- [ ] Test setup: real MongoDB, Ollama running, Gemini API key available
- [ ] Test flow: POST symptom → coordinator generates trace → analyzer executes → result stored
- [ ] Assertions:
  - No raw PHI in Gemini request logs
  - Analysis result populated correctly
  - Task completed successfully
  - Audit trail captured
- [ ] Performance assertions: total flow < 15s (with model latency)
- [ ] Error cases: Ollama down, Gemini timeout, patient not found

**Artifacts:**
- `backend/tests/integration/test_hybrid_pipeline.py`
- Test data fixtures (sample patients, traces)
- Test documentation

---

## Implementation Sequence

1. **Week 5 - Days 1-2:** Cloud Coordinator
   - Implement Gemini coordinator with de-identification
   - Create prompt templates
   - Add unit tests with mocked Gemini

2. **Week 5 - Days 3-4:** Local Agents
   - Implement medical analyzer (Ollama integration)
   - Implement history summarizer
   - Add Ollama client wrapper

3. **Week 5 - Day 5:** Queue + Workers
   - Build async task queue
   - Implement analysis and summarization workers
   - Add queue lifecycle management to FastAPI app

4. **Week 6 - Days 1-2:** API Endpoints
   - Add `/analyze/symptoms` and `/analyze/history` endpoints
   - Implement task polling endpoint
   - Add request validation

5. **Week 6 - Day 3:** PHI Boundary
   - Implement privacy middleware
   - Add redaction logic and privacy tests
   - Verify no PHI in cloud requests

6. **Week 6 - Days 4-5:** Integration & Testing
   - Write end-to-end tests
   - Run full flow with real services
   - Document setup and troubleshooting

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Two-stage hybrid** | Outsource reasoning, keep PHI local for compliance and performance |
| **Async queue** | Decouple API response time from model latency; enable retries |
| **ReasoningTrace as executable spec** | Coordinator generates deterministic instructions; local execution is predictable |
| **In-memory queue (Phase 3)** | Simple, fast; upgrade to Celery later if needed for multi-server setup |
| **Worker pool** | Concurrency without threading complexity; async I/O native |
| **Privacy middleware** | Centralized enforcement; prevents accidental leakage |

---

## Data Flows

### Symptom Analysis Flow
```
1. Frontend POST /analyze/symptoms { patient_id, symptoms }
2. API enqueues task with de-identified context
3. Coordinator generates ReasoningTrace (no PHI)
4. Worker dequeues task
5. Analyzer fetches PHI (local)
6. MedGemma processes trace against PHI
7. Result stored in DB
8. Frontend polls GET /analysis/{task_id} → returns result
```

### History Summarization Flow
```
1. Frontend POST /analyze/history { patient_id, date_range }
2. API enqueues task
3. Coordinator generates summarization trace
4. Worker dequeues
5. Summarizer fetches historical records (local)
6. MedGemma generates timeline + insights
7. Result stored
8. Frontend retrieves via polling
```

---

## Exit Criteria Checklist

- [ ] Cloud Coordinator generates ReasoningTraces without PHI in requests
- [ ] Medical Analyzer executes traces against local PHI correctly
- [ ] History Summarizer handles longitudinal analysis
- [ ] Async queue persists tasks; handles retries
- [ ] Workers execute tasks end-to-end reliably
- [ ] `/analyze/symptoms` endpoint works (202 accepted, async execution)
- [ ] `/analyze/history` endpoint works
- [ ] Task polling endpoint returns status correctly
- [ ] Privacy middleware blocks/redacts any attempted PHI in cloud requests
- [ ] End-to-end test passes: no raw PHI in logs, analysis correct
- [ ] All audit logs capture trace execution and PHI access

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Ollama unavailability** | Analysis fails | Health check; graceful error response; retry queue |
| **Gemini rate limit** | API throttling | Batch requests; cache traces; backoff strategy |
| **Task loss on crash** | Incomplete analyses | Persist queue to DB; implement recovery on startup |
| **PHI redaction bugs** | Privacy breach | Red-team tests; strict validation; logging audits |
| **Model latency > SLA** | Poor UX | Async queue handles this; monitor latency, optimize prompts |

---

## Performance Targets

| Metric | Target|
|--------|--------|
| API response time (task acceptance) | ≤ 500ms |
| Medical analyzer latency (cloud trace gen + local execution) | 5-15s |
| History summarizer latency | 10-20s |
| Queue task throughput | ≥5 tasks/second |
| Worker error recovery | < 30s retry |

---

## Next Phase

Upon completion of Phase 3, proceed to **[Phase 4: Alerts & Reliability](PHASE_4_ALERTS_RELIABILITY.md)** to add notification system and resilience patterns.

---

## Document Metadata

- **Created:** 2026-04-14
- **Depends On:** Phase 1, Phase 2
- **Core Principle:** Hybrid cloud/local processing; PHI remains local
- **Review Date:** Start of Phase 4
