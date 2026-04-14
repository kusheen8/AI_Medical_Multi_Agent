---
title: "Phase Plan Quick Reference for Agents"
description: "Quick lookup for AI agents: how to reference phase documents, when to use each phase, exit criteria"
---

# AI Medical Multi-Agent: Phase Plan Quick Reference for Agents

## 🚀 Start Here

**All backend development is organized into 5 modular phases documented in markdown files:**

| Phase | File | Weeks | Use When |
|-------|------|-------|----------|
| **1: Foundation** | `PHASE_1_FOUNDATION.md` | 1-2 | Setting up FastAPI app, config, logging, health checks |
| **2: Core Domain** | `PHASE_2_CORE_DOMAIN.md` | 3-4 | Building data models, repositories, CRUD API endpoints |
| **3: Agent Pipeline** | `PHASE_3_AGENT_PIPELINE.md` | 5-6 | Implementing hybrid cloud/local workflow, PHI boundary enforcement |
| **4: Alerts & Reliability** | `PHASE_4_ALERTS_RELIABILITY.md` | 7 | Building notification system, retries, circuit breaker |
| **5: Hardening & Compliance** | `PHASE_5_HARDENING_COMPLIANCE.md` | 8 | Security, encryption, privacy tests, runbooks |

**Hub documents:**
- `PHASE_INDEX.md` — Overview, roadmap, dependencies (read first for understanding)
- `QUICK_REFERENCE.md` — One-page summary, timeline, metrics
- `.github/instructions/PHASE_EXECUTION.instructions.md` — Detailed agent execution guide (comprehensive)

---

## 🎯 How Agents Should Use Phase Documents

### Before Starting Any Work
1. **Open `PHASE_INDEX.md`** — Understand current phase, dependencies, roadmap
2. **Open the relevant phase file** — (e.g., `PHASE_3_AGENT_PIPELINE.md`)
3. **Review cross-phase dependencies** — Check "Depends On" section

### During Implementation
- **Track deliverables** — Each phase has 6-13 deliverables with acceptance criteria (checkboxes)
- **Follow implementation sequence** — Deliverables are ordered by dependency
- **Check artifacts** — Know which files to create/modify
- **Mark criteria as complete** — `[x]` when each acceptance criterion is verified

### Before Proceeding to Next Phase
- **Verify exit criteria** — All items in "Exit Criteria Checklist" must be checked
- **Do not skip phases** — Sequential execution required (no parallel phases)
- **Confirm dependencies met** — Ensure previous phases' exit criteria are complete

---

## 🏗️ Phase Deliverable Overview

| Phase | # Deliverables | Key Focus |
|-------|---|---|
| 1 | 6 | FastAPI scaffold, config, logging, DB client, health checks, CI/CD |
| 2 | 7 | Domain models, repositories, CRUD API, audit logging, validation, tests |
| 3 | 10 | Cloud Coordinator, local analyzers, queue, workers, PHI boundary (CRITICAL) |
| 4 | 10 | Risk engine, notifications, retries, circuit breaker, metrics, tests |
| 5 | 13 | Auth, encryption, privacy tests, security audit, logging, runbooks |

**Total: 46 deliverables across 8 weeks**

---

## 🔄 Phase Dependency Chain

```
PHASE 1 ← Must complete before starting PHASE 2
↓
PHASE 2 ← Must complete before starting PHASE 3
↓
PHASE 3 ← Must complete before starting PHASE 4 (PHI boundary verification is critical)
↓
PHASE 4 ← Must complete before starting PHASE 5
↓
PHASE 5 ← Production readiness and compliance
```

**No parallel work. Each phase gates the next.**

---

## ⚠️ Critical Architecture Principles (Never Forget)

### PHI Boundary (Phase 3 Critical)
- ✅ Gemini (cloud) sees ONLY: Reasoning Traces, metadata (age, condition enum, risk tier)
- ✅ Ollama (local) sees ONLY: Full PHI (names, symptoms, medical history)
- ❌ NO raw PHI ever sent to cloud APIs

### Async & Queue-Based
- API accepts tasks immediately (202 Accepted)
- Background workers process via internal queue
- Queue persists to DB for durability

### Auditable
- Every PHI access logged with user_id, action, timestamp
- Immutable audit logs in separate MongoDB collection

---

## 📋 What Each Phase Looks Like

### Structure of Each Phase File

```markdown
# Phase X: [Name]

## Phase Overview
- Duration
- Objective
- Entry/Exit Criteria

## Goals
- 5-7 goals

## Deliverables (6-13 items)
Each has:
- Description
- Acceptance Criteria (checkboxes)
- Artifacts (file list)

## Implementation Sequence
- Day-by-day breakdown

## Exit Criteria Checklist
- All must be ✓ before next phase

## Known Risks & Mitigations
```

---

## 🎓 Common Agent Tasks by Phase

### Phase 1 Tasks
- "Create FastAPI project structure"
- "Set up Pydantic config management"
- "Implement structured JSON logging"
- "Abstract MongoDB client for Motor → PyMongo migration"
- "Add health check endpoints"

### Phase 2 Tasks
- "Define Patient, MedicalRecord, Alert models"
- "Implement repository pattern for data access"
- "Build CRUD endpoints (POST/GET/PUT/DELETE)"
- "Add input validation rules"
- "Implement audit logging middleware"

