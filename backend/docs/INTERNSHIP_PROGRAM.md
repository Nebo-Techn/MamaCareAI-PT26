# MamaCare AI — 8-Week Program

Elia, Walii, Jackson, and Kornelly — UDSM AI-track — building MamaCare AI from
**Monday, 3 August 2026** to **Friday, 25 September 2026**. This is your
build. By Week 8 the goal is that each of you can point at a real, working
piece of it and say "I built that."

## Goals, both of them, at once

1. **You leave with real, demonstrable AI-engineering experience**: shipped
   code, code review habits, working with a team, presenting to stakeholders
   — not just a certificate.
2. **Nebo has a working product at Week 8**: a Telegram bot that answers real
   Swahili maternal/newborn health questions, grounded in vetted sources,
   with safety guardrails, evaluated and documented — not a pile of
   disconnected scripts.

Neither goal is sacrificed for the other. See `docs/ARCHITECTURE.md` for what
"working" concretely means and why the scope (Telegram, text-only, free-tier
LLM) is set where it is.

## Team & leadership

See `docs/TEAM.md` for the full roster, how track ownership gets
self-selected in Week 1, the rotating integration-owner role, and reviewer
pairing. See `docs/COLLABORATION.md` for how the team stays autonomous
without four people colliding, and `docs/DECISIONS.md` for the shared
decision log.

- **Kelvin Byabato** — Program Lead: schedule, admin, the daily rhythm.
- **Abdillah Issa** — Technical Lead: architecture calls, final sign-off on
  anything touching `modules/safety`.

Four tracks (Data & Knowledge, LLM/Conversation & Safety, API/Bot, and a
weekly-rotating fourth), each with a named owner and a named reviewer — but
every student touches more than one track over the 8 weeks. Full
track-to-folder mapping is in `docs/ARCHITECTURE.md`.

## Working mode

- **On-site**, Nebo office, Monday–Friday, core hours 08:30–17:00.
- Two short live check-ins with Kelvin each day — everything else is yours to
  run. Most of the day is **asynchronous by design**: the task board, the
  logbook, the decision log, PR review — so the team moves independently
  most of the time. Synchronous time is kept to what actually needs a live
  conversation.
- **Contribution happens through PRs**, reviewed by a peer, not through
  handing work to a lead to finish or approve — see `CONTRIBUTING.md`.

## What a day looks like

| Time | What |
|---|---|
| 08:30 | Arrive |
| 08:30–08:45 | **Check-in** (15 min, with Kelvin) — today's priorities off the task board, blockers, quick alignment |
| Morning | Build block on your track's current task — your call on how |
| Midday | Pairing block — cross-track tasks, or a PR review that needs a real conversation |
| Afternoon | Continue build block; open/respond to PRs |
| Wednesday, mid-afternoon | Mid-week technical sync (peer-run, see `docs/COLLABORATION.md`) |
| 16:50–17:00 | **Check-out** (10 min, with Kelvin) — what shipped today, what's flagged for tomorrow |
| End of day | Two-minute logbook entry (`logbooks/<name>/week-XX.md`) |

The check-in and check-out are Kelvin's — firm, on time, every day. Everything
between them is yours to run.

## Calendar: 4 two-week sprints

**Week 1 (3–7 Aug): Orientation + Sprint 0**
- Mon 3 Aug — **Orientation**: introductions, workplace basics, GitHub access,
  repo walkthrough, read `docs/ARCHITECTURE.md`, `CONTRIBUTING.md`,
  `docs/TEAM.md`, and `docs/COLLABORATION.md` together. Logbook explained;
  arrival notes flagged as due next Wednesday.
- Tue 4 Aug — Skills self-assessment + track self-selection (`docs/TEAM.md`),
  reviewer pairs decided, integration-owner rotation order set.
- Wed–Thu, 5–6 Aug — Guided foundations: git branching/PR workflow, FastAPI
  basics, what RAG is and why, intro to embeddings, intro to LLM prompting.
  Hands-on, not lecture-only.
- Fri 7 Aug — Sprint 1 planning, first PRs opened (everyone ships something
  reviewed and merged by end of Week 1).

**Sprint 1 — Weeks 2–3 (10–21 Aug): Prove the system is wired together**
Goal: a "hello world" round trip works end-to-end — Telegram message → bot →
API `/chat` → canned response → back to Telegram — plus the vector store is
set up and the first batch of real sources is vetted and ingested.
→ **Arrival notes due Wed 12 Aug.**
→ Sprint review/retro Fri 21 Aug.

