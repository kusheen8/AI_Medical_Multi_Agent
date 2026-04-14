---
title: "Phase 5: Hardening & Compliance"
phase: 5
duration: "Week 8"
dependencies: ["PHASE_1_FOUNDATION.md", "PHASE_2_CORE_DOMAIN.md", "PHASE_3_AGENT_PIPELINE.md", "PHASE_4_ALERTS_RELIABILITY.md"]
tags: ["security", "privacy", "compliance", "observability", "production"]
---

# Phase 5: Hardening & Compliance

## Phase Overview

**Duration:** Week 8  
**Objective:** Finalize security, privacy, compliance, and observability; prepare for production  
**Entry Criteria:** Phase 4 complete; all functional requirements met  
**Exit Criteria:** All security/privacy gates pass; compliance audit complete; runbooks finalized

---

## Goals

- ✓ Prove no raw PHI appears in cloud logs (privacy validation)
- ✓ Implement encryption at rest and in transit
- ✓ Add authentication and authorization (AuthN/AuthZ)
- ✓ Complete security penetration testing
- ✓ Implement centralized observability (logging, metrics, traces)
- ✓ Create runbooks and incident procedures
- ✓ Finalize compliance documentation
- ✓ Performance profiling and optimization

---

## Deliverables

### D5.1: Authentication & Authorization (AuthN/AuthZ)
**Description:** API access control  
**Acceptance Criteria:**
- [ ] `core/security.py` implements token-based auth (JWT or OAuth2)
- [ ] Token schema: user_id, role (patient, caregiver, doctor, admin), scopes, exp
- [ ] Endpoints protected:
  - Patient CRUD: only patient owner or authorized caregiver
  - Records: only patient + authorized care team
  - Alerts: only relevant caregivers
  - Admin endpoints: admin role only
- [ ] Role-based access control (RBAC):
  - Patient: read own records, submit symptoms
  - Caregiver: read assigned patient records, acknowledge alerts
  - Doctor: read/write clinical findings
  - Admin: all operations
- [ ] Token refresh mechanism (short-lived access tokens, refresh tokens)
- [ ] Logout/token revocation
- [ ] Unit tests: verify access control boundaries

**Artifacts:**
- `backend/app/core/security.py` (JWT/OAuth2 implementation)
- `backend/app/models/user.py` (user and role schemas)
- `backend/app/api/v1/routes_auth.py` (login/logout endpoints)
- RBAC middleware
- Tests: test_authz.py

---

### D5.2: Encryption at Rest
**Description:** Data protection in MongoDB  
**Acceptance Criteria:**
- [ ] MongoDB encryption enabled:
  - Database-level encryption (MongoDB Enterprise or managed service)
  - Or: application-level encryption for sensitive fields (PHI)
- [ ] Sensitive fields encrypted:
  - Patient: name, dob, identifiers
  - MedicalRecord: symptoms, entities
  - Alert: trigger_reason
- [ ] Encryption key management:
  - Keys stored in secure key vault (AWS Secrets Manager, Azure Key Vault)
  - Key rotation policy (quarterly)
  - Master key never in code
- [ ] Decryption only during processing (in memory)
- [ ] Database backups encrypted with same keys

**Artifacts:**
- Encryption configuration in `config.py`
- Key management procedures documentation
- Backup encryption verification

---

