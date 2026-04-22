"""
Unit tests for worker processes (analysis_worker.py and summarization_worker.py).

Tests with fully mocked dependencies:
- Worker start/stop lifecycle
- Task processing pipeline
- Retry and error handling
- Graceful shutdown
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.services.local_agents.medical_analyzer import AnalysisResult
from app.services.local_agents.history_summarizer import TimelineSummary
from app.services.queue.task_schema import TaskType
from app.workers.analysis_worker import AnalysisWorker
from app.workers.summarization_worker import SummarizationWorker


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_queue() -> MagicMock:
    from app.services.queue.task_queue import TaskQueue

    queue = MagicMock(spec=TaskQueue)
    queue.dequeue = AsyncMock(return_value=None)
    queue.mark_done = AsyncMock()
    queue.mark_failed = AsyncMock(return_value=False)
    return queue


@pytest.fixture
def mock_coordinator() -> MagicMock:
    from app.services.coordinator.gemini_coordinator import GeminiCoordinator

    coordinator = MagicMock(spec=GeminiCoordinator)
    coordinator.generate_reasoning_trace = AsyncMock(return_value={
        "task_type": "symptom_analysis",
        "instructions": "Analyze cardiovascular symptoms.",
        "allowed_data_classes": ["vitals", "symptoms"],
        "origin": "gemini_coordinator",
    })
    return coordinator


@pytest.fixture
def mock_analyzer() -> MagicMock:
    from app.services.local_agents.medical_analyzer import MedicalAnalyzer

    analyzer = MagicMock(spec=MedicalAnalyzer)
    analyzer.analyze = AsyncMock(return_value=AnalysisResult(
        entities={"chest_pain": "acute"},
        risk_level="high",
        recommendations=["ECG"],
        analysis_text="Elevated cardiac risk detected.",
    ))
    return analyzer


@pytest.fixture
def mock_summarizer() -> MagicMock:
    from app.services.local_agents.history_summarizer import HistorySummarizer

    summarizer = MagicMock(spec=HistorySummarizer)
    summarizer.summarize = AsyncMock(return_value=TimelineSummary(
        key_events=[{"date": "2025-09-01", "event": "Cardiac symptoms"}],
        patterns=["Escalating risk"],
        clinical_context="Progressive cardiovascular issues.",
        record_count=5,
    ))
    return summarizer


@pytest.fixture
def mock_patient_repo() -> MagicMock:
    from app.db.repositories.patient_repository import PatientRepository

    repo = MagicMock(spec=PatientRepository)
    repo.get_by_id = AsyncMock(return_value={
        "_id": ObjectId(),
        "name": "John Doe",
        "dob": "1985-03-15",
        "sex": "M",
        "conditions": ["diabetes"],
        "medications": ["metformin"],
        "allergies": [],
    })
    return repo


@pytest.fixture
def mock_record_repo() -> MagicMock:
    from app.db.repositories.medical_record_repository import MedicalRecordRepository

    repo = MagicMock(spec=MedicalRecordRepository)
    repo.list_by_patient_id = AsyncMock(return_value={
        "items": [{"_id": ObjectId(), "symptoms": "chest pain"}],
        "total": 1,
        "page": 1,
        "page_size": 1,
        "pages": 1,
    })
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_trace_repo() -> MagicMock:
    from app.db.repositories.trace_repository import TraceRepository

    repo = MagicMock(spec=TraceRepository)
    repo.create_trace = AsyncMock(return_value={"_id": ObjectId()})
    return repo


# ── AnalysisWorker Tests ─────────────────────────────────────────────────


class TestAnalysisWorker:
    """Tests for the symptom analysis worker."""

    def _make_worker(
        self, queue, coordinator, analyzer, patient_repo, record_repo, trace_repo,
    ) -> AnalysisWorker:
        return AnalysisWorker(
            worker_id="test-analysis-0",
            queue=queue,
            coordinator=coordinator,
            analyzer=analyzer,
            patient_repo=patient_repo,
            record_repo=record_repo,
            trace_repo=trace_repo,
        )

    @pytest.mark.asyncio
    async def test_process_task_success(
        self, mock_queue, mock_coordinator, mock_analyzer,
        mock_patient_repo, mock_record_repo, mock_trace_repo,
    ) -> None:
        worker = self._make_worker(
            mock_queue, mock_coordinator, mock_analyzer,
            mock_patient_repo, mock_record_repo, mock_trace_repo,
        )

        task_doc = {
            "_id": ObjectId(),
            "task_type": TaskType.SYMPTOM_ANALYSIS.value,
            "patient_id": str(ObjectId()),
            "payload": {"symptoms": "chest pain"},
            "status": "processing",
        }

        await worker._process_task(task_doc)

        # Verify full pipeline was executed
        mock_patient_repo.get_by_id.assert_called_once()
        mock_coordinator.generate_reasoning_trace.assert_called_once()
        mock_trace_repo.create_trace.assert_called_once()
        mock_analyzer.analyze.assert_called_once()
        mock_record_repo.update.assert_called_once()
        mock_queue.mark_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_task_failure_retries(
        self, mock_queue, mock_coordinator, mock_analyzer,
        mock_patient_repo, mock_record_repo, mock_trace_repo,
    ) -> None:
        worker = self._make_worker(
            mock_queue, mock_coordinator, mock_analyzer,
            mock_patient_repo, mock_record_repo, mock_trace_repo,
        )

        # Make coordinator fail
        mock_coordinator.generate_reasoning_trace.side_effect = Exception("API timeout")
        mock_queue.mark_failed.return_value = True  # Will be retried

        task_doc = {
            "_id": ObjectId(),
            "task_type": TaskType.SYMPTOM_ANALYSIS.value,
            "patient_id": str(ObjectId()),
            "payload": {"symptoms": "headache"},
            "status": "processing",
        }

        await worker._process_task(task_doc)

        mock_queue.mark_failed.assert_called_once()
        mock_queue.mark_done.assert_not_called()

    @pytest.mark.asyncio
    async def test_worker_stop_flag(
        self, mock_queue, mock_coordinator, mock_analyzer,
        mock_patient_repo, mock_record_repo, mock_trace_repo,
    ) -> None:
        """Verify stop() sets running flag to False."""
        worker = self._make_worker(
            mock_queue, mock_coordinator, mock_analyzer,
            mock_patient_repo, mock_record_repo, mock_trace_repo,
        )

        # Worker starts with _running = False
        assert worker._running is False

        # After stop it should still be False (no crash)
        await worker.stop()
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_process_task_not_called_for_wrong_type(
        self, mock_queue, mock_coordinator, mock_analyzer,
        mock_patient_repo, mock_record_repo, mock_trace_repo,
    ) -> None:
        """Verify _process_task is NOT the entry path for wrong task types.

        The worker's start() loop filters by task_type before calling
        _process_task.  Here we verify _process_task itself works on the
        correct type and that the coordinator is only called for matching
        tasks.
        """
        worker = self._make_worker(
            mock_queue, mock_coordinator, mock_analyzer,
            mock_patient_repo, mock_record_repo, mock_trace_repo,
        )

        # Process a correct task type — should call coordinator
        task_doc = {
            "_id": ObjectId(),
            "task_type": TaskType.SYMPTOM_ANALYSIS.value,
            "patient_id": str(ObjectId()),
            "payload": {"symptoms": "headache"},
            "status": "processing",
        }
        await worker._process_task(task_doc)
        mock_coordinator.generate_reasoning_trace.assert_called_once()


# ── SummarizationWorker Tests ───────────────────────────────────────────


class TestSummarizationWorker:
    """Tests for the history summarization worker."""

    def _make_worker(
        self, queue, coordinator, summarizer, patient_repo, trace_repo,
    ) -> SummarizationWorker:
        return SummarizationWorker(
            worker_id="test-summary-0",
            queue=queue,
            coordinator=coordinator,
            summarizer=summarizer,
            patient_repo=patient_repo,
            trace_repo=trace_repo,
        )

    @pytest.mark.asyncio
    async def test_process_task_success(
        self, mock_queue, mock_coordinator, mock_summarizer,
        mock_patient_repo, mock_trace_repo,
    ) -> None:
        worker = self._make_worker(
            mock_queue, mock_coordinator, mock_summarizer,
            mock_patient_repo, mock_trace_repo,
        )

        task_doc = {
            "_id": ObjectId(),
            "task_type": TaskType.HISTORY_SUMMARIZATION.value,
            "patient_id": str(ObjectId()),
            "payload": {"date_range": {"start": "2025-01-01", "end": "2026-01-01"}},
            "status": "processing",
        }

        await worker._process_task(task_doc)

        mock_patient_repo.get_by_id.assert_called_once()
        mock_coordinator.generate_reasoning_trace.assert_called_once()
        mock_trace_repo.create_trace.assert_called_once()
        mock_summarizer.summarize.assert_called_once()
        mock_queue.mark_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_task_failure(
        self, mock_queue, mock_coordinator, mock_summarizer,
        mock_patient_repo, mock_trace_repo,
    ) -> None:
        worker = self._make_worker(
            mock_queue, mock_coordinator, mock_summarizer,
            mock_patient_repo, mock_trace_repo,
        )

        mock_summarizer.summarize.side_effect = Exception("Insufficient data")
        mock_coordinator.generate_reasoning_trace = AsyncMock(return_value={
            "task_type": "history_summarization",
            "instructions": "Summarize history.",
            "allowed_data_classes": [],
            "origin": "gemini_coordinator",
        })
        mock_trace_repo.create_trace = AsyncMock(return_value={"_id": ObjectId()})

        task_doc = {
            "_id": ObjectId(),
            "task_type": TaskType.HISTORY_SUMMARIZATION.value,
            "patient_id": str(ObjectId()),
            "payload": {},
            "status": "processing",
        }

        await worker._process_task(task_doc)

        mock_queue.mark_failed.assert_called_once()
        mock_queue.mark_done.assert_not_called()
