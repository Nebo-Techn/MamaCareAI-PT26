"""
Tests for the store, review, and publish stages — plus the end-to-end gate.

**Owner: Dev C** (see the Sprint 1 split in `docs/PIPELINE_BACKLOG.md`), except
`test_full_pipeline_walks_submitted_to_published`, which is **Dev A's**
PIPE-13 and the Sprint 1 exit gate.

That one test is the single integration point of the sprint. It is the only
place four people's work meets, and it is deliberately at the end rather than
spread through the week.

The stage template-method tests are not repeated here — they live once in
`test_stages_ingest_extract.py`.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (Dev C): implement these. Every one uses build_test_container().
#
# === store stage ===
#
# def test_indexes_content_and_opens_one_review_assignment():
#     Exactly one assignment — a duplicate means two reviewers do the same work.
#
# def test_already_swahili_path_still_indexes():
#     No machine version exists on this path, so the stage must index the
#     extracted document instead. Easy to miss, and when it is missed
#     Swahili-native sources silently never become searchable while everything
#     else looks fine.
#
# === review stage ===
#
# def test_stored_moves_to_in_review_and_stops():
#     next_stage is None — the pipeline PARKS here, on purpose, and waits for a
#     human. Assert no further job was published.
#
# === publish stage ===
#
# def test_compliance_failure_blocks_publication():
#     -> BLOCKED_LICENSING, nothing written to the search index.
#
# def test_publishes_the_latest_version_not_version_one():
#     After a human edit, publishing version 1 would silently discard every
#     correction the reviewer made. This is the worst bug this stage can have —
#     guard it here.
#
# def test_publication_writes_an_audit_event_naming_the_approver():
#     Publication is the governance-critical moment; "who approved this?" must
#     always have an answer.
#
# ---------------------------------------------------------------------------
# TODO (Dev A) — PIPE-13, the Sprint 1 exit gate. Do not start before the
# other three stage files are green.
#
# def test_full_pipeline_walks_submitted_to_published():
#     Using build_test_container() and fakes only — no network, no models, no
#     database. Submit one resource, run every stage in order, and assert it
#     lands in PUBLISHED with:
#       - a machine version and a human version stored
#       - an audit trail that reconstructs the full lifecycle in order
#       - nothing in the dead-letter queue
#
#     When this passes, Sprint 1 is done.
# ---------------------------------------------------------------------------
