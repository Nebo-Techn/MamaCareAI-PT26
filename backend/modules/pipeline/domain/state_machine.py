"""
The resource lifecycle state machine (PDF 3.6).

    translated -> in_review -> (approved | needs_edit) -> edited -> approved -> published

This file is the ONE place that knows which state transitions are legal. Every
stage and the review service ask it for permission before changing a status.

WHY CENTRALIZE THIS
Scattering `if status == "translated"` checks across seven stages means the
rules exist in seven places and drift apart within a month. Here, the rules are
data (`ALLOWED_TRANSITIONS`), they are readable in one screen, and they are
testable without touching a database or a queue.

This is also our concurrency guard. Two workers picking up the same resource
is normal in a distributed pipeline; the second one to arrive hits an illegal
transition and fails loudly instead of silently double-processing.

TODO (junior dev):
  [ ] Fill in ALLOWED_TRANSITIONS completely, then implement the two functions.
  [ ] Write `tests/pipeline/test_state_machine.py` FIRST — it needs no mocks and
      it is the cheapest high-value test in the whole repo. Cover at minimum:
        - the full happy path submitted -> published
        - needs_edit -> edited -> approved (the review loop)
        - that approved -> in_review is REJECTED (no silent un-approving)
        - that every terminal state has no outgoing transitions
"""

from __future__ import annotations

from .enums import ResourceStatus
from .errors import InvalidStateTransition

S = ResourceStatus

# Map of: current status -> the set of statuses reachable from it.
#
# Read this as the specification of the pipeline. If a transition is not listed
# here, it cannot happen. Adding an arrow is a design decision that belongs in
# a PR review, not something a stage decides at runtime.
ALLOWED_TRANSITIONS: dict[ResourceStatus, frozenset[ResourceStatus]] = {
    # --- ingestion ---
    S.SUBMITTED: frozenset({S.FETCHED, S.DUPLICATE, S.FAILED}),
    S.FETCHED: frozenset({S.EXTRACTED, S.FAILED}),
    # --- extraction & normalization ---
    S.EXTRACTED: frozenset(
        {S.LANGUAGE_DETECTED, S.NEEDS_LANGUAGE_CONFIRMATION, S.FAILED}
    ),
    # --- language detection ---
    # A human confirming the language sends it back to LANGUAGE_DETECTED.
    S.NEEDS_LANGUAGE_CONFIRMATION: frozenset({S.LANGUAGE_DETECTED, S.FAILED}),
    # Already-Swahili content skips translation entirely (PDF 3.4) and goes
    # straight to STORED — that is why both arrows exist here.
    S.LANGUAGE_DETECTED: frozenset({S.TRANSLATED, S.STORED, S.FAILED}),
    # --- translation & storage ---
    S.TRANSLATED: frozenset({S.STORED, S.FAILED}),
    S.STORED: frozenset({S.IN_REVIEW, S.FAILED}),
    # --- human review loop ---
    S.IN_REVIEW: frozenset({S.APPROVED, S.NEEDS_EDIT, S.FAILED}),
    S.NEEDS_EDIT: frozenset({S.EDITED, S.FAILED}),
    S.EDITED: frozenset({S.APPROVED, S.NEEDS_EDIT, S.FAILED}),
    # --- publication ---
    # The compliance gate runs on the approved -> published edge, which is why
    # BLOCKED_LICENSING is reachable only from here (PDF section 4: gate before
    # publication, not before translation).
    S.APPROVED: frozenset({S.PUBLISHED, S.BLOCKED_LICENSING}),
    # --- terminal states: no way out ---
    S.PUBLISHED: frozenset(),
    S.DUPLICATE: frozenset(),
    S.BLOCKED_LICENSING: frozenset(),
    # FAILED is terminal for the automatic pipeline. Re-driving a dead-lettered
    # resource is a deliberate operator action that creates a NEW resource_id,
    # so the failed attempt stays in the record instead of being erased.
    S.FAILED: frozenset(),
}

# States a human must act on before the resource moves again. Used by the
# review dashboard and by the "stuck work" alert in observability/metrics.py.
HUMAN_ACTION_REQUIRED: frozenset[ResourceStatus] = frozenset(
    {S.NEEDS_LANGUAGE_CONFIRMATION, S.IN_REVIEW, S.NEEDS_EDIT}
)

TERMINAL_STATES: frozenset[ResourceStatus] = frozenset(
    {S.PUBLISHED, S.DUPLICATE, S.BLOCKED_LICENSING, S.FAILED}
)


def can_transition(current: ResourceStatus, target: ResourceStatus) -> bool:
    """Return True if `current -> target` is a legal move.

    TODO: look `current` up in ALLOWED_TRANSITIONS and test membership.
    Treat an unknown `current` as "no transitions allowed" rather than raising —
    callers use this for questions, and `assert_can_transition` for enforcement.
    """
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def assert_can_transition(current: ResourceStatus, target: ResourceStatus) -> None:
    """Raise `InvalidStateTransition` unless `current -> target` is legal.

    Call this at the top of every status change. It is two lines of code that
    turn a whole class of concurrency bug into a loud, traceable error.

    TODO: raise with a message naming BOTH states and the legal alternatives —
    "cannot go approved -> in_review (allowed: published, blocked_licensing)"
    is a message an on-call engineer can act on at 2am. "invalid transition" is not.
    """
    if can_transition(current, target):
        return

    allowed = ", ".join(status.value for status in sorted(ALLOWED_TRANSITIONS.get(current, frozenset()), key=lambda s: s.value))
    raise InvalidStateTransition(
        f"Cannot transition {current.value} -> {target.value} "
        f"(allowed: {allowed or 'none'})"
    )
