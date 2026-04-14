---
title: "Phase 4: Alerts & Reliability"
phase: 4
duration: "Week 7"
dependencies: ["PHASE_1_FOUNDATION.md", "PHASE_2_CORE_DOMAIN.md", "PHASE_3_AGENT_PIPELINE.md"]
tags: ["notifications", "resilience", "retry", "alert-system"]
---

# Phase 4: Alerts & Reliability

## Phase Overview

**Duration:** Week 7  
**Objective:** Implement caregiver notification system with reliability patterns; harden queue and worker processes  
**Entry Criteria:** Phase 3 complete; end-to-end analysis pipeline working  
**Exit Criteria:** Alerts dispatch within SLA; no message loss; retries and acknowledgement working

---

## Goals

- ✓ Implement risk policy engine to detect alert thresholds
- ✓ Build Caregiver Notification Agent (cloud-safe, rule-based)
- ✓ Integrate SMS/Email/Push notification channels
- ✓ Add retry logic with exponential backoff and dead-letter queue
- ✓ Implement idempotency for alert creation (prevent duplicates)
- ✓ Add delivery receipt tracking and acknowledgement flow
- ✓ Implement circuit breaker pattern for external services
- ✓ Add observability: alert latency, delivery rates, error tracking

---

## Deliverables

### D4.1: Risk Policy Engine
**Description:** Configurable rules for alert triggering  
**Acceptance Criteria:**
- [ ] `services/risk_policy/policy_engine.py` evaluates risk thresholds
- [ ] Policies defined as rules:
  - If risk_level = "critical" AND not acknowledged → alert
  - If risk_level = "high" AND consecutive 3+ records → escalate alert
  - If symptoms match known emergency patterns → immediate alert
- [ ] Risk tiers: low (no alert), medium (info notification), high (urgent), critical (emergency escalation)
- [ ] Policies stored in MongoDB; can be updated without code deployment
- [ ] Policy versioning: track policy changes over time
- [ ] Dry-run mode: test policies without triggering alerts
- [ ] Unit tests for all rule combinations

**Artifacts:**
- `backend/app/services/risk_policy/policy_engine.py`
- `backend/app/models/policy_rule.py`
- `backend/app/db/repositories/policy_repository.py`
- Sample policies in JSON format

---

### D4.2: Caregiver Notification Service
**Description:** Rule-based notification orchestrator (non-PHI cloud service)  
**Acceptance Criteria:**
- [ ] `services/notifications/caregiver_notifier.py` handles alert dispatch
- [ ] Input: alert trigger, de-identified patient context (age, risk tier), severity
- [ ] Determine notification channels:
  - SMS for critical/high severity
  - Email for all severity levels
  - Push notifications for mobile app
- [ ] Route to appropriate external provider:
  - SMS: Twilio API
  - Email: SendGrid API
  - Push: Firebase Cloud Messaging
- [ ] Request sanitization: no raw PHI sent to external providers
- [ ] Configuration per patient: caregiver contact info, preferred channels
- [ ] Error handling: provider unavailability, invalid contact info

**Artifacts:**
- `backend/app/services/notifications/caregiver_notifier.py`
- SMS provider adapter (Twilio)
- Email provider adapter (SendGrid)
- Push provider adapter (FCM)

---

### D4.3: Alert Management API
**Description:** Endpoints for alert lifecycle  
**Acceptance Criteria:**
- [ ] `POST /api/v1/alerts` - Create alert (triggered by analyzer)
  - Body: patient_id, severity, trigger_reason, channels
  - Returns: alert_id, created_at
  - Idempotency key to prevent duplicates
- [ ] `GET /api/v1/alerts/{id}` - Retrieve alert details
- [ ] `GET /api/v1/patients/{patient_id}/alerts` - List alerts for patient (paginated)
- [ ] `PUT /api/v1/alerts/{id}/acknowledge` - Acknowledge alert by caregiver
  - Stops retries; marks resolved
- [ ] `GET /api/v1/alerts/{id}/delivery-status` - Query delivery receipts for all channels
- [ ] `GET /api/v1/alerts/failed` - List undelivered alerts (for admin/retry)

**Artifacts:**
- `backend/app/api/v1/routes_alerts.py` (routes)
- Request/response schemas with OpenAPI examples
- Integration tests for all endpoints

---

### D4.4: Delivery Receipt Tracking
**Description:** Audit trail for notification delivery  
**Acceptance Criteria:**
- [ ] Alert schema includes `delivery_receipts` array:
  - Channel (sms, email, push)
  - Timestamp
  - Status (sent, delivered, bounced, failed)
  - Provider response code
  - Retry count
- [ ] Webhook endpoints to receive delivery status from providers
  - `POST /api/v1/webhooks/sms-status` (Twilio webhook)
  - `POST /api/v1/webhooks/email-status` (SendGrid webhook)
  - `POST /api/v1/webhooks/push-status` (FCM webhook)
