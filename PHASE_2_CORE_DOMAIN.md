---
title: "Phase 2: Core Domain + API"
phase: 2
duration: "Weeks 3-4"
dependencies: ["PHASE_1_FOUNDATION.md"]
tags: ["data-models", "crud", "validation", "repositories"]
---

# Phase 2: Core Domain + API

## Phase Overview

**Duration:** Weeks 3-4  
**Objective:** Implement core domain models, data persistence layer, and CRUD API endpoints  
**Entry Criteria:** Phase 1 complete; FastAPI app bootstrapped with config and health checks  
**Exit Criteria:** All CRUD endpoints functional; data persists correctly; validation enforced; audit logging active

---

## Goals

- ✓ Define and validate core domain models (Patient, MedicalRecord, Alert)
- ✓ Implement repository pattern for clean data access abstraction
- ✓ Build CRUD endpoints for patient and record management
- ✓ Enforce schema validation at API boundary
- ✓ Add audit logging hooks for PHI access tracking
- ✓ Implement idempotency keys for critical writes

---

## Deliverables

### D2.1: Domain Models
**Description:** Pydantic models and MongoDB schemas for core entities  
**Acceptance Criteria:**
- [ ] `models/patient.py`: Patient model with id, name, dob, sex, conditions, medications, allergies, timestamps
- [ ] `models/medical_record.py`: MedicalRecord model with patient_id, symptoms, entities, analysis_result, risk_level, timestamps
- [ ] `models/alert.py`: Alert model with patient_id, severity, trigger, channels, status, delivery_receipts, timestamps
- [ ] `models/trace.py`: ReasoningTrace model with task_type, instructions, allowed_data_classes, origin, expires_at, timestamps
- [ ] All models validated with Pydantic; type hints complete
- [ ] MongoDB ObjectId serialization handled correctly
- [ ] Request/Response schemas separated from DB schemas

**Artifacts:**
- `backend/app/models/patient.py`
- `backend/app/models/medical_record.py`
- `backend/app/models/alert.py`
- `backend/app/models/trace.py`
- Schema documentation (types, constraints, examples)

---

### D2.2: Repository Pattern
**Description:** Data access layer for clean separation of concerns  
**Acceptance Criteria:**
- [ ] `db/repositories/patient_repository.py` implements PatientRepository interface
- [ ] `db/repositories/medical_record_repository.py` implements RecordRepository interface
- [ ] `db/repositories/alert_repository.py` implements AlertRepository interface
- [ ] All CRUD operations async: `create()`, `read()`, `update()`, `delete()`, `list()`
- [ ] Repositories use dependency injection (FastAPI Depends)
- [ ] Error handling returns meaningful exceptions (NotFound, ValidationError, etc.)
- [ ] Query filtering and pagination support

**Artifacts:**
- `backend/app/db/repositories/__init__.py` (base interfaces)
- `backend/app/db/repositories/patient_repository.py`
- `backend/app/db/repositories/medical_record_repository.py`
- `backend/app/db/repositories/alert_repository.py`
- Type hints and docstrings for all methods

---

### D2.3: Patient CRUD API
**Description:** RESTful endpoints for patient management  
**Acceptance Criteria:**
- [ ] `POST /api/v1/patients` - Create patient (returns 201, returns created patient)
- [ ] `GET /api/v1/patients/{id}` - Retrieve patient by ID (returns 200 or 404)
- [ ] `GET /api/v1/patients` - List all patients (paginated, queryable)
- [ ] `PUT /api/v1/patients/{id}` - Update patient (returns 200 or 404)
- [ ] `DELETE /api/v1/patients/{id}` - Delete patient (returns 204 or 404)
- [ ] Request validation: name required, dob valid date, etc.
- [ ] Response sanitization: no MongoDB internal fields exposed
- [ ] Idempotency key support for POST/PUT (via header)

**Artifacts:**
- `backend/app/api/v1/routes_patients.py`
- Request/response schemas with OpenAPI examples
- Unit tests for all endpoints

---

### D2.4: Medical Record API
**Description:** Endpoints for symptom submissions and analysis storage  
**Acceptance Criteria:**
- [ ] `POST /api/v1/records` - Create medical record for patient
- [ ] `GET /api/v1/records/{id}` - Retrieve record
- [ ] `GET /api/v1/patients/{patient_id}/records` - List records by patient (paginated)
- [ ] `PUT /api/v1/records/{id}` - Update record (e.g., add analysis_result)
- [ ] All endpoints validate patient_id exists before operating
- [ ] Timestamps (created_at, updated_at) managed automatically
- [ ] Risk level validation: enum (low, medium, high, critical)

**Artifacts:**
- `backend/app/api/v1/routes_analysis.py` (record endpoints)
- Request/response schemas with examples
- Validation error handling

---

### D2.5: Audit Logging
**Description:** PHI access tracking for compliance  
**Acceptance Criteria:**
- [ ] Middleware logs all GET requests to `/patients/**` and `/records/**` endpoints
- [ ] Log includes: user_id, action (read/write), resource_type, resource_id, timestamp, request_id
- [ ] Audit logs stored in separate MongoDB collection
- [ ] Audit logs prevent accidental deletion (immutable design)
- [ ] Log sanitization: no request bodies with PHI written to logs
- [ ] Query for audit trail by patient_id or user_id

