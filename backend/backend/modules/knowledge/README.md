# Knowledge

Turns approved Swahili content into a retrievable knowledge base:

1. Chunk approved text into retrieval-sized passages with source metadata
   (which document, which section) → `data/05_processed`
2. Generate embeddings for each chunk using a local, free, multilingual model
   (e.g. `sentence-transformers` multilingual-e5) and write them to the vector
   store via `modules/storage`

**Input:** `data/04_cleaned` — approved, human-reviewed Swahili text published
by `modules/pipeline`
**Output:** `data/05_processed`, populated vector store
**Owner track:** Data & Knowledge
**Sprint:** 2–3

Every chunk must keep a traceable link back to its source document — the RAG
module cites sources, and citations are only honest if this link is intact.

## What changed, and what this module no longer does

Cleaning, de-duplication, and Swahili-aware normalization used to live here.
They now happen upstream in `modules/pipeline`, which extracts, translates,
and puts every document through **human review** before publishing it to
`data/04_cleaned`. That is a stronger guarantee than the manual spot-check this
module originally promised.

So this module's job is now narrower and better defined: **chunk and embed**.
Anything arriving in `data/04_cleaned` has already been read and approved by a
person.

## Two chunkers, on purpose — do not merge them

There is also a chunker in
`modules/pipeline/adapters/translation/chunker.py`. It looks similar and wants
the opposite things:

| | Pipeline chunker | This module's chunker |
|---|---|---|
| Splits for | a machine-translation engine's length limit | retrieval quality |
| Overlap | **zero** — overlapping text gets translated twice, then has to be de-duplicated | **non-zero** — overlap improves retrieval recall |
| Must preserve | exact block alignment for side-by-side human review | semantic coherence within a chunk |

Copying one into the other will quietly break whichever it was not written for.

See `DEC-0002` in `docs/DECISIONS.md`.
