# Evaluation

The evaluation harness — how the team, Nebo, and the students themselves know
the bot actually works, not just "looks like it works in the demo I picked."

- `test_questions/` — a fixed, versioned set of real Swahili maternal/newborn
  health questions, including some deliberately out-of-scope or emergency
  ones, to test that `modules/safety` actually catches them. Grows over the
  8 weeks; never delete an old question, only add.
- `reports/` — dated output of running the harness: for each question, was
  the answer correct, grounded in a real source, safe, in natural Swahili,
  and did it cite its source?

This is what gets run before the Week 4 and Week 8 presentations — the
report in `reports/` is the evidence behind "it works," not a claim.

## Translation quality belongs here too

`modules/pipeline` produces a second quality number for the same audience:
**% of machine translations approved by a reviewer with no edit**, plus mean
edit distance per source language
(`modules/pipeline/services/feedback_export.py`).

Put that report in `reports/` alongside the bot evaluation. It comes free from
work the reviewers already did, and it is stronger evidence than any automatic
MT score — it is human judgement, counted. Same standard as the rest of this
folder: numbers, not adjectives.

**Owner track:** LLM/Conversation & Safety, with input from everyone (good
test questions come from people who understand the domain, not just the
code)
**Sprint:** 3 (first real harness), 4 (final evaluation run for handover)
