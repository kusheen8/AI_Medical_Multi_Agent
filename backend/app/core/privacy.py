"""
PHI boundary enforcement utilities.

Provides de-identification, PHI scanning, and redaction to prevent
Protected Health Information from leaking to cloud APIs (Gemini).

Components:
- ``DeIdentifier``: Converts patient records to de-identified metadata
- ``PHIScanner``: Detects PHI patterns in text via regex
- ``validate_cloud_payload()``: Gate that blocks any cloud call containing PHI

Usage::

    scanner = PHIScanner()
    if scanner.contains_phi(text):
        raise PHILeakageError("PHI detected in cloud payload")

    de_id = DeIdentifier()
    safe_context = de_id.de_identify_patient(patient_doc)
"""

import re
from datetime import date, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class PHILeakageError(Exception):
    """Raised when PHI is detected in a payload destined for cloud APIs."""

    def __init__(self, message: str = "PHI detected in cloud-bound payload.") -> None:
        self.message = message
        super().__init__(self.message)


# ── PHI Detection Patterns ──────────────────────────────────────────────

# Common PHI patterns used for scanning
_PHI_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # US Social Security Numbers
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Phone numbers (US format)
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    # Email addresses
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    # Dates of birth (various formats)
    ("dob", re.compile(
        r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"  # MM/DD/YYYY
        r"|\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b"  # YYYY-MM-DD
    )),
    # Medical Record Numbers (MRN) — common patterns
    ("mrn", re.compile(r"\bMRN[:\s#]?\s*\d{4,12}\b", re.IGNORECASE)),
    # US ZIP codes (5-digit or 5+4)
    ("zip", re.compile(r"\b\d{5}(?:-\d{4})?\b")),
]

# Pattern for detecting names — checks for capitalized word sequences
# that look like personal names (2+ capitalized words together).
# Uses [ ] instead of \s to avoid matching across newline boundaries.
_NAME_PATTERN = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?\b")

# Common non-name capitalized phrases to exclude from name detection
_NAME_EXCLUSIONS = frozenset({
    # Geography
    "United States", "New York", "Los Angeles", "San Francisco",
    # Medical facilities
    "Medical Center", "General Hospital", "Health System",
    # Clinical terms
    "Blood Pressure", "Heart Rate", "Body Mass", "White Blood",
    "Red Blood", "Emergency Room", "Intensive Care",
    "Primary Care", "Follow Up", "Side Effect", "Risk Level",
    "High Risk", "Low Risk", "Medium Risk", "Critical Risk",
    "Risk Factor", "Drug Interaction", "Adverse Event",
    # Prompt template phrases (used in coordinator prompts)
    "Patient Profile", "Age bracket", "Symptom Information",
    "Task Type", "Date Range", "Output JSON", "Step by",
    "Generate Step", "Clinical Recommendations", "Clinical Risk",
    "Condition Categories", "Medication Count", "Known Allergies",
    "No Patient", "No patient", "Reasoning Trace", "Reasoning Instructions",
    "Clinical Context", "Patient Context",
    "Assess Risk", "Risk Assessment", "Cardiovascular Risk",
    "Cardiac Distress", "Medical Record", "Medical History",
    "Symptom Categories", "Focus Areas", "Temporal Patterns",
    "Timeline Summary", "Key Events", "Pattern Detection",
    "Structured Analysis", "Narrative Clinical",
})


class PHIScanner:
    """Scans text for Protected Health Information patterns.

    Uses regex-based detection for common PHI types: SSN, phone, email,
    dates of birth, MRNs, and potential personal names.
    """

    def scan(self, text: str) -> list[dict[str, Any]]:
        """Scan text and return a list of detected PHI occurrences.

        Args:
            text: The text to scan for PHI.

        Returns:
            List of dicts with keys: type, match, start, end.
        """
        findings: list[dict[str, Any]] = []

        for phi_type, pattern in _PHI_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({
                    "type": phi_type,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })

        # Name detection (with exclusion list)
        for match in _NAME_PATTERN.finditer(text):
            name = match.group()
            if name not in _NAME_EXCLUSIONS:
                findings.append({
                    "type": "name",
                    "match": name,
                    "start": match.start(),
                    "end": match.end(),
                })

        return findings

    def contains_phi(self, text: str) -> bool:
        """Check whether the given text contains any detectable PHI.

        Args:
            text: The text to check.

        Returns:
            True if PHI is detected, False otherwise.
        """
        return len(self.scan(text)) > 0

    def redact(self, text: str) -> str:
        """Replace all detected PHI in text with [REDACTED].

        Args:
            text: The text to redact.

        Returns:
            Text with PHI replaced by [REDACTED].
        """
        findings = self.scan(text)
        if not findings:
            return text

        # Sort findings by start position (descending) to replace from end
        findings.sort(key=lambda f: f["start"], reverse=True)
        result = text
        for finding in findings:
            result = result[:finding["start"]] + "[REDACTED]" + result[finding["end"]:]
        return result


