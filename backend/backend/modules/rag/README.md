# RAG (Retrieval-Augmented Generation)

The core "brain" of MamaCare AI. Given a user's Swahili question:

1. Embed the question with the same model used in `modules/knowledge`
2. Retrieve the top-k most relevant chunks from the vector store
   (`modules/storage`)
3. Build a grounded prompt: the question + retrieved chunks + instructions to
   answer only from what was retrieved, in Swahili, and to say when it
   doesn't know
4. Call the LLM (Gemini free tier, via `backend/core`) to generate the answer
5. Return the answer **with** which sources it was grounded in

Every response from this module must pass through `modules/safety` before it
reaches a user — RAG is responsible for a grounded, cited draft answer, not
for deciding what's safe to send.

**Input:** a user question (from `modules/api` / the bot)
**Output:** a grounded answer + source citations
**Owner track:** LLM/Conversation & Safety
**Sprint:** 2 (basic retrieval + generation), 3 (query rewriting for
Swahili colloquialisms/code-switching, re-ranking), 4 (polish)
