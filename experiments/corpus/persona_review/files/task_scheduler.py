"""Task scheduler with priority queue, dependency resolution, and retry logic.

Manages a pool of async tasks with configurable concurrency, backoff,
and dead letter queue for permanently failed tasks.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class Priority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class ScheduledTask:
    """A task in the priority queue."""

    priority: int
    created_at: float = field(compare=False)
    task_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    name: str = field(compare=False, default="")
    fn: Callable[..., Awaitable[Any]] = field(compare=False, default=None)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    dependencies: set[str] = field(compare=False, default_factory=set)
    max_retries: int = field(compare=False, default=3)
    retry_count: int = field(compare=False, default=0)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result: Any = field(compare=False, default=None)
    error: Exception | None = field(compare=False, default=None)


class TaskScheduler:
    """Async task scheduler with dependency resolution and retry logic."""

    def __init__(
        self,
        max_concurrency: int = 5,
        base_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0,
    ) -> None:
        self._queue: list[ScheduledTask] = []
        self._tasks: dict[str, ScheduledTask] = {}
        self._completed: set[str] = set()
        self._dead_letter: list[ScheduledTask] = []
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._base_retry_delay = base_retry_delay
        self._max_retry_delay = max_retry_delay
        self._running = False

    def submit(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args: Any,
        name: str = "",
        priority: Priority = Priority.NORMAL,
        dependencies: set[str] | None = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> str:
        """Submit a new task to the scheduler. Returns the task ID."""
        task = ScheduledTask(
            priority=priority.value,
            created_at=time.time(),
            name=name or fn.__name__,
            fn=fn,
            args=args,
            kwargs=kwargs,
            dependencies=dependencies or set(),
            max_retries=max_retries,
        )
        self._tasks[task.task_id] = task
        heapq.heappush(self._queue, task)
        return task.task_id

    def _dependencies_satisfied(self, task: ScheduledTask) -> bool:
        """Check if all dependencies of a task have completed."""
        return task.dependencies.issubset(self._completed)

    def _get_retry_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self._base_retry_delay * (2 ** retry_count)
        return min(delay, self._max_retry_delay)

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single task with retry logic."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            logger.info(f"Running task {task.name} ({task.task_id})")

            try:
                task.result = await task.fn(*task.args, **task.kwargs)
                task.status = TaskStatus.COMPLETED
                self._completed.add(task.task_id)
                logger.info(f"Task {task.name} completed successfully")
            except Exception as e:
                task.error = e
                task.retry_count += 1
                logger.warning(
                    f"Task {task.name} failed (attempt {task.retry_count}/{task.max_retries}): {e}"
                )

                if task.retry_count < task.max_retries:
                    # Re-queue with backoff
                    delay = self._get_retry_delay(task.retry_count)
                    await asyncio.sleep(delay)
                    task.status = TaskStatus.PENDING
                    heapq.heappush(self._queue, task)
                else:
                    task.status = TaskStatus.DEAD
                    self._dead_letter.append(task)
                    logger.error(
                        f"Task {task.name} permanently failed after {task.max_retries} attempts"
                    )

    async def run(self) -> dict[str, Any]:
        """Execute all queued tasks respecting dependencies and concurrency.

        Returns a summary of results.
        """
        self._running = True
        pending_tasks: list[asyncio.Task] = []

        while self._queue or pending_tasks:
            # Launch ready tasks
            ready: list[ScheduledTask] = []
            remaining: list[ScheduledTask] = []

            while self._queue:
                task = heapq.heappop(self._queue)
                if task.status == TaskStatus.PENDING and self._dependencies_satisfied(task):
                    ready.append(task)
                elif task.status == TaskStatus.PENDING:
                    remaining.append(task)

            # Put back tasks with unmet dependencies
            for task in remaining:
                heapq.heappush(self._queue, task)

            # Launch ready tasks
            for task in ready:
                coro = self._execute_task(task)
                pending_tasks.append(asyncio.create_task(coro))

            if pending_tasks:
                # Wait for at least one task to complete
                done, pending = await asyncio.wait(
                    pending_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                pending_tasks = list(pending)

                # Re-check queue for newly unblocked tasks
                for task in remaining:
                    if self._dependencies_satisfied(task):
                        heapq.heappush(self._queue, task)
            elif remaining:
                # Deadlock — remaining tasks have unsatisfiable dependencies
                logger.error(
                    f"Deadlock detected: {len(remaining)} tasks have unsatisfiable dependencies"
                )
                for task in remaining:
                    task.status = TaskStatus.DEAD
                    task.error = RuntimeError("Dependency deadlock")
                    self._dead_letter.append(task)
                break

        self._running = False
        return self._build_summary()

    def _build_summary(self) -> dict[str, Any]:
        """Build a summary of all task outcomes."""
        completed = [t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]
        failed = [t for t in self._tasks.values() if t.status == TaskStatus.DEAD]

        return {
            "total": len(self._tasks),
            "completed": len(completed),
            "failed": len(failed),
            "dead_letter": [
                {"task_id": t.task_id, "name": t.name, "error": str(t.error)}
                for t in self._dead_letter
            ],
            "results": {t.task_id: t.result for t in completed},
        }

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Retrieve a task by ID."""
        return self._tasks.get(task_id)

    @property
    def dead_letter_queue(self) -> list[ScheduledTask]:
        """Return the list of permanently failed tasks."""
        return list(self._dead_letter)
