# Pipeline backlog — reduced scope, sprint by sprint

Build plan for `backend/modules/pipeline` (the multilingual data collection
pipeline), fitted into the remaining weeks of the 8-week program.

**Drafted:** Thu 13 Aug 2026 — Week 2, Sprint 1.
**Status:** proposed. Needs sign-off from Kelvin (schedule) and Abdillah
(scope) before these become board items.

Read alongside [ARCHITECTURE.md](ARCHITECTURE.md),
[INTERNSHIP_PROGRAM.md](INTERNSHIP_PROGRAM.md), and the module's own
[README](../backend/modules/pipeline/README.md), which has the layering rules
and the per-file TODO checklists this backlog references.

---

## 1. The scope decision this plan assumes

The pipeline described in `Multilingual_Data_Pipeline_Architecture.pdf` is 51
template files. **Six weeks remain, and the committed Week 8 deliverable is a
working Telegram bot** — not this pipeline. Both cannot be built in full.

**Building (the spine, ~30 files):**
web + PDF ingestion → extraction → language detection → translation to Swahili
→ storage → human review → published output.

**Parked as templates, not deleted** — same treatment
[modules/media](../backend/modules/media/README.md) already has, for the same
reason:

| Parked | Why |
|---|---|
| Video ingestion, captions, ASR/Whisper | The most expensive and GPU-shaped work in the pipeline. A text-source pipeline delivered well beats a multi-modal one delivered badly. |
| OCR for scanned PDFs | Adds Tesseract + preprocessing + a confidence floor. The text-layer path covers most vetted health PDFs. |
| S3, SQS, Kafka, OpenSearch, cloud MT | The free stack is the deliverable. These are documented escape hatches with stated switch thresholds. |

The parked files keep their templates so the scope stays visible instead of
being silently forgotten. Nothing here is thrown away.

## 2. Capacity reality — read this before agreeing to the plan

| Sprint | Pipeline work | People needed on pipeline |
|---|---|---|
| Sprint 1 remainder | ~14 person-days over 7 working days | **2 minimum — see note** |
| Sprint 2 | ~19 person-days over 10 working days | **~2 people** |
| Sprint 3 | ~18 person-days over 10 working days | **~2 people** |
| Sprint 4 | ~4 person-days over 5 working days | 1 person, part-time |

At two people this is roughly **half the team, sustained, for five weeks.** The
other half stays entirely on the committed product path (real RAG, safety,
emergency detection, evaluation, deploy). If two people cannot be freed, cut
scope using §7 rather than running both at half speed — that is how neither
ships.

**Two people is the minimum, not the plan.** Sprint 1 at two people has exactly
zero slack: 14 person-days of work in 14 person-days of capacity, so one sick
day or one PR left unreviewed overnight fails the 21 Aug gate. The agreed split
puts **all four people on the pipeline for Sprint 1** and pulls three Sprint 2
adapter tasks forward to fill the non-critical-path capacity — see §4. That
buys ~12% slack, and correspondingly reduces the Sprint 2 load below the ~19
person-days shown above.

## 3. Track allocation

Track names are per [ARCHITECTURE.md](ARCHITECTURE.md); owner names get filled
in once [TEAM.md](TEAM.md)'s assignment section is completed (still showing the
Week 1 placeholder as of 13 Aug — that is a prerequisite to putting any of this
on the board).

| Track | Pipeline responsibility |
|---|---|
| **Data & Knowledge** | Owner. Domain, stages, fetchers, extractors, translation, storage. |
| **Rotating fourth** | Consistent second on pipeline. Reviewer for D&K's pipeline PRs. |
| **API/Bot** | Review API + review UI, from Sprint 3 — once the bot is on the real `/chat`. |
| **LLM/Conversation & Safety** | **Untouched.** Stays on RAG, safety, emergency detection, eval. Do not pull this track onto pipeline work; it owns the non-negotiables. |

**Before any of this starts:** add `pipeline` to the track/branch prefixes in
[CONTRIBUTING.md](../CONTRIBUTING.md) (currently `data`, `knowledge`, `rag`,
`safety`, `api`, `bot`). Branches become `pipeline/<short-description>`. That is
an interface change → integration owner → log in [DECISIONS.md](DECISIONS.md).

---

## 4. Sprint 1 remainder — Thu 13 → Fri 21 Aug

**Goal: the walking skeleton.** A resource walks `SUBMITTED → PUBLISHED` in a
test, using fakes only. No network, no models, no database.

This is deliberately unglamorous and it unblocks everyone. Nobody starts on
NLLB or fetchers this sprint.

