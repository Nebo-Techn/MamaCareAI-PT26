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

from ..domain.enums import ResourceStatus
from ..domain.models import Resource
from ..ports.deduplicator import Deduplicator
from ..ports.job_queue import JobQueue
from ..ports.object_store import ObjectStore
from ..ports.repositories import ResourceRepository, ReviewRepository
from ..registry import FetcherRegistry
from .base import Stage, StageResult


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

        TODO (junior dev) — implement in this order:

          1. URL-LEVEL DEDUP (before spending a download):
                 url_hash = self._dedup.compute_hash(source_url=resource.source_url,
                                                     content=b"")
                 if self._dedup.is_duplicate(url_hash):
                     return StageResult(next_status=ResourceStatus.DUPLICATE,
                                        next_stage=None)
             Terminal, and cheap. This is the single biggest cost saver here.

          2. PICK THE FETCHER by source type:
                 fetcher = self._fetchers.get(resource.source_type)
             Raises UnsupportedSourceType (permanent) if none is registered.

          3. FETCH:
                 result = fetcher.fetch(resource.source_url)
             Transient failures raise FetchError; the base class retries with
             backoff. Do not catch and swallow them here.

          4. CONTENT-LEVEL DEDUP (the same document at two URLs):
                 content_hash = self._dedup.compute_hash(
                     source_url=resource.source_url, content=result.content)
                 if self._dedup.is_duplicate(content_hash):
                     -> DUPLICATE, terminal.

          5. STORE THE RAW BYTES — never put them in the database:
                 key = build_raw_key(resource)   # adapters/storage/keys.py
                 self._object_store.put(key, result.content,
                                        content_type=result.content_type)

          6. RETURN, carrying forward what we learned:
                 return StageResult(
                     next_status=ResourceStatus.FETCHED,
                     next_stage="extract",
                     resource_changes={
                         "raw_object_key": key,
                         "content_hash": content_hash,
                         # merge, don't replace: keep the submitter's metadata
                         "source_metadata": {**resource.source_metadata,
                                             **result.metadata},
                     },
                     details={"bytes": len(result.content),
                              "content_type": result.content_type},
                 )

        IDEMPOTENCY: if `raw_object_key` is already set and the object exists,
        skip the download and go straight to step 6. A redelivered job should
        not re-hit the source — that is both wasteful and rude to the publisher.

        VIDEO NOTE: if `result.existing_captions` is set, persist it in
        source_metadata. The extract stage checks for it and skips ASR
        entirely — the most expensive step in the whole pipeline, avoided by
        one metadata field.

        COMPLIANCE NOTE (PDF section 4): record any license/usage-restriction
        string the fetcher found into source_metadata NOW, while we have it.
        The compliance gate before publication reads it later; re-fetching a
        page months afterwards to find out whether we were allowed to use it
        is not a plan.
        """
        raise NotImplementedError
