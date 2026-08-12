# Safety

Non-negotiable guardrails. Every answer from `modules/rag` passes through
here before it reaches a real user. This module exists because MamaCare AI
gives health information to real pregnant people and new parents — getting
this wrong is not an acceptable trade for shipping faster.

Responsibilities:

- **Emergency/red-flag detection** — if the question describes symptoms that
  need real, immediate care (heavy bleeding, severe pain, no fetal movement,
  danger signs in a newborn, etc.), do not attempt to answer it with RAG.
  Redirect to real emergency guidance and a real referral (e.g. nearest
  facility / hotline — to be confirmed with Nebo before launch).
- **Medical disclaimer** — attached to every response, not just some of them.
- **Scope refusal** — refuse diagnosis, medication dosing, or anything beyond
  general educational maternal/newborn health information.
- **Groundedness check** — reject or flag answers that aren't actually
  supported by the retrieved sources (no hallucinated claims presented as
  fact).
- **Logging** — every flagged/refused interaction is logged (see
  `modules/storage`) so the team and Nebo can review it — this is what makes
  "we monitor safety" true instead of aspirational.

**Owner track:** LLM/Conversation & Safety
**Sprint:** 2 (baseline: disclaimer + scope refusal), 3 (emergency
detection + logging — hardened before the midpoint presentation)

This module is reviewed line-by-line before the Week 4 and Week 8
presentations — nothing ships to real users without a human checking this
folder specifically.
