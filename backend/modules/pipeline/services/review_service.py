"""
Review workflow service (PDF 3.6) — the human side of the pipeline.

Everything a reviewer does goes through this class: claim work, submit an edit,
approve, request changes. The API layer (`api/routes_review.py`) is a thin
translation from HTTP to these methods and does nothing else — put workflow
rules in here, not in a route handler, or they become impossible to test and
impossible to reuse from a CLI or a batch job.

THE THREE RULES THIS SERVICE ENFORCES
  1. A human edit creates a NEW VERSION. It never overwrites the machine
     translation. Both stay readable forever.
  2. Every action writes an audit event. Governance is not optional — this
     content is treated as authoritative once published.
  3. Every transition is validated against `domain/state_machine.py`. There is
     no back door into a state.

FOR MAMACARE AI: the reviewer is the last line of defence before Swahili
maternal-health content reaches real pregnant people. This file is worth
reviewing line by line before each presentation, alongside `modules/safety`.
"""

from __future__ import annotations

from ..domain.enums import ReviewDecision
from ..domain.models import ContentVersion, Resource, ReviewAssignment, TranslationUnit
from ..ports.job_queue import JobQueue
from ..ports.repositories import (
    DocumentRepository,
    ResourceRepository,
    ReviewRepository,
    VersionRepository,
)


class ReviewService:
    """Drives the review state machine in response to human actions."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        reviews: ReviewRepository,
        versions: VersionRepository,
        documents: DocumentRepository,
        queue: JobQueue,
    ) -> None:
        self._resources = resources
        self._reviews = reviews
        self._versions = versions
        self._documents = documents
        self._queue = queue

    # --- Queue management ----------------------------------------------------

    def enqueue_for_review(
        self, resource: Resource, version: ContentVersion | None
    ) -> ReviewAssignment:
        """Create the review task for a stored resource. Called by `stages/store.py`.

        TODO (junior dev):
          [ ] Build a ReviewAssignment with reviewer_id=None (unclaimed).
          [ ] Compute PRIORITY — this is the "quality signal" from PDF 3.4
              finally being used for something:
                  - lowest mean translation confidence first (most likely wrong)
                  - then oldest first (nothing starves in the queue)
              Put the formula in one small helper so it is testable and tunable.
          [ ] Be idempotent: if an open assignment already exists for this
              resource, return it instead of creating a second one. Duplicate
              assignments mean two reviewers do the same work.
        """
        raise NotImplementedError

    def claim_next(self, reviewer_id: str) -> ReviewAssignment | None:
        """Give a reviewer their next piece of work.

        TODO: delegate to `reviews.claim_next()` — the ATOMIC one. Do not
        implement "find unclaimed, then update" here; that race hands the same
        document to two reviewers, and reviewer time is the scarcest resource
        in this whole system.

        Then transition STORED -> IN_REVIEW if it has not happened yet.
        """
        raise NotImplementedError

    def get_review_payload(self, resource_id: str) -> dict[str, object]:
        """Everything the side-by-side review UI needs, in one call.

        TODO: return
              - source blocks (from documents.get_document) — the LEFT pane
              - latest version units — the RIGHT pane, aligned by `order`
              - the machine version, when the latest is a human edit, so the UI
                can show what changed
              - version history metadata (who, when, which engine)

        Aligning by `order` here rather than in JavaScript keeps the alignment
        rule in one tested place instead of duplicated in the frontend.
        """
        raise NotImplementedError

    # --- Reviewer actions ----------------------------------------------------

    def submit_edit(
        self,
        *,
        assignment_id: str,
        reviewer_id: str,
        edited_units: list[TranslationUnit],
        note: str | None = None,
    ) -> ContentVersion:
        """Save a reviewer's corrections as a NEW version.

        TODO (junior dev) — the most important method in this file:
          [ ] Load the resource; assert the reviewer owns this assignment.
              (Anyone can edit anything = no audit trail worth the name.)
          [ ] assert_can_transition(current, ResourceStatus.EDITED)
          [ ] Create ContentVersion(author_kind=HUMAN, author_id=reviewer_id,
              version_number=<assigned by the repository>, note=note).
              INSERT — never update version 1. If you find yourself writing an
              UPDATE here, stop and re-read `ports/repositories.py`.
          [ ] Save, transition to EDITED, append the audit event.
          [ ] Re-index the edited text so search reflects the human version.
          [ ] Compute and store the DIFF against the machine version — see
              `feedback_export.py`. This is the training signal that makes
              review effort compound instead of repeating forever (PDF 3.6).
        """
        raise NotImplementedError

    def submit_decision(
        self,
        *,
        assignment_id: str,
        reviewer_id: str,
        decision: ReviewDecision,
        note: str | None = None,
    ) -> None:
        """Record approve / needs_edit / reject and move the workflow forward.

        TODO — map decisions to transitions, validating each one:

            APPROVE     -> ResourceStatus.APPROVED, then publish the "publish"
                           job on the queue. This is where the workflow rejoins
                           the automated pipeline.
            NEEDS_EDIT  -> ResourceStatus.NEEDS_EDIT, assignment stays open.
            REJECT      -> ResourceStatus.FAILED with the reason recorded.
                           Rejection must be explainable later; a rejected
                           resource with no reason is a mystery forever.

        [ ] Every branch writes an audit event with reviewer_id and the note.
        [ ] Approval is the governance-critical action — it is the moment this
            content becomes authoritative. Never allow it without a reviewer_id.
        [ ] TODO (roles/permissions): only users with the reviewer role may
            approve. Add the check here, in the service — not in the UI. A UI
            check is a suggestion; a service check is a rule.
        """
        raise NotImplementedError
