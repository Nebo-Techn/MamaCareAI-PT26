# Storage

Data access for the **runtime** path — what the bot needs at answer time.

- **Vector store client** — wraps a local, free vector database (Chroma) that
  holds embedded knowledge chunks from `modules/knowledge`. This is what
  `modules/rag` queries at answer time.
- **Relational data access** for runtime state that doesn't belong in the
  vector store: evaluation run logs, conversation history, safety event logs.
  Only add a table when a real feature needs one; don't pre-build a schema
  nobody uses yet.

**Owner track:** Data & Knowledge (vector store), API/Bot track (relational, if/when needed)
**Sprint:** 1–2 (vector store setup is a Sprint 1 priority — the team can't
build RAG until this exists)

## Split with `modules/pipeline` — by data, not by module

The pipeline has its own object store, repositories, and search index. That is
deliberate, not duplication: they hold different data with different lifecycles.

| | This module | `modules/pipeline` |
|---|---|---|
| Holds | embedded chunks, conversation and eval logs | resources, versions, review assignments, audit trail |
| Lifecycle | read constantly at answer time | written once per pipeline stage, read by reviewers |
| Backed by | Chroma + SQLite | SQLite (→ Postgres), filesystem (→ S3), FTS5 (→ OpenSearch) |

**One database file, one engine.** The SQLAlchemy engine and session factory
live in `backend/core` and are shared by both, so there is a single connection
pool and a single Alembic migration history — not two modules each opening
their own SQLite handle to the same file.

See `DEC-0002` in `docs/DECISIONS.md`.
