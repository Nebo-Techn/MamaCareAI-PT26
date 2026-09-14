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

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager


class Metrics(ABC):
    """Metric sink. Implemented by Prometheus in prod, by a no-op in tests."""

    @abstractmethod
    def increment(self, name: str, *, labels: dict[str, str] | None = None) -> None:
        """Bump a counter."""
        raise NotImplementedError

    @abstractmethod
    def observe(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        """Record a value in a histogram (durations, confidence scores)."""
        raise NotImplementedError

    @abstractmethod
    def gauge(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        """Set a gauge (queue depth, oldest review age)."""
        raise NotImplementedError

    @contextmanager
    def timed(
        self, name: str, *, labels: dict[str, str] | None = None
    ) -> Iterator[None]:
        """Time a block and record it as a histogram observation.

            with metrics.timed("stage_duration_seconds", labels={"stage": "translate"}):
                ...

        Implemented once here so every subclass gets it for free. The
        `finally` is deliberate — a failed stage's duration is exactly the
        one you want when finding the slow/broken stage in an incident.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, time.perf_counter() - start, labels=labels)


class NullMetrics(Metrics):
    """No-op sink for tests and local runs.

    A legitimate Null Object, not laziness — it means no test ever needs a
    metrics server, and `if self._metrics is not None` never has to appear
    anywhere in the codebase.
    """

    def increment(self, name: str, *, labels: dict[str, str] | None = None) -> None:
        """Discard a counter bump."""

    def observe(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        """Discard a histogram observation."""

    def gauge(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        """Discard a gauge setting."""


class PrometheusMetrics(Metrics):
    """Prometheus-backed sink for production.

    Skeleton for Sprint 3 (PIPE-31): counter/histogram/gauge routing with
    once-only declaration and deliberate buckets is implemented and tested
    through fakes. The client library (`prometheus-client`, still commented
    out in `backend/requirements.txt`) is imported lazily — constructing
    this class and calling it without the library installed is a safe no-op,
    so clean checkouts, tests, and CI never need it.

    Sprint 4 follow-ups (not this task): expose `/metrics` from the worker
    process (`start_http_server`) and the FastAPI app, and run a background
    task publishing the polled gauges (`queue_depth`,
    `review_queue_age_seconds`) on a timer — those are polled, not per-job.
    """

    # Buckets cover fast stages (ms) through minute-long jobs. The client
    # defaults top out around 10s, which would land every slow job in +Inf.
    DURATION_BUCKETS = (
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
        300.0,
        600.0,
    )
    # Confidence scores live in [0, 1]; duration buckets would be meaningless.
    CONFIDENCE_BUCKETS = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0)

    def __init__(self, *, registry: object = None) -> None:
        self._registry = registry
        self._counters: dict[str, object] = {}
        self._histograms: dict[str, object] = {}
        self._gauges: dict[str, object] = {}
        try:
            import prometheus_client  # noqa: F401

            self._available = True
        except ImportError:
            self._available = False

    @property
    def available(self) -> bool:
        """Whether the client library is installed (False == safe no-op)."""
        return self._available

    def _counter(self, name: str, labelnames: tuple[str, ...]) -> object | None:
        if not self._available:
            return None
        metric = self._counters.get(name)
        if metric is None:
            from prometheus_client import Counter

            kwargs: dict[str, object] = {"labelnames": labelnames}
            if self._registry is not None:
                kwargs["registry"] = self._registry
            metric = Counter(name, f"Pipeline counter {name}", **kwargs)  # type: ignore[arg-type]
            self._counters[name] = metric
        return metric

    def _histogram(self, name: str, labelnames: tuple[str, ...]) -> object | None:
        if not self._available:
            return None
        metric = self._histograms.get(name)
        if metric is None:
            from prometheus_client import Histogram

            buckets = (
                self.CONFIDENCE_BUCKETS if "confidence" in name else self.DURATION_BUCKETS
            )
            kwargs: dict[str, object] = {"labelnames": labelnames, "buckets": buckets}
            if self._registry is not None:
                kwargs["registry"] = self._registry
            metric = Histogram(name, f"Pipeline histogram {name}", **kwargs)  # type: ignore[arg-type]
            self._histograms[name] = metric
        return metric

    def _gauge(self, name: str, labelnames: tuple[str, ...]) -> object | None:
        if not self._available:
            return None
        metric = self._gauges.get(name)
        if metric is None:
            from prometheus_client import Gauge

            kwargs: dict[str, object] = {"labelnames": labelnames}
            if self._registry is not None:
                kwargs["registry"] = self._registry
            metric = Gauge(name, f"Pipeline gauge {name}", **kwargs)  # type: ignore[arg-type]
            self._gauges[name] = metric
        return metric

    @staticmethod
    def _label_tuple(labels: dict[str, str] | None) -> tuple[str, ...]:
        return tuple(sorted((labels or {}).keys()))

    def increment(self, name: str, *, labels: dict[str, str] | None = None) -> None:
        """Bump a counter, creating it once and reusing it afterwards."""
        metric = self._counter(name, self._label_tuple(labels))
        if metric is None:
            return
        metric.labels(**(labels or {})).inc()  # type: ignore[attr-defined]

    def observe(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        """Record a histogram observation, creating it once and reusing it."""
        metric = self._histogram(name, self._label_tuple(labels))
        if metric is None:
            return
        metric.labels(**(labels or {})).observe(value)  # type: ignore[attr-defined]

    def gauge(
        self, name: str, value: float, *, labels: dict[str, str] | None = None
    ) -> None:
        """Set a gauge, creating it once and reusing it afterwards."""
        metric = self._gauge(name, self._label_tuple(labels))
        if metric is None:
            return
        metric.labels(**(labels or {})).set(value)  # type: ignore[attr-defined]


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
