# Knowledge

Turns extracted text into a usable knowledge base:

1. Clean and de-duplicate extracted text (Swahili-aware normalization, encoding
   fixes, boilerplate removal) → `data/04_cleaned`
2. Chunk cleaned text into retrieval-sized passages with source metadata
   (which document, which section) → `data/05_processed`
3. Generate embeddings for each chunk using a local, free, multilingual model
   (e.g. `sentence-transformers` multilingual-e5) and write them to the vector
   store via `modules/storage`

**Input:** `data/03_extracted`
**Output:** `data/04_cleaned`, `data/05_processed`, populated vector store
**Owner track:** Data & Knowledge
**Sprint:** 2–3

Every chunk must keep a traceable link back to its source document — the RAG
module cites sources, and citations are only honest if this link is intact.
