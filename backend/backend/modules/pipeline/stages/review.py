"""
Stage 6: Human review & edit (PDF 3.6).

    translated -> in_review -> (approved | needs_edit) -> edited -> approved -> published

"This is a workflow state machine, not just a UI." That sentence from the
design doc is the whole design of this stage.

WHERE THE LOGIC LIVES — READ THIS BEFORE WRITING CODE
This stage class does ONE small thing: move a stored resource into IN_REVIEW so
it appears in the queue. Everything a human then does — claim, edit, approve,
request changes — is NOT a queue job, because it is driven by a person clicking
in a UI, not by a worker polling a topic. That logic lives in
`services/review_service.py` and is exposed over HTTP in `api/routes_review.py`.

Do not put reviewer actions in this file. A stage runs on a worker; a reviewer
action runs inside an HTTP request. Mixing the two is how you end up with a
review UI that cannot be tested without a running queue.
"""

from __future__ import annotations

from ..domain.enums import ResourceStatus
from ..domain.models import Resource
from .base import Stage, StageResult


class ReviewStage(Stage):
    """Moves stored content into the human review queue, then hands off to people."""

    @property
    def name(self) -> str:
        return "review"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset({ResourceStatus.STORED})

    def handle(self, resource: Resource) -> StageResult:
        """Park the resource in IN_REVIEW and stop.

        `next_stage=None` is the whole point: no worker advances this resource.
        It waits for a human. The next transition comes from
        `ReviewService.submit_decision()` when a reviewer acts.

        WATCH FOR: a resource sitting in IN_REVIEW forever is invisible unless
        you measure it. `observability/metrics.py` must track the age of the
        oldest item in the review queue and alert on it. Content stuck in
        review is content that never reaches a user — the pipeline looks
        perfectly healthy while delivering nothing.
        """
        return StageResult(
            next_status=ResourceStatus.IN_REVIEW,
            next_stage=None,
        )
