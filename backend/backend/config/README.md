# Config

Environment configuration and settings, loaded via `pydantic-settings` from a
local `.env` file (never committed — see root `.gitignore`).

Holds things like: the Gemini API key, vector store path, Telegram bot token,
log level. Anything that differs between a developer's laptop and the
deployed bot belongs here, not hard-coded in the modules that use it.

**Owner track:** whoever sets up `backend/core` in Sprint 1 — after that,
anyone adding a new setting touches this folder.