### D5.3: Encryption in Transit
**Description:** HTTPS/TLS for all API communication  
**Acceptance Criteria:**
- [ ] FastAPI app enforces HTTPS in production
  - Certificate: valid CA-signed cert (Let's Encrypt or enterprise)
  - TLS 1.2+ only
  - Strong cipher suites (TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 or better)
- [ ] Outbound connections (Gemini, Ollama, external APIs) over HTTPS
- [ ] Certificate validation (no self-signed in production)
- [ ] HSTS header: `Strict-Transport-Security: max-age=31536000`
- [ ] Security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy` (appropriate for API)
- [ ] No credentials in logs or error messages

**Artifacts:**
- FastAPI HTTPS middleware
- Certificate provisioning runbook
- Security headers middleware

---

### D5.4: Privacy Validation Tests
**Description:** Prove no raw PHI in cloud logs  
**Acceptance Criteria:**
- [ ] Test suite: `test_privacy_validation.py`
- [ ] Scenarios:
  1. POST `/analyze/symptoms` with patient name and symptoms
     → Assert Gemini request doesn't contain name or symptom text
  2. POST `/analyze/history` with full medical history
     → Assert Gemini request uses only aggregate statistics
  3. Cloud error response
     → Assert response scrubbed before returning to frontend
  4. Concurrent analysis on multiple patients
     → Assert no patient context leakage between requests
- [ ] Test methodology: capture all outbound HTTP requests (mock or proxy)
- [ ] Assertions: regex scan for known PHI patterns (names, medical terms, identifiers)
- [ ] Coverage: all cloud API calls (Gemini, external services)
- [ ] False positive rate < 1% (tuned redaction patterns)

**Artifacts:**
- `backend/tests/privacy/test_privacy_validation.py`
- Request capture utilities (mock interceptors)
- PHI pattern definitions
- Privacy validation report template

---

### D5.5: Input Validation & Output Encoding
**Description:** Prevent injection and XSS attacks  
**Acceptance Criteria:**
- [ ] Input validation:
  - SQL injection prevention (Pydantic + parametrized queries via Motor/PyMongo)
  - Command injection prevention (no shell execution)
  - Path traversal prevention (no direct file access with user input)
- [ ] Output encoding: HTML entity encoding for any user input echoed in responses
- [ ] API responses use JSON (inherently safe from XSS)
- [ ] CORS policy: restrict origins to known frontend domains only
- [ ] Rate limiting: prevent brute force and DoS
  - 100 requests/min per IP for login endpoint
  - 1000 requests/min per authenticated user for analysis endpoints
- [ ] Unit tests: injection payloads blocked

**Artifacts:**
- CORS middleware configuration
- Rate limiting middleware
- Tests: test_injection_prevention.py, test_rate_limiting.py

---

### D5.6: Centralized Logging & Log Aggregation
**Description:** Structured logs for security monitoring and debugging  
**Acceptance Criteria:**
- [ ] All logs structured JSON with fields:
  - timestamp, level, logger_name, message, request_id, user_id, context
- [ ] Log destinations:
  - Local file (for development)
  - Stdout (for container/k8s)
  - Cloud logging service (e.g., AWS CloudWatch, Azure Monitor)
- [ ] Log levels:
  - ERROR: failures, exceptions
  - WARN: retries, degradation
  - INFO: API calls, state transitions
  - DEBUG: variable values (no PHI or credentials)
- [ ] Sensitive data filtering:
  - No API keys, tokens in logs
  - No raw request/response bodies (summary only)
  - PHI redacted (names → "REDACTED", numbers → "***")
- [ ] Log retention: 90 days hot, 1 year archive
- [ ] Security event logging:
  - Authentication failures (invalid token)
  - Authorization violations (unauthorized access)
  - Unusual patterns (rate limit triggers, repeated errors)

**Artifacts:**
- `backend/app/core/logging.py` (enhanced)
- Sensitive data filter middleware
- Cloud logging configuration
- Log retention policy documentation

---

### D5.7: Metrics & Monitoring
**Description:** System health and performance observability  
**Acceptance Criteria:**
- [ ] Metrics collected:
  - Request metrics: count, latency, status codes (by endpoint)
  - Error rates: 4xx, 5xx (by endpoint)
  - Database metrics: query latency, connection pool usage
  - Queue metrics: length, processing latency, retry count
  - Model latency: Ollama response time, Gemini response time
  - Alert metrics: created, delivered, failed (by channel)
  - Privacy metrics: PHI redaction events, policy blocks
- [ ] Metrics exported in Prometheus format
  - Endpoint: `GET /metrics` (Prometheus scrape target)
- [ ] Time-series database: Prometheus or managed service
- [ ] Dashboards (Grafana or cloud dashboard):
  - System health dashboard (API latency, error rates, queue depth)
  - Alert delivery dashboard (success rate, latency by channel)
  - Privacy monitoring dashboard (redaction events, blocked requests)
- [ ] Alerts (configured in monitoring service):
  - Error rate > 5% → Warning
  - P95 latency > 5s → Warning
  - Queue depth > 100 → Warning
  - Alert success rate < 95% → Critical

**Artifacts:**
- `backend/app/core/metrics.py` (metrics instrumenting)
- Prometheus configuration (scrape_configs)
- Grafana dashboard JSON (system health, alerts, privacy)
- Alert thresholds and policies

---

### D5.8: Distributed Tracing
**Description:** End-to-end request tracing  
**Acceptance Criteria:**
- [ ] Tracing library: OpenTelemetry + Jaeger backend
- [ ] Trace context propagated across:
  - FastAPI request handling
  - Queue task execution
  - Ollama calls (via headers)
  - Gemini calls (via headers)
  - MongoDB queries
- [ ] Span details:
  - Operation name, start time, duration
  - Tags: endpoint, user_id, patient_id
  - Logs: significant events within span
- [ ] Sampling: sample 10% of requests in production (configurable)
- [ ] Jaeger UI: view traces by service, endpoint, error
- [ ] Performance analysis: identify bottlenecks in trace

**Artifacts:**
- OpenTelemetry setup in `core/tracing.py`
- Jaeger Docker Compose config
- Instrumentation for FastAPI, database, external APIs
- Tracing documentation

---

### D5.9: Penetration Testing & Security Audit
**Description:** Identify and remediate vulnerabilities  
**Acceptance Criteria:**
- [ ] Test plan covering:
  1. Authentication bypass (force invalid tokens, expire times)
  2. Authorization bypass (access other users' data)
  3. Injection attacks (SQL, command, path traversal)
  4. Data exposure (response inspection, error messages)
  5. Sensitive data in logs
  6. Cryptographic weaknesses (weak algorithms, bad key management)
  7. API enumeration (CORS, path discovery)
- [ ] Execution: manual + automated security scanner (OWASP ZAP, SonarQube)
- [ ] Findings: document by severity, propose remediations
- [ ] Sign-off: security officer approval before production
- [ ] Ongoing: annual re-testing, post-incident testing

**Artifacts:**
- `backend/tests/security/test_pen_scenarios.py` (automated security tests)
- Penetration test report (findings + remediations)
- Security audit checklist

---

### D5.10: Performance Profiling & Optimization
**Description:** Ensure system meets performance SLAs  
**Acceptance Criteria:**
- [ ] Load testing:
  - 100 concurrent users submitting symptoms
  - 1000 analysis tasks in queue
  - Measure: API latency (P50, P95, P99), throughput, error rate
- [ ] Database query profiling:
  - Identify slow queries via MongoDB logs
  - Add indexes for frequently filtered fields
  - Target: all queries < 100ms
- [ ] Memory profiling:
  - Identify memory leaks (tracemalloc)
  - Ensure stable memory under sustained load
- [ ] Optimization:
  - Query result caching (for frequently accessed data)
  - Connection pooling tuning (optimal pool size)
  - Model prompt caching (reuse Reasoning Traces)
  - Batch API calls to external services
- [ ] Targets:
  - API response: P95 < 1.5s (task acceptance), P99 < 5s (full execution)
  - Throughput: ≥100 analysis tasks/min

**Artifacts:**
- `backend/tests/performance/load_test.py` (load test script)
- Profiling results with timeline analysis
- Database query optimization report
- Performance tuning recommendations

---

### D5.11: Compliance Documentation
**Description:** Audit-ready documentation  
**Acceptance Criteria:**
- [ ] Data flow diagram showing:
  - PHI boundaries (what data is local vs. cloud)
  - Encryption points
  - Audit logging points
  - Security controls at each stage
- [ ] Privacy policy:
  - Data collected, purposes
  - Retention periods
  - Sharing with third parties
  - User rights (access, deletion)
- [ ] Security control matrix (HIPAA/GDPR):
  - Administrative controls (access management, training)
  - Physical controls (facility security)
  - Technical controls (encryption, logging, monitoring)
  - Examples: MFA, key rotation, audit logs
- [ ] Incident response plan:
  - Breach detection procedures
  - Escalation path
  - Notification timeline
  - Forensic analysis steps
- [ ] Business continuity / Disaster recovery:
  - RTO (recovery time objective): < 1 hour
  - RPO (recovery point objective): < 15 min
  - Backup and restore procedures
  - Failover mechanisms

**Artifacts:**
- `docs/DATA_FLOW_SECURITY.md` (architecture + controls)
- `docs/PRIVACY_POLICY.md`
- `docs/SECURITY_CONTROLS_MATRIX.md` (HIPAA/GDPR mapping)
- `docs/INCIDENT_RESPONSE_PLAN.md`
- `docs/CONTINUITY.md`

---

### D5.12: Runbooks & Operations
**Description:** Support and incident management procedures  
**Acceptance Criteria:**
- [ ] Runbooks for common scenarios:
  1. Service startup/shutdown (graceful)
  2. Database migration / upgrade
  3. Certificate renewal
  4. Scaling (add more workers)
  5. Ollama model update / fallback
  6. Gemini API quota exceeded (graceful degradation)
  7. Alert channel provider outage
- [ ] Incident response runbooks:
  1. High error rate → investigate logs, scale workers
  2. Ollama unavailable → circuit breaker activates, queue holds
  3. Database connection pool exhausted → increase pool, investigate leaks
  4. Privacy breach detected → isolation, notification, forensics
- [ ] Monitoring & alerting dashboard setup
- [ ] On-call procedures (escalation, paging)
- [ ] Post-incident review template

**Artifacts:**
- `docs/RUNBOOKS.md` (comprehensive operational procedures)
- `docs/INCIDENT_RESPONSE.md` (incident playbooks)
- `docs/DEPLOYMENT_CHECKLIST.md`
- `docs/DASHBOARDS.md` (Grafana setup guide)

---

### D5.13: Final Test Suite
**Description:** Comprehensive validation before production  
**Acceptance Criteria:**
- [ ] Unit test coverage ≥85% (all modules)
- [ ] Integration tests: all API endpoints + workflows
- [ ] Privacy tests: no PHI in cloud logs
- [ ] Reliability tests: failure scenarios + recovery
- [ ] Security tests: injection, auth bypass, data exposure
- [ ] Performance tests: load, latency, throughput SLAs
- [ ] All tests pass with CI/CD pipeline
- [ ] Code review sign-off

**Artifacts:**
- Coverage report (pytest-cov)
- CI/CD pipeline results
- Test execution summary

---

## Implementation Sequence

1. **Day 1:** Authentication & Authorization
   - JWT/OAuth2 setup
   - RBAC middleware
   - Protected endpoints
   - Unit tests

2. **Day 2:** Encryption (at rest + in transit)
   - Database encryption config
   - HTTPS enforcement
   - Security headers middleware
   - Certificate management

3. **Day 3:** Privacy Validation
   - Privacy test suite
   - Request interceptors
   - PHI pattern detection
   - Privacy report generation

4. **Day 4:** Input Validation & Injection Prevention
   - CORS policy
   - Rate limiting
   - Injection prevention tests
   - Security test coverage

5. **Day 5:** Logging & Metrics
   - Centralized logging setup
   - Metrics collection
   - Prometheus export
   - Grafana dashboards

6. **Day 6:** Distributed Tracing & Profiling
   - OpenTelemetry setup
   - Jaeger backend
   - Performance profiling
   - Optimization pass

7. **Day 7:** Penetration Testing & Compliance
   - Security audit
   - Pen test scenarios
   - Compliance documentation
   - Runbooks finalization
   - Production sign-off

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **JWT for auth** | Stateless, scalable, standard |
| **Application-level encryption** | Works with any database; key control |
| **Prometheus + Grafana** | Open-source, standard, good integrations |
| **OpenTelemetry tracing** | Vendor-agnostic, integrates with Jaeger |
| **OWASP security testing** | Comprehensive, industry-standard framework |

---

## Security & Compliance Checklist

### HIPAA Compliance
- [ ] Access controls (authentication + RBAC)
- [ ] Encryption at rest and in transit
- [ ] Audit logs for all PHI access
- [ ] Encryption key management
- [ ] Regular security updates
- [ ] Privacy policies documented
- [ ] Breach notification procedures

### GDPR Compliance
- [ ] Explicit user consent for data processing
- [ ] Data minimization (only collect necessary data)
- [ ] Right to access (user can download data)
- [ ] Right to deletion (user can request data deletion)
- [ ] Data retention limits
- [ ] Processor agreements (with third-party services)

### General Security
- [ ] Authentication & Authorization
- [ ] Input validation
- [ ] Output encoding
- [ ] Encryption in transit + at rest
- [ ] Logging & monitoring
- [ ] Incident response plan

---

## Exit Criteria Checklist

- [ ] All AuthN/AuthZ endpoints pass security tests
- [ ] Encryption at rest enabled; keys rotated
- [ ] HTTPS enforced; all outbound connections encrypted
- [ ] Privacy validation: no PHI in cloud logs (100% coverage)
- [ ] Injection attacks prevented (test coverage)
- [ ] Centralized logging active; log retention policy enforced
- [ ] Metrics and dashboards operational
- [ ] Distributed tracing working end-to-end
- [ ] Penetration test completed; findings remediated
- [ ] Compliance documentation complete and signed off
- [ ] All runbooks written and tested
- [ ] Performance profiling complete; SLAs met
- [ ] Full test suite passing (unit + integration + security)
- [ ] Production deployment readiness sign-off

---

## Production Deployment Criteria

✅ Definition of Done (from original plan):
- Hybrid flow works end-to-end in staging
- No raw PHI appears in cloud request logs
- Critical alert flow is reliable with delivery receipts
- Audit logs cover all PHI accesses
- Tests pass with privacy and resilience gates enforced

✅ Additional Phase 5 gates:
- Security audit passed
- Compliance documentation complete
- Runbooks tested and socialized
- Monitoring dashboards operational
- Incident response procedures in place
- Performance SLAs verified

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Cryptographic key loss** | Data unrecoverable | Key backup + HSM; quarterly rotation testing |
| **Certificate expiry** | Service outage | Automated renewal (Let's Encrypt); monitoring |
| **Compliance change** | Legal liability | Quarterly policy review; legal counsel engagement |
| **Zero-day exploit** | Security breach | Dependency scanning; rapid patching process |
| **Scaling limits** | Performance degradation | Load testing; horizontal scaling readiness |

---

## Post-Production

- **Week 9+:** Monitor metrics; incident response drills
- **Monthly:** Security updates and dependency patches
- **Quarterly:** Compliance review, pentest, policy update
- **Annual:** Full security audit, disaster recovery drill

---

## Document Metadata

- **Created:** 2026-04-14
- **Depends On:** Phases 1-4
- **Focus:** Security, Privacy, Compliance, Operations
- **Review Date:** Production go-live approval
- **Next Action:** Deploy to staging; conduct final validation
