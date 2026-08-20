"""
Stages — the seven use cases of the pipeline (PDF section 3).

    ingest -> extract -> detect_language -> translate -> store -> review -> publish

One file per stage, one responsibility per file. That is the Single
Responsibility Principle applied at the level that actually matters here: each
stage can be deployed, scaled, retried, and reasoned about on its own. ASR is
GPU-heavy and bursty; language detection is cheap and constant. They should
never share a process, and this layout is what makes that possible.

RULES FOR THIS PACKAGE
  - Import from `ports/` and `domain/`. NEVER from `adapters/`.
    (If you need a concrete class here, the design has gone wrong — ask for a
    review before you work around it.)
  - Every stage receives its dependencies through `__init__`. No module-level
    clients, no globals, no `os.getenv` at call time. Constructor injection is
    what lets tests hand you a fake instead of a real S3 bucket.
  - Every stage is idempotent: running the same job twice must not corrupt
    state or produce a second version.
"""
