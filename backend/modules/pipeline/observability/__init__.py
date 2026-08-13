"""
Observability (PDF section 4).

"Per-stage metrics (queue depth, failure rate, latency) with alerting, so a
translation backlog is visible before the review team notices an empty queue."

That sentence describes the failure this package exists to prevent: the
pipeline looks fine — no errors, no crashes — while nothing reaches the review
team. Silence is not health. Measure the queues.
"""
