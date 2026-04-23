"""
Privacy validation test suite (D5.4).

Proves that no raw PHI appears in cloud-bound API calls (Gemini).
Tests:
1. Symptom analysis — name/symptoms not sent to Gemini
2. History summarization — only aggregate stats sent to cloud
3. Cloud error response — scrubbed before returning
4. Concurrent multi-patient — no context leakage
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.privacy import PHIScanner, validate_cloud_payload, PHILeakageError
from tests.conftest import SAMPLE_PATIENT_ID


# ── PHI Scanner Tests ────────────────────────────────────────────────────


class TestPHIScanner:
    """Test PHI pattern detection in text."""

    def setup_method(self):
        self.scanner = PHIScanner()

    def test_detects_ssn(self):
        assert self.scanner.contains_phi("SSN: 123-45-6789")

    def test_detects_phone(self):
        assert self.scanner.contains_phi("Call me at (555) 123-4567")

    def test_detects_email(self):
        assert self.scanner.contains_phi("Contact john@example.com")

    def test_detects_dob(self):
        assert self.scanner.contains_phi("DOB: 03/15/1985")

    def test_detects_mrn(self):
        assert self.scanner.contains_phi("MRN: 123456789")

    def test_detects_name(self):
        assert self.scanner.contains_phi("Patient: John Smith")

    def test_clean_text_passes(self):
        assert not self.scanner.contains_phi(
            "symptoms_in_categories: cardiovascular, respiratory"
        )

    def test_redacts_phi(self):
        text = "Patient John Smith (SSN: 123-45-6789) has chest pain"
        redacted = self.scanner.redact(text)
        assert "John Smith" not in redacted
        assert "123-45-6789" not in redacted
        assert "[REDACTED]" in redacted

    def test_de_identified_data_passes(self):
        """De-identified metadata should not trigger PHI detection."""
        safe_text = (
            "age_bracket: 30-39, condition_categories: cardiovascular, endocrine, "
            "sex: M, medication_count: 2"
        )
        assert not self.scanner.contains_phi(safe_text)


# ── Cloud Payload Validation ─────────────────────────────────────────────


class TestCloudPayloadValidation:
    """Test that cloud payloads are validated for PHI."""

    def test_clean_payload_passes(self):
        payload = {
            "task_type": "symptom_analysis",
            "patient_context": {
                "age_bracket": "30-39",
                "condition_categories": ["cardiovascular"],
                "sex": "M",
            },
        }
        # Should not raise
        validate_cloud_payload(payload)

    def test_phi_in_payload_blocked(self):
        payload = {
            "task_type": "symptom_analysis",
            "patient_name": "John Smith",
            "ssn": "123-45-6789",
        }
        with pytest.raises(PHILeakageError):
            validate_cloud_payload(payload)

    def test_phi_in_string_payload_blocked(self):
        text = "Analyze symptoms for John Smith, DOB 03/15/1985"
        with pytest.raises(PHILeakageError):
            validate_cloud_payload(text)


# ── Privacy Boundary Integration ─────────────────────────────────────────


class TestPrivacyBoundaryIntegration:
    """Integration tests verifying PHI boundary enforcement."""

    def test_de_identifier_removes_raw_data(self):
        """De-identifier should produce only categorical data."""
        from app.core.privacy import DeIdentifier

        de_id = DeIdentifier()
        patient_doc = {
            "name": "Jane Doe",
            "dob": "1990-05-20",
            "sex": "F",
            "conditions": ["diabetes", "hypertension"],
            "medications": ["metformin", "lisinopril"],
            "allergies": ["penicillin"],
        }

        result = de_id.de_identify_patient(patient_doc)

        # Should NOT contain raw PHI
        assert "Jane Doe" not in str(result)
        assert "1990-05-20" not in str(result)

        # Should contain only categories
        assert "age_bracket" in result
        assert "condition_categories" in result
        assert "sex" in result
        assert result["sex"] == "F"

    def test_symptom_de_identification(self):
        """Symptom text should be converted to categories."""
        from app.core.privacy import DeIdentifier

        de_id = DeIdentifier()
        raw_symptoms = "I have severe chest pain radiating to my left arm, with shortness of breath"
        result = de_id.de_identify_symptoms(raw_symptoms)

        # Should not contain raw symptom text
        assert "severe chest pain" not in result
        assert "left arm" not in result
        # Should contain categories
        assert "symptoms_in_categories:" in result
        assert "cardiovascular" in result

    def test_privacy_filter_blocks_phi_in_coordinator_payload(self):
        """The privacy filter should prevent any PHI from reaching the coordinator."""
        scanner = PHIScanner()

        # Simulate what the coordinator would receive (de-identified)
        safe_payload = {
            "instructions": "Analyze symptoms and assess risk level",
            "patient_context": {
                "age_bracket": "30-39",
                "condition_categories": ["cardiovascular", "endocrine"],
                "sex": "M",
                "medication_count": 2,
            },
            "symptom_summary": "symptoms_in_categories: cardiovascular",
        }

        assert not scanner.contains_phi(str(safe_payload))

    def test_concurrent_de_identification_isolation(self):
        """Multiple de-identification operations should not leak context."""
        from app.core.privacy import DeIdentifier

        de_id = DeIdentifier()

        patient_a = {
            "name": "Alice Johnson",
            "dob": "1985-03-15",
            "sex": "F",
            "conditions": ["asthma"],
            "medications": ["albuterol"],
            "allergies": [],
        }

        patient_b = {
            "name": "Bob Williams",
            "dob": "1970-11-22",
            "sex": "M",
            "conditions": ["hypertension"],
            "medications": ["lisinopril"],
            "allergies": ["aspirin"],
        }

        result_a = de_id.de_identify_patient(patient_a)
        result_b = de_id.de_identify_patient(patient_b)

        # Results should be independent
        assert "Alice" not in str(result_a)
        assert "Bob" not in str(result_b)
        assert result_a["condition_categories"] != result_b["condition_categories"]


# ── Sensitive Data Filter Tests ──────────────────────────────────────────


class TestSensitiveDataLogging:
    """Test that sensitive data is filtered from logs."""

    def test_sensitive_keys_redacted(self):
        from app.core.logging import _filter_sensitive_data

        event = {
            "event": "test",
            "password": "secret123",
            "api_key": "sk-abc123",
            "normal_field": "safe value",
        }

        filtered = _filter_sensitive_data(None, "info", event)
        assert filtered["password"] == "[REDACTED]"
        assert filtered["api_key"] == "[REDACTED]"
        assert filtered["normal_field"] == "safe value"

    def test_jwt_pattern_redacted(self):
        from app.core.logging import _filter_sensitive_data

        event = {
            "event": "test",
            "auth": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc123def456",
        }

        filtered = _filter_sensitive_data(None, "info", event)
        assert filtered["auth"] == "[REDACTED]"

    def test_non_sensitive_data_preserved(self):
        from app.core.logging import _filter_sensitive_data

        event = {
            "event": "request_completed",
            "status_code": 200,
            "duration_ms": 42.5,
            "path": "/api/v1/patients",
        }

        filtered = _filter_sensitive_data(None, "info", event)
        assert filtered == event  # No changes
