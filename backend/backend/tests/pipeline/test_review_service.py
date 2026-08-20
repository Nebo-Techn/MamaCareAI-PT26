"""
Tests for the human review workflow (PDF 3.6).

This file protects the promises the project makes about its content: that human
edits are never lost, that nothing is published without a person approving it,
and that every action is attributable. Those are governance claims — they need
executable evidence, not a paragraph in a README.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (junior dev): implement these tests.
#
# --- Versioning: the append-only guarantee ---
#
# def test_edit_creates_a_new_version_and_preserves_the_machine_output():
#     Submit an edit; assert version 2 exists AND version 1 is byte-identical
#     to what the machine produced.
#     THE CENTRAL TEST OF THIS FILE. Everything else — the audit trail, the
#     feedback loop, the ability to answer "what did the model actually say?" —
#     rests on version 1 surviving forever.
#
# def test_second_edit_creates_version_3():
#     Editing an edit keeps stacking versions, never overwrites.
#
# def test_concurrent_edits_do_not_collide_on_version_number():
#     Two edits, same resource. Both must be stored with DISTINCT version
#     numbers. Losing a reviewer's work is unacceptable.
#
# --- Queue mechanics ---
#
# def test_claim_next_returns_highest_priority_first():
#     Low-confidence translations reach a human first (the quality signal from
#     PDF 3.4 finally doing something useful).
#
# def test_two_reviewers_never_claim_the_same_assignment():
#     Simulate concurrent claims; assert they get different items or one gets
#     None. Duplicated review work wastes the scarcest resource in the system.
#
# def test_claim_next_on_an_empty_queue_returns_none():
#     Normal state, not an error.
#
# --- Decisions ---
#
# def test_approve_transitions_to_approved_and_queues_publication():
#
# def test_needs_edit_keeps_the_assignment_open():
#
# def test_reject_records_the_reason():
#     A rejection with no reason is a mystery forever.
#
# def test_reviewer_cannot_complete_someone_elses_assignment():
#     403-equivalent at the service layer, not just in the route.
#
# --- Governance ---
#
# def test_every_action_writes_an_audit_event():
#     Claim, edit, approve — each appends exactly one event with the right
#     actor_id. Table-drive this so a new action cannot be added without one.
#
# def test_audit_trail_is_ordered_and_complete():
#     Full lifecycle, then assert the audit reconstructs it in order. This is
#     the test behind the claim "we can always say who changed what and when".
#
# --- Side-by-side payload ---
#
# def test_payload_aligns_source_and_translation_by_order():
#     Blocks and units must line up. Misalignment makes review actively
#     misleading — a reviewer approves a translation of a different paragraph.
#
# def test_payload_includes_the_machine_version_after_a_human_edit():
#     So the UI can diff human against machine.
# ---------------------------------------------------------------------------