class DeIdentifier:
    """Converts patient records to de-identified metadata safe for cloud APIs.

    Produces only aggregate/categorical data: age bracket, condition enums,
    sex, risk tier. Never includes names, specific dates, or identifiers.
    """

    @staticmethod
    def _calculate_age_bracket(dob: date | str) -> str:
        """Calculate an age bracket from date of birth.

        Returns a 10-year bracket (e.g., '30-39', '40-49') to prevent
        re-identification from exact age.
        """
        if isinstance(dob, str):
            try:
                dob = date.fromisoformat(dob)
            except ValueError:
                return "unknown"

        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        bracket_start = (age // 10) * 10
        bracket_end = bracket_start + 9
        return f"{bracket_start}-{bracket_end}"

    @staticmethod
    def _categorize_conditions(conditions: list[str]) -> list[str]:
        """Map specific conditions to broader clinical categories.

        This prevents re-identification from rare condition combinations.
        """
        category_map: dict[str, str] = {
            "diabetes": "endocrine",
            "type 1 diabetes": "endocrine",
            "type 2 diabetes": "endocrine",
            "hypothyroidism": "endocrine",
            "hyperthyroidism": "endocrine",
            "hypertension": "cardiovascular",
            "heart failure": "cardiovascular",
            "coronary artery disease": "cardiovascular",
            "atrial fibrillation": "cardiovascular",
            "asthma": "respiratory",
            "copd": "respiratory",
            "pneumonia": "respiratory",
            "depression": "mental_health",
            "anxiety": "mental_health",
            "bipolar disorder": "mental_health",
            "arthritis": "musculoskeletal",
            "osteoporosis": "musculoskeletal",
            "chronic kidney disease": "renal",
            "kidney stones": "renal",
        }

        categories = set()
        for condition in conditions:
            mapped = category_map.get(condition.lower(), "other")
            categories.add(mapped)
        return sorted(categories)

    def de_identify_patient(self, patient_doc: dict[str, Any]) -> dict[str, Any]:
        """Convert a patient document to de-identified metadata.

        Args:
            patient_doc: Raw patient document from MongoDB.

        Returns:
            Dict with only age_bracket, condition_categories, sex, and
            medication_count — no PII or PHI.
        """
        dob = patient_doc.get("dob", "")
        conditions = patient_doc.get("conditions", [])
        sex = patient_doc.get("sex", "unknown")
        medications = patient_doc.get("medications", [])

        return {
            "age_bracket": self._calculate_age_bracket(dob),
            "condition_categories": self._categorize_conditions(conditions),
            "sex": sex,
            "medication_count": len(medications),
            "has_allergies": len(patient_doc.get("allergies", [])) > 0,
        }

    def de_identify_symptoms(self, symptoms_text: str) -> str:
        """Convert raw symptom text to generic categories.

        Replaces specific symptom descriptions with clinical categories
        to prevent patient identification from symptom patterns.

        Args:
            symptoms_text: Raw symptom description from the patient.

        Returns:
            Categorical symptom summary (no raw text).
        """
        symptom_categories: dict[str, list[str]] = {
            "cardiovascular": [
                "chest pain", "palpitations", "shortness of breath",
                "edema", "dizziness", "syncope", "irregular heartbeat",
            ],
            "respiratory": [
                "cough", "wheezing", "dyspnea", "sputum",
                "hemoptysis", "stridor",
            ],
            "neurological": [
                "headache", "migraine", "numbness", "tingling",
                "seizure", "tremor", "weakness", "confusion",
            ],
            "gastrointestinal": [
                "nausea", "vomiting", "diarrhea", "constipation",
                "abdominal pain", "bloating", "heartburn",
            ],
            "musculoskeletal": [
                "joint pain", "back pain", "muscle pain", "stiffness",
                "swelling", "limited mobility",
            ],
            "general": [
                "fever", "fatigue", "weight loss", "weight gain",
                "malaise", "chills", "night sweats",
            ],
        }

        text_lower = symptoms_text.lower()
        detected: list[str] = []

        for category, keywords in symptom_categories.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(category)

        if not detected:
            detected.append("unspecified")

        return f"symptoms_in_categories: {', '.join(sorted(detected))}"


def validate_cloud_payload(payload: dict[str, Any] | str) -> None:
    """Validate that a payload destined for cloud APIs contains no PHI.

    Should be called before every cloud API request (Gemini).

    Args:
        payload: The payload to validate (dict or string).

    Raises:
        PHILeakageError: If PHI is detected in the payload.
    """
    scanner = PHIScanner()

    if isinstance(payload, dict):
        text = str(payload)
    else:
        text = payload

    findings = scanner.scan(text)
    if findings:
        phi_types = list({f["type"] for f in findings})
        logger.warning(
            "phi_leakage_blocked",
            phi_types=phi_types,
            finding_count=len(findings),
        )
        raise PHILeakageError(
            f"Cloud payload contains PHI ({', '.join(phi_types)}). "
            "Request blocked to prevent data leakage."
        )
