"""
Tests for the resource lifecycle state machine.

START HERE. WRITE THESE FIRST.
This is the highest value-per-minute test file in the whole pipeline: pure
functions over data, no I/O, no fixtures, no mocks, runs in milliseconds. It
also pins down the workflow specification from PDF 3.6, so a later change that
breaks the lifecycle fails here rather than in production.

If a trainee is new to testing, this is the file to learn on.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TODO (junior dev): implement these tests.
#
# def test_happy_path_is_fully_connected():
#     Walk SUBMITTED -> FETCHED -> EXTRACTED -> LANGUAGE_DETECTED ->
#     TRANSLATED -> STORED -> IN_REVIEW -> APPROVED -> PUBLISHED, asserting
#     can_transition() at every step. If someone breaks the chain, this fails.
#
# def test_already_swahili_skips_translation():
#     LANGUAGE_DETECTED -> STORED must be allowed (PDF 3.4, first bullet).
#
# def test_review_loop():
#     IN_REVIEW -> NEEDS_EDIT -> EDITED -> APPROVED all allowed.
#     Also EDITED -> NEEDS_EDIT (a second round of changes is normal).
#
# def test_cannot_unapprove():
#     APPROVED -> IN_REVIEW must be REJECTED. Once approved, the only ways out
#     are PUBLISHED or BLOCKED_LICENSING. This protects the governance claim
#     that approval is a real, recorded decision.
#
# def test_cannot_skip_review():
#     STORED -> PUBLISHED must be REJECTED. Nothing reaches users without a
#     human. This is the single most important assertion in the file — it is
#     the executable form of the project's core safety promise.
#
# def test_terminal_states_have_no_exits():
#     For each of PUBLISHED, DUPLICATE, BLOCKED_LICENSING, FAILED:
#     ALLOWED_TRANSITIONS[state] is empty.
#
# def test_every_status_appears_in_the_map():
#     for status in ResourceStatus: assert status in ALLOWED_TRANSITIONS
#     Catches the classic bug: someone adds an enum value, forgets the
#     transitions, and the pipeline mysteriously refuses to enter that state.
#
# def test_every_target_is_a_real_status():
#     Every value in every transition set is a member of ResourceStatus.
#
# def test_assert_can_transition_raises_with_a_useful_message():
#     Assert InvalidStateTransition is raised AND that the message names both
#     states. A test that only checks the exception type lets someone ship
#     "invalid transition" as the entire message, which helps nobody at 2am.
#
# def test_all_states_reachable_from_submitted():
#     Graph traversal from SUBMITTED. Every non-terminal status should be
#     reachable. An unreachable state is dead code or a missing arrow.
# ---------------------------------------------------------------------------
