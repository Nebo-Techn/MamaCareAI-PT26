"""
Stage 2: Extraction & normalization (PDF 3.2).

Converts raw bytes into the ONE common schema — `NormalizedDocument` — that
every later stage speaks.

THIS IS THE MOST IMPORTANT ARCHITECTURAL BOUNDARY IN THE PIPELINE.
Everything before it is source-type-specific. Everything after it is not.
Translation, review, and publication never learn whether the content started
as a PDF, a web page, or a video transcript. Protect that boundary: if
source-type knowledge leaks past this stage, every later stage grows branches
and the pipeline stops being extensible.
"""

from __future__ import annotations

from ..domain.enums import ResourceStatus
from ..domain.models import Resource
from ..ports.job_queue import JobQueue
from ..ports.object_store import ObjectStore
from ..ports.repositories import DocumentRepository, ResourceRepository, ReviewRepository
from ..registry import ExtractorRegistry
from .base import Stage, StageResult


class ExtractStage(Stage):
    """Produces a NormalizedDocument from stored raw bytes."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        documents: DocumentRepository,
        extractors: ExtractorRegistry,
        object_store: ObjectStore,
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        self._documents = documents
        self._extractors = extractors
        self._object_store = object_store

    @property
    def name(self) -> str:
        return "extract"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset({ResourceStatus.FETCHED})

    def handle(self, resource: Resource) -> StageResult:
        """Load raw bytes, run the right extractor, save the normalized document.

        TODO (junior dev) — implement in this order:

          1. LOAD the raw bytes:
                 content = self._object_store.get(resource.raw_object_key)
             A missing key is a permanent error — do not retry it forever.

          2. SELECT THE EXTRACTOR VIA THE REGISTRY, with fallback:
                 extractor = self._extractors.select(content_type, content)
             The registry tries candidates in priority order and picks the
             first whose `can_handle` returns True. That is how
             "PDF text layer, else OCR" and "captions, else ASR" work WITHOUT a
             single if-statement in this file. Do not reimplement that logic here.

          3. EXTRACT:
                 document = extractor.extract(resource.resource_id, content,
                                              metadata=resource.source_metadata)

          4. VALIDATE THE OUTPUT before accepting it:
                 - at least one TextBlock
                 - total text length above a sane minimum (config:
                   min_extracted_chars — a 12-character "document" is an
                   extraction failure wearing a success costume)
                 - `order` values are unique and contiguous
             Fail with ExtractionError rather than passing junk downstream.
             Every stage after this one costs money; garbage caught here is
             garbage that never reaches an MT bill or a reviewer's queue.

          5. PERSIST and continue:
                 self._documents.save_document(document)
                 return StageResult(next_status=ResourceStatus.EXTRACTED,
                                    next_stage="detect_language",
                                    resource_changes={"source_metadata": {...merged...}},
                                    details={"blocks": len(document.blocks),
                                             "extractor": type(extractor).__name__})

        IDEMPOTENCY: `save_document` overwrites by resource_id, so re-running is
        safe by construction. Keep it that way — do not switch it to an insert.

        ASR NOTE (PDF 3.1): audio transcription belongs in its OWN stage and its
        OWN autoscaling worker pool, because it is the most expensive step and
        it is bursty. The ASR extractor adapter is invoked from this stage for
        now; when volume justifies it, split it into `stages/transcribe.py`
        reading a separate queue. Because this stage only talks to the registry,
        that split is a routing change — no rewrite. Note it in
        `docs/DECISIONS.md` when you make the call.
        """
        raise NotImplementedError
