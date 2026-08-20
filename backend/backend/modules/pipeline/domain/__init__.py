"""
Domain layer — the pipeline's vocabulary and rules.

Hard rule for this package: **zero I/O and zero third-party infrastructure
imports.** No `requests`, no `boto3`, no `sqlalchemy`, no `openai`. Only the
standard library (plus `pydantic`/`dataclasses` for structure).

Why: everything else in the pipeline depends on this layer, so if it stays
pure it stays testable with no fixtures, no network, and no database. A test
for the review state machine should run in microseconds.
"""
