---
name: phase-plan-execution
description: "Use when: implementing backend features, planning work iterations, structuring deliverables, checking phase dependencies, understanding exit criteria, following modular phases for the AI Medical Multi-Agent backend"
applyTo: "backend/**"
---

# Phase Plan Execution Guide for AI Agents

## 🎯 Purpose

This guide ensures AI agents correctly discover, reference, and execute work using the modular phase plan for the AI Medical Multi-Agent backend implementation.

---

## 📚 Phase Plan Document Discovery

### Primary Hub
- **[PHASE_INDEX.md](../PHASE_INDEX.md)** — Start here for overview, dependencies, and roadmap
- Contains the authoritative phase structure, cross-phase data/service layer dependencies
- Reference this first to understand phase relationships

### Individual Phase Documents (Sequential)
| Phase | File | Status |
|-------|------|--------|
| 1: Foundation | `PHASE_1_FOUNDATION.md` | Weeks 1-2 |
| 2: Core Domain | `PHASE_2_CORE_DOMAIN.md` | Weeks 3-4 |
| 3: Agent Pipeline | `PHASE_3_AGENT_PIPELINE.md` | Weeks 5-6 |
| 4: Alerts & Reliability | `PHASE_4_ALERTS_RELIABILITY.md` | Week 7 |
| 5: Hardening & Compliance | `PHASE_5_HARDENING_COMPLIANCE.md` | Week 8 |

### Quick Reference
- **[QUICK_REFERENCE.md](../QUICK_REFERENCE.md)** — One-page summary, timeline, metrics, checklists

---

## 🔄 When to Reference Each Phase

### Phase 1 (Foundation)
**Reference when:**
- Setting up FastAPI application structure
- Configuring environment variables and settings
- Implementing logging infrastructure
- Creating database client abstraction
- Setting up health check endpoints
- Configuring CI/CD pipeline

**Key deliverables to track:**
- D1.1: Project Scaffolding
- D1.2: Configuration Management
- D1.3: Structured Logging
- D1.4: Database Client Abstraction
- D1.5: Health Check Endpoints
- D1.6: CI/CD Pipeline

**Do NOT proceed to Phase 2 until:** Service starts, config validates, health endpoints pass

---

### Phase 2 (Core Domain)
**Reference when:**
- Defining Pydantic models for entities (Patient, MedicalRecord, Alert)
- Implementing repository pattern for data access
- Building CRUD API endpoints
- Adding input validation rules
- Implementing audit logging for PHI access
- Writing unit/integration tests for data layer

**Key deliverables to track:**
- D2.1: Domain Models (4 entities)
- D2.2: Repository Pattern (3 repositories)
- D2.3: Patient CRUD API (5 endpoints)
- D2.4: Medical Record API (4 endpoints)
- D2.5: Audit Logging
- D2.6: Input Validation
- D2.7: Testing Suite

**Depends on:** Phase 1 complete (FastAPI app, config, logging, DB client)

**Do NOT proceed to Phase 3 until:** All CRUD endpoints work, data persists, audit logs active

---

### Phase 3 (Agent Pipeline)
**Reference when:**
- Building Gemini-based Coordinator for Reasoning Trace generation
- Implementing local Ollama + MedGemma analyzers
- Creating async task queue for decoupling
- Building worker processes for background execution
- Enforcing PHI boundaries (no sensitive data to cloud)
- Writing end-to-end integration tests

**Key deliverables to track:**
- D3.1: Cloud Coordinator Service
- D3.2: Reasoning Trace Storage
- D3.3: Local Medical Analyzer
- D3.4: Local History Summarizer
- D3.5: Internal Async Queue
- D3.6: Worker Processes
- D3.7: Symptom Analysis API Endpoint
- D3.8: History Summarization API Endpoint
- D3.9: PHI Boundary Enforcement (middleware + validators)
- D3.10: End-to-End Integration Tests

**Depends on:** Phase 2 complete (domain models, CRUD, audit logging)

**Critical:** This is where the hybrid pipeline is implemented. PHI boundary enforcement must be verified before leaving this phase.

**Do NOT proceed to Phase 4 until:** End-to-end analysis works, no raw PHI in cloud logs verified, queue is reliable

---