| ID | Task | Files | Size | Depends on |
|---|---|---|---|---|
| PIPE-01 | Domain enums + models | `domain/enums.py`, `domain/models.py` | 0.5d | — |
| PIPE-02 | State machine + full test suite | `domain/state_machine.py`, `tests/pipeline/test_state_machine.py` | 1d | 01 |
| PIPE-03 | Convert test TODOs to skipped stubs | all `tests/pipeline/test_*.py` | 0.5d | — |
| PIPE-04 | Fakes for every port | `tests/pipeline/fakes.py` | 1.5d | 01 |
| PIPE-05 | **Stage template method** | `stages/base.py` | 2d | 01, 04 |
| PIPE-06 | In-memory queue | `adapters/queue/memory_queue.py` | 1d | 01 |
| PIPE-07 | Filesystem object store | `adapters/storage/filesystem_object_store.py`, `adapters/storage/keys.py` | 0.5d | — |
| PIPE-08 | Fetcher + extractor registries | `registry.py`, `tests/pipeline/test_registry.py` | 0.5d | — |
| PIPE-09 | Stages: ingest, extract | `stages/ingest.py`, `stages/extract.py` | 1.5d | 05, 08 |
| PIPE-10 | Stages: detect_language, translate | `stages/detect_language.py`, `stages/translate.py` | 1.5d | 05 |
| PIPE-11 | Stages: store, review, publish | `stages/store.py`, `stages/review.py`, `stages/publish.py` | 1.5d | 05 |
| PIPE-12 | Passthrough translator + test container | `adapters/translation/passthrough_translator.py`, `container.build_test_container` | 1d | 04, 06, 07 |
| PIPE-13 | **End-to-end skeleton test** | `tests/pipeline/test_stages.py` | 1d | all above |

**PIPE-05 needs Abdillah's review, not just a peer's.** Every stage inherits its
correctness — retry policy, idempotency, transition safety. Getting it wrong
once costs seven times.

**Sprint 1 exit gate:** `pytest backend/tests/pipeline/` is green, and one test
walks a resource from `SUBMITTED` to `PUBLISHED` through all seven stages.

### Sprint 1 work split — four people, zero shared files

The critical path (`01 → 04 → 05 → stages → 13`) is **6.5 days of unavoidably
serial work**. Adding people cannot shorten it — so one person owns that chain
end to end and never waits, and the others work strictly parallel to it.

Sprint 1 alone is only 14 person-days, which would leave three people idle
half the sprint. So three **Sprint 2 adapter tasks are pulled forward**: they
sit behind ports that are already merged, so they have zero dependency on the
critical path and can start on day one. That is exactly what the ports layer
was built for.

| | Owns | Tasks | Days |
|---|---|---|---|
| **Dev A** | Critical path — no context switching | 01 → 04 → 05 `base.py` → 09 ingest/extract → **13 exit gate** | 6.5 |
| **Dev B** | Domain + core infrastructure | 03 → 02 state machine → 08 registries → 07 object store → 06 queue → 12 test container → 10 detect/translate | 6.0 |
| **Dev C** | Real ingestion *(pulled from Sprint 2)* | **17 web fetcher** → **18 HTML extractor** → 11 store/review/publish | 5.5 |
| **Dev D** | Persistence + language *(pulled from Sprint 2)* | **15 SQL repositories** → **19 fastText detector** → **22 chunker** | 6.5 |

**24.5 person-days against 28 capacity — about 12% slack.** A two-person split
of the same work has exactly zero slack, which is why this is the safer shape
even though the sprint total is larger.

#### Day-1 sequencing — the only tight coupling all sprint

1. **Dev B ships PIPE-03 first.** It rewrites every test file, so it must merge
   before anyone else writes a test.
2. **Dev A ships PIPE-01 by lunch.** Dev B and Dev D both need the domain models.
3. **Dev C starts at 09:00.** The web fetcher needs only `ports/fetcher.py`,
   which is already merged. No waiting on anyone.

#### File ownership — nobody touches another person's file

| Dev | Files |
|---|---|
| **A** | `domain/enums.py`, `domain/models.py`, `tests/fakes.py`, `stages/base.py`, `stages/ingest.py`, `stages/extract.py`, `tests/test_stages_ingest_extract.py` |
| **B** | `domain/state_machine.py`, `registry.py`, `container.py`, `adapters/queue/*`, `adapters/storage/keys.py`, `adapters/storage/filesystem_object_store.py`, `adapters/translation/passthrough_translator.py`, `stages/detect_language.py`, `stages/translate.py`, `tests/test_stages_language_translate.py` |
| **C** | `adapters/fetchers/web_fetcher.py`, `adapters/extractors/html_extractor.py`, `stages/store.py`, `stages/review.py`, `stages/publish.py`, `tests/test_stages_store_review_publish.py` |
| **D** | `adapters/storage/sql_repositories.py`, `adapters/language/fasttext_detector.py`, `adapters/translation/chunker.py`, `tests/test_chunker.py` |

