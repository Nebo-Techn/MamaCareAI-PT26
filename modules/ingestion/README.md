# Ingestion — absorbed into `modules/pipeline`

**This module's work moved.** Fetching and parsing source documents is now
stages 1–2 of the multilingual data collection pipeline:

| What you're looking for | Where it lives now |
|---|---|
| Fetching web pages, PDFs | `modules/pipeline/adapters/fetchers/` |
| Parsing HTML, PDF text layers | `modules/pipeline/adapters/extractors/` |
| Orchestration, retries, dedup | `modules/pipeline/stages/ingest.py`, `stages/extract.py` |

**The data contract is unchanged:** raw originals still land in
`data/02_raw`, extracted text still lands in `data/03_extracted`.

**The vetting rule is unchanged and still enforced:** nothing is fetched
without an approved row in `data/01_source_register` first. It now lives in
`modules/pipeline/services/submission.py`, where there is no bypass.

## Why it moved

Ingestion and pipeline stages 1–2 were the same job, owned by the same track,
scheduled in the same sprint. Two fetchers and two extractors maintained by the
same people is precisely the duplication `docs/COLLABORATION.md` exists to
prevent — so there is one of each, behind the `SourceFetcher` and
`ContentExtractor` ports.

Ingestion also only ever handled the first two steps. Everything after
extraction — language detection, translation to Swahili, human review,
publication — had no home before the pipeline module existed.

See `DEC-0002` in `docs/DECISIONS.md`.

**Owner track:** Data & Knowledge (unchanged — same people, one codebase)
