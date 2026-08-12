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
    ingestion/    fetch & parse source documents
    knowledge/    clean, chunk, embed
    storage/      vector store + optional relational data access
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

Start here, in order: [docs/TEAM.md](docs/TEAM.md) (who's building this and
how tracks get assigned), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (how
the pieces fit together and why), [CONTRIBUTING.md](CONTRIBUTING.md) (the
day-to-day workflow: branches, PRs, Definition of Done), and
[docs/COLLABORATION.md](docs/COLLABORATION.md) (how four people build this
independently without colliding). [docs/INTERNSHIP_PROGRAM.md](docs/INTERNSHIP_PROGRAM.md)
has the full 8-week plan, and [docs/DECISIONS.md](docs/DECISIONS.md) is the
running log of cross-team decisions.

## Quick start

```
cd backend
pip install -r requirements.txt
cp config/.env.example config/.env   # fill in your own API keys
uvicorn main:app --reload
```
