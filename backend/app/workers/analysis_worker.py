"""
Analysis worker — background executor for symptom analysis tasks.

Polls the task queue for ``symptom_analysis`` tasks and executes them
through the hybrid pipeline:
1. Generate reasoning trace via cloud coordinator (Gemini, no PHI)
2. Execute trace locally against PHI via medical analyzer (MedGemma)
3. Store results in the medical record
4. Store reasoning trace for audit trail

Error handling:
- Retry with exponential backoff (max 3 attempts)
- Dead-letter queue for permanently failed tasks
- Graceful shutdown: completes in-flight task before stopping
"""

import asyncio
from typing import Any

import structlog

from app.db.repositories.medical_record_repository import MedicalRecordRepository
from app.db.repositories.patient_repository import PatientRepository
from app.db.repositories.trace_repository import TraceRepository
from app.services.coordinator.gemini_coordinator import GeminiCoordinator
from app.services.local_agents.medical_analyzer import MedicalAnalyzer
from app.services.queue.task_queue import TaskQueue
from app.services.queue.task_schema import TaskType

logger = structlog.get_logger(__name__)


class AnalysisWorker:
    """Background worker that processes symptom analysis tasks.

    Continuously polls the task queue and executes the hybrid pipeline
    for each analysis task.

    Attributes:
        _queue: Task queue to poll.
        _coordinator: Cloud coordinator for reasoning trace generation.
        _analyzer: Local medical analyzer for PHI processing.
        _patient_repo: Repository for patient data access.
        _record_repo: Repository for medical record updates.
        _trace_repo: Repository for storing reasoning traces.
        _running: Flag controlling the polling loop.
        _worker_id: Identifier for logging.
    """

    def __init__(
        self,
        worker_id: str,
        queue: TaskQueue,
        coordinator: GeminiCoordinator,
        analyzer: MedicalAnalyzer,
        patient_repo: PatientRepository,
        record_repo: MedicalRecordRepository,
        trace_repo: TraceRepository,
    ) -> None:
        self._worker_id = worker_id
        self._queue = queue
        self._coordinator = coordinator
        self._analyzer = analyzer
        self._patient_repo = patient_repo
        self._record_repo = record_repo
        self._trace_repo = trace_repo
        self._running = False
        self._current_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the worker polling loop.

        Runs until ``stop()`` is called. Polls the queue with a 1-second
        timeout between checks.
        """
        self._running = True
        await logger.ainfo("worker_started", worker_id=self._worker_id)

        while self._running:
            try:
                task_doc = await self._queue.dequeue(timeout=1.0)
                if task_doc is None:
                    continue

                # Only process symptom_analysis tasks
                if task_doc.get("task_type") != TaskType.SYMPTOM_ANALYSIS.value:
                    continue

                await self._process_task(task_doc)

            except asyncio.CancelledError:
                await logger.ainfo("worker_cancelled", worker_id=self._worker_id)
                break
            except Exception:
                await logger.aerror(
                    "worker_poll_error",
                    worker_id=self._worker_id,
                    exc_info=True,
                )
                await asyncio.sleep(1)

        await logger.ainfo("worker_stopped", worker_id=self._worker_id)

    async def stop(self) -> None:
        """Gracefully stop the worker.

        Sets the running flag to False. The current in-flight task
        (if any) will complete before the worker shuts down.
        """
        self._running = False
        await logger.ainfo("worker_stopping", worker_id=self._worker_id)

    async def _process_task(self, task_doc: dict[str, Any]) -> None:
        """Process a single symptom analysis task.

        Pipeline:
        1. Fetch patient data
        2. Generate reasoning trace via coordinator
        3. Execute analysis via local analyzer
        4. Store trace and update medical record
        5. Mark task as done

        Args:
            task_doc: The task document from MongoDB.
        """
        task_id = str(task_doc["_id"])
        patient_id = task_doc["patient_id"]
        symptoms = task_doc.get("payload", {}).get("symptoms", "")

        await logger.ainfo(
            "task_processing_started",
            worker_id=self._worker_id,
            task_id=task_id,
            patient_id=patient_id,
        )

        try:
            # Step 1: Fetch patient
            patient_doc = await self._patient_repo.get_by_id(patient_id)

            # Step 2: Generate reasoning trace (cloud, no PHI)
            trace_data = await self._coordinator.generate_reasoning_trace(
                task_type="symptom_analysis",
                patient_doc=patient_doc,
                symptoms=symptoms,
            )

            # Step 3: Store reasoning trace
            trace_data["task_id"] = task_id
            trace_data["patient_id"] = patient_id
            trace_doc = await self._trace_repo.create_trace(trace_data)
            trace_id = str(trace_doc["_id"])

            # Step 4: Execute local analysis (with PHI)
            result = await self._analyzer.analyze(
                trace=trace_data,
                patient_doc=patient_doc,
                symptoms=symptoms,
            )

            # Step 5: Update medical record with analysis results
            # Find the most recent record for this patient with matching symptoms
            records = await self._record_repo.list_by_patient_id(
                patient_id=patient_id, page=1, page_size=1
            )
            if records.get("items"):
                record_id = str(records["items"][0]["_id"])
                await self._record_repo.update(record_id, {
                    "entities": result.entities,
                    "analysis_result": result.analysis_text,
                    "risk_level": result.risk_level,
                })

            # Step 6: Mark task done
            await self._queue.mark_done(
                task_id=task_id,
                result=result.to_dict(),
                trace_id=trace_id,
            )

            await logger.ainfo(
                "task_processing_completed",
                worker_id=self._worker_id,
                task_id=task_id,
                risk_level=result.risk_level,
            )

        except Exception as exc:
            await logger.aerror(
                "task_processing_failed",
                worker_id=self._worker_id,
                task_id=task_id,
                error=str(exc),
                exc_info=True,
            )
            retried = await self._queue.mark_failed(task_id, str(exc))
            if not retried:
                await logger.awarning(
                    "task_sent_to_dlq",
                    worker_id=self._worker_id,
                    task_id=task_id,
                )
