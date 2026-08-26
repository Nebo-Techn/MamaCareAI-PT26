# Architecture

## What we're building

A Telegram bot that answers Swahili questions about maternal and newborn
health, grounded in vetted, real sources, with safety guardrails around
emergencies and scope. Text-only for the 8-week build (see
`backend/modules/media/README.md` for why).

## Why this stack (all free-tier / open-source — no budget provisioned)

| Piece | Choice | Why |
|---|---|---|
| LLM (generation) | Google Gemini free tier | Generous free quota, strong multilingual/Swahili quality, simple Python SDK. Isolated behind `backend/core` so it can be swapped later. |
| Embeddings | Local multilingual `sentence-transformers` model | Runs free on a laptop/small server, no API cost, good multilingual coverage — avoids paying for every embedding call. |
| Vector store | Chroma (local) | Free, embedded, no server to provision — right-sized for an 8-week MVP's data volume. |
| Backend | FastAPI | Standard, well-documented, easy for students to learn, async-friendly. |
| Bot channel | Telegram Bot API | Free, no business-verification approval gate (unlike WhatsApp Business API), real chat UX. |
| Relational storage | SQLite via `backend/alembic` | Now required: `modules/pipeline` needs real tables for resource state, content versions, review assignments, and the audit trail. Same migrations apply to PostgreSQL if it outgrows SQLite. |
| Translation (source language → Swahili) | Self-hosted NLLB-200 | Free, no per-call cost, solid Swahili coverage — cost scales with hardware, not corpus size. Isolated behind `modules/pipeline`'s `Translator` port so cloud MT is a config change. |

## Data flow

```
Vetted source (data/01_source_register)
        │
        ▼
  pipeline ── ingest ──▶ data/02_raw
        │       │
        │     extract ──▶ data/03_extracted   (source language, still messy)
        │       │
        │  detect language ──▶ translate to Swahili
        │       │
        │   HUMAN REVIEW  ──▶ approve  ──▶ publish
        │                                     │
        ▼                                     ▼
                                        data/04_cleaned   (approved Swahili)
        │
        ▼
  knowledge  ──▶  data/05_processed  ──▶  vector store (storage)
                                                                       │
Telegram user ──▶ bot ──▶ api (/chat) ──▶ rag (retrieve + generate) ──┘
                                              │
                                              ▼
                                           safety (disclaimer, emergency
                                           redirect, scope refusal, groundedness
                                           check, logging)
                                              │
                                              ▼
                                        answer back to bot ──▶ Telegram user
```

## Non-negotiables

1. **Every response carries a medical disclaimer.** Not optional, not
   sometimes — every response.
2. **Every response is grounded in a real, cited source**, or the bot says it
   doesn't know. No hallucinated medical claims.
3. **Emergency/red-flag questions are never answered by the LLM.** They're
   detected and redirected to real care information.
4. **Every source in the knowledge base is traceable** to a row in
   `data/01_source_register` with a vetting decision.
5. **Safety-relevant interactions are logged** for human review, not just
   generated and forgotten.

## After the 8-week handover (documented, not built now)

- WhatsApp channel via Meta Cloud API or Twilio, once business verification
  is sorted — the bot/api split means this is a new thin adapter, not a
  rewrite.
- Voice-note and image support (`backend/modules/media`).
- Moving off free-tier LLM/embedding limits if usage grows past them.
