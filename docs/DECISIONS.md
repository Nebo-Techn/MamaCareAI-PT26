# Decisions

A running log of decisions that affect more than one track — so nobody has to
remember them verbally, and nobody quietly re-decides them differently later.
Add a new entry (don't edit old ones — if a decision changes, add a new entry
that supersedes the old one and says so).

Keep each entry short: what was decided, why, and who it affects. This is a
log, not a design document — the reasoning belongs here in a sentence or two,
not a full write-up.

## Format

```
## DEC-0001 — <short title>
Date: YYYY-MM-DD · Decided by: <names> · Affects: <tracks/modules>

**Decision:** <one or two sentences>
**Why:** <one or two sentences>
**Supersedes:** <DEC-xxxx, if any>
```

## Log

## DEC-0000 — Telegram over WhatsApp for the 8-week build
Date: 2026-08-12 · Decided by: Program lead · Affects: bot, api

**Decision:** The bot ships on Telegram for the 8-week build; WhatsApp is
documented as the post-handover next step.
**Why:** WhatsApp Business API requires Meta business verification — an
approval delay outside the team's control, a bad risk against a fixed 8-week
window. Telegram is free, has no approval gate, and is a real chat channel.
**Supersedes:** —

## DEC-0001 — Multilingual data pipeline, reduced scope
Date: 2026-08-13 · Decided by: *(pending — Kelvin on schedule, Abdillah on scope)* · Affects: data, knowledge, pipeline

**Decision:** Build the spine of `Multilingual_Data_Pipeline_Architecture.pdf`
in `backend/modules/pipeline` — web + PDF ingestion, extraction, language
detection, translation to Swahili, storage, human review, publication. Park
video/ASR/OCR and the cloud stack (S3, SQS, Kafka, OpenSearch, cloud MT) as
templates, not deleted.
**Why:** The full design is 51 files; six weeks remain and the committed Week 8
deliverable is a working Telegram bot. A text-source pipeline delivered well
beats a multi-modal one delivered badly — the same reasoning already applied to
`modules/media`. Scope, capacity, and cut lines are in `docs/PIPELINE_BACKLOG.md`.
**Supersedes:** —

## DEC-0002 — `modules/ingestion` absorbed into `modules/pipeline`
Date: 2026-08-13 · Decided by: *(pending — Abdillah)* · Affects: data, knowledge, pipeline, storage

**Decision:** Fetching and parsing move into pipeline stages 1–2.
`modules/ingestion` becomes a pointer README. The data contract is unchanged
(`02_raw`, `03_extracted`). `modules/knowledge` now reads from `04_cleaned` and
owns chunking + embedding only; cleaning and review move upstream into the
pipeline. `modules/storage` keeps the vector store and runtime tables; the
pipeline keeps its own repositories, object store, and search index — one
shared DB engine in `backend/core`.
**Why:** Ingestion and pipeline stages 1–2 were the same job, same owner track,
same sprint. Two fetchers and two extractors maintained by the same people is
the duplication `docs/COLLABORATION.md` exists to prevent.
**Supersedes:** —

## DEC-0003 — Free stack for the pipeline MVP
Date: 2026-08-13 · Decided by: *(pending)* · Affects: pipeline, storage

**Decision:** SQLite, local filesystem, in-process queue, SQLite FTS5, and
self-hosted NLLB-200 for translation. The production stack in the design doc
(PostgreSQL, S3, SQS, OpenSearch, cloud MT) stays reachable by changing
environment variables only.
**Why:** `docs/ARCHITECTURE.md` commits to free-tier and open-source — no budget
is provisioned. The ports/adapters layering makes the switch a config change
rather than a rewrite, so the "what volume?" and "cloud or self-hosted MT?"
questions in the design doc can be answered later, on evidence. Each adapter's
docstring states the threshold that justifies switching.
**Supersedes:** —

## DEC-0004 — Server-rendered review UI, not React
Date: 2026-08-13 · Decided by: *(pending)* · Affects: api, bot, pipeline

**Decision:** The human review interface is one server-rendered HTML page
(FastAPI + Jinja2) — two columns, inline edit, save. No React, no build step,
no npm.
**Why:** A custom React review app is a two-week project that would consume the
rest of the program. Three days of server-rendered HTML delivers the same
reviewer capability. The API (`modules/pipeline/api/routes_review.py`) is the
real contract, so a richer UI can be built later against it without touching
the workflow.
**Supersedes:** —

*(Next entries start at DEC-0005, made by the team as real decisions come up.)*
