"""
Stage base class — retries, idempotency, transitions, and metrics in ONE place.

WHY A BASE CLASS HERE (and not copy-paste in seven files)
Every stage needs identical plumbing: load the resource, check it is in a state
this stage handles, do the work, transition it, publish the next job, record
the audit event, emit metrics, and decide retry-vs-dead-letter on failure.
Written seven times, that plumbing is wrong in at least three of them within a
month — and the wrong ones will be the stages nobody looks at.

So `run()` is a TEMPLATE METHOD: it owns the plumbing and calls the one
abstract hook each stage actually implements. Subclasses write business logic
only. When you need to change retry policy, you change it here, once.

This is also Open/Closed at the stage level: new stage = new subclass, no edits
to the runner or the worker.

TODO (junior dev): implement `run()` carefully — every other stage inherits its
correctness from this method. Get it reviewed before building on it.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..domain.enums import ResourceStatus
from ..domain.errors import PipelineError
from ..domain.models import AuditEvent, Job, Resource
from ..ports.job_queue import JobQueue
from ..ports.repositories import ResourceRepository, ReviewRepository

logger = logging.getLogger(__name__)


class StageResult:
    """What a stage's business logic reports back to the template method.

    Returning a result object instead of mutating shared state keeps the
    "what happened" decision in the stage and the "how it is persisted"
    decision in the base class.

    Attributes:
        next_status: state to move the resource into.
        next_stage: stage to enqueue afterwards; None ends this path
            (e.g. the resource now waits for a human).
        resource_changes: extra fields to persist on the Resource
            (detected_language, raw_object_key, ...).
        details: anything worth putting in the audit event.
    """

    def __init__(
        self,
        *,
        next_status: ResourceStatus,
        next_stage: str | None = None,
        resource_changes: dict[str, object] | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.next_status = next_status
        self.next_stage = next_stage
        self.resource_changes = resource_changes or {}
        self.details = details or {}


class Stage(ABC):
    """Template for every pipeline stage."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        max_attempts: int = 5,
    ) -> None:
        # Dependencies arrive here, always. A stage that builds its own S3
        # client in a method cannot be tested without AWS credentials.
        self._resources = resources
        self._queue = queue
        self._reviews = reviews
        self._max_attempts = max_attempts

    # --- What each subclass must declare -------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name used as the queue topic and in metrics, e.g. "extract"."""

    @property
    @abstractmethod
    def accepts(self) -> frozenset[ResourceStatus]:
        """Statuses this stage is willing to process.

        The guard against out-of-order and duplicate work. If a redelivered job
        arrives for a resource that has already moved on, `run()` sees the
        status is not in `accepts` and skips it as a no-op instead of
        re-processing. This is how at-least-once delivery is made safe.
        """

    @abstractmethod
    def handle(self, resource: Resource) -> StageResult:
        """The actual work of this stage. THE ONLY METHOD A SUBCLASS WRITES.

        Preconditions guaranteed by `run()`:
          - `resource` was just loaded fresh from the repository.
          - `resource.status` is in `self.accepts`.

        Rules:
          - Raise a `PipelineError` subclass on failure; `run()` decides retry
            vs dead-letter from its `retryable` flag.
          - Do not call `self._resources.save()` — return a StageResult and let
            `run()` persist. One writer means one place where transitions can
            go wrong.
          - Be idempotent. Assume this may be the second time you have run.
        """
        raise NotImplementedError

    # --- The plumbing every stage shares -------------------------------------

    def run(self, job: Job) -> None:
        """Execute one job end to end. Implemented ONCE, inherited by all stages.

        TODO (junior dev) — implement in this order:

          1. LOAD fresh state:
                 resource = self._resources.get(job.resource_id)
             Never trust a payload on the job; the message may be minutes old.

          2. IDEMPOTENCY GUARD:
                 if resource.status not in self.accepts:
                     log at INFO ("already processed / out of order"), return.
             Return, do NOT raise — a duplicate delivery is expected traffic,
             not an error, and must not page anyone.

          3. DO THE WORK:
                 result = self.handle(resource)
             Time it and emit the stage latency metric.

          4. VALIDATE THE TRANSITION before writing:
                 assert_can_transition(resource.status, result.next_status)

          5. PERSIST:
                 updated = resource.with_status(result.next_status,
                                                **result.resource_changes)
                 self._resources.save(updated)
             `save` is a conditional update; if it reports zero rows changed,
             another worker won the race — log and return, do not retry.

          6. AUDIT:
                 self._reviews.append_audit(AuditEvent(...actor=f"system:{self.name}"...))

          7. ENQUEUE THE NEXT STAGE (only after the state change is committed):
                 if result.next_stage:
                     self._queue.publish(Job(resource_id=..., stage=result.next_stage))
             ORDER MATTERS. Publishing before committing means the next stage
             can start on a resource whose status was never saved — a race that
             is miserable to debug and easy to avoid by publishing last.

          8. ERROR HANDLING — wrap steps 3-7:
                 except PipelineError as exc:
                     if exc.retryable and job.attempts < self._max_attempts:
                         re-publish with exponential backoff + jitter
                         (`not_before`; honour retry_after_seconds when the
                          provider supplied one)
                     else:
                         mark the resource FAILED, record last_error,
                         self._queue.send_to_dead_letter(job, reason=str(exc))
                 except Exception as exc:
                     an UNEXPECTED error is a bug, not a transient fault.
                     Log with traceback and dead-letter it — retrying a bug
                     five times just multiplies the noise.

          9. ALWAYS emit success/failure counters (observability/metrics.py).
        """
        raise NotImplementedError

    def _backoff_seconds(self, attempt: int) -> float:
        """Exponential backoff with jitter.

        TODO: `min(base * 2 ** attempt, cap)` then multiply by a random factor
        in roughly [0.5, 1.5].

        The jitter is not optional. Without it, 200 jobs that failed together
        during a provider outage all retry at the exact same instant and knock
        the provider over again the moment it recovers. This is the
        thundering-herd problem, and one line of `random.uniform` prevents it.
        """
        raise NotImplementedError