- [ ] Verify webhook authenticity (signature validation)
- [ ] Update alert delivery_receipts on webhook receipt
- [ ] Query delivery status by alert_id and channel

**Artifacts:**
- `backend/app/api/v1/routes_webhooks.py` (webhook endpoints)
- Webhook signature validation logic
- Delivery receipt schema updates

---

### D4.5: Retry Logic & Dead-Letter Queue
**Description:** Reliable task/alert processing with recovery  
**Acceptance Criteria:**
- [ ] Failed alert notifications retry with exponential backoff:
  - Retry 1: +5s
  - Retry 2: +10s
  - Retry 3: +20s
  - After 3 failed attempts: move to dead-letter queue (DLQ)
- [ ] DLQ:
  - Stored separately in MongoDB
  - Can be manually inspected and re-queued
  - Endpoint: `POST /api/v1/admin/dlq/retry/{id}` to retry DLQ item
- [ ] Task queue enhancements:
  - Serialize failure reason (timeout, rate limit, auth error, etc.)
  - Different retry strategies by failure type
  - Max age for tasks (1 hour default)
- [ ] Idempotency keys prevent duplicate processing
- [ ] Unit tests for retry scenarios

**Artifacts:**
- `backend/app/services/queue/retry_handler.py`
- `backend/app/services/queue/dlq_manager.py`
- DLQ schema and repository
- Tests: test_retry_logic.py

---

### D4.6: Circuit Breaker Pattern
**Description:** Graceful degradation for external service failures  
**Acceptance Criteria:**
- [ ] Implement circuit breaker for each external service:
  - Twilio SMS API
  - SendGrid Email API
  - Firebase Cloud Messaging
  - Ollama health
- [ ] States: Closed (OK), Open (failing), Half-Open (testing)
- [ ] Transitions:
  - Closed → Open: 5 consecutive failures
  - Open → Half-Open: after 30s
  - Half-Open → Closed: if test succeeds
  - Half-Open → Open: if test fails
- [ ] When Open: fail fast without attempting calls (no timeout waste)
- [ ] Metrics: failure count, success rate, state transitions
- [ ] Unit tests for all state transitions

**Artifacts:**
- `backend/app/services/circuit_breaker.py`
- Circuit breaker decorators for service calls
- Tests: test_circuit_breaker.py

---

### D4.7: Idempotency for Writes
**Description:** Prevent duplicate operations on retries  
**Acceptance Criteria:**
- [ ] Idempotency key support for:
  - `POST /api/v1/patients` (create)
  - `POST /api/v1/records` (create)
  - `POST /api/v1/alerts` (create)
- [ ] Idempotency key header: `Idempotency-Key` (UUID format)
- [ ] Store executed requests in `idempotency_store` collection:
  - request_id, method, path, response, created_at, expires_at (24h)
- [ ] On retry (same idempotency key): return cached response
- [ ] Cleanup: expired entries deleted via TTL index
- [ ] Documentation and tests

**Artifacts:**
- `backend/app/core/idempotency.py` (middleware)
- `backend/app/db/repositories/idempotency_repository.py`
- Tests: test_idempotency.py

---

### D4.8: Observability & Metrics
**Description:** Monitoring for alerts and reliability  
**Acceptance Criteria:**
- [ ] Metrics collected:
  - `alert_created_count` (gauge by severity)
  - `alert_delivery_latency_ms` (histogram)
  - `alert_delivery_success_rate` (gauge per channel)
  - `alert_retry_count` (per alert)
  - `circuit_breaker_state` (gauge per service)
  - `queue_length` (gauge)
  - `queue_processing_latency_ms` (histogram)
- [ ] Metrics stored as time-series in MongoDB
- [ ] Endpoint: `GET /api/v1/metrics` returns Prometheus-format metrics
- [ ] Example dashboards: alert delivery, system health
- [ ] Logging: structured logs for all alert operations

**Artifacts:**
- `backend/app/services/metrics.py` (metrics collector)
- `backend/app/api/v1/routes_metrics.py` (metrics endpoint)
- `backend/app/core/logging.py` (enhanced structured logging)

---

### D4.9: Reliability Tests
**Description:** Resilience and failure scenario validation  
**Acceptance Criteria:**
- [ ] Test scenarios:
  1. Ollama down during analysis → alert not created prematurely
  2. SMS provider rate limit → retry with backoff
  3. Email provider timeout → move to DLQ, re-queue later
  4. Circuit breaker opens → fail fast, restore when service recovers
  5. Queue process crashes → on restart, resume pending tasks
  6. Duplicate alert on retry → idempotency prevents duplicate
  7. Webhook out of order → delivery receipt updates correctly
- [ ] Load test: send 100 alerts in 1s → verify throughput and latency
- [ ] Chaos test: random service failures → observe recovery behavior
- [ ] Test coverage ≥90% for services/ module