**Artifacts:**
- `core/audit.py` (audit logging middleware)
- `models/audit_log.py` (audit log schema)
- `db/repositories/audit_repository.py` (audit log queries)
- Endpoint: `GET /api/v1/audit/patient/{patient_id}` (for compliance review)

---

### D2.6: Input Validation
**Description:** Enforce data constraints and prevent invalid state  
**Acceptance Criteria:**
- [ ] Patient name not empty; max 255 chars
- [ ] Date of birth is valid date in ISO 8601 format
- [ ] Medical conditions must be known enum values (optional: implement taxonomy)
- [ ] Medication names validated against known list (optional: FDA RxNorm)
- [ ] Symptoms field is non-empty text
- [ ] Risk level enum: low/medium/high/critical only
- [ ] Severity for alerts: warning/error/critical only
- [ ] Return HTTP 422 Unprocessable Entity with field-level error details

**Artifacts:**
- Pydantic field validators in models
- Custom error response schema for validation failures
- Documentation of all field constraints

---

### D2.7: Testing Suite
**Description:** Unit and integration tests for data layer  
**Acceptance Criteria:**
- [ ] Unit tests: model validation (valid/invalid inputs)
- [ ] Integration tests: CRUD operations with real MongoDB (test DB)
- [ ] Test fixtures: sample patients, records, alerts
- [ ] Test coverage ≥85% for `db/` and `models/` modules
- [ ] Tests verify idempotency (same input → same output)
- [ ] Tests verify permission boundaries (isolation)

**Artifacts:**
- `backend/tests/unit/test_models.py`
- `backend/tests/integration/test_patient_repository.py`
- `backend/tests/integration/test_api_patients.py`
- `backend/tests/conftest.py` (pytest fixtures)

---

## Implementation Sequence

1. **Week 3 - Days 1-2:** Domain Models
   - Define Pydantic models for Patient, MedicalRecord, Alert, ReasoningTrace
   - Add validation rules and field constraints
   - Create example data

2. **Week 3 - Days 3-4:** Repositories
   - Implement repository interfaces and base class
   - Implement PatientRepository, RecordRepository, AlertRepository
   - Add error handling and async operations

3. **Week 3 - Day 5:** Patient CRUD API
   - Create routes_patients.py with all CRUD endpoints
   - Add request/response schemas
   - Integrate repository layer

4. **Week 4 - Day 1:** Medical Record API
   - Create routes_analysis.py with record endpoints
   - Implement patient_id validation

5. **Week 4 - Day 2:** Audit Logging
   - Implement audit middleware
   - Create audit log schema and repository
   - Add audit query endpoint

6. **Week 4 - Days 3-5:** Testing & Documentation
   - Write comprehensive test suites
   - Achieve coverage targets
   - Document schemas and API contract

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Pydantic models** | Type-safe validation; auto-generated OpenAPI docs |
| **Repository pattern** | Decouples business logic from data access; testable |
| **Separate request/response schemas** | Frontend doesn't need internal fields (id, timestamps) |
| **Audit via middleware** | Centralized, captures all access patterns |
| **Idempotency keys** | Prevents duplicate processing in retry scenarios |

---

## Data Model Examples

### Patient
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "John Doe",
  "dob": "1985-03-15",
  "sex": "M",
  "conditions": ["diabetes", "hypertension"],
  "medications": ["metformin", "lisinopril"],
  "allergies": ["penicillin"],
  "created_at": "2026-03-01T10:00:00Z",
  "updated_at": "2026-03-01T10:00:00Z"
}
```

### MedicalRecord
```json
{
  "id": "507f1f77bcf86cd799439012",
  "patient_id": "507f1f77bcf86cd799439011",
  "symptoms": "Chest pain, shortness of breath",
  "entities": {"symptom1": "chest pain", "severity": "high"},
  "analysis_result": "Possible cardiac issue; recommend EKG",
  "risk_level": "high",
  "created_at": "2026-03-01T11:00:00Z",
  "updated_at": "2026-03-01T11:30:00Z"
}
```

---

## Exit Criteria Checklist

- [ ] All 5 domain models defined and validated
- [ ] Repository pattern implemented for 3 entities
- [ ] Patient CRUD: 5 endpoints functional (POST, GET, PUT, DELETE, LIST)
- [ ] Medical Record API: 4 endpoints functional
- [ ] Audit logging captures all PHI access
- [ ] Input validation enforced; 422 responses for invalid data
- [ ] Idempotency keys prevent duplicate operations
- [ ] Test coverage ≥85% for db/ and models/
- [ ] All tests pass locally and in CI
- [ ] OpenAPI docs (`/docs`) shows all endpoints with examples

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| N+1 queries | Performance degradation | Repository handles eager loading; add indexes on patient_id |
| Schema migration | Data loss | Keep snapshots; test migrations on test DB first |
| Audit log bloat | Storage cost | Implement retention policy; archive old logs |
| Validation too strict | UX friction | Allow optional fields; provide clear error messages |

---

## Next Phase

Upon completion of Phase 2, proceed to **[Phase 3: Agent Pipeline](PHASE_3_AGENT_PIPELINE.md)** to implement hybrid cloud/local workflow orchestration.

---

## Document Metadata

- **Created:** 2026-04-14
- **Depends On:** Phase 1 (Foundation)
- **Review Date:** Start of Phase 3