### Phase 4 (Alerts & Reliability)
**Reference when:**
- Implementing risk policy engine for alert triggering
- Building caregiver notification service
- Adding retry logic with exponential backoff
- Implementing circuit breaker pattern for external services
- Handling delivery receipts and webhooks
- Adding idempotency for write operations
- Implementing observability (metrics, structured logging)

**Key deliverables to track:**
- D4.1: Risk Policy Engine
- D4.2: Caregiver Notification Service (SMS/Email/Push)
- D4.3: Alert Management API (6 endpoints)
- D4.4: Delivery Receipt Tracking (webhooks)
- D4.5: Retry Logic & Dead-Letter Queue
- D4.6: Circuit Breaker Pattern
- D4.7: Idempotency for Writes
- D4.8: Observability & Metrics
- D4.9: Reliability Tests (7 scenarios)
- D4.10: Admin/Monitoring Dashboard

**Depends on:** Phase 3 complete (hybrid pipeline functional)

**Do NOT proceed to Phase 5 until:** Alerts dispatch on time, no message loss, reliability tests pass

---

### Phase 5 (Hardening & Compliance)
**Reference when:**
- Implementing JWT/OAuth2 authentication and RBAC
- Configuring encryption at rest and in transit
- Running privacy validation tests (no PHI in cloud)
- Performing penetration testing
- Setting up centralized logging and metrics
- Implementing distributed tracing
- Writing compliance documentation
- Creating runbooks and incident procedures

**Key deliverables to track:**
- D5.1: Authentication & Authorization (AuthN/AuthZ)
- D5.2: Encryption at Rest
- D5.3: Encryption in Transit (HTTPS/TLS)
- D5.4: Privacy Validation Tests
- D5.5: Input Validation & Output Encoding
- D5.6: Centralized Logging
- D5.7: Metrics & Monitoring
- D5.8: Distributed Tracing
- D5.9: Penetration Testing & Security Audit
- D5.10: Performance Profiling & Optimization
- D5.11: Compliance Documentation
- D5.12: Runbooks & Operations
- D5.13: Final Test Suite

**Depends on:** Phase 4 complete (alerts and reliability working)

**Do NOT deploy to production until:** All security/privacy gates pass, compliance audit complete, runbooks tested

---

## How to Structure Work Using Phases

### Step 1: Determine Current Phase
- Check the project timeline (PHASE_INDEX.md)
- Verify all exit criteria from previous phase are met
- Do not skip phases or attempt parallel phase work

### Step 2: Reference Phase Document
- Open the appropriate phase file (e.g., `PHASE_3_AGENT_PIPELINE.md`)
- Read the "Phase Overview" section
- Review "Goals" and "Deliverables"

### Step 3: Understand Dependencies
- Check "Depends On" section
- Review cross-phase dependency matrix (if applicable)
- Verify all data layer and service layer prerequisites are in place

### Step 4: Plan Implementation Sequence
- Follow the "Implementation Sequence" section for day-by-day breakdown
- Each deliverable builds on the previous one
- Estimated effort per deliverable is included

### Step 5: Track Deliverables
- Each deliverable has specific "Acceptance Criteria" (checkboxes)
- Mark criteria as complete `[x]` as work progresses
- When all criteria for all deliverables are met, the phase is complete

### Step 6: Verify Exit Criteria
- Scroll to "Exit Criteria Checklist" section
- All items must be checked ✓ before proceeding to next phase
- Exit criteria are the gate between phases

### Step 7: Move to Next Phase
- Only when exit criteria are fully verified
- Review the next phase's "Depends On" section
- Start fresh with the next phase document

---

##  Architecture Principles (Always Remember)

### Hybrid Cloud/Local Pipeline
- **Cloud (Gemini):** Non-sensitive reasoning only (generates Reasoning Traces)
- **Local (Ollama):** Executes against PHI, no PHI sent to cloud

### Async & Decoupled
- API accepts tasks immediately (202 Accepted)
- Background workers process via queue
- FastAPI async throughout

### Auditable & Compliant
- Every PHI access logged
- Encryption at rest + in transit
- Privacy validation proves no PHI leakage

### Reliable & Resilient
- Retry logic with exponential backoff
- Circuit breaker for cascading failures
- Dead-letter queue for manual recovery

---

## Deliverable Anatomy

Each deliverable follows this structure:

