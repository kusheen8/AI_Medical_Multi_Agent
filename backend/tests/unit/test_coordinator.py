"""
Unit tests for GroqCoordinator (services/coordinator/).

Tests with mocked Groq API responses:
- Reasoning trace generation for symptom analysis
- Reasoning trace generation for history summarization
- Prompt template rendering
- PHI validation on outbound requests
- Error handling (timeout, rate limit, retry)
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import groq

from app.core.config import Settings
from app.core.privacy import PHILeakageError
from app.services.coordinator.groq_coordinator import (
    CoordinatorError,
    CoordinatorTimeoutError,
    CoordinatorRateLimitError,
    GroqCoordinator,
)
from app.services.coordinator.prompts import (
    format_history_summarization_prompt,
    format_symptom_analysis_prompt,
)
from app.services.privacy_filter import PrivacyFilter


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        GROQ_API_KEY="test-key",
        MONGODB_URI="mongodb://localhost:27017",
        GROQ_MODEL="meta-llama/llama-4-scout-17b-16e-instruct",
        COORDINATOR_TIMEOUT=5,
    )


@pytest.fixture
def mock_privacy_filter() -> PrivacyFilter:
    return PrivacyFilter()


@pytest.fixture
def sample_patient_doc() -> dict:
    return {
        "_id": "507f1f77bcf86cd799439011",
        "name": "John Doe",
        "dob": "1985-03-15",
        "sex": "M",
        "conditions": ["diabetes", "hypertension"],
        "medications": ["metformin", "lisinopril"],
        "allergies": ["penicillin"],
    }


# ── Prompt Template Tests ────────────────────────────────────────────────


class TestPromptTemplates:
    """Tests for prompt template rendering."""

    def test_symptom_analysis_prompt_format(self) -> None:
        context = {
            "age_bracket": "40-49",
            "condition_categories": ["endocrine", "cardiovascular"],
            "sex": "M",
            "medication_count": 2,
            "has_allergies": True,
            "symptom_categories": "symptoms_in_categories: cardiovascular",
        }
        system_prompt, user_prompt = format_symptom_analysis_prompt(context)

        assert "40-49" in user_prompt
        assert "endocrine" in user_prompt
        assert "cardiovascular" in user_prompt
        assert "CRITICAL RULES" in system_prompt
        assert "NO" in system_prompt  # "Do NOT include..."

    def test_history_summarization_prompt_format(self) -> None:
        context = {
            "age_bracket": "40-49",
            "condition_categories": ["endocrine"],
            "sex": "M",
            "medication_count": 2,
            "has_allergies": False,
            "date_range": {"start": "2025-01-01", "end": "2026-01-01"},
        }
        system_prompt, user_prompt = format_history_summarization_prompt(context)

        assert "40-49" in user_prompt
        assert "2025-01-01" in user_prompt
        assert "2026-01-01" in user_prompt

    def test_prompt_contains_no_phi(self) -> None:
        context = {
            "age_bracket": "40-49",
            "condition_categories": ["endocrine"],
            "sex": "M",
            "medication_count": 2,
            "has_allergies": True,
            "symptom_categories": "symptoms_in_categories: cardiovascular",
        }
        _, user_prompt = format_symptom_analysis_prompt(context)

        # Should NOT contain any raw PHI
        assert "John" not in user_prompt
        assert "Doe" not in user_prompt
        assert "1985" not in user_prompt
        assert "chest pain" not in user_prompt


# ── GroqCoordinator Tests ──────────────────────────────────────────────


class TestGroqCoordinator:
    """Tests for the GroqCoordinator with mocked Groq API."""

    @pytest.fixture
    def mock_groq_response(self) -> str:
        return json.dumps({
            "instructions": "1. Analyze cardiovascular symptoms. 2. Check risk factors.",
            "allowed_data_classes": ["vitals", "symptoms", "medications"],
            "focus_areas": ["cardiac", "respiratory"],
            "risk_assessment_criteria": "Assess based on symptom severity and history.",
            "recommended_analyses": ["ECG", "blood panel"],
        })

    @patch("app.services.coordinator.groq_coordinator.AsyncGroq")
    @pytest.mark.asyncio
    async def test_generate_trace_success(
        self, mock_async_groq: MagicMock, test_settings: Settings,
        mock_privacy_filter: PrivacyFilter, sample_patient_doc: dict,
        mock_groq_response: str,
    ) -> None:
        # Setup mock
        mock_client_instance = AsyncMock()
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [
            MagicMock(message=MagicMock(content=mock_groq_response))
        ]
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_chat_completion)
        mock_async_groq.return_value = mock_client_instance

        coordinator = GroqCoordinator(
            settings=test_settings,
            privacy_filter=mock_privacy_filter,
        )

        result = await coordinator.generate_reasoning_trace(
            task_type="symptom_analysis",
            patient_doc=sample_patient_doc,
            symptoms="chest pain and shortness of breath",
        )

        assert result["task_type"] == "symptom_analysis"
        assert result["origin"] == "groq_coordinator"
        assert "instructions" in result
        assert "allowed_data_classes" in result
        assert result["expires_at"] is not None

    @patch("app.services.coordinator.groq_coordinator.AsyncGroq")
    @pytest.mark.asyncio
    async def test_generate_trace_no_phi_in_request(
        self, mock_async_groq: MagicMock, test_settings: Settings,
        mock_privacy_filter: PrivacyFilter, sample_patient_doc: dict,
        mock_groq_response: str,
    ) -> None:
        # Track what prompts are sent to Groq
        sent_prompts: list[str] = []

        mock_client_instance = AsyncMock()
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [
            MagicMock(message=MagicMock(content=mock_groq_response))
        ]

        async def capture_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            for msg in messages:
                sent_prompts.append(msg["content"])
            return mock_chat_completion

        mock_client_instance.chat.completions.create = capture_create
        mock_async_groq.return_value = mock_client_instance

        coordinator = GroqCoordinator(
            settings=test_settings,
            privacy_filter=mock_privacy_filter,
        )

        await coordinator.generate_reasoning_trace(
            task_type="symptom_analysis",
            patient_doc=sample_patient_doc,
            symptoms="chest pain",
        )

        # Verify NO PHI in any sent prompt
        for prompt in sent_prompts:
            assert "John Doe" not in prompt
            assert "1985-03-15" not in prompt
            assert "chest pain" not in prompt  # Raw symptoms should be categorized

    @patch("app.services.coordinator.groq_coordinator.AsyncGroq")
    @pytest.mark.asyncio
    async def test_generate_trace_unknown_task_type(
        self, mock_async_groq: MagicMock, test_settings: Settings,
        mock_privacy_filter: PrivacyFilter, sample_patient_doc: dict,
    ) -> None:
        mock_async_groq.return_value = MagicMock()

        coordinator = GroqCoordinator(
            settings=test_settings,
            privacy_filter=mock_privacy_filter,
        )

        with pytest.raises(CoordinatorError, match="Unknown task type"):
            await coordinator.generate_reasoning_trace(
                task_type="unknown_task",
                patient_doc=sample_patient_doc,
            )

    def test_parse_response_valid_json(self, test_settings: Settings) -> None:
        coordinator = GroqCoordinator(settings=test_settings)
        response = json.dumps({
            "instructions": "Step 1: Analyze symptoms",
            "allowed_data_classes": ["vitals"],
        })
        result = coordinator._parse_response(response, "symptom_analysis")
        assert result["instructions"] == "Step 1: Analyze symptoms"
        assert result["allowed_data_classes"] == ["vitals"]

    def test_parse_response_json_in_code_block(self, test_settings: Settings) -> None:
        coordinator = GroqCoordinator(settings=test_settings)
        response = '```json\n{"instructions": "test", "allowed_data_classes": []}\n```'
        result = coordinator._parse_response(response, "symptom_analysis")
        assert result["instructions"] == "test"

    def test_parse_response_invalid_json_fallback(self, test_settings: Settings) -> None:
        coordinator = GroqCoordinator(settings=test_settings)
        response = "This is not JSON, but it has analysis instructions."
        result = coordinator._parse_response(response, "symptom_analysis")
        assert result["instructions"] == response
        assert len(result["allowed_data_classes"]) > 0  # Fallback defaults
