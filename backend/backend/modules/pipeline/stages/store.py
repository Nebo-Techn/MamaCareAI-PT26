"""
Stage 5: Storage (PDF 3.5).

Three distinct concerns, deliberately kept separate rather than collapsed into
one table:

  - Object storage  -> raw files (already written during ingestion)
  - Relational DB   -> structured state, versions, review assignments
  - Search index    -> full-text search over the translated Swahili text

WHY NOT ONE TABLE
They have genuinely different shapes, sizes, and access patterns: blobs are
huge and immutable, state is small and updated constantly, the index is a
rebuildable read model. Collapsing them means every query fights the wrong
storage engine, and the "just one more column" table becomes unqueryable
within a year.

WHAT THIS STAGE ACTUALLY DOES
By the time we get here the content is already persisted. This stage's job is
to make it FINDABLE and to open a review task — it is the handoff from machine
processing to human judgement.
"""

from __future__ import annotations

from ..domain.enums import ResourceStatus
from ..domain.models import Resource
from ..ports.job_queue import JobQueue
from ..ports.repositories import (
    DocumentRepository,
    ResourceRepository,
    ReviewRepository,
    VersionRepository,
)
from ..ports.search_index import IndexedResource, SearchIndex
from .base import Stage, StageResult


class StoreStage(Stage):
    """Indexes translated content and opens a human review task."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        documents: DocumentRepository,
        versions: VersionRepository,
        search: SearchIndex,
        review_service: object,  # TODO: type as services.review_service.ReviewService
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        self._documents = documents
        self._versions = versions
        self._search = search
        self._review_service = review_service

    @property
    def name(self) -> str:
        return "store"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        # TRANSLATED = normal path. LANGUAGE_DETECTED = the already-Swahili
        # shortcut from stage 3, which has no machine translation to index.
        return frozenset({ResourceStatus.TRANSLATED, ResourceStatus.LANGUAGE_DETECTED})

    def handle(self, resource: Resource) -> StageResult:
        """Index the content and create the review assignment.

        Two paths, both must index:
          - the resource has a machine translation (normal path): index the
            latest version's translated text;
          - it is already-Swahili (skipped translation): index the extracted
            document directly. Forgetting this case silently makes
            Swahili-native sources unsearchable while everything else works.
        """
        version = self._versions.get_latest(resource.resource_id)
        if version is not None:
            translated_text = self._units_to_text(version.units)
            version_number = version.version_number
            title = resource.source_metadata.get("title")
        else:
            document = self._documents.get_document(resource.resource_id)
            translated_text = "\n\n".join(block.text for block in document.blocks)
            version_number = 0
            title = document.title

        self._search.index(
            IndexedResource(
                resource_id=resource.resource_id,
                title=title,
                translated_text=translated_text,
                source_url=resource.source_url,
                status=ResourceStatus.STORED.value,
                version_number=version_number,
                metadata={"language": resource.detected_language or ""},
            )
        )

        self._review_service.enqueue_for_review(resource, version)

        return StageResult(
            next_status=ResourceStatus.STORED,
            next_stage="review",
        )

    @staticmethod
    def _units_to_text(units) -> str:
        """Flatten translation units into the searchable plain-text projection."""
        return "\n\n".join(unit.translated_text for unit in units)
