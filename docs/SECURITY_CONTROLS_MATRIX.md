# Security Controls Matrix

This document maps implemented controls to common healthcare regulatory frameworks (HIPAA / GDPR).

## 1. Administrative Controls
| Control Type | Description | Implementation Status |
|---|---|---|
| Access Management | Role-Based Access Control (Patient, Caregiver, Doctor, Admin). | Implemented via JWT Scopes (Phase 5). |
| Workforce Training | Mandatory annual PHI handling training for administrators. | Organizational Policy. |
| Incident Response | Defined workflows for containing suspected data breaches within 24h. | See `INCIDENT_RESPONSE_PLAN.md`. |
| Audit Validation | Logging of read/write activities across patient boundaries. | Implemented via `AuditMiddleware`. |

## 2. Physical Controls
| Control Type | Description | Implementation Status |
|---|---|---|
| Facility Access | Data centers restricted to authorized personnel. | Managed by Cloud Provider (AWS/Azure/GCP). |
| Hardware Integrity | Workstation lock policies for development teams handling staging PHI. | Organizational Policy. |

## 3. Technical Controls
| Control Type | Description | Implementation Status |
|---|---|---|
| Encryption At Rest | Database storage encrypted using standard AES. | Active (Phase 5 MongoDB encryption at rest enabled + App logic encryption). |
| Encryption In Transit | HTTPS/TLS 1.2+ forced on all ingress and egress nodes. | Active (Phase 5). |
| Data Obfuscation | Redacting all cleartext PHI from third-party vendor requests. | Active (Privacy Filter / DeIdentifier). |
| System Availability | Circuit breakers and DLQ integrations. | Active (Phase 4). |
| Network Isolation | Internal queuing agents are cordoned off from public endpoints. | Active (Queue Managers). |
| Secrets Management | Injection of environment variables; zero hard-coded secrets. | Active (`core.config.Settings`). |
