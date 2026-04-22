"""
Internal async task queue with MongoDB persistence.

Provides an in-memory ``asyncio.PriorityQueue`` backed by MongoDB for
durability.  Tasks are persisted to the ``tasks`` collection on enqueue
and status updates are written on every lifecycle transition.

On startup, ``recover_pending()`` re-enqueues any tasks that were in
``processing`` status when the application last shut down (crash recovery).

Upgrade path: replace the in-memory queue with Celery/RabbitMQ for
multi-server deployments.  The ``TaskQueue`` interface stays the same.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from bson import ObjectId

from app.db.client import AsyncMongoClient
from app.services.queue.task_schema import TaskCreate, TaskPriority, TaskStatus, TaskType

logger = structlog.get_logger(__name__)


@dataclass(order=True)
class _PriorityItem:
    """Wrapper that makes tasks orderable by priority + creation time."""

    priority: int
    created_at: float  # timestamp for FIFO within same priority
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)


class TaskQueue:
    """Async task queue with in-memory ordering and MongoDB persistence.

    Attributes:
        _db_client: Shared async MongoDB client.
        _queue: In-memory priority queue for fast dequeue ordering.
        _collection_name: MongoDB collection for task persistence.
    """

    COLLECTION = "tasks"
    MAX_RETRIES = 3

    def __init__(self, db_client: AsyncMongoClient) -> None:
        self._db_client = db_client
        self._queue: asyncio.PriorityQueue[_PriorityItem] = asyncio.PriorityQueue()

    @property
    def _collection(self) -> Any:
        """Return the MongoDB collection handle."""
        return self._db_client.get_collection(self.COLLECTION)

    # ── Enqueue ──────────────────────────────────────────────────────────

    async def enqueue(self, task: TaskCreate) -> str:
        """Persist a new task to MongoDB and add to in-memory queue.

        Args:
            task: Task creation payload.

        Returns:
            The task_id (string ObjectId) of the enqueued task.
        """
        now = datetime.now(timezone.utc)
        document: dict[str, Any] = {
            "task_type": task.task_type.value,
            "patient_id": task.patient_id,
            "payload": task.payload,
            "status": TaskStatus.QUEUED.value,
            "priority": task.priority.value,
            "retries": 0,
            "max_retries": self.MAX_RETRIES,
            "result": None,
            "error": None,
            "trace_id": None,
            "created_at": now,
            "updated_at": now,
        }

        result = await self._collection.insert_one(document)
        task_id = str(result.inserted_id)

        # Add to in-memory queue
        item = _PriorityItem(
            priority=task.priority.value,
            created_at=now.timestamp(),
            task_id=task_id,
            task_type=task.task_type.value,
        )
        await self._queue.put(item)

        await logger.ainfo(
            "task_enqueued",
            task_id=task_id,
            task_type=task.task_type.value,
            priority=task.priority.value,
        )
        return task_id

    # ── Dequeue ──────────────────────────────────────────────────────────

    async def dequeue(self, timeout: float = 1.0) -> dict[str, Any] | None:
        """Pop the highest-priority task from the queue.

        Updates the task status to ``processing`` in MongoDB.

        Args:
            timeout: Seconds to wait for a task before returning None.

        Returns:
            The task document dict, or None if the queue is empty.
        """
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

        # Mark as processing in DB
        now = datetime.now(timezone.utc)
        doc = await self._collection.find_one_and_update(
            {"_id": ObjectId(item.task_id), "status": TaskStatus.QUEUED.value},
            {"$set": {"status": TaskStatus.PROCESSING.value, "updated_at": now}},
            return_document=True,
        )

        if doc is None:
            # Task was already processed/cancelled — skip
            await logger.awarning("task_dequeue_stale", task_id=item.task_id)
            return None

        await logger.ainfo(
            "task_dequeued",
            task_id=item.task_id,
            task_type=item.task_type,
        )
        return doc

    # ── Mark Done ────────────────────────────────────────────────────────

    async def mark_done(
        self, task_id: str, result: dict[str, Any], trace_id: str | None = None
    ) -> None:
        """Mark a task as completed with its result.

        Args:
            task_id: The task ObjectId string.
            result: The analysis result to store.
            trace_id: Optional reasoning trace ID.
        """
        now = datetime.now(timezone.utc)
        await self._collection.find_one_and_update(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": TaskStatus.COMPLETED.value,
                    "result": result,
                    "trace_id": trace_id,
                    "updated_at": now,
                }
            },
        )
        await logger.ainfo("task_completed", task_id=task_id)

    # ── Mark Failed ──────────────────────────────────────────────────────

    async def mark_failed(self, task_id: str, error: str) -> bool:
        """Mark a task as failed and handle retry/DLQ logic.

        If retries < max_retries, re-enqueues the task.
        If retries >= max_retries, moves to dead-letter queue.

        Args:
            task_id: The task ObjectId string.
            error: Error message describing the failure.

        Returns:
            True if the task was re-enqueued for retry, False if sent to DLQ.
        """
        now = datetime.now(timezone.utc)
        doc = await self._collection.find_one({"_id": ObjectId(task_id)})
        if doc is None:
            await logger.awarning("task_mark_failed_not_found", task_id=task_id)
            return False

        retries = doc.get("retries", 0) + 1
        max_retries = doc.get("max_retries", self.MAX_RETRIES)

        if retries >= max_retries:
            # Move to dead-letter queue
            await self._collection.find_one_and_update(
                {"_id": ObjectId(task_id)},
                {
                    "$set": {
                        "status": TaskStatus.DEAD_LETTER.value,
                        "error": error,
                        "retries": retries,
                        "updated_at": now,
                    }
                },
            )
            await logger.awarning(
                "task_dead_lettered",
                task_id=task_id,
                retries=retries,
                error=error,
            )
            return False

        # Re-enqueue for retry
        await self._collection.find_one_and_update(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": TaskStatus.QUEUED.value,
                    "error": error,
                    "retries": retries,
                    "updated_at": now,
                }
            },
        )

        # Add back to in-memory queue
        item = _PriorityItem(
            priority=doc.get("priority", TaskPriority.NORMAL.value),
            created_at=now.timestamp(),
            task_id=task_id,
            task_type=doc["task_type"],
        )
        await self._queue.put(item)

        await logger.ainfo(
            "task_requeued",
            task_id=task_id,
            retries=retries,
            max_retries=max_retries,
        )
        return True

    # ── Get Task ─────────────────────────────────────────────────────────

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a task document by ID.

        Args:
            task_id: The task ObjectId string.

        Returns:
            The task document, or None if not found.
        """
        if not ObjectId.is_valid(task_id):
            return None
        return await self._collection.find_one({"_id": ObjectId(task_id)})

    # ── Recovery ─────────────────────────────────────────────────────────

    async def recover_pending(self) -> int:
        """Re-enqueue tasks stuck in ``processing`` status after a crash.

        Called on application startup to recover any in-flight tasks
        that were interrupted when the process last shut down.

        Returns:
            Number of tasks recovered.
        """
        cursor = self._collection.find({"status": TaskStatus.PROCESSING.value})
        recovered = 0
        async for doc in cursor:
            task_id = str(doc["_id"])
            now = datetime.now(timezone.utc)

            await self._collection.find_one_and_update(
                {"_id": doc["_id"]},
                {"$set": {"status": TaskStatus.QUEUED.value, "updated_at": now}},
            )

            item = _PriorityItem(
                priority=doc.get("priority", TaskPriority.NORMAL.value),
                created_at=now.timestamp(),
                task_id=task_id,
                task_type=doc["task_type"],
            )
            await self._queue.put(item)
            recovered += 1

        if recovered > 0:
            await logger.ainfo("tasks_recovered", count=recovered)
        return recovered

    # ── Queue Info ───────────────────────────────────────────────────────

    @property
    def pending_count(self) -> int:
        """Return the number of tasks in the in-memory queue."""
        return self._queue.qsize()
