# Pipeline — multilingual data collection

Implements the architecture in `Multilingual_Data_Pipeline_Architecture.pdf`:
collect resources from web links, video links, and PDFs → detect source
language → translate to Swahili → store every artifact → route through human
review → publish.

For MamaCare AI, this module is the **feeder** for the knowledge base. Its
published output is the vetted Swahili content that `modules/knowledge` chunks
and embeds. Nothing reaches the bot without passing through here and being
approved by a human.

**Owner track:** Data & Knowledge (stages 1–5), API/Bot track (review UI,
stages 6–7)
**Sprint:** see the build order below

---

## The one rule: dependencies point inward

```
domain/     pure Python. No I/O. The vocabulary and the lifecycle rules.
   ▲
ports/      abstract interfaces. What the pipeline NEEDS.
   ▲
stages/     the seven use cases. Orchestrates ports. NEVER imports adapters.
services/   human-driven use cases (review, submission, compliance).
   ▲
adapters/   concrete implementations. httpx, boto3, PyMuPDF, NLLB, SQLAlchemy.
   ▲
container.py   the ONLY file that knows which adapter fills which port.
```

If you write `from ..adapters...` inside `stages/`, stop — that is the mistake
this layout exists to prevent. Ask for a review before working around it.

### Why this is worth the extra folders

1. **Tests run with no infrastructure.** No API keys, no database, no GPU,
   no network. `build_test_container()` and every stage is testable in
   milliseconds.
2. **The MVP runs free.** `docs/ARCHITECTURE.md` commits to free-tier and
   open-source only. The defaults are SQLite + local filesystem + in-memory
   queue + self-hosted NLLB. Production swaps to Postgres + S3 + SQS +
   OpenSearch by changing environment variables — **zero stage code changes**.
3. **The design doc's open questions do not block us.** Section 6 asks
   "self-hosted or cloud translation?" and "what volume?". Both are answered by
   config, later, on evidence.
4. **Four people can work in parallel** without editing the same files. One
   person on extractors, one on translation, one on review, one on storage.

---

## How the PDF maps onto this folder

| PDF section | Lives in |
|---|---|
| 3.1 Ingestion | `stages/ingest.py`, `adapters/fetchers/` |
| 3.2 Extraction & normalization | `stages/extract.py`, `adapters/extractors/` |
| 3.3 Language detection | `stages/detect_language.py`, `adapters/language/` |
| 3.4 Translation to Swahili | `stages/translate.py`, `adapters/translation/` |
| 3.5 Storage | `stages/store.py`, `adapters/storage/` |
| 3.6 Human review & edit | `stages/review.py`, `services/review_service.py`, `api/routes_review.py` |
| 3.7 Published output | `stages/publish.py` |
| 4. Orchestration & retries | `stages/base.py`, `worker.py` |
| 4. Observability | `observability/metrics.py` |
| 4. Compliance | `services/compliance.py` |
| 5. Technology stack | `container.py`, `config.py` |

---

## Build order

Do not build this in the order the PDF describes it. Build a thin slice that
runs end to end first, then deepen each stage. A pipeline that processes one
document badly is far more useful than four perfect stages that have never been
connected.

**Sprint 1 — the skeleton that runs**
1. `domain/` (enums, models, state_machine) + `tests/pipeline/test_state_machine.py`
2. `ports/` — all interfaces, no implementations
3. `tests/pipeline/fakes.py` — write these before the real adapters
4. `stages/base.py` — the template method, reviewed carefully
5. `MemoryQueue`, `FilesystemObjectStore`, `PassthroughTranslator`
6. `container.build_test_container()`
   → **Done when:** a fake resource walks SUBMITTED → PUBLISHED in a test.

**Sprint 2 — real content in**
7. `WebFetcher` + `HtmlExtractor` (one real web page, end to end)
8. `PdfFetcher` + `PdfTextExtractor`
9. `SqlRepositories` on SQLite + `ContentDeduplicator`
10. `FastTextDetector`
    → **Done when:** a real ministry-of-health URL reaches the review queue.

**Sprint 3 — translation and review**
11. `NllbTranslator` + `Chunker` (the chunker deserves real tests)
12. `ReviewService` + `api/routes_review.py`
13. `SqliteSearchIndex`
    → **Done when:** a reviewer edits a machine translation in a UI and
    version 2 is stored alongside version 1.

**Sprint 4 — hardening**
14. `PdfOcrExtractor`, `VideoFetcher`, `CaptionExtractor`, `AsrExtractor`
15. `ComplianceGate` + `stages/publish.py`
16. `observability/metrics.py`, `cli.py` (`requeue`, `reindex`)
17. `FeedbackExporter` — once there are enough human edits to learn from

---

## Running it

```bash
cd backend
pip install -r requirements.txt
cp config/.env.example config/.env

# one worker per stage (separate terminals, or separate containers)
python -m backend.modules.pipeline.worker --stage ingest
python -m backend.modules.pipeline.worker --stage extract
python -m backend.modules.pipeline.worker --stage translate

# submit something
python -m backend.modules.pipeline.cli submit --url https://example.org/guide.pdf --type pdf
python -m backend.modules.pipeline.cli status --resource-id <id>
```

---

## Non-negotiables

These are not style preferences. A PR that breaks one does not get merged.

1. **Nothing publishes without human approval.** `STORED → PUBLISHED` is not a
   legal transition and never will be.
2. **A human edit creates a new version.** It never overwrites the machine
   translation. `VersionRepository` has no update method, deliberately.
3. **Every action writes an audit event.** This content is authoritative once
   published; "who approved this?" must always have an answer.
4. **Every source is vetted before ingestion** — it has a row in
   `data/01_source_register`. `SubmissionService` enforces it, with no bypass.
5. **Stages are idempotent.** Queues deliver at-least-once. Assume every job
   runs twice.
6. **`stages/` never imports `adapters/`.**

## Known trade-offs, recorded honestly

- **SQLite over PostgreSQL, SQLite FTS5 over OpenSearch, in-process queue over
  Kafka.** The PDF specifies the production stack; `docs/ARCHITECTURE.md` says
  no budget is provisioned. The ports make this reversible, and each adapter
  documents the threshold at which switching is justified.
- **ASR runs inside the extract stage for now**, rather than as its own stage.
  It should be split out when video volume justifies it — the registry makes
  that a routing change, not a rewrite. Log it in `docs/DECISIONS.md` when you
  do.
- **Near-duplicate detection is not built.** Exact content hashing only. Add
  SimHash/MinHash if exact hashing proves insufficient in practice — measure
  before building.
