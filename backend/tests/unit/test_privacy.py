"""
Unit tests for PHI boundary enforcement (core/privacy.py and services/privacy_filter.py).

Tests:
- PHI detection (SSNs, phone numbers, emails, DOBs, names, MRNs)
- De-identification produces no raw PHI
- Redaction replaces PHI with [REDACTED]
- validate_cloud_payload blocks PHI
- PrivacyFilter integration
"""

import pytest

from app.core.privacy import (
    DeIdentifier,
    PHILeakageError,
    PHIScanner,
    validate_cloud_payload,
)
from app.services.privacy_filter import PrivacyFilter


# ── PHIScanner Tests ─────────────────────────────────────────────────────


class TestPHIScanner:
    """Tests for PHI pattern detection and redaction."""

    def setup_method(self) -> None:
        self.scanner = PHIScanner()

    def test_detects_ssn(self) -> None:
        text = "Patient SSN is 123-45-6789"
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "ssn" in types

    def test_detects_phone_number(self) -> None:
        text = "Contact at (555) 123-4567"
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "phone" in types

    def test_detects_email(self) -> None:
        text = "Email: john.doe@hospital.com"
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "email" in types

    def test_detects_dob_mmddyyyy(self) -> None:
        text = "Date of birth: 03/15/1985"
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "dob" in types

    def test_detects_dob_yyyymmdd(self) -> None:
        text = "DOB: 1985-03-15"
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "dob" in types

    def test_detects_mrn(self) -> None:
        text = "MRN: 123456789"
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "mrn" in types

    def test_detects_names(self) -> None:
        text = "Patient John Doe presented with symptoms."
        findings = self.scanner.scan(text)
        types = [f["type"] for f in findings]
        assert "name" in types

    def test_excludes_medical_terms_from_names(self) -> None:
        text = "Blood Pressure was elevated. Heart Rate normal."
        findings = self.scanner.scan(text)
        name_findings = [f for f in findings if f["type"] == "name"]
        name_matches = [f["match"] for f in name_findings]
        assert "Blood Pressure" not in name_matches
        assert "Heart Rate" not in name_matches

    def test_contains_phi_positive(self) -> None:
        text = "Patient John Doe has SSN 123-45-6789"
        assert self.scanner.contains_phi(text) is True

    def test_contains_phi_negative(self) -> None:
        text = "symptoms_in_categories: cardiovascular, respiratory"
        assert self.scanner.contains_phi(text) is False

    def test_redact_replaces_phi(self) -> None:
        text = "Patient SSN is 123-45-6789, email john@test.com"
        redacted = self.scanner.redact(text)
        assert "123-45-6789" not in redacted
        assert "john@test.com" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_no_phi_returns_original(self) -> None:
        text = "No sensitive information here."
        assert self.scanner.redact(text) == text

    def test_scan_empty_string(self) -> None:
        assert self.scanner.scan("") == []

    def test_multiple_phi_types_detected(self) -> None:
        text = "John Smith SSN 123-45-6789 phone (555) 111-2222 email j@x.com"
        findings = self.scanner.scan(text)
        types = set(f["type"] for f in findings)
        assert len(types) >= 3  # name, ssn, phone, email


# ── DeIdentifier Tests ───────────────────────────────────────────────────


