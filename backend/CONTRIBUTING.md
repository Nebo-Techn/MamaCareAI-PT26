# Contributing

Working agreement for everyone on MamaCare AI, students and mentors alike.
Start with `docs/TEAM.md` (who owns what) and `docs/COLLABORATION.md` (how
four people stay autonomous without colliding) — this file is the mechanics
those two documents rely on. `docs/INTERNSHIP_PROGRAM.md` has the full
8-week program this supports.

## Branches

- Never commit directly to `main` — enforced by a GitHub branch-protection
  rule (1 required review, no direct pushes), not just this document.
- Branch name: `<track>/<short-description>`, e.g. `rag/add-source-citations`,
  `data/vetting-first-10-sources`.
- Tracks: `data`, `knowledge`, `rag`, `safety`, `api`, `bot`.

## Commits

Short, present-tense, describes what changed: `Add emergency keyword
detection to safety module`, not `fix stuff` or `wip`.

## Pull requests

Every PR must, before merge:

1. Link to the task/issue it addresses.
2. Include or update a test in `backend/tests/` for any behavior change.
3. Pass CI (`.github/workflows/ci.yml`).
4. Get **at least one review from a teammate** — not a mentor, a peer. This
   is how the team learns to read each other's code and catch issues early,
   not just how the code gets approved.
5. Fill out the PR template checklist (`.github/PULL_REQUEST_TEMPLATE.md`).
6. If it changes an interface another track depends on (an API shape, a data
   schema, a config name), it goes through that week's integration owner —
   see `docs/TEAM.md` — and gets logged in `docs/DECISIONS.md`.

## Weekly technical sync

Wednesdays, 15–20 minutes, run by that week's integration owner — not the
program lead's meeting. Covers what merged, what's about to change that
others depend on, and anything about to collide. Full details in
`docs/COLLABORATION.md`.

## Definition of Done (applies to every task, not just code)

A task is not done when it "works on my machine." It's done when:

- [ ] It runs end-to-end from a clean checkout (not just in one person's setup)
- [ ] There's a test that would fail if this broke
- [ ] It's been reviewed and merged, not sitting in a branch
- [ ] Anything a teammate needs to know is written down (README update, code
      comment only where the *why* isn't obvious from the code)
- [ ] If it touches `modules/safety` or `modules/rag`, it's been manually
      tried with at least one real Swahili question, not just imagined

## Running locally

```
cd backend
pip install -r requirements.txt
cp config/.env.example config/.env   # fill in your own API keys, never commit this file
uvicorn main:app --reload
pytest
```
