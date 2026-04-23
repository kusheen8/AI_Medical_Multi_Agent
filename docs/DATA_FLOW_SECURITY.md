# Data Flow & Security Architecture

## 1. PHI Boundaries

The AI Medical Multi-Agent enforces a strict boundary between the local processing environment and the cloud processing environment to preserve Protected Health Information (PHI) privacy.

- **Local Network (PHI-Safe):** 
  - Medical Record Database (MongoDB with Encryption-at-Rest)
  - API Gateway & Handlers
  - Notification Delivery Components
  - **Ollama Client / MedGemma**: Used for all symptom analysis, medical summarization, and PHI extraction.

- **Cloud Network (No PHI):**
  - **Gemini Context Coordinator**: Only receives heavily de-identified inputs to generate reasoning pathways. NEVER processes names, IDs, exact dates of birth, or text containing unredacted symptoms if they correlate back to a patient.

## 2. Encryption Points

All data states transition through structured cryptographic controls:

### Encryption In-Transit
- End-to-end `TLS 1.2+` encryption enforced by reverse proxy / FastAPI middleware.
- Outbound API calls (Gemini) enforce HTTPS explicitly through HTTPX client transports.

### Encryption At-Rest
- MongoDB database-level encryption utilizing `AES-256`.
- Internal PII and PHI field-level application encryption utilized by Fernet logic inside the Application ORM. Includes fields: `Patient.name`, `Patient.identifiers`, `MedicalRecord.symptoms`.

## 3. Request Lifecycle Security Flow

1. **Intake**: A User POSTs a new symptom analysis Request (`TLS`).
2. **AuthN/AuthZ**: Security Middleware validates JWT Token. Checks `RBAC` against patient associations list and issues correlated Request UUID.
3. **Queue**: Data is validated and submitted to local async queue.
4. **Analysis Worker**: Data is pulled from queue.
   - Triggers `PrivacyFilter` middleware immediately.
   - Extracts PII.
   - Obfuscated Request travels to Cloud `Gemini API` via `TLS` -> receives JSON format reasoning trace.
   - Worker queries original PHI from MongoDB -> mixes PHI with Reasoning Trace.
   - Local `Ollama` performs medical evaluation based on the trace and PHI data.
5. **Persistence**: Analysis results encoded via Application-field encryption, stored securely to MongoDB.
6. **Alert**: If High-Risk, Notification Worker triggers encrypted Push/SMS via external Webhooks using `HTTPS`.

## 4. Audit Log Touchpoints
Immutable audit logs are triggered by the API repository wrapper whenever clinical data is touched:
- Access (`read`)
- Modification (`update`, `delete`)
- Generation (`create`)

*End Data Flow Security Reference.*