### Phase 3 Tasks (Most Complex)
- "Build Gemini Coordinator for Reasoning Traces"
- "Implement Ollama + MedGemma analyzer"
- "Create async task queue"
- "Implement worker processes"
- "Enforce PHI boundary middleware"
- "Write end-to-end integration tests proving no PHI leakage"

### Phase 4 Tasks
- "Build risk policy engine"
- "Implement Twilio/SendGrid notification adapters"
- "Add retry logic with exponential backoff"
- "Implement circuit breaker pattern"
- "Add delivery receipt tracking"

### Phase 5 Tasks
- "Implement JWT/OAuth2 authentication"
- "Enable database encryption at rest"
- "Configure HTTPS/TLS"
- "Run privacy validation tests"
- "Create compliance documentation"
- "Write operational runbooks"

---

## ✅ Exit Criteria Pattern

Each phase document includes a **"Exit Criteria Checklist"** with measurable gates:

```markdown
## Exit Criteria Checklist

- [ ] Specific, testable criterion 1
- [ ] Measurable criterion 2
- [ ] Observable criterion 3
- [ ] Verifiable criterion 4
```

**All items must be `[x]` before phase is considered done.**

Example from Phase 3:
```markdown
- [ ] End-to-end test passes: no raw PHI in logs
- [ ] Analysis result populated correctly
- [ ] Task completed successfully
- [ ] Audit trail captured
```

---

## 🚨 Agent Anti-Patterns to Avoid

| ❌ Wrong | ✅ Right |
|---------|---------|
| "I'll skip to Phase 3, it's faster" | Check Phase 2 exit criteria; Phase 3 depends on them |
| "Phase 2 is done, we can start Phase 3" | Verify ALL exit criteria before starting next phase |
| "I'll implement feature X from Phase 5" | Follow sequential phases; features are phased deliberately |
| "Let me send patient name to Gemini API" | NEVER; only de-identified metadata to cloud |
| "I'll track work status separately" | Use phase document acceptance criteria; mark `[x]` |

---

## 📍 Document Locations

**All phase documents live in the root of the repository:**

```
AI_Medical_Multi_Agent/
├── PHASE_INDEX.md                          ← Start here (overview + roadmap)
├── PHASE_1_FOUNDATION.md                   ← Weeks 1-2
├── PHASE_2_CORE_DOMAIN.md                  ← Weeks 3-4
├── PHASE_3_AGENT_PIPELINE.md               ← Weeks 5-6 (PHI boundary critical)
├── PHASE_4_ALERTS_RELIABILITY.md           ← Week 7
├── PHASE_5_HARDENING_COMPLIANCE.md         ← Week 8
├── QUICK_REFERENCE.md                      ← One-page summary
├── .github/instructions/
│   └── PHASE_EXECUTION.instructions.md     ← This file (detailed agent guide)
```

---

## 🎯 Definition of Done (All Phases Complete)

✅ Hybrid flow works end-to-end in staging  
✅ No raw PHI appears in cloud request logs  
✅ Critical alert flow is reliable with delivery receipts  
✅ Audit logs cover all PHI accesses  
✅ Tests pass with privacy and resilience gates enforced  

---

## 🔗 When Referencing in Chat

**Good agent prompt phrasing:**
- "Implement D2.1 (Domain Models) from PHASE_2_CORE_DOMAIN.md"
- "Check Phase 3 exit criteria before proceeding to Phase 4"
- "Verify the acceptance criteria for D3.9 (PHI Boundary Enforcement)"
- "Follow the implementation sequence in PHASE_4_ALERTS_RELIABILITY.md"

**Good agent context gathering:**
- "Which phase are we currently executing?"
- "Have all exit criteria from Phase 2 been verified?"
- "What are the data layer dependencies for Phase 3?"

---

## 📚 Reading Order

1. **First time:** Read `PHASE_INDEX.md` (10 min understanding)
2. **Starting work:** Read current phase file (20-30 min deep dive)
3. **During implementation:** Reference deliverables and acceptance criteria
4. **Between phases:** Verify exit criteria and review next phase "Depends On"
5. **For quick lookup:** Use `QUICK_REFERENCE.md` or `QUICK_REFERENCE_FOR_AGENTS.md`

---

## 🤝 Collaboration with Other Agents

**When multiple agents are working:**
- Agents should link phase documents to show context
- Agents should reference specific deliverables (e.g., "D3.5: Internal Async Queue")
- Agents should verify dependencies before claiming phase is complete
- Agents should update phase document acceptance criteria as work completes

**Example collaboration:**
- Agent A: "Implemented D2.1-D2.4 (models + CRUD). Verified Patient/Record endpoints working."
- Agent B: "Thanks! I see D2.5 (Audit Logging) and D2.6 (Validation) are next. I'll take those."
- Coordinator: "Once D2.7 (Tests) complete with ≥85% coverage, Phase 2 exit criteria will be met."

---

## Document Metadata

- **Created:** 2026-04-14
- **For:** AI agents implementing the backend
- **Applies To:** All phases, all deliverables
- **Next Step:** Open `PHASE_INDEX.md` for overview