class TestDeIdentifier:
    """Tests for patient de-identification."""

    def setup_method(self) -> None:
        self.de_id = DeIdentifier()

    def test_de_identify_patient_basic(self) -> None:
        patient_doc = {
            "name": "John Doe",
            "dob": "1985-03-15",
            "sex": "M",
            "conditions": ["diabetes", "hypertension"],
            "medications": ["metformin", "lisinopril"],
            "allergies": ["penicillin"],
        }
        result = self.de_id.de_identify_patient(patient_doc)

        # Should NOT contain raw PHI
        assert "John Doe" not in str(result)
        assert "1985-03-15" not in str(result)

        # Should contain de-identified data
        assert "age_bracket" in result
        assert "condition_categories" in result
        assert result["sex"] == "M"
        assert result["medication_count"] == 2
        assert result["has_allergies"] is True

    def test_age_bracket_calculation(self) -> None:
        # For someone born in 1985, as of 2026 they are ~40-41
        result = self.de_id._calculate_age_bracket("1985-03-15")
        assert result in ("40-49",)  # Age 40-41 → bracket 40-49

    def test_age_bracket_invalid_dob(self) -> None:
        result = self.de_id._calculate_age_bracket("invalid")
        assert result == "unknown"

    def test_condition_categorization(self) -> None:
        conditions = ["diabetes", "hypertension", "asthma"]
        categories = self.de_id._categorize_conditions(conditions)
        assert "endocrine" in categories
        assert "cardiovascular" in categories
        assert "respiratory" in categories

    def test_condition_categorization_unknown(self) -> None:
        conditions = ["rare_condition_xyz"]
        categories = self.de_id._categorize_conditions(conditions)
        assert "other" in categories

    def test_de_identify_symptoms(self) -> None:
        symptoms = "chest pain and shortness of breath"
        result = self.de_id.de_identify_symptoms(symptoms)
        assert "chest pain" not in result
        assert "shortness of breath" not in result
        assert "cardiovascular" in result

    def test_de_identify_symptoms_unspecified(self) -> None:
        symptoms = "feeling weird"
        result = self.de_id.de_identify_symptoms(symptoms)
        assert "unspecified" in result

    def test_de_identify_patient_empty_fields(self) -> None:
        patient_doc = {"sex": "F"}
        result = self.de_id.de_identify_patient(patient_doc)
        assert result["age_bracket"] == "unknown"
        assert result["condition_categories"] == []
        assert result["medication_count"] == 0
        assert result["has_allergies"] is False


# ── validate_cloud_payload Tests ─────────────────────────────────────────


class TestValidateCloudPayload:
    """Tests for cloud payload validation."""

    def test_blocks_phi_in_dict(self) -> None:
        payload = {"patient_name": "John Doe", "ssn": "123-45-6789"}
        with pytest.raises(PHILeakageError):
            validate_cloud_payload(payload)

    def test_blocks_phi_in_string(self) -> None:
        payload = "Patient John Smith has SSN 123-45-6789"
        with pytest.raises(PHILeakageError):
            validate_cloud_payload(payload)

    def test_allows_safe_payload(self) -> None:
        payload = {
            "age_bracket": "40-49",
            "condition_categories": ["endocrine", "cardiovascular"],
            "sex": "M",
        }
        # Should not raise
        validate_cloud_payload(payload)


# ── PrivacyFilter Tests ──────────────────────────────────────────────────


class TestPrivacyFilter:
    """Tests for the high-level PrivacyFilter service."""

    def setup_method(self) -> None:
        self.filter = PrivacyFilter()

    def test_prepare_coordinator_context_safe(self) -> None:
        patient_doc = {
            "name": "Jane Smith",
            "dob": "1990-06-20",
            "sex": "F",
            "conditions": ["asthma"],
            "medications": ["albuterol"],
            "allergies": [],
        }
        context = self.filter.prepare_coordinator_context(
            patient_doc=patient_doc,
            symptoms="cough and wheezing",
        )

        # Should not contain raw PHI
        assert "Jane Smith" not in str(context)
        assert "1990-06-20" not in str(context)
        assert "cough" not in str(context)
        assert "wheezing" not in str(context)

        # Should contain de-identified data
        assert "age_bracket" in context
        assert "symptom_categories" in context
        assert "respiratory" in context["symptom_categories"]

    def test_sanitize_response_clean(self) -> None:
        response = "The patient shows signs of cardiovascular risk."
        result = self.filter.sanitize_response(response)
        assert result == response

    def test_sanitize_response_with_phi(self) -> None:
        response = "John Doe (SSN 123-45-6789) shows cardiac risk."
        result = self.filter.sanitize_response(response)
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_contains_phi_check(self) -> None:
        assert self.filter.contains_phi("John Doe is sick") is True
        assert self.filter.contains_phi("cardiovascular symptoms noted") is False

    def test_scan_text(self) -> None:
        findings = self.filter.scan_text("Email: test@example.com")
        assert len(findings) > 0
        assert findings[0]["type"] == "email"
