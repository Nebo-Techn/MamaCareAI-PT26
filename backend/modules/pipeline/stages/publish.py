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
from ..domain.errors import InvalidStateTransition
from ..domain.models import Resource
from ..ports.job_queue import JobQueue
from ..ports.repositories import ResourceRepository, ReviewRepository, VersionRepository
from ..ports.search_index import IndexedResource, SearchIndex
from ..services import ComplianceGate
from .base import Stage, StageResult


class KnowledgeHandoffError(Exception):
    """Raised when knowledge handoff fails."""


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
        compliance_gate: ComplianceGate,
        knowledge_handoff: object | None = None,  # TODO: type as knowledge.KnowledgeHandoff
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        self._versions = versions
        self._search = search
        self._compliance = compliance_gate
        self._knowledge_handoff = knowledge_handoff

    @property
    def name(self) -> str:
        return "publish"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset({ResourceStatus.APPROVED})

    def handle(self, resource: Resource) -> StageResult:
        """Check licensing, then publish the approved version.

        Order is non-negotiable: the compliance gate runs FIRST, before anything
        becomes visible. Then the LATEST version is published — that is the
        human-edited one when a reviewer edited it. Publishing version 1
        unconditionally would silently discard every human correction.
        """
        decision = self._compliance.evaluate(resource)
        if not decision.allowed:
            return StageResult(
                next_status=ResourceStatus.BLOCKED_LICENSING,
                next_stage=None,
                details={"reason": decision.reason},
            )

        version = self._versions.get_latest(resource.resource_id)
        if version is None:
            raise InvalidStateTransition(
                f"Resource {resource.resource_id} is APPROVED but has no "
                "content version to publish",
                resource_id=resource.resource_id,
            )

        translated_text = "\n\n".join(unit.translated_text for unit in version.units)
        self._search.index(
            IndexedResource(
                resource_id=resource.resource_id,
                title=resource.source_metadata.get("title"),
                translated_text=translated_text,
                source_url=resource.source_url,
                status=ResourceStatus.PUBLISHED.value,
                version_number=version.version_number,
                metadata={"language": resource.detected_language or ""},
            )
        )

        # Knowledge handoff (PIPE-32): Send to modules/knowledge for chunking and embedding
        if self._knowledge_handoff is not None:
            try:
                self._knowledge_handoff.handoff_published_content(
                    resource_id=resource.resource_id,
                    source_url=resource.source_url,
                    title=resource.source_metadata.get("title"),
                    translated_text=translated_text,
                    version_number=version.version_number,
                    language=resource.detected_language or "",
                    metadata=resource.source_metadata,
                )
            except Exception as e:
                # Log the error but don't fail the publish - search index is more critical
                # In production, this should be monitored and retried
                raise KnowledgeHandoffError(
                    f"Failed to handoff resource {resource.resource_id} to knowledge module: {e}"
                ) from e

        return StageResult(
            next_status=ResourceStatus.PUBLISHED,
            next_stage=None,
            details={
                "approved_version": version.version_number,
                "approved_by": resource.source_metadata.get("approved_by"),
                "knowledge_handoff": self._knowledge_handoff is not None,
            },
        )