`tests/test_stages.py` was split into three files along this boundary for
exactly this reason — as one file, Devs A, B and C would have hit a three-way
merge conflict every day of the sprint.

#### Assignment notes

- **PIPE-05 (`stages/base.py`) is reviewed by Abdillah**, not by a peer. Every
  stage inherits its correctness; a subtle mistake there multiplies by seven.
- **PIPE-15 (SQL repositories)** is the hardest task off the critical path —
  conditional updates and atomic claims, both of which pass single-threaded
  tests while being broken. Give it to whoever rated highest on the skills
  self-assessment.
- **Fix reviewer pairs now**, not ad hoc: A↔B and C↔D. Four people means more
  PRs crossing more boundaries, and "whoever's free" stops working at this size.
- **The stage tasks assume THIN implementations** — status transitions and job
  publishing, with real logic left as TODO for Sprint 2. If someone starts
  implementing real dedup logic in `ingest.py` this week, the sprint fails.

#### What this costs

Putting all four people on the pipeline means Sprint 1's originally committed
goals — the hello-world Telegram round trip, vector store setup, and first
source vetting — **do not happen this sprint**. That is a scope decision for
Kelvin, made knowingly, not discovered at the 21 Aug review.

---

## 5. Sprint 2 — Mon 24 Aug → Fri 4 Sep

**Goal: real content in, real Swahili out.** A vetted URL becomes a
machine-translated Swahili document sitting in the review queue.

| ID | Task | Files | Size | Depends on |
|---|---|---|---|---|
| PIPE-14 | Settings + production container wiring | `config.py`, `container.py` | 1d | 12 |
| PIPE-15 | **SQL repositories on SQLite** | `adapters/storage/sql_repositories.py` | 3d | 01 |
| PIPE-16 | Content deduplicator | `adapters/storage/content_deduplicator.py` | 1d | 15 |
| PIPE-17 | Web fetcher (robots.txt, rate limit, size cap) | `adapters/fetchers/web_fetcher.py` | 2d | 08 |
| PIPE-18 | HTML extractor | `adapters/extractors/html_extractor.py` | 2d | 08 |
| PIPE-19 | fastText language detector | `adapters/language/fasttext_detector.py` | 1.5d | 10 |
| PIPE-20 | Submission service + admin API | `services/submission.py`, `api/routes_pipeline.py`, `api/schemas.py` | 2d | 15 |
| PIPE-21 | Worker entrypoint + CLI submit/status | `worker.py`, `cli.py` | 1.5d | 14 |
| PIPE-22 | Chunker + full test suite | `adapters/translation/chunker.py`, `tests/pipeline/test_chunker.py` | 2d | 01 |
| PIPE-23 | NLLB-200 translator | `adapters/translation/nllb_translator.py` | 3d | 22 |

**PIPE-15 is the highest-risk task in the sprint.** `save()` must be a
conditional update and `claim_next()` must be atomic — both pass every
single-threaded test while being broken. It needs a concurrency test that spawns
two threads and asserts exactly one wins.

**PIPE-23 warning:** torch + NLLB is a multi-GB download. Whoever takes it
should start the download on day one of the sprint, not day six.

> **Midpoint presentation — Fri 28 Aug** falls only 5 days into this sprint.
> Demo honestly: the walking skeleton plus real web ingestion and language
> detection. Translation will not be ready. Say so, and show the review queue
> concept rather than pretending.

**Sprint 2 exit gate:** `cli submit --url <real ministry-of-health page>`
produces a Swahili machine translation stored as version 1, visible via
`cli status`.

---

## 6. Sprint 3 — Mon 7 Sep → Fri 18 Sep

**Goal: the human in the loop.** A real person reviews and edits a real machine
translation, and the edit is stored as a new version.

