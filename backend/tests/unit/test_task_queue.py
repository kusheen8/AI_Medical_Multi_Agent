"""
Unit tests for the internal async task queue (services/queue/).

Tests:
- Enqueue/dequeue ordering (priority)
- Task lifecycle: queued → processing → completed/failed
- Dead-letter queue after max retries
- Recovery of stuck tasks
- Task retrieval by ID
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.services.queue.task_queue import TaskQueue
from app.services.queue.task_schema import (
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskType,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_collection() -> MagicMock:
    """Create a mock MongoDB collection with async stubs."""
    collection = MagicMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find_one_and_update = AsyncMock()

    # find() returns an async-iterable cursor
    cursor = MagicMock()
    cursor.__aiter__ = MagicMock(return_value=iter([]))
    collection.find = MagicMock(return_value=cursor)

    return collection


@pytest.fixture
def mock_db_client(mock_collection: MagicMock) -> MagicMock:
    """Create a mocked db client that returns the mock collection."""
    from app.db.client import AsyncMongoClient

    client = MagicMock(spec=AsyncMongoClient)
    client.get_collection = MagicMock(return_value=mock_collection)
    return client


@pytest.fixture
def task_queue(mock_db_client: MagicMock) -> TaskQueue:
    """Create a TaskQueue instance with mocked DB."""
    return TaskQueue(mock_db_client)


# ── Enqueue Tests ────────────────────────────────────────────────────────


class TestEnqueue:
    """Tests for task enqueuing."""

    @pytest.mark.asyncio
    async def test_enqueue_persists_to_db(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId()
        )

        task = TaskCreate(
            task_type=TaskType.SYMPTOM_ANALYSIS,
            patient_id=str(ObjectId()),
            payload={"symptoms": "chest pain"},
        )
        task_id = await task_queue.enqueue(task)

        assert task_id is not None
        assert ObjectId.is_valid(task_id)
        mock_collection.insert_one.assert_called_once()

        # Verify the document structure
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["task_type"] == "symptom_analysis"
        assert call_args["status"] == "queued"
        assert call_args["retries"] == 0

    @pytest.mark.asyncio
    async def test_enqueue_adds_to_memory_queue(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId()
        )

        task = TaskCreate(
            task_type=TaskType.SYMPTOM_ANALYSIS,
            patient_id=str(ObjectId()),
            payload={},
        )
        await task_queue.enqueue(task)

        assert task_queue.pending_count == 1

    @pytest.mark.asyncio
    async def test_enqueue_with_priority(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        mock_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId()
        )

        task = TaskCreate(
            task_type=TaskType.SYMPTOM_ANALYSIS,
            patient_id=str(ObjectId()),
            payload={},
            priority=TaskPriority.URGENT,
        )
        await task_queue.enqueue(task)

        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["priority"] == TaskPriority.URGENT.value


# ── Dequeue Tests ────────────────────────────────────────────────────────


class TestDequeue:
    """Tests for task dequeuing."""

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_when_empty(
        self, task_queue: TaskQueue,
    ) -> None:
        result = await task_queue.dequeue(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_marks_processing_in_db(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        # Enqueue a task first
        task_id = ObjectId()
        mock_collection.insert_one.return_value = MagicMock(inserted_id=task_id)

        task = TaskCreate(
            task_type=TaskType.SYMPTOM_ANALYSIS,
            patient_id=str(ObjectId()),
            payload={},
        )
        await task_queue.enqueue(task)

        # Setup dequeue DB response
        task_doc = {
            "_id": task_id,
            "task_type": "symptom_analysis",
            "patient_id": str(ObjectId()),
            "status": "processing",
        }
        mock_collection.find_one_and_update.return_value = task_doc

        result = await task_queue.dequeue(timeout=1.0)

        assert result is not None
        assert result["status"] == "processing"
        mock_collection.find_one_and_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_dequeue_priority_order(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        """Urgent tasks should be dequeued before normal tasks."""
        id_normal = ObjectId()
        id_urgent = ObjectId()

        # Insert normal task first
        mock_collection.insert_one.return_value = MagicMock(inserted_id=id_normal)
        await task_queue.enqueue(TaskCreate(
            task_type=TaskType.SYMPTOM_ANALYSIS,
            patient_id=str(ObjectId()),
            payload={},
            priority=TaskPriority.NORMAL,
        ))

        # Insert urgent task second
        mock_collection.insert_one.return_value = MagicMock(inserted_id=id_urgent)
        await task_queue.enqueue(TaskCreate(
            task_type=TaskType.SYMPTOM_ANALYSIS,
            patient_id=str(ObjectId()),
            payload={},
            priority=TaskPriority.URGENT,
        ))

        # Dequeue should return urgent task first
        urgent_doc = {"_id": id_urgent, "task_type": "symptom_analysis", "status": "processing"}
        mock_collection.find_one_and_update.return_value = urgent_doc

        result = await task_queue.dequeue(timeout=1.0)
        assert result is not None
        assert result["_id"] == id_urgent


# ── Mark Done / Failed Tests ─────────────────────────────────────────────


class TestMarkDone:
    """Tests for marking tasks as completed."""

    @pytest.mark.asyncio
    async def test_mark_done_updates_db(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        task_id = str(ObjectId())
        result = {"risk_level": "high", "analysis_text": "Elevated cardiac risk."}

        await task_queue.mark_done(task_id=task_id, result=result, trace_id="trace123")

        mock_collection.find_one_and_update.assert_called_once()
        call_args = mock_collection.find_one_and_update.call_args
        update = call_args[0][1]["$set"]
        assert update["status"] == "completed"
        assert update["result"] == result
        assert update["trace_id"] == "trace123"


class TestMarkFailed:
    """Tests for marking tasks as failed with retry/DLQ logic."""

    @pytest.mark.asyncio
    async def test_mark_failed_retries(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        task_id = str(ObjectId())
        # Simulate a task with 0 retries (first failure)
        mock_collection.find_one.return_value = {
            "_id": ObjectId(task_id),
            "task_type": "symptom_analysis",
            "retries": 0,
            "max_retries": 3,
            "priority": TaskPriority.NORMAL.value,
        }
        mock_collection.find_one_and_update.return_value = None

        retried = await task_queue.mark_failed(task_id, "Connection timeout")

        assert retried is True
        assert task_queue.pending_count == 1  # Re-enqueued in memory

    @pytest.mark.asyncio
    async def test_mark_failed_dead_letter_after_max_retries(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        task_id = str(ObjectId())
        # Simulate a task with 2 retries (3rd failure → DLQ)
        mock_collection.find_one.return_value = {
            "_id": ObjectId(task_id),
            "task_type": "symptom_analysis",
            "retries": 2,
            "max_retries": 3,
            "priority": TaskPriority.NORMAL.value,
        }
        mock_collection.find_one_and_update.return_value = None

        retried = await task_queue.mark_failed(task_id, "Model unavailable")

        assert retried is False  # Sent to DLQ, not retried

        # Verify DLQ status was set
        call_args = mock_collection.find_one_and_update.call_args
        update = call_args[0][1]["$set"]
        assert update["status"] == "dead_letter"

    @pytest.mark.asyncio
    async def test_mark_failed_task_not_found(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        retried = await task_queue.mark_failed(str(ObjectId()), "error")

        assert retried is False


# ── Get Task Tests ───────────────────────────────────────────────────────


class TestGetTask:
    """Tests for task retrieval."""

    @pytest.mark.asyncio
    async def test_get_task_by_id(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        task_id = str(ObjectId())
        expected = {"_id": ObjectId(task_id), "status": "queued"}
        mock_collection.find_one.return_value = expected

        result = await task_queue.get_task(task_id)

        assert result is not None
        assert result["status"] == "queued"

    @pytest.mark.asyncio
    async def test_get_task_invalid_id(
        self, task_queue: TaskQueue,
    ) -> None:
        result = await task_queue.get_task("invalid-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_not_found(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        result = await task_queue.get_task(str(ObjectId()))
        assert result is None


# ── Recovery Tests ───────────────────────────────────────────────────────


class TestRecovery:
    """Tests for crash recovery of stuck tasks."""

    @pytest.mark.asyncio
    async def test_recover_pending_re_enqueues(
        self, task_queue: TaskQueue, mock_collection: MagicMock,
    ) -> None:
        # Simulate two stuck tasks
        stuck_tasks = [
            {
                "_id": ObjectId(),
                "task_type": "symptom_analysis",
                "priority": TaskPriority.NORMAL.value,
                "status": "processing",
            },
            {
                "_id": ObjectId(),
                "task_type": "history_summarization",
                "priority": TaskPriority.HIGH.value,
                "status": "processing",
            },
        ]

        # Make cursor iterable async
        cursor = MagicMock()
        cursor.__aiter__ = lambda self: iter(stuck_tasks).__aiter__() if hasattr(iter(stuck_tasks), '__aiter__') else self
        # Use an async generator wrapper
        async def async_iter():
            for item in stuck_tasks:
                yield item
        cursor.__aiter__ = lambda s: async_iter().__aiter__()
        mock_collection.find.return_value = cursor

        mock_collection.find_one_and_update.return_value = None

        recovered = await task_queue.recover_pending()

        assert recovered == 2
        assert task_queue.pending_count == 2


# ── TaskResponse Tests ───────────────────────────────────────────────────


class TestTaskResponse:
    """Tests for TaskResponse serialization."""

    def test_from_mongo_complete(self) -> None:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "task_type": "symptom_analysis",
            "patient_id": str(ObjectId()),
            "status": "completed",
            "priority": 2,
            "retries": 1,
            "result": {"risk_level": "high"},
            "error": None,
            "trace_id": "trace123",
            "created_at": now,
            "updated_at": now,
        }
        response = TaskResponse.from_mongo(doc)

        assert response.status == TaskStatus.COMPLETED
        assert response.result == {"risk_level": "high"}
        assert response.trace_id == "trace123"

    def test_from_mongo_minimal(self) -> None:
        doc = {
            "_id": ObjectId(),
            "task_type": "symptom_analysis",
            "patient_id": str(ObjectId()),
            "status": "queued",
        }
        response = TaskResponse.from_mongo(doc)

        assert response.status == TaskStatus.QUEUED
        assert response.result is None
