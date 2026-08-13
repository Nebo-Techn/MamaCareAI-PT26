"""
Per-stage metrics (PDF section 4: Prometheus + Grafana).

WHAT TO MEASURE, AND WHY EACH ONE EARNS ITS PLACE
Do not instrument everything. These six answer the questions that actually get
asked during an incident:

  1. jobs_processed_total{stage, outcome}
     Throughput and failure rate. "Is anything moving?"
  2. stage_duration_seconds{stage}  (histogram)
     Latency per stage. Finds the slow one without guessing.
  3. queue_depth{stage}  (gauge)
     THE MOST IMPORTANT ONE. A rising queue is the earliest possible warning:
     it goes up long before anyone notices missing content.
  4. dead_letter_depth  (gauge)
     Must alert at > 0. A DLQ nobody watches is a slower way to lose data.
  5. review_queue_age_seconds  (gauge, age of the OLDEST item)
     Catches the silent failure mode: content stuck in review forever while
     every technical metric looks perfectly green.
  6. translation_confidence  (histogram)
     Quality drift. A sudden drop means the MT engine or the input changed,
     and you want to know that before the reviewers tell you.

DESIGN NOTE — why this is a class and not module-level Prometheus globals:
module-level metric objects blow up on double registration in tests, cannot be
faked, and make every importer depend on prometheus_client. A small interface
here means tests use `NullMetrics` and the code under test stays clean.

CARDINALITY WARNING: never use resource_id or source_url as a metric label.
Metric labels have low-cardinality values (stage names, outcomes). Putting an
ID in a label creates one time series per document and takes down Prometheus.
Per-document detail belongs in logs, not metrics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from collections.abc import Iterator


class Metrics(ABC):
    """Metric sink. Implemented by Prometheus in prod, by a no-op in tests."""

    @abstractmethod
    def increment(self, name: str, *, labels: dict[str, str] | None = None) -> None:
        """Bump a counter."""
        raise NotImplementedError

    @abstractmethod
    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        """Record a value in a histogram (durations, confidence scores)."""
        raise NotImplementedError

    @abstractmethod
    def gauge(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        """Set a gauge (queue depth, oldest review age)."""
        raise NotImplementedError

    @contextmanager
    def timed(self, name: str, *, labels: dict[str, str] | None = None) -> Iterator[None]:
        """Time a block and record it as a histogram observation.

            with metrics.timed("stage_duration_seconds", labels={"stage": "translate"}):
                ...

        TODO: implement here on the base class (perf_counter around the yield,
        observe in a `finally`) so every subclass gets it for free. Use
        `finally` — a failed stage's duration is exactly the one you want.
        """
        raise NotImplementedError


class NullMetrics(Metrics):
    """No-op sink for tests and local runs.

    TODO: implement all three methods as `pass`. This is a legitimate Null
    Object, not laziness — it means no test ever needs a metrics server, and
    `if self._metrics is not None` never has to appear anywhere in the codebase.
    """


class PrometheusMetrics(Metrics):
    """Prometheus-backed sink for production.

    TODO (junior dev):
      [ ] Declare Counter/Histogram/Gauge objects ONCE in __init__, keyed by
          name, and reuse them. Re-creating a metric per call raises.
      [ ] Choose histogram buckets deliberately. The defaults top out around
          10s, which is useless for ASR jobs that take minutes — every slow job
          lands in +Inf and you learn nothing.
      [ ] Expose /metrics from the worker process (prometheus_client
          start_http_server) and from the FastAPI app.
      [ ] A background task should publish queue_depth and
          review_queue_age_seconds on a timer — those are polled gauges, not
          per-job events.
    """


class MetricNames:
    """One place for metric names, so a typo cannot silently split a series.

    A metric emitted as "job_processed_total" in one file and
    "jobs_processed_total" in another produces two half-empty dashboards and
    an alert that never fires.
    """

    JOBS_PROCESSED = "pipeline_jobs_processed_total"
    STAGE_DURATION = "pipeline_stage_duration_seconds"
    QUEUE_DEPTH = "pipeline_queue_depth"
    DEAD_LETTER_DEPTH = "pipeline_dead_letter_depth"
    REVIEW_QUEUE_AGE = "pipeline_review_queue_age_seconds"
    TRANSLATION_CONFIDENCE = "pipeline_translation_confidence"
