"""
Stage 7: Published output (PDF 3.7) + the compliance gate (PDF section 4).

Approved, versioned Swahili content becomes searchable and available to
downstream consumers.

THE COMPLIANCE GATE IS PART OF THIS STAGE, NOT AN EARLIER ONE.
The design doc is explicit: "add a licensing/compliance gate before
publication, not only before translation." Reason: publication is the act with
legal consequence. Translating something we may not republish costs us a few
cents; publishing it is the actual problem. So the last thing that happens
before content goes live is a licensing check.

FOR MAMACARE AI SPECIFICALLY: published output is the input to
`backend/modules/knowledge` (chunking + embedding into the vector store). This
stage is the seam between "vetted content" and "what the bot is allowed to say"
— which makes it the enforcement point for ARCHITECTURE.md non-negotiable #4:
every source in the knowledge base is traceable to a vetted register entry.
"""

from __future__ import annotations

from ..domain.enums import ResourceStatus
from ..domain.models import Resource
from ..ports.job_queue import JobQueue
from ..ports.repositories import ResourceRepository, ReviewRepository, VersionRepository
from ..ports.search_index import SearchIndex
from .base import Stage, StageResult


class PublishStage(Stage):
    """Runs the compliance gate, then publishes approved content."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        versions: VersionRepository,
        search: SearchIndex,
        compliance_gate: object,  # TODO: type as services.compliance.ComplianceGate
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        self._versions = versions
        self._search = search
        self._compliance = compliance_gate

    @property
    def name(self) -> str:
        return "publish"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset({ResourceStatus.APPROVED})

    def handle(self, resource: Resource) -> StageResult:
        """Check licensing, then publish the approved version.

        TODO (junior dev) — implement in this order:

          1. COMPLIANCE GATE FIRST, before anything becomes visible:
                 decision = self._compliance.evaluate(resource)
                 if not decision.allowed:
                     return StageResult(
                         next_status=ResourceStatus.BLOCKED_LICENSING,
                         next_stage=None,
                         details={"reason": decision.reason})
             Terminal. Do not publish and clean up later — "we will unpublish it
             if someone complains" is not a compliance strategy.

          2. RESOLVE THE VERSION TO PUBLISH:
                 version = self._versions.get_latest(resource.resource_id)
             ALWAYS the latest — that is the human-edited one when a reviewer
             edited it, and the machine one when they approved it as-is.
             Publishing version 1 unconditionally would silently discard every
             human correction, which is the single worst bug this stage can
             have. Guard it with a test.

          3. UPDATE THE INDEX to the published state:
                 self._search.index(IndexedResource(..., status="published",
                                                    version_number=version.version_number))

          4. AUDIT — publication is the event that matters most for governance:
             record who approved it, which version, and when. The base class
             writes the transition event; add publication specifics in `details`.

          5. RETURN:
                 StageResult(next_status=ResourceStatus.PUBLISHED, next_stage=None)

        DOWNSTREAM HANDOFF (MamaCare-specific, do this once publication works):
        emit an event or enqueue a job that tells `modules/knowledge` new
        Swahili content is available for chunking and embedding. Keep it as a
        published event rather than a direct import — the pipeline should not
        depend on the RAG module, only announce to it. Log the decision in
        `docs/DECISIONS.md`.

        UNPUBLISHING: needed eventually (a source is retracted, a licence
        changes). Do NOT delete rows — add an UNPUBLISHED state and remove it
        from the index. The version history must survive; deleting evidence
        breaks the audit trail we promised.
        """
        raise NotImplementedError
