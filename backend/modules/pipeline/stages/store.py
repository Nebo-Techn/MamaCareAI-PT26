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
from ..ports.search_index import SearchIndex
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

        TODO (junior dev) — implement in this order:

          1. RESOLVE THE TEXT TO INDEX:
                 version = self._versions.get_latest(resource.resource_id)
                 if version is None:
                     # already-Swahili path: no MT version exists, so index the
                     # extracted document text directly
                     document = self._documents.get_document(resource.resource_id)
             Handle BOTH paths. Forgetting the already-Swahili case means
             Swahili-native sources silently never become searchable — a bug
             that hides for weeks because everything else looks fine.

          2. INDEX IT:
                 self._search.index(IndexedResource(
                     resource_id=..., title=..., translated_text=...,
                     source_url=resource.source_url, status=...,
                     version_number=version.version_number if version else 0,
                     metadata={"language": resource.detected_language, ...}))
             Upsert by resource_id so re-indexing replaces rather than duplicates.

          3. OPEN THE REVIEW TASK:
                 self._review_service.enqueue_for_review(resource, version)
             Priority comes from the translation confidence signal — see
             `services/review_service.py`. Low-confidence translations should
             reach a human first.

          4. RETURN:
                 StageResult(next_status=ResourceStatus.STORED,
                             next_stage="review")
             The "review" job is a workflow marker: it moves STORED -> IN_REVIEW
             and then waits. Humans, not workers, drive it from there.

        FAILURE MODE TO GET RIGHT: the search index is a DERIVED read model. If
        indexing fails, the content is still safe in Postgres and object
        storage — this stage retries, and nothing is lost. Never write to the
        index as if it were the source of truth, and make sure the
        `reindex` management command can rebuild it from scratch. Test that
        command before you need it in an incident.
        """
        raise NotImplementedError
