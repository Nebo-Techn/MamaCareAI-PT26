# Processed

Final chunked passages with source metadata (which document, which section),
ready to be embedded into the vector store. This is what
`backend/modules/rag` actually retrieves from at answer time — chunk size and
boundaries directly determine answer quality, so this stage is worth getting
right, not rushing.

**Owner track:** Data & Knowledge
**Sprint:** 2–3
