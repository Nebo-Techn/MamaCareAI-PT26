# Core

Shared orchestration and glue code:

- Loads configuration from `backend/config` (settings, API keys from `.env`)
- Wraps the LLM provider (Google Gemini free tier) behind one interface, so
  switching providers later is a one-file change, not a rewrite
- Owns the **database engine and session factory** shared by
  `modules/storage` and `modules/pipeline` — one connection pool and one
  migration history for the single SQLite file, not two modules each opening
  their own handle
- Wires the app together at startup (which modules talk to which)

**Owner track:** shared — whoever is building `modules/rag` will spend the
most time here, since the LLM client wrapper lives in this folder.
**Sprint:** 1 (skeleton), refined through 4

## Note on the LLM wrapper and the pipeline

The pipeline does **not** use the chat LLM. It translates with NLLB-200 behind
its own `Translator` port (`modules/pipeline/ports/translator.py`), which is a
separate concern with separate failure modes and a separate cost profile.

So there is no contention over this folder: the Gemini wrapper serves
`modules/rag` only. Don't route machine translation through it, and don't add
translation methods to it.
