# Storage

Data access layer used by every other module. Two things live here:

- **Vector store client** — wraps a local, free vector database (Chroma) that
  holds embedded knowledge chunks from `modules/knowledge`. This is what
  `modules/rag` queries at answer time.
- **Relational data access** (optional, via `backend/alembic`) — for
  structured data that doesn't belong in the vector store: the source
  register, evaluation run logs, conversation history. Only add a table when
  a real feature needs one; don't pre-build a schema nobody uses yet.

**Owner track:** Data & Knowledge (vector store), API/Bot track (relational, if/when needed)
**Sprint:** 1–2 (vector store setup is a Sprint 1 priority — the team can't
build RAG until this exists)
