"""
Unit tests for local agents (medical_analyzer.py and history_summarizer.py).

Tests with mocked Ollama client:
- Medical analyzer output parsing (JSON and fallback)
- Risk level extraction from text
- History summarizer record aggregation
- Error handling (model unavailable, timeout)
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.local_agents.medical_analyzer import AnalysisResult, MedicalAnalyzer
from app.services.local_agents.history_summarizer import (
    HistorySummarizer,
    InsufficientDataError,
    TimelineSummary,
)
from app.services.local_agents.ollama_client import (
    OllamaClient,
    OllamaResponseError,
    OllamaUnavailableError,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_ollama_client() -> MagicMock:
    client = MagicMock(spec=OllamaClient)
    client.generate = AsyncMock()
    client.is_available = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_record_repo() -> MagicMock:
    from app.db.repositories.medical_record_repository import MedicalRecordRepository
    repo = MagicMock(spec=MedicalRecordRepository)
    repo.list_by_patient_id = AsyncMock()
    return repo


@pytest.fixture
def sample_trace() -> dict:
    return {
        "task_type": "symptom_analysis",
        "instructions": "1. Analyze cardiovascular symptoms. 2. Check risk factors.",
        "allowed_data_classes": ["vitals", "symptoms", "medications"],
        "origin": "gemini_coordinator",
    }


@pytest.fixture
def sample_patient() -> dict:
    return {
        "_id": "507f1f77bcf86cd799439011",
        "name": "John Doe",
        "dob": "1985-03-15",
        "sex": "M",
        "conditions": ["diabetes", "hypertension"],
        "medications": ["metformin", "lisinopril"],
        "allergies": ["penicillin"],
    }


# ── MedicalAnalyzer Tests ──────────────────────────────────────────────


class TestMedicalAnalyzer:
    """Tests for the local medical analyzer."""

    @pytest.mark.asyncio
    async def test_analyze_structured_json_response(
        self, mock_ollama_client: MagicMock, sample_trace: dict, sample_patient: dict,
    ) -> None:
        response = json.dumps({
            "entities": {"chest_pain": "acute", "dyspnea": "moderate"},
            "risk_level": "high",
            "recommendations": ["ECG", "Troponin test"],
            "analysis_text": "Patient shows signs of acute cardiac distress.",
        })
        mock_ollama_client.generate.return_value = response

        analyzer = MedicalAnalyzer(ollama_client=mock_ollama_client)
        result = await analyzer.analyze(
            trace=sample_trace,
            patient_doc=sample_patient,
            symptoms="chest pain and shortness of breath",
        )

        assert isinstance(result, AnalysisResult)
        assert result.risk_level == "high"
        assert "chest_pain" in result.entities
        assert len(result.recommendations) == 2
        assert result.analysis_text != ""

    @pytest.mark.asyncio
    async def test_analyze_fallback_on_invalid_json(
        self, mock_ollama_client: MagicMock, sample_trace: dict, sample_patient: dict,
    ) -> None:
        mock_ollama_client.generate.return_value = (
            "The patient appears to have high risk cardiac symptoms. "
            "Recommend immediate evaluation."
        )

        analyzer = MedicalAnalyzer(ollama_client=mock_ollama_client)
        result = await analyzer.analyze(
            trace=sample_trace,
            patient_doc=sample_patient,
            symptoms="chest pain",
        )

        assert isinstance(result, AnalysisResult)
        assert result.risk_level == "high"  # Extracted from "high risk"
        assert result.analysis_text != ""

    @pytest.mark.asyncio
    async def test_analyze_json_in_code_block(
        self, mock_ollama_client: MagicMock, sample_trace: dict, sample_patient: dict,
    ) -> None:
        response = '```json\n{"entities": {}, "risk_level": "low", "recommendations": [], "analysis_text": "Normal."}\n```'
        mock_ollama_client.generate.return_value = response

        analyzer = MedicalAnalyzer(ollama_client=mock_ollama_client)
        result = await analyzer.analyze(
            trace=sample_trace,
            patient_doc=sample_patient,
            symptoms="mild headache",
        )

        assert result.risk_level == "low"
        assert result.analysis_text == "Normal."

    @pytest.mark.asyncio
    async def test_analyze_ollama_unavailable(
        self, mock_ollama_client: MagicMock, sample_trace: dict, sample_patient: dict,
    ) -> None:
        mock_ollama_client.generate.side_effect = OllamaUnavailableError("Connection refused")

        analyzer = MedicalAnalyzer(ollama_client=mock_ollama_client)
        with pytest.raises(OllamaUnavailableError):
            await analyzer.analyze(
                trace=sample_trace,
                patient_doc=sample_patient,
                symptoms="chest pain",
            )

    def test_validate_risk_level(self) -> None:
        assert MedicalAnalyzer._validate_risk_level("high") == "high"
        assert MedicalAnalyzer._validate_risk_level("HIGH") == "high"
        assert MedicalAnalyzer._validate_risk_level("  medium  ") == "medium"
        assert MedicalAnalyzer._validate_risk_level("invalid") == "low"

    def test_extract_risk_from_text(self) -> None:
        assert MedicalAnalyzer._extract_risk_from_text("critical condition") == "critical"
        assert MedicalAnalyzer._extract_risk_from_text("high risk") == "high"
        assert MedicalAnalyzer._extract_risk_from_text("moderate risk") == "medium"
        assert MedicalAnalyzer._extract_risk_from_text("normal findings") == "low"

    def test_analysis_result_to_dict(self) -> None:
        result = AnalysisResult(
            entities={"test": "value"},
            risk_level="high",
            recommendations=["rec1"],
            analysis_text="Analysis",
        )
        d = result.to_dict()
        assert d["entities"] == {"test": "value"}
        assert d["risk_level"] == "high"
        assert "raw_response" not in d


# ── HistorySummarizer Tests ──────────────────────────────────────────────


class TestHistorySummarizer:
    """Tests for the local history summarizer."""

    @pytest.mark.asyncio
    async def test_summarize_success(
        self, mock_ollama_client: MagicMock, mock_record_repo: MagicMock,
        sample_trace: dict, sample_patient: dict,
    ) -> None:
        # Setup mock records
        mock_record_repo.list_by_patient_id.return_value = {
            "items": [
                {
                    "_id": "rec1",
                    "patient_id": "p1",
                    "symptoms": "headache",
                    "risk_level": "low",
                    "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
                },
                {
                    "_id": "rec2",
                    "patient_id": "p1",
                    "symptoms": "chest pain",
                    "risk_level": "high",
                    "created_at": datetime(2025, 9, 1, tzinfo=timezone.utc),
                },
                {
                    "_id": "rec3",
                    "patient_id": "p1",
                    "symptoms": "fatigue",
                    "risk_level": "medium",
                    "created_at": datetime(2025, 12, 1, tzinfo=timezone.utc),
                },
            ],
            "total": 3,
            "page": 1,
            "page_size": 50,
            "pages": 1,
        }

        response = json.dumps({
            "key_events": [{"date": "2025-09-01", "event": "Cardiac symptoms", "significance": "high"}],
            "patterns": ["Escalating risk levels over 6 months"],
            "clinical_context": "Progressive cardiovascular deterioration.",
        })
        mock_ollama_client.generate.return_value = response

        summarizer = HistorySummarizer(
            ollama_client=mock_ollama_client,
            record_repository=mock_record_repo,
        )
        result = await summarizer.summarize(
            trace=sample_trace,
            patient_doc=sample_patient,
            patient_id="p1",
            date_range={"start": "2025-01-01", "end": "2026-01-01"},
        )

        assert isinstance(result, TimelineSummary)
        assert result.record_count == 3
        assert len(result.key_events) == 1
        assert len(result.patterns) == 1
        assert result.clinical_context != ""

    @pytest.mark.asyncio
    async def test_summarize_insufficient_data(
        self, mock_ollama_client: MagicMock, mock_record_repo: MagicMock,
        sample_trace: dict, sample_patient: dict,
    ) -> None:
        mock_record_repo.list_by_patient_id.return_value = {
            "items": [{"_id": "rec1", "symptoms": "headache", "created_at": datetime.now(timezone.utc)}],
            "total": 1,
            "page": 1,
            "page_size": 50,
            "pages": 1,
        }

        summarizer = HistorySummarizer(
            ollama_client=mock_ollama_client,
            record_repository=mock_record_repo,
        )
        with pytest.raises(InsufficientDataError):
            await summarizer.summarize(
                trace=sample_trace,
                patient_doc=sample_patient,
                patient_id="p1",
            )

    @pytest.mark.asyncio
    async def test_summarize_fallback_on_bad_json(
        self, mock_ollama_client: MagicMock, mock_record_repo: MagicMock,
        sample_trace: dict, sample_patient: dict,
    ) -> None:
        mock_record_repo.list_by_patient_id.return_value = {
            "items": [
                {"_id": "rec1", "symptoms": "headache", "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc)},
                {"_id": "rec2", "symptoms": "fatigue", "created_at": datetime(2025, 9, 1, tzinfo=timezone.utc)},
            ],
            "total": 2,
            "page": 1,
            "page_size": 50,
            "pages": 1,
        }
        mock_ollama_client.generate.return_value = "Not valid JSON but contains analysis."

        summarizer = HistorySummarizer(
            ollama_client=mock_ollama_client,
            record_repository=mock_record_repo,
        )
        result = await summarizer.summarize(
            trace=sample_trace,
            patient_doc=sample_patient,
            patient_id="p1",
        )

        assert isinstance(result, TimelineSummary)
        assert result.clinical_context != ""
        assert result.record_count == 2

    def test_timeline_summary_to_dict(self) -> None:
        summary = TimelineSummary(
            key_events=[{"date": "2025-01-01", "event": "test"}],
            patterns=["pattern1"],
            clinical_context="context",
            record_count=5,
            date_range={"start": "2025-01-01", "end": "2025-12-31"},
        )
        d = summary.to_dict()
        assert d["record_count"] == 5
        assert "raw_response" not in d