**Sprint 2 — Weeks 4–5 (24 Aug–4 Sep): Real RAG + baseline safety**
Goal: real retrieval and generation grounded in the first real knowledge
base; baseline safety (disclaimer on every response, scope refusal); bot
wired to the real pipeline, not canned responses.
→ **Midpoint presentation, Fri 28 Aug** (or when convenient for Nebo
leadership that week). See agenda below.
→ Sprint review/retro Fri 4 Sep.

**Sprint 3 — Weeks 6–7 (7–18 Sep): Harden it**
Goal: broaden the knowledge base, improve retrieval quality (query rewriting
for Swahili colloquialisms/code-switching), emergency/red-flag detection with
real referral info, logging of flagged interactions, first real evaluation
run with the `eval/` harness.
→ Sprint review/retro Fri 18 Sep.

**Sprint 4 — Week 8 (21–25 Sep): Evaluate, polish, hand over**
Goal: final evaluation run, fix top issues it surfaces, polish bot UX and
error handling, finish documentation, deploy, rehearse the final
presentation, write the handover doc.
→ **Final presentation, Fri 25 Sep** (or when convenient for Nebo leadership
that week).

## Ceremonies

- **Daily check-in** (08:30, 15 min, with Kelvin): today's priorities and
  blockers.
- **Daily check-out** (16:50, 10 min, with Kelvin): what moved today.
- **Sprint planning** (Day 1 of each sprint): what's being built, broken into
  tasks small enough to finish in 2–3 days each.
- **Sprint review/demo** (last day of each sprint): show what actually
  runs — a live demo, not a slide describing what should work.
- **Retro** (last day of each sprint, 15 min): what went well, what didn't,
  one thing to change next sprint.
- **Weekly 1:1s** (15 min each, with Kelvin, informal): how it's going,
  anything stuck, anything worth knowing. About you, not the code.
- **Mid-week technical sync** (Wednesday, peer-run — see
  `docs/COLLABORATION.md`): separate from check-in/check-out, this one's
  about keeping the pieces you're each building actually fitting together.

## Presentation agendas

**Midpoint (Fri 28 Aug)**: what's built and demoably working today (live
demo of the hello-world-to-real-RAG progression), what the evaluation harness
looks like even if early, what's on track vs. at risk for Week 8, what
decisions need Nebo's input (e.g. real emergency referral contact info,
WhatsApp timeline).

**Final (Fri 25 Sep)**: live demo of the working bot answering real
questions, the evaluation report (numbers, not adjectives), safety guardrails
demonstrated (refusal + emergency redirect), documentation and handover
materials, what's explicitly out of scope and why, recommended next steps.

## Administrative timeline

| When | What | Owned by |
|---|---|---|
| Mon 3 Aug | Orientation | Kelvin |
| **Wed 12 Aug** | **Arrival notes due** — official reporting confirmation, countersigned by Nebo, ready for UDSM | You request/bring it, Kelvin countersigns |
| Every Friday | Weekly logbook submitted (`logbooks/<name>/week-XX.md`) for sign-off | Each of you |
| End of each sprint | Internal progress check-in | Kelvin |
| Fri 28 Aug | Midpoint presentation to Nebo leadership | Whole team |
| Fri 25 Sep | Final presentation to Nebo leadership | Whole team |
| Late Sep | Final assessment compiled, report sent to UDSM | Kelvin |

Being assessed on shipped work, collaboration, growth, communication, and
professionalism, roughly evenly weighted, isn't a secret — knowing that from
Week 1 is more useful to you than finding out at the end. Your logbook and
your merged PRs are the actual evidence behind that assessment and behind
what goes into your university report — keep both honest and current, not
tidied up after the fact.

## What "usable at the end of 8 weeks" concretely means

By 25 September: a deployed Telegram bot, answering real vetted-source-
grounded Swahili questions, with disclaimers and emergency redirection
working, an evaluation report showing how well it performs, a source
register Nebo can audit, documentation good enough that someone new could
pick this up, and a written list of known limitations and recommended next
steps. That's the bar — not "we learned things," though you will, and not
"there's a lot of code," but a product you built that Nebo can actually point
to and use.
