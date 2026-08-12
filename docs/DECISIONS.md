# Decisions

A running log of decisions that affect more than one track — so nobody has to
remember them verbally, and nobody quietly re-decides them differently later.
Add a new entry (don't edit old ones — if a decision changes, add a new entry
that supersedes the old one and says so).

Keep each entry short: what was decided, why, and who it affects. This is a
log, not a design document — the reasoning belongs here in a sentence or two,
not a full write-up.

## Format

```
## DEC-0001 — <short title>
Date: YYYY-MM-DD · Decided by: <names> · Affects: <tracks/modules>

**Decision:** <one or two sentences>
**Why:** <one or two sentences>
**Supersedes:** <DEC-xxxx, if any>
```

## Log

## DEC-0000 — Telegram over WhatsApp for the 8-week build
Date: 2026-08-12 · Decided by: Program lead · Affects: bot, api

**Decision:** The bot ships on Telegram for the 8-week build; WhatsApp is
documented as the post-handover next step.
**Why:** WhatsApp Business API requires Meta business verification — an
approval delay outside the team's control, a bad risk against a fixed 8-week
window. Telegram is free, has no approval gate, and is a real chat channel.
**Supersedes:** —

*(Next entries start at DEC-0001, made by the team as real decisions come up.)*
