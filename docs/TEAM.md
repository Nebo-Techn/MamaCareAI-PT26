# Team

MamaCare AI is built by four people: **Elia, Walii, Jackson, Kornelly** — UDSM
AI-track trainees. It's your build. By Week 8 the goal is that each of you can
point at a real, working piece of it and say "I built that," not "I helped."

## Leadership

- **Abdillah Issa** — AI Lead. 
- **Kelvin Byabato** — PT26 Program Lead. 


Teamwork: Day-to-day, most decisions are yours to make as a team — see
`docs/COLLABORATION.md` for how. Kelvin and Abdillah are there for the important guides and decisions.

## How tracks get assigned — Day 2 of Week 1, by the team, not for them

Track ownership is decided by the four of you, in your first working session, using
a short skills self-assessment: everyone rates their own comfort (1–5) with Python,
git/GitHub, HTTP APIs, and general NLP/ML concepts. Use that, plus what each of you
finds most interesting, to divide the four tracks in `docs/ARCHITECTURE.md` among
yourselves. Two rules on how you do it:

1. **Every track gets a named owner** — accountable for it existing and working,
   not for doing 100% of the work in it alone.
2. **Every track gets a second reviewer** — a teammate (not the owner) who reviews
   every PR into that track. Pick this pairing deliberately in the same session, not
   ad hoc later — this is what makes review fast instead of "whoever's free."

Write the result down as the first entry in this file (edit this section, open a PR,
get it merged) — that PR is also the first real exercise in the git workflow
everyone will use for the next 8 weeks.

*[Track assignments and reviewer pairs go here once decided in Week 1.]*

## Rotating integration owner

Each week, Team Lead (or rotate if it fits) holds the **integration
owner** role for that week:

- Owns keeping `main` in a working, demoable state
- Is the person others check with before changing something another track depends
  on (an API response shape, a data schema, a function signature)
- Flags to the team - same day - if two people's work is about to conflict or
  duplicate
- Runs the mid-week technical sync (see `docs/COLLABORATION.md`)

Rotate it every Monday, in order: Elia → Walii → Jackson → Kornelly → repeat. Nobody
is "the lead" for the whole 8 weeks - everyone gets the rep, and no single person
becomes a bottleneck or a single point of failure. 

(This is a peer role, distinct
from Kelvin and Abdillah above — it's about keeping your own code integrated, not
about program management or technical sign-off.)

## Why this exists

Four autonomous people building interdependent pieces (bot → API → RAG → safety →
knowledge base) without a shared way to divide work and keep the seams aligned is how
you get stray branches, duplicated effort, and modules that silently stop fitting
together. This file — plus `docs/COLLABORATION.md` and `docs/DECISIONS.md` — is the
lightweight structure that lets you stay autonomous *and* stay integrated. Read all
three before Sprint 1 planning.
