"""
Privacy filter service for preparing cloud-safe contexts.

Wraps ``DeIdentifier`` and ``PHIScanner`` into a single service class
used by the coordinator and API layer to ensure PHI never reaches
cloud APIs.

Usage::

    privacy_filter = PrivacyFilter()
    safe_context = privacy_filter.prepare_coordinator_context(patient_doc, symptoms)
    clean_response = privacy_filter.sanitize_response(raw_response)
"""

from typing import Any

import structlog

from app.core.privacy import DeIdentifier, PHIScanner, validate_cloud_payload

logger = structlog.get_logger(__name__)


class PrivacyFilter:
    """High-level privacy service composing de-identification and scanning.

    Used by the coordinator to prepare safe payloads and by the API
    layer to sanitize responses before returning to the frontend.
    """

    def __init__(self) -> None:
        self._de_identifier = DeIdentifier()
        self._scanner = PHIScanner()

    def prepare_coordinator_context(
        self,
        patient_doc: dict[str, Any],
        symptoms: str | None = None,
        date_range: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Prepare a de-identified context dictionary for the cloud coordinator.

        This is the ONLY data that should be sent to Gemini.

        Args:
            patient_doc: Raw patient document from MongoDB.
            symptoms: Optional raw symptom text (will be categorized).
            date_range: Optional date range for history queries.

        Returns:
            De-identified context dict safe for cloud transmission.

        Raises:
            PHILeakageError: If the resulting context still contains PHI.
        """
        context = self._de_identifier.de_identify_patient(patient_doc)

        if symptoms:
            context["symptom_categories"] = self._de_identifier.de_identify_symptoms(symptoms)

        if date_range:
            context["date_range"] = date_range

        # Final validation — belt and suspenders
        validate_cloud_payload(context)

        return context

    def sanitize_response(self, response_text: str) -> str:
        """Strip any PHI that might appear in a response before returning to frontend.

        This is a safety net for cases where model outputs accidentally
        include patient information.

        Args:
            response_text: Raw response text from any model.

        Returns:
            Sanitized text with any detected PHI redacted.
        """
        if self._scanner.contains_phi(response_text):
            redacted = self._scanner.redact(response_text)
            logger.warning(
                "response_phi_redacted",
                original_length=len(response_text),
                redacted_length=len(redacted),
            )
            return redacted
        return response_text

    def scan_text(self, text: str) -> list[dict[str, Any]]:
        """Scan text for PHI — useful for audit and testing.

        Args:
            text: Text to scan.

        Returns:
            List of PHI finding dicts.
        """
        return self._scanner.scan(text)

    def contains_phi(self, text: str) -> bool:
        """Check whether text contains PHI.

        Args:
            text: Text to check.

        Returns:
            True if PHI detected.
        """
        return self._scanner.contains_phi(text)
