"""
Summarization worker — background executor for history summarization tasks.

Polls the task queue for ``history_summarization`` tasks and executes them
through the hybrid pipeline:
1. Generate reasoning trace via cloud coordinator (Gemini, no PHI)
2. Execute trace locally via history summarizer (MedGemma)
3. Store results and reasoning trace

Error handling mirrors AnalysisWorker: retry, backoff, DLQ, graceful shutdown.
"""

import asyncio
from typing import Any

import structlog

from app.db.repositories.patient_repository import PatientRepository
from app.db.repositories.trace_repository import TraceRepository
from app.services.coordinator.gemini_coordinator import GeminiCoordinator
from app.services.local_agents.history_summarizer import HistorySummarizer
from app.services.queue.task_queue import TaskQueue
from app.services.queue.task_schema import TaskType

logger = structlog.get_logger(__name__)


class SummarizationWorker:
    """Background worker that processes history summarization tasks.

    Attributes:
        _queue: Task queue to poll.
        _coordinator: Cloud coordinator for reasoning trace generation.
        _summarizer: Local history summarizer for PHI processing.
        _patient_repo: Repository for patient data access.
        _trace_repo: Repository for storing reasoning traces.
        _running: Flag controlling the polling loop.
        _worker_id: Identifier for logging.
    """

    def __init__(
        self,
        worker_id: str,
        queue: TaskQueue,
        coordinator: GeminiCoordinator,
        summarizer: HistorySummarizer,
        patient_repo: PatientRepository,
        trace_repo: TraceRepository,
    ) -> None:
        self._worker_id = worker_id
        self._queue = queue
        self._coordinator = coordinator
        self._summarizer = summarizer
        self._patient_repo = patient_repo
        self._trace_repo = trace_repo
        self._running = False

    async def start(self) -> None:
        """Start the worker polling loop."""
        self._running = True
        await logger.ainfo("summarization_worker_started", worker_id=self._worker_id)

        while self._running:
            try:
                task_doc = await self._queue.dequeue(timeout=1.0)
                if task_doc is None:
                    continue

                # Only process history_summarization tasks
                if task_doc.get("task_type") != TaskType.HISTORY_SUMMARIZATION.value:
                    continue

                await self._process_task(task_doc)

            except asyncio.CancelledError:
                await logger.ainfo(
                    "summarization_worker_cancelled",
                    worker_id=self._worker_id,
                )
                break
            except Exception:
                await logger.aerror(
                    "summarization_worker_poll_error",
                    worker_id=self._worker_id,
                    exc_info=True,
                )
                await asyncio.sleep(1)

        await logger.ainfo("summarization_worker_stopped", worker_id=self._worker_id)

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self._running = False
        await logger.ainfo("summarization_worker_stopping", worker_id=self._worker_id)

    async def _process_task(self, task_doc: dict[str, Any]) -> None:
        """Process a single history summarization task.

        Pipeline:
        1. Fetch patient data
        2. Generate reasoning trace via coordinator
        3. Execute summarization via local summarizer
        4. Store trace and task result

        Args:
            task_doc: The task document from MongoDB.
        """
        task_id = str(task_doc["_id"])
        patient_id = task_doc["patient_id"]
        payload = task_doc.get("payload", {})
        date_range = payload.get("date_range")

        await logger.ainfo(
            "summarization_task_started",
            worker_id=self._worker_id,
            task_id=task_id,
            patient_id=patient_id,
        )

        try:
            # Step 1: Fetch patient
            patient_doc = await self._patient_repo.get_by_id(patient_id)

            # Step 2: Generate reasoning trace (cloud, no PHI)
            trace_data = await self._coordinator.generate_reasoning_trace(
                task_type="history_summarization",
                patient_doc=patient_doc,
                date_range=date_range,
            )

            # Step 3: Store reasoning trace
            trace_data["task_id"] = task_id
            trace_data["patient_id"] = patient_id
            trace_doc = await self._trace_repo.create_trace(trace_data)
            trace_id = str(trace_doc["_id"])

            # Step 4: Execute local summarization (with PHI)
            summary = await self._summarizer.summarize(
                trace=trace_data,
                patient_doc=patient_doc,
                patient_id=patient_id,
                date_range=date_range,
            )

            # Step 5: Mark task done
            await self._queue.mark_done(
                task_id=task_id,
                result=summary.to_dict(),
                trace_id=trace_id,
            )

            await logger.ainfo(
                "summarization_task_completed",
                worker_id=self._worker_id,
                task_id=task_id,
                record_count=summary.record_count,
            )

        except Exception as exc:
            await logger.aerror(
                "summarization_task_failed",
                worker_id=self._worker_id,
                task_id=task_id,
                error=str(exc),
                exc_info=True,
            )
            retried = await self._queue.mark_failed(task_id, str(exc))
            if not retried:
                await logger.awarning(
                    "summarization_task_sent_to_dlq",
                    worker_id=self._worker_id,
                    task_id=task_id,
                )
