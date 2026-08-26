# Collaboration — staying autonomous without going in four directions

The goal is for the team to run itself day-to-day with minimal outside
intervention. That only works if a few seams are agreed on explicitly — without
them, "autonomous" turns into stray branches, two people solving the same
problem differently, and modules that stop fitting together. This document is
that agreement.

## 1. Define the interface before you build against it

Before writing code that depends on another track's output, agree on the
**shape** of that dependency first — in writing, in a PR to `docs/DECISIONS.md`
or as a comment on the relevant module's README — not by guessing or copying
whatever the other person happened to build first.

Concretely, these interfaces need to be agreed before both sides build against
them:

- The `POST /chat` request/response shape (bot ↔ api)
- The chunk record shape written to the vector store (knowledge → storage → rag)
- The structure of a logged safety event (safety → storage)
- Config variable names anyone else's code reads (`backend/config`)

Once agreed, changing an interface is a normal PR like any other — but it goes
through the **integration owner for that week** (see `docs/TEAM.md`) and pings
whoever else's code depends on it, before merge, not after something breaks.

## 2. One task board, no side channels

All work is tracked in one place (GitHub Projects / Issues on this repo) —
not in someone's private notes, not in a WhatsApp thread that only some people
saw. If a task isn't on the board, it isn't planned work; if you're not sure
what to pick up next, the board is where you look, not a teammate's memory.

## 3. Branch, PR, one review, merge — every time

No direct commits to `main` (this is enforced by a branch-protection rule on
GitHub, not just a promise). Every change is:

```
git checkout -b <track>/<short-description>
# ... work, commit ...
git push -u origin <track>/<short-description>
# open a PR, fill the template, request review from that track's reviewer
```

A PR needs one approving review from a teammate before merge — see the
Definition of Done in `CONTRIBUTING.md`. This is what actually prevents
duplicated or conflicting work: nothing lands in `main` that someone else on
the team hasn't seen.

## 4. Mid-week technical sync (15–20 min, peer-run, not Kelvin's meeting)

Run by that week's integration owner, Wednesday, four questions:

1. What did each of us merge into `main` since Monday?
2. Is anyone about to build against an interface that might change?
3. Any two people about to touch the same file/module?
4. Anything blocking that hasn't shown up in check-in yet?

This is separate from Kelvin's daily check-in/check-out — that one is for
visibility, unblocking, and staying aligned as a program; this one is
peer-to-peer technical coordination. Both matter; they're not redundant.

## 5. Decisions get written down once

Any decision that affects more than one track — chunk size, which embedding
model, the bot's error-message wording, how retries work — gets a short entry
in `docs/DECISIONS.md` when it's made. The rule: if you find yourself
re-explaining a decision out loud for the second time, it should have already
been in that file the first time.

## 6. When something's actually stuck

Check-in/check-out blockers get addressed same-day by whoever can unblock it
— usually a teammate, not automatically a lead. Beyond that, escalate to the
right lead, not whichever is more convenient:

- **Kelvin Byabato (Program Lead)** — schedule, admin, scope decisions, or
  anything blocked more than a day with no clear owner.
- **Abdillah Issa (Technical Lead)** — architecture or design questions
  genuinely beyond the team's judgment, and anything touching
  `modules/safety` that needs sign-off beyond a peer review.
