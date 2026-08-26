"""
In-memory queue — tests and single-process local development.

Makes the entire pipeline runnable with no infrastructure at all. A trainee
clones the repo and watches a document go from URL to review queue in one
process. That is worth a lot in week 1 of an 8-week program.

LIMITS, STATED PLAINLY: jobs vanish on restart, and nothing is shared between
processes. Correct for tests, wrong for anything else. `container.build_queue`
should refuse to build this outside development.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager

from ...domain.models import Job
from ...ports.job_queue import JobQueue


class MemoryQueue(JobQueue):
    """Queue backed by in-process lists."""

    def __init__(self) -> None:
        # TODO: dict of stage -> list[Job], plus a separate dead-letter list.
        # Guard with a threading.Lock — FastAPI's threadpool can touch this
        # from more than one thread even in "single process" mode.
        self._queues: dict[str, list[Job]] = {}
        self._dead_letter: list[tuple[Job, str]] = []

    def publish(self, job: Job) -> None:
        """TODO: append to the stage's list. Honour `not_before` by storing it
        and skipping the job in `consume` until that time has passed — do NOT
        sleep, or a delayed retry blocks every other job behind it."""
        raise NotImplementedError

    def consume(
        self, stage: str, *, max_messages: int = 1
    ) -> Iterator[AbstractContextManager[Job]]:
        """TODO: yield a context manager per job.

        On clean exit: drop the job (ack).
        On exception:  re-append it (nack), respecting attempts.

        Implement the handle with @contextmanager — the try/yield/except shape
        is exactly what the ack protocol needs, and it keeps the behaviour
        identical to the SQS adapter so tests written against this one stay
        meaningful.

        For tests, stop when the queue is empty rather than blocking forever.
        Add a `block: bool = False` parameter if a local dev run needs to wait.
        """
        raise NotImplementedError

    def depth(self, stage: str) -> int:
        """TODO: len of that stage's list."""
        raise NotImplementedError

    def send_to_dead_letter(self, job: Job, *, reason: str) -> None:
        """TODO: append (job, reason) to the dead-letter list and log a WARNING.
        Tests assert on this list — it is how you verify that a permanent error
        does NOT get retried."""
        raise NotImplementedError
