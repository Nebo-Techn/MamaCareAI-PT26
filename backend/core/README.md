# Core

Shared orchestration and glue code:

- Loads configuration from `backend/config` (settings, API keys from `.env`)
- Wraps the LLM provider (Google Gemini free tier) behind one interface, so
  switching providers later is a one-file change, not a rewrite
- Wires the app together at startup (which modules talk to which)

**Owner track:** shared — whoever is building `modules/rag` will spend the
most time here, since the LLM client wrapper lives in this folder.
**Sprint:** 1 (skeleton), refined through 4
