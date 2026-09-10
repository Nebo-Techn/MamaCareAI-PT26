"""
Port: JobQueue — the decoupling between stages (PDF section 2).

This is what makes the pipeline "seven independently scalable stages" rather
than one long function. A slow ASR job sits in the ASR queue; PDF extraction
keeps running at full speed because it reads a different queue.

MVP binds this to an in-memory/SQLite queue (free, runs on a laptop).
Production binds it to SQS or Kafka. Same stage code either way.

AT-LEAST-ONCE DELIVERY — DESIGN FOR IT
Every real queue can deliver the same message twice (worker dies after doing
the work but before acking). We do not fight this; we make stages idempotent
and let the state machine reject the duplicate. Assume every job may run twice.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager

from ..domain.models import Job


class JobQueue(ABC):
    """Publishes and consumes pipeline jobs."""

    @abstractmethod
    def publish(self, job: Job) -> None:
        """Enqueue a job for a stage.

        TODO: honour `job.not_before` for delayed retries (SQS DelaySeconds, or
        a `visible_at` column). Sleeping inside a worker to implement backoff
        holds a worker slot hostage for the whole delay — never do that.
        """
        raise NotImplementedError

    @abstractmethod
    def consume(
        self, stage: str, *, max_messages: int = 1
    ) -> Iterator[AbstractContextManager[Job]]:
        """Yield jobs for `stage`, each wrapped in a context manager.

        The context manager is the ack protocol, and it exists so a junior dev
        cannot forget to ack:

            for handle in queue.consume("extract"):
                with handle as job:
                    process(job)     # clean exit -> ack (delete from queue)
                                     # exception  -> nack (redeliver or DLQ)

        Contract:
          - Leaving the block normally ACKs the message.
          - An exception NACKs it: retryable errors go back with backoff,
            permanent ones go to the dead-letter queue.
          - Long-poll rather than busy-loop; a spin loop burns CPU for nothing.
        """
        raise NotImplementedError

    @abstractmethod
    def depth(self, stage: str) -> int:
        """Approximate number of pending jobs for a stage.

        Feeds the queue-depth metric (PDF section 4, Observability). This is the
        number that tells us there is a translation backlog BEFORE the review
        team notices an empty queue.
        """
        raise NotImplementedError

    @abstractmethod
    def send_to_dead_letter(self, job: Job, *, reason: str) -> None:
        """Park a job that cannot be retried, with the reason recorded.

        A dead-letter queue nobody reads is just a slower way to lose data —
        `observability/metrics.py` must alert on DLQ depth > 0.
        """
        raise NotImplementedError