```markdown
### D[Phase].[Number]: Deliverable Name
**Description:** What this delivers  
**Acceptance Criteria:**
- [ ] Specific, measurable criterion 1
- [ ] Specific, measurable criterion 2
- [ ] Testable, verifiable criterion 3

**Artifacts:**
- File paths and descriptions
- Code modules and functions
- Documentation and schemas
```

**When implementing a deliverable:**
1. Read the description (understand the what and why)
2. Review acceptance criteria (know what done means)
3. Check artifacts (know what files to create/modify)
4. Follow implementation sequence for order
5. Mark criteria as complete when verified

---

## ✅ Exit Criteria Pattern

Each phase has an "Exit Criteria Checklist" section with specific, measurable gates:

```markdown
- [ ] Measurable criterion 1 (testable)
- [ ] Measurable criterion 2 (observable)
- [ ] Measurable criterion 3 (verifiable)
```

**All items must be checked before phase is considered complete.**

Example from Phase 3:
```
- [ ] End-to-end test passes: no raw PHI in logs
- [ ] Analysis result populated correctly
- [ ] Task completed successfully
- [ ] Audit trail captured
```

---

## Common Agent Mistakes to Avoid

### ❌ Mistake 1: Skipping Phases
- **Wrong:** "I'll jump to Phase 3 and implement analytics"
- **Right:** "Phase 3 depends on Phase 2 being complete. Let me verify Phase 2 exit criteria first."

### ❌ Mistake 2: Ignoring Dependencies
- **Wrong:** Implementing Phase 3 workers before Phase 2 domain models exist
- **Right:** Review the "Depends On" section before starting work

### ❌ Mistake 3: Not Tracking Deliverables
- **Wrong:** Completing work without checking off acceptance criteria
- **Right:** For each deliverable, verify each criterion is met and mark `[x]`

### ❌ Mistake 4: Proceeding Without Exit Criteria
- **Wrong:** "Phase 2 is mostly done, let's start Phase 3"
- **Right:** "All Phase 2 exit criteria must be verified before starting Phase 3"

### ❌ Mistake 5: Missing PHI Boundary Enforcement
- **Wrong:** Sending any raw PHI to Gemini API
- **Right:** Only Reasoning Traces (no PHI) go to cloud; all PHI stays local

---

##  Quick Reference: Phase Deliverable Count

| Phase | Deliverables | Duration | Status |
|-------|--------------|----------|--------|
| **1: Foundation** | 6 | Weeks 1-2 | Scaffolding & config |
| **2: Core Domain** | 7 | Weeks 3-4 | Data models & CRUD |
| **3: Agent Pipeline** | 10 | Weeks 5-6 | Hybrid workflow (PHI boundary critical) |
| **4: Alerts & Reliability** | 10 | Week 7 | Notifications & resilience |
| **5: Hardening & Compliance** | 13 | Week 8 | Security & ops |
| **TOTAL** | **46** | **8 weeks** | |

---

##  Key Connections

### Data Layer Progression
- **Phase 1:** DB client abstraction (Motor → PyMongo migration path)
- **Phase 2:** Patient, record, alert schemas + repositories
- **Phase 3:** Reasoning trace storage and queries
- **Phase 4+:** Audit logging, delivery receipts, metrics storage

### Service Layer Progression
- **Phase 1:** Configuration and health checks
- **Phase 2:** Repository pattern and validation
- **Phase 3:** Queue and worker orchestration
- **Phase 4:** Risk policy and notification services
- **Phase 5:** Observability (logging, metrics, tracing)

---

##  When to Reference This File

- **Before starting any phase:** Understand phase dependencies and deliverables
- **During work:** Track deliverables using acceptance criteria
- **When stuck:** Review the "Common Agent Mistakes" section
- **Between phases:** Verify all exit criteria before proceeding
- **For context:** Review architecture principles and deliverable anatomy

---

##  Success Criteria (Definition of Done)

The entire backend is complete when:
✅ Hybrid flow works end-to-end in staging  
✅ No raw PHI appears in cloud request logs  
✅ Critical alert flow is reliable with delivery receipts  
✅ Audit logs cover all PHI accesses  
✅ Tests pass with privacy and resilience gates enforced  

---

## Document Metadata

- **Created:** 2026-04-14
- **Applies To:** backend/ directory (all phases)
- **Review Date:** Before starting Phase 1
- **Next Action:** Open [PHASE_INDEX.md](../PHASE_INDEX.md) for overview