| ID | Task | Files | Size | Depends on |
|---|---|---|---|---|
| PIPE-24 | SQLite FTS5 search index | `adapters/storage/sqlite_search_index.py` | 1.5d | 15 |
| PIPE-25 | **Review workflow service** | `services/review_service.py`, `tests/pipeline/test_review_service.py` | 3d | 15 |
| PIPE-26 | Review API routes | `api/routes_review.py` | 2d | 25 |
| PIPE-27 | **Minimal review UI** | new: `api/templates/review.html` | 3d | 26 |
| PIPE-28 | PDF fetcher + text-layer extractor | `adapters/fetchers/pdf_fetcher.py`, `adapters/extractors/pdf_text_extractor.py` | 3d | 08 |
| PIPE-29 | Compliance gate + publish stage | `services/compliance.py` | 1.5d | 11 |
| PIPE-30 | CLI requeue / reindex / stats | `cli.py` | 1.5d | 21 |
| PIPE-31 | Per-stage metrics | `observability/metrics.py` | 1.5d | 05 |
| PIPE-32 | Published → `modules/knowledge` handoff | `stages/publish.py` | 1d | 29 |

**PIPE-27 — do not build a React app.** No build step, no npm, no frontend
framework. One server-rendered HTML page with two columns and a save button.
FastAPI + Jinja2, three days. A React review UI is a two-week project that
would eat the rest of the program. Log this in [DECISIONS.md](DECISIONS.md).

**PIPE-32 is the point of the whole module** — it is where vetted Swahili
content reaches the bot's knowledge base. Coordinate with whoever owns
`modules/knowledge` through the integration owner.

**Sprint 3 exit gate:** a teammate opens the review page, edits a machine
translation, saves it, and both version 1 (machine) and version 2 (human) are
retrievable.

---

## 7. Sprint 4 — Mon 21 Sep → Fri 25 Sep

**Goal: prove it works on real content, then hand it over.** No new features.

| ID | Task | Size | Notes |
|---|---|---|---|
| PIPE-33 | **First real review run** — ≥10 vetted documents reviewed end to end | 1d | Not a code task. Nebo staff or the team acting as reviewers. This is the evidence the pipeline works. |
| PIPE-34 | Feedback exporter + quality report | 2d | **Only if PIPE-33 produced ≥50 human edits.** Otherwise there is nothing to learn from — skip it and say why. |
| PIPE-35 | Module docs + known limitations + handover | 1d | Update the module README with what was built vs. parked. |

**The number for the final presentation:** *% of machine translations approved
with no human edit*. It comes free from work the reviewers already did, and it
is far stronger evidence than any automatic MT score. Have it ready.

---

## 8. Cut lines — decide in advance, not in week 8

If the pipeline falls behind, cut **in this order**, top first:

1. PIPE-34 feedback exporter
2. PIPE-31 metrics
3. PIPE-30 CLI requeue/reindex
4. PIPE-24 search index (review UI can list from the database)
5. PIPE-28 PDF path (web-only ingestion)
6. PIPE-29 compliance gate — **only with Abdillah's sign-off**, and then
   publication stays manual

**Never cut:**

- PIPE-02 state machine tests — they encode the safety promise
- PIPE-25 / PIPE-26 / PIPE-27 review path — a pipeline with no human review is
  not the thing that was designed, and it breaks
  [ARCHITECTURE.md](ARCHITECTURE.md) non-negotiable #2
- PIPE-33 the real review run — without it, "it works" is untested

**Trigger to escalate to Kelvin:** if the Sprint 1 exit gate (PIPE-13) is not
met by **Fri 21 Aug**, the reduced scope is still too large. Cut to web-only
ingestion with no PDF path and no compliance gate, and say so at the midpoint
presentation rather than at the final.

## 9. Decisions to log in DECISIONS.md

Each of these affects more than one track, so per
[COLLABORATION.md §5](COLLABORATION.md) they get written down when made:

- [ ] Reduced pipeline scope — video/ASR/OCR parked (this document)
- [ ] `pipeline` added as a track and branch prefix
- [ ] SQLite + filesystem + in-process queue for the MVP; switch thresholds per
      adapter docstring
- [ ] NLLB-200 self-hosted over cloud MT — cost and data control
- [ ] Server-rendered review UI, not React
- [ ] The licence allowlist and the strict-by-default compliance posture
      (needs Nebo's input — raise at the midpoint presentation)
- [ ] The shape of the published → `modules/knowledge` handoff

## 10. Definition of Done — pipeline addendum

Everything in [CONTRIBUTING.md](../CONTRIBUTING.md) applies unchanged. Three
additions specific to this module:

- [ ] The file's TODO checklist is fully addressed, or the remainder is left as
      a TODO with a linked issue — not silently dropped
- [ ] Nothing in `stages/` imports from `adapters/`
- [ ] Any new port implementation honours the contract in its docstring — for
      `translate_batch`, that means a test proving same length and same order
