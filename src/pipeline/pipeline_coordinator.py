"""
Pipeline Coordinator for EduLens

Coordinates concurrent processing across vision, audio, and AI components.
Manages task scheduling, resource allocation, and inter-component communication.

Author: Integration Agent (INT-001)
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Priority levels for pipeline tasks."""
    CRITICAL = 0  # Immediate processing required
    HIGH = 1      # Important, process soon
    NORMAL = 2    # Standard priority
    LOW = 3       # Background task


class TaskStatus(Enum):
    """Status of a pipeline task."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class PipelineTask:
    """Represents a task in the pipeline."""
    task_id: str
    task_type: str
    priority: TaskPriority
    coroutine: Coroutine
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        """Get task duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass
class CoordinatorStats:
    """Statistics for the pipeline coordinator."""
    tasks_scheduled: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_cancelled: int = 0
    average_task_duration_ms: float = 0.0
    active_workers: int = 0
    queue_depth: int = 0


class PipelineCoordinator:
    """
    Coordinates concurrent processing across pipeline components.

    Features:
    - Priority-based task scheduling
    - Worker pool management
    - Concurrent execution with configurable limits
    - Task lifecycle tracking
    - Performance monitoring
    - Resource management
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        max_queue_size: int = 100
    ) -> None:
        """
        Initialize the pipeline coordinator.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
            max_queue_size: Maximum task queue size
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queue_size = max_queue_size

        # Task management
        self._task_queues: dict[TaskPriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=max_queue_size)
            for priority in TaskPriority
        }
        self._active_tasks: dict[str, PipelineTask] = {}
        self._completed_tasks: dict[str, PipelineTask] = {}

        # Worker management
        self._workers: list[asyncio.Task] = []
        self._is_running: bool = False
        self._shutdown_event = asyncio.Event()

        # Statistics
        self._stats = CoordinatorStats()
        self._task_durations: list[float] = []

        # Callbacks
        self._task_callbacks: dict[str, list[Callable]] = {}

        logger.info(
            f"PipelineCoordinator initialized: "
            f"max_concurrent={max_concurrent_tasks}, "
            f"max_queue_size={max_queue_size}"
        )

    async def start(self) -> None:
        """Start the coordinator and worker pool."""
        if self._is_running:
            logger.warning("Coordinator already running")
            return

        logger.info("Starting pipeline coordinator...")

        self._is_running = True
        self._shutdown_event.clear()

        # Start worker tasks
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Started {len(self._workers)} worker tasks")

    async def stop(self) -> None:
        """Stop the coordinator and cancel all tasks."""
        if not self._is_running:
            return

        logger.info("Stopping pipeline coordinator...")

        self._is_running = False
        self._shutdown_event.set()

        # Cancel active tasks
        for task in self._active_tasks.values():
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.CANCELLED
                self._stats.tasks_cancelled += 1

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()

        logger.info("Pipeline coordinator stopped")

    async def schedule_task(
        self,
        task_type: str,
        coroutine: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable[[PipelineTask], None]] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Schedule a task for execution.

        Args:
            task_type: Type/name of the task
            coroutine: Coroutine to execute
            priority: Task priority
            callback: Optional callback when task completes
            metadata: Optional task metadata

        Returns:
            Task ID

        Raises:
            ValueError: If queue is full
        """
        task_id = str(uuid4())

        task = PipelineTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            coroutine=coroutine,
            metadata=metadata or {}
        )

        # Add callback if provided
        if callback:
            if task_id not in self._task_callbacks:
                self._task_callbacks[task_id] = []
            self._task_callbacks[task_id].append(callback)

        # Add to appropriate priority queue
        try:
            self._task_queues[priority].put_nowait(task)
            self._stats.tasks_scheduled += 1
            self._stats.queue_depth += 1

            logger.debug(
                f"Scheduled task: id={task_id}, type={task_type}, priority={priority.name}"
            )

            return task_id

        except asyncio.QueueFull:
            logger.error(f"Task queue full for priority {priority.name}")
            raise ValueError(f"Task queue full for priority {priority.name}")

    async def start_session(
        self,
        session_id: str,
        student_id: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Start a new tutoring session.

        Args:
            session_id: Session identifier
            student_id: Student identifier
            metadata: Optional session metadata
        """
        async def _start_session() -> dict[str, Any]:
            logger.info(f"Starting session: {session_id} for student: {student_id}")
            return {
                "session_id": session_id,
                "student_id": student_id,
                "started_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

        await self.schedule_task(
            task_type="start_session",
            coroutine=_start_session(),
            priority=TaskPriority.HIGH,
            metadata={"session_id": session_id, "student_id": student_id}
        )

    async def process_frame(
        self,
        frame_data: Any,
        session_id: str,
        processor: Callable[[Any], Coroutine[Any, Any, Any]]
    ) -> str:
        """
        Process a camera frame.

        Args:
            frame_data: Frame data to process
            session_id: Current session ID
            processor: Coroutine function to process the frame

        Returns:
            Task ID
        """
        return await self.schedule_task(
            task_type="process_frame",
            coroutine=processor(frame_data),
            priority=TaskPriority.NORMAL,
            metadata={"session_id": session_id}
        )

    async def process_audio(
        self,
        audio_data: Any,
        session_id: str,
        processor: Callable[[Any], Coroutine[Any, Any, Any]]
    ) -> str:
        """
        Process audio input.

        Args:
            audio_data: Audio data to process
            session_id: Current session ID
            processor: Coroutine function to process the audio

        Returns:
            Task ID
        """
        return await self.schedule_task(
            task_type="process_audio",
            coroutine=processor(audio_data),
            priority=TaskPriority.HIGH,  # Audio is time-sensitive
            metadata={"session_id": session_id}
        )

    async def generate_response(
        self,
        query: str,
        context: dict[str, Any],
        session_id: str,
        generator: Callable[[str, dict], Coroutine[Any, Any, Any]]
    ) -> str:
        """
        Generate AI response.

        Args:
            query: Student query
            context: Context for generation
            session_id: Current session ID
            generator: Coroutine function to generate response

        Returns:
            Task ID
        """
        return await self.schedule_task(
            task_type="generate_response",
            coroutine=generator(query, context),
            priority=TaskPriority.HIGH,
            metadata={"session_id": session_id, "query": query[:50]}
        )

    async def deliver_response(
        self,
        response_text: str,
        session_id: str,
        deliverer: Callable[[str], Coroutine[Any, Any, Any]]
    ) -> str:
        """
        Deliver response via TTS.

        Args:
            response_text: Text to speak
            session_id: Current session ID
            deliverer: Coroutine function to deliver response

        Returns:
            Task ID
        """
        return await self.schedule_task(
            task_type="deliver_response",
            coroutine=deliverer(response_text),
            priority=TaskPriority.CRITICAL,  # TTS should be immediate
            metadata={"session_id": session_id}
        )

    async def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        Wait for a task to complete.

        Args:
            task_id: Task identifier
            timeout: Maximum wait time in seconds

        Returns:
            Task result or None if timeout/error
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check if task completed
            if task_id in self._completed_tasks:
                task = self._completed_tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    return task.result
                else:
                    logger.error(f"Task {task_id} failed: {task.error}")
                    return None

            # Check timeout
            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Task {task_id} timed out after {timeout}s")
                    return None

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Task status or None if not found
        """
        if task_id in self._active_tasks:
            return self._active_tasks[task_id].status
        elif task_id in self._completed_tasks:
            return self._completed_tasks[task_id].status
        return None

    def get_stats(self) -> CoordinatorStats:
        """Get coordinator statistics."""
        self._stats.active_workers = len([w for w in self._workers if not w.done()])
        self._stats.queue_depth = sum(
            q.qsize() for q in self._task_queues.values()
        )

        if self._task_durations:
            self._stats.average_task_duration_ms = sum(self._task_durations) / len(self._task_durations)

        return self._stats

    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop that processes tasks from queues.

        Args:
            worker_id: Worker identifier
        """
        logger.debug(f"Worker {worker_id} started")

        while self._is_running:
            try:
                # Try to get task from highest priority queue first
                task = await self._get_next_task()

                if task is None:
                    # No tasks available, wait a bit
                    await asyncio.sleep(0.1)
                    continue

                # Execute task
                await self._execute_task(task, worker_id)

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.debug(f"Worker {worker_id} stopped")

    async def _get_next_task(self) -> Optional[PipelineTask]:
        """
        Get next task from priority queues.

        Returns:
            Next task or None if no tasks available
        """
        # Try each priority level in order
        for priority in TaskPriority:
            queue = self._task_queues[priority]
            if not queue.empty():
                try:
                    task = queue.get_nowait()
                    self._stats.queue_depth -= 1
                    return task
                except asyncio.QueueEmpty:
                    continue

        return None

    async def _execute_task(self, task: PipelineTask, worker_id: int) -> None:
        """
        Execute a pipeline task.

        Args:
            task: Task to execute
            worker_id: Worker executing the task
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self._active_tasks[task.task_id] = task

        logger.debug(
            f"Worker {worker_id} executing task: "
            f"id={task.task_id}, type={task.task_type}"
        )

        try:
            # Execute the coroutine
            task.result = await task.coroutine

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()

            self._stats.tasks_completed += 1

            # Track duration
            if task.duration_ms:
                self._task_durations.append(task.duration_ms)
                # Keep only last 100 durations
                if len(self._task_durations) > 100:
                    self._task_durations = self._task_durations[-100:]

            logger.debug(
                f"Task completed: id={task.task_id}, "
                f"duration={task.duration_ms:.1f}ms"
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            task.completed_at = datetime.utcnow()

            self._stats.tasks_failed += 1

            logger.error(
                f"Task failed: id={task.task_id}, type={task.task_type}, error={e}",
                exc_info=True
            )

        finally:
            # Move to completed tasks
            if task.task_id in self._active_tasks:
                del self._active_tasks[task.task_id]
            self._completed_tasks[task.task_id] = task

            # Execute callbacks
            if task.task_id in self._task_callbacks:
                for callback in self._task_callbacks[task.task_id]:
                    try:
                        callback(task)
                    except Exception as e:
                        logger.error(f"Callback error: {e}", exc_info=True)

                del self._task_callbacks[task.task_id]

            # Cleanup old completed tasks (keep last 1000)
            if len(self._completed_tasks) > 1000:
                oldest_ids = sorted(
                    self._completed_tasks.keys(),
                    key=lambda k: self._completed_tasks[k].completed_at or datetime.min
                )[:100]
                for task_id in oldest_ids:
                    del self._completed_tasks[task_id]


async def create_coordinator(
    max_concurrent_tasks: int = 5,
    max_queue_size: int = 100
) -> PipelineCoordinator:
    """
    Create and start a pipeline coordinator.

    Args:
        max_concurrent_tasks: Maximum concurrent tasks
        max_queue_size: Maximum queue size

    Returns:
        Started coordinator
    """
    coordinator = PipelineCoordinator(
        max_concurrent_tasks=max_concurrent_tasks,
        max_queue_size=max_queue_size
    )
    await coordinator.start()
    return coordinator
