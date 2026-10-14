# MamaCare AI

MamaCare AI is a Swahili conversational AI project focused on providing
natural, accessible, and trustworthy maternal and newborn health information
via a Telegram bot, grounded in vetted, reputable health sources.

> MamaCare AI is an educational and technical project. It does not replace
> qualified medical professionals or emergency medical care.

## Repository layout

```
data/            Source register + the pipeline stages that turn vetted
                  sources into machine-usable knowledge (see data/*/README.md)
backend/
  modules/
    pipeline/     collect (web/PDF) → detect language → translate to Swahili
                  → human review → publish. Feeds knowledge/.
    ingestion/    absorbed into pipeline/ — see its README
    knowledge/    chunk & embed approved Swahili content
    storage/      vector store + runtime relational data access
    rag/          retrieval + grounded generation
    safety/       disclaimers, emergency detection, scope refusal, logging
    api/          FastAPI routers (/chat, /health)
    media/        OUT OF SCOPE for the 8-week MVP — see its README
  bot/            the Telegram bot — the actual user-facing product
  core/           config loading, LLM client wrapper
  config/         environment settings (.env, never committed)
  shared/         cross-cutting utilities
  tests/          automated tests (required for every module change)
  alembic/        DB migrations, only if/when needed
eval/             evaluation harness: test questions + dated reports
docs/             architecture, team, collaboration, and the 8-week program
logbooks/         each trainee's weekly work log
```

Start here, in order: 
- [docs/TEAM.md](docs/TEAM.md) (who's building this and
how tracks get assigned)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (how
the pieces fit together and why)
- [CONTRIBUTING.md](CONTRIBUTING.md) (the
day-to-day workflow: branches, PRs, Definition of Done)
- [docs/COLLABORATION.md](docs/COLLABORATION.md) (how four people build this
independently without colliding). 
- [docs/INTERNSHIP_PROGRAM.md](docs/INTERNSHIP_PROGRAM.md)
has the full 8-week plan
- [docs/DECISIONS.md](docs/DECISIONS.md) is the
running log of cross-team decisions.

## Quick start

### Windows PowerShell

```powershell
uv sync
Copy-Item backend/config/.env.example backend/config/.env   # add your own API keys
uv run uvicorn backend.main:app --reload
```

### Run the automated tests

From the repository root, run:

```powershell
uv run pytest backend/tests/pipeline -q
```

To run the complete suite, use `uv run pytest -q`. The first `uv` command
creates the project's local environment from `pyproject.toml` and `uv.lock`.

## 30-minute project presentation

The presentation should be delivered as a product-and-safety walkthrough for
Nebo leadership, partners, and reviewers. The key message is: **MamaCare AI
is a practical Swahili maternal and newborn health assistant whose answers are
traceable to vetted sources and protected by safety guardrails.**

| Time | Slide | What to say |
|---:|---|---|
| 0:00–1:30 | **MamaCare AI: trusted maternal and newborn health information in Swahili** | Introduce the project, the intended users, and the promise: accessible information without pretending to replace a clinician. State that it is a Telegram-based, text-first MVP. |
| 1:30–4:00 | **The problem is not only access—it is trustworthy understanding** | Explain that people need maternal and newborn information in a language and channel they can use. Stress that medical answers require trustworthy sources, clear limits, and urgent-care escalation. |
| 4:00–6:00 | **Our response: a grounded Swahili conversation experience** | Describe the user journey: a person asks in Telegram; MamaCare retrieves approved information; the answer returns with a disclaimer and source grounding. |
| 6:00–9:00 | **The architecture separates the conversation from the knowledge pipeline** | Walk through Telegram → bot → FastAPI → RAG → safety → response. Explain that separating these parts makes the system easier to test and improve. |
| 9:00–13:00 | **Only vetted content can reach the knowledge base** | Explain the pipeline: source register, ingest, extract, language detection, Swahili translation, human review, publish, chunk/embed, and retrieval. Highlight that human review comes before publishing. |
| 13:00–16:00 | **Safety is built into every response, not added at the end** | Cover the non-negotiables: medical disclaimer, cited/grounded responses or an honest “I don’t know,” emergency redirection outside the LLM, source traceability, and logging for review. |
| 16:00–20:00 | **Live demo: normal question, uncertainty, and emergency red flag** | Demo three prepared flows: (1) a routine Swahili question, (2) a question the bot cannot safely answer, and (3) an emergency/red-flag message that redirects to immediate care. Do not improvise clinical advice. |
| 20:00–23:00 | **Quality is demonstrated with tests and evaluation, not claims** | Show the test command below and one passing run. Explain that each module change needs a matching automated test. Then show the evaluation harness/report if available; do not invent performance figures. |
| 23:00–26:00 | **The eight-week plan turns the prototype into a handover-ready MVP** | Summarize the four sprints: end-to-end wiring, real RAG and baseline safety, hardening/evaluation, then polish/deployment/handover. |
| 26:00–28:30 | **What is deliberately out of scope today** | State the boundaries: text-only MVP, Telegram before WhatsApp, no voice or image processing, and free-tier/open-source infrastructure. Explain that these are scope decisions, not forgotten features. |
| 28:30–30:00 | **What we need next** | Close with the next decisions: confirm emergency referral information, validate the source register/review process, select pilot users, and agree the WhatsApp/deployment roadmap. Invite questions. |

### Demo checklist

Before presenting, use a prepared Telegram test account and verify that the
API is running. Prepare a routine question in Swahili, an out-of-scope or
uncertain question, and an emergency/red-flag example. Keep any real health
information anonymized. Show only verified results—never substitute a mock
metric for evaluation evidence.