**Artifacts:**
- `backend/tests/integration/test_reliability_scenarios.py`
- `backend/tests/chaos/test_failure_modes.py`
- Documented test procedures and success criteria

---

### D4.10: Admin/Monitoring Dashboard Endpoints
**Description:** Operations visibility  
**Acceptance Criteria:**
- [ ] `GET /api/v1/admin/health/summary` - Overall system status
  - Analyst: online/offline
  - Queue: length, oldest task age
  - Circuit breakers: state of each
  - Alert delivery: success rate (24h, 7d)
- [ ] `GET /api/v1/admin/alerts/failed` - Failed alerts awaiting retry
- [ ] `GET /api/v1/admin/queue/tasks` - Active queue tasks
- [ ] `POST /api/v1/admin/dlq/retry/{id}` - Manually retry DLQ item
- [ ] Require admin authentication for these endpoints

**Artifacts:**
- `backend/app/api/v1/routes_admin.py`
- Admin dashboard schema

---

## Implementation Sequence

1. **Day 1:** Risk Policy Engine
   - Implement policy engine and schema
   - Store policies in MongoDB
   - Add dry-run endpoint for testing

2. **Day 2:** Notification Service
   - Implement caregiver notifier
   - Add SMS, Email, Push provider adapters
   - Request sanitization (no PHI)

3. **Day 3:** Alert CRUD API
   - Create `/alerts` endpoints
   - Implement alert creation and lifecycle
   - Add delivery receipt schema

4. **Day 4:** Webhook Receivers + Delivery Tracking
   - Implement webhook endpoints
   - Signature validation
   - Delivery receipt updates

5. **Day 5:** Retry Logic & Circuit Breaker
   - Build retry handler with exponential backoff
   - Implement DLQ and admin retry endpoint
   - Circuit breaker pattern for each external service

6. **Day 6:** Idempotency + Observability
   - Add idempotency middleware
   - Metrics collection
   - Structured logging enhancements

7. **Day 7:** Testing & Hardening
   - Write reliability tests
   - Load tests
   - Chaos tests
   - Document runbooks

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Circuit breaker per service** | Independent failure isolation; fast fallback |
| **Exponential backoff** | Prevents thundering herd; gives external services time to recover |
| **Idempotency via header** | RESTful standard; prevents accidental duplicates |
| **Webhook-driven delivery receipts** | Real-time status; provider authoritative source |
| **Separate DLQ** | Admin visibility; manual retry capability |

---

## Alert Lifecycle

```
1. Analysis completes → risk_level set
2. Policy engine evaluates → triggers alert
3. Alert created (POST /alerts) with idempotency key
4. Notification service queues dispatch task
5. Worker picks up notification task
6. Sends to SMS/Email/Push provider
7. Wait for webhook delivery confirmation
8. If failure → retry loop (3 attempts) with exponential backoff
9. If all retries fail → move to DLQ
10. Caregiver acknowledges via PUT /alerts/{id}/acknowledge
11. Alert marked resolved; notifications stop
12. Alert queries: GET /alerts/{id} show full delivery history
```

---

## Exit Criteria Checklist

- [ ] Risk policy engine evaluates thresholds correctly
- [ ] Alert created endpoint works with idempotency
- [ ] SMS/Email/Push notifications sent without PHI leakage
- [ ] Delivery receipts tracked via webhooks
- [ ] Failed alerts retry with exponential backoff
- [ ] DLQ stores failed items; manual retry works
- [ ] Circuit breaker prevents cascading failures
- [ ] Metrics endpoint returns all required metrics
- [ ] Reliability tests: all 7 scenarios pass
- [ ] Load test: 100 alerts/sec throughput achieved
- [ ] No duplicate alerts on retry
- [ ] Admin endpoints operational

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Alert dispatch latency | ≤ 2s |
| SMS delivery time | ≤ 15s from creation |
| Email delivery time | ≤ 30s from creation |
| DLQ recovery time | < 5 minutes manual |
| Delivery success rate (normal conditions) | ≥ 99% |
| Retry overhead (exponential backoff) | Average < 10s |

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Provider rate limits** | Alert backlog | Circuit breaker + backoff prevent hammering |
| **Webhook delivery failure** | Missing delivery status | Polling fallback; manual admin queries |
| **Duplicate alerts** | Alert fatigue for caregivers | Idempotency + policy deduplication |
| **Queue crash** | Unprocessed alerts | Persist queue to DB; resume on restart |
| **Caregiver unresponsiveness** | No escalation | Implement escalation rules in policy engine |

---

## Next Phase

Upon completion of Phase 4, proceed to **[Phase 5: Hardening & Compliance](PHASE_5_HARDENING_COMPLIANCE.md)** to finalize security, privacy, and observability.

---

## Document Metadata

- **Created:** 2026-04-14
- **Depends On:** Phases 1-3
- **Focus:** Reliability & Notifications
- **Review Date:** Start of Phase 5
