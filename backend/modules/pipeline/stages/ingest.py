"""
Stage 1: Ingestion (PDF 3.1).

Takes a submitted resource, fetches its raw bytes, dedups it, and lands the
original in object storage.

THE RULE FROM THE DESIGN DOC: every source type becomes a job on a queue, not
a synchronous call. Sites go down, videos run long, PDFs are large. Nothing in
this stage may block an HTTP request the user is waiting on — submission
returns immediately with a resource_id, and this stage runs on a worker.

MAMACARE-SPECIFIC RULE (docs/ARCHITECTURE.md non-negotiable #4):
Ingestion never starts from a URL that has not been vetted. Every resource
must already have a row in `data/01_source_register` with a vetting decision.
Enforce that in `submit()` — see `services/submission.py`.
"""

from __future__ import annotations

import hashlib

from backend.modules.pipeline.domain.enums import ResourceStatus
from backend.modules.pipeline.domain.errors import FetchError, UnsupportedSourceType
from backend.modules.pipeline.domain.models import Resource
from backend.modules.pipeline.ports.deduplicator import Deduplicator
from backend.modules.pipeline.ports.job_queue import JobQueue
from backend.modules.pipeline.ports.object_store import ObjectStore
from backend.modules.pipeline.ports.repositories import ResourceRepository, ReviewRepository
from backend.modules.pipeline.registry import FetcherRegistry
from .base import Stage, StageResult


def build_raw_key(resource: Resource) -> str:
    """Build object storage key for raw content."""
    return f"raw/{resource.resource_id}/{resource.source_type.value}"

class IngestStage(Stage):
    """Fetches raw content and stores it, or marks the resource a duplicate."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        fetchers: FetcherRegistry,
        object_store: ObjectStore,
        deduplicator: Deduplicator,
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        # NOTE: a REGISTRY, not three fetchers. This stage must not know that
        # video or PDF fetchers exist — adding a source type must not edit this file.
        self._fetchers = fetchers
        self._object_store = object_store
        self._dedup = deduplicator

    @property
    def name(self) -> str:
        return "ingest"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset({ResourceStatus.SUBMITTED})

    def handle(self, resource: Resource) -> StageResult:
        """Fetch, dedup, store.

        IMPLEMENTATION following the TODO order:

        1. URL-LEVEL DEDUP (before spending a download)
        2. PICK THE FETCHER by source type
        3. FETCH content
        4. CONTENT-LEVEL DEDUP
        5. STORE THE RAW BYTES
        6. RETURN StageResult with FETCHED status
        """
        # IDEMPOTENCY: if raw_object_key is already set and object exists, skip download
        if resource.raw_object_key and self._object_store.exists(resource.raw_object_key):
            # Already fetched, just move to extract
            return StageResult(
                next_status=ResourceStatus.FETCHED,
                next_stage="extract",
                details={"idempotent": True, "existing_key": resource.raw_object_key},
            )

        # 1. URL-LEVEL DEDUP (before spending a download)
        url_hash = self._dedup.compute_hash(source_url=resource.source_url, content=b"")
        if self._dedup.is_duplicate(url_hash):
            return StageResult(
                next_status=ResourceStatus.DUPLICATE,
                next_stage=None,  # Terminal
                details={"dedup_reason": "url_hash", "hash": url_hash},
            )

        # 2. PICK THE FETCHER by source type
        try:
            fetcher = self._fetchers.get(resource.source_type)
        except UnsupportedSourceType as exc:
            # Permanent error - no fetcher for this type
            raise FetchError(f"No fetcher registered for source type {resource.source_type}", resource_id=resource.resource_id)

        # 3. FETCH
        try:
            result = fetcher.fetch(resource.source_url)
        except FetchError as exc:
            # Transient failures - let base class retry
            raise
        except Exception as exc:
            # Other fetch errors - treat as fetch error
            raise FetchError(f"Fetch failed: {exc}", resource_id=resource.resource_id)

        # 4. CONTENT-LEVEL DEDUP (the same document at two URLs)
        content_hash = self._dedup.compute_hash(
            source_url=resource.source_url, content=result.content
        )
        if self._dedup.is_duplicate(content_hash):
            return StageResult(
                next_status=ResourceStatus.DUPLICATE,
                next_stage=None,  # Terminal
                details={"dedup_reason": "content_hash", "hash": content_hash},
            )

        # 5. STORE THE RAW BYTES — never put them in the database
        key = build_raw_key(resource)
        self._object_store.put(key, result.content, content_type=result.content_type)

        # 6. RETURN, carrying forward what we learned
        # Merge metadata, don't replace - keep submitter's metadata
        merged_metadata = {**resource.source_metadata, **result.metadata}

        # Handle existing captions for video
        if result.existing_captions:
            merged_metadata["existing_captions"] = result.existing_captions

        return StageResult(
            next_status=ResourceStatus.FETCHED,
            next_stage="extract",
            resource_changes={
                "raw_object_key": key,
                "content_hash": content_hash,
                "source_metadata": merged_metadata,
            },
            details={
                "bytes": len(result.content),
                "content_type": result.content_type,
                "content_hash": content_hash,
            },
        )
