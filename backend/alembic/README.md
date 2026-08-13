# Alembic

Database migration scripts.

**Status: now needed.** This folder was parked until something genuinely
required relational tables. `modules/pipeline` does — it needs five:

| Table | Holds |
|---|---|
| `resources` | pipeline control record: status, source, hashes, timestamps |
| `documents` | normalized extracted text (the common schema) |
| `content_versions` | append-only translation versions, machine and human |
| `review_assignments` | who is reviewing what |
| `audit_events` | append-only "who changed what and when" |

Full column and index notes are in
`modules/pipeline/adapters/storage/sql_repositories.py`.

**Set this up in Sprint 2, alongside task PIPE-15** (see
`docs/PIPELINE_BACKLOG.md`) — not before. The migration and the repository
that uses it should land in the same PR, so a migration never sits in `main`
with no code reading it.

**Owner track:** Data & Knowledge (the pipeline tables), API/Bot track (runtime
tables in `modules/storage`, if/when needed)
**Sprint:** 2

## Two indexes that are not optional

Both are correctness, not performance — the code that depends on them is
written assuming the database enforces them:

- `UNIQUE` on `resources.content_hash` — the actual deduplication guarantee.
  The `Deduplicator` port is only a fast pre-check; under concurrency two
  workers can both see "not a duplicate", and this constraint is what stops
  them.
- `UNIQUE` on `(content_versions.resource_id, version_number)` — stops two
  concurrent reviewers from both creating "version 3" and one silently losing
  their edit.

Run migrations against SQLite for the MVP; the same migrations apply to
PostgreSQL when the pipeline's storage backend is switched.
