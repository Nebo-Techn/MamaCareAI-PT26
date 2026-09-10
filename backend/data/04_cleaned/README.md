# Cleaned

Approved Swahili text — published by the publish stage of
`backend/modules/pipeline` after a human has reviewed it.

Everything here has been through the full review workflow: machine-translated,
read by a named reviewer, edited if needed, and explicitly approved. The
version history (machine output vs. human edit) and the audit trail of who
approved what live in the pipeline's database, not in these files.

This is the boundary between "collected content" and "content the bot is
allowed to say." `backend/modules/knowledge` reads from here to chunk and
embed.

**Owner track:** Data & Knowledge
**Sprint:** 2

## What changed

This stage used to be a manual spot-check — "the last stage a human should
visually sanity-check." That is now a formal review workflow with assignment,
versioning, and an audit trail (`modules/pipeline/services/review_service.py`).

The intent is unchanged and the guarantee is stronger: a human still reads this
content before it becomes machine-searchable knowledge, but now there is a
record of who, when, and what they changed.

See `DEC-0002` in `docs/DECISIONS.md`.
