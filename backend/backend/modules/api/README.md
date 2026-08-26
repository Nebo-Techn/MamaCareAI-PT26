# API

FastAPI routers that expose the RAG pipeline over HTTP:

- `POST /chat` — the main endpoint: takes a user message, runs it through
  `modules/rag` → `modules/safety`, returns the final answer. This is what
  `backend/bot` calls.
- `GET /health` — liveness check, used by deployment and by CI.
- Admin/eval endpoints — trigger an evaluation run, inspect flagged
  interactions (kept simple; this is an internal tool, not a public surface).

**Input:** HTTP requests (from the bot, or a developer testing locally via
Swagger UI at `/docs`)
**Output:** JSON responses
**Owner track:** API/Bot track
**Sprint:** 1 (skeleton with `/health` — this is the very first thing that
should run, before any real logic exists, to prove the app boots), 2–4 (real
`/chat` endpoint as RAG and safety come online)
