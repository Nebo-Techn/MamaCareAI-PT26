from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import replace
from datetime import UTC, datetime
from threading import Lock

from ...domain.models import Job
from ...ports.job_queue import JobQueue

logger = logging.getLogger(__name__)


class MemoryQueue(JobQueue):
    """Queue backed by in-process lists."""

    def __init__(self) -> None:
        self._queues: dict[str, list[Job]] = {}
        self._dead_letter: list[tuple[Job, str]] = []
        self._lock = Lock()

    def publish(self, job: Job) -> None:
        """Enqueue a job without blocking for a delayed retry."""
        with self._lock:
            self._queues.setdefault(job.stage, []).append(job)

    def consume(self, stage: str, *, max_messages: int = 1) -> Iterator[AbstractContextManager[Job]]:
        """Yield up to ``max_messages`` ready jobs, without waiting for work."""
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1")

        for _ in range(max_messages):
            job = self._claim_ready_job(stage)
            if job is None:
                return
            yield self._handle(job)

    def depth(self, stage: str) -> int:
        """Return the number of pending jobs, including delayed retries."""
        with self._lock:
            return len(self._queues.get(stage, []))

    def send_to_dead_letter(self, job: Job, *, reason: str) -> None:
        """Record a permanently failed job and its diagnostic reason."""
        with self._lock:
            self._dead_letter.append((job, reason))
        logger.warning("Job %s sent to dead letter queue: %s", job.job_id, reason)

    def _claim_ready_job(self, stage: str) -> Job | None:
        now = datetime.now(UTC)
        with self._lock:
            jobs = self._queues.get(stage)
            if not jobs:
                return None
            for index, job in enumerate(jobs):
                if job.not_before is None or job.not_before <= now:
                    return jobs.pop(index)
        return None

    def _handle(self, job: Job) -> AbstractContextManager[Job]:
        return _MemoryJobHandle(self, job)


class _MemoryJobHandle(AbstractContextManager[Job]):
    def __init__(self, queue: MemoryQueue, job: Job) -> None:
        self._queue = queue
        self._job = job

    def __enter__(self) -> Job:
        return self._job

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> bool:
        if exception_type is not None:
            self._queue.publish(replace(self._job, attempts=self._job.attempts + 1))
        return False
