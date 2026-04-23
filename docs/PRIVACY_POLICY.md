# Privacy Policy (HIPAA & GDPR Baseline)

## Information We Collect
In order to provide our diagnostic analysis, we must process personal health and medical data (PHI):
- Identifiable information (Names, Dates of Birth, Contact Details).
- Clinical signs, symptoms, observations, and relevant historical diagnoses.
- Technical logs including IP addresses, User Agents, and system interactions.

## How Information is Used
Data is used solely to generate AI-assisted clinical reasoning pathways and notify relevant caregivers when a high-risk medical condition correlates with current symptom inputs.
Processing logic runs entirely locally, protecting direct patient details from being shared with third parties.

## Third-Party Data Sharing (Processor Agreements)
We utilize limited Sub-processors.
- **Cloud LLM API (Google Gemini)**: Processes only heavily sanitized, anonymized metrics to evaluate context traces. We maintain Business Associate Agreements (BAAs) and DPA strict boundaries restricting the training of patient data.
- **Notification Providers (Twilio, SendGrid, FCM)**: Used solely to deliver urgent caregiver alerts. We strictly limit PHI exposure within the text content of these messages, opting for secure links requiring portal authentication.

## Data Retention
- Patient identities are kept indefinitely until deletion is requested.
- Associated medical logs, traces, and reasoning pathways age out after **7 years** to maintain HIPAA compliance mandates. 

## Patient Rights (GDPR & HIPAA)
1. **Right to Access**: Patients can request a structured JSON dump of all records associated with their identifier via the Admin endpoints.
2. **Right to Erasure (Right to be Forgotten)**: Accounts and all trace associations can be hard-deleted upon verifiable request. Note that immutable Audit Event Logs tracking system actions must remain for compliance indexing (with stripped PII where applicable).

*This policy serves as a compliant baseline outlining the data handling practices for the AI Medical System.*
