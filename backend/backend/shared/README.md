# Shared

Cross-cutting utilities used by more than one module: Swahili text helpers,
logging setup, shared constants.

Rule: don't put something here until at least two modules actually need it.
A `shared/` folder that gets used as a dumping ground for one-off helpers is
how codebases rot — if only `modules/rag` needs it, it lives in
`modules/rag`.

**Owner track:** shared, whoever needs it first

## Confirmed candidates (the two-module rule is now met)

**Swahili text normalization** — NFC normalization, whitespace collapse,
mojibake repair, zero-width character stripping. Needed by:

- `modules/pipeline/adapters/extractors/*` — every extractor owes normalized
  output, and broken encodings survive all the way into the vector store if
  they don't
- `modules/knowledge` — same operations before chunking

Two modules, same operations, high cost of divergence. This belongs here.
Write it once, test it once, with real Swahili strings — not English ones.

**Logging setup** — structured JSON logging with `resource_id` and `stage` on
every line. The pipeline's workers need it (see
`modules/pipeline/worker.py`), and the API and bot want the same format so
one grep answers "what happened to this request?" across all of them.

Nothing else qualifies yet. Resist the third candidate until it genuinely has
two callers.
