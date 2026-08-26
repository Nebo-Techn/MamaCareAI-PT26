"""
Stage 4: Translation to Swahili (PDF 3.4).

Chunks the document, translates it, reassembles it WITH STRUCTURE INTACT, and
writes the result as version 1 — the machine version — of the content.

THE FOUR REQUIREMENTS FROM THE DESIGN DOC, AND WHERE EACH LIVES:
  - "Already Swahili -> skip translation": handled upstream in
    `detect_language.py`; this stage never sees those resources.
  - "Chunking ... reassembled while preserving structure": chunking lives in
    `adapters/translation/chunker.py`, reassembly is step 4 below. Content must
    NOT be flattened into a single block — the reviewer's side-by-side view
    depends on the structure surviving.
  - "Engine choice": entirely behind the `Translator` port. This file does not
    know whether it is talking to NLLB-200 or a cloud API, which is what keeps
    PDF section 6's open question from blocking us.
  - "Quality signal": store the provider's confidence so `review_service.py`
    can prioritize the review queue by it.

COST WARNING FOR JUNIOR DEVS: this stage is where money is spent (cloud MT) or
GPU time is burned (self-hosted). Every bug that causes a re-translation costs
real budget. Make it idempotent, and check `get_machine_version()` before
translating anything.
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
from ..ports.translator import Translator
from .base import Stage, StageResult


class TranslateStage(Stage):
    """Machine-translates a normalized document into Swahili."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        documents: DocumentRepository,
        versions: VersionRepository,
        translator: Translator,
        chunker: object,  # TODO: type as adapters.translation.chunker.Chunker port
        target_language: str = "sw",
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        self._documents = documents
        self._versions = versions
        self._translator = translator
        self._chunker = chunker
        self._target_language = target_language

    @property
    def name(self) -> str:
        return "translate"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset({ResourceStatus.LANGUAGE_DETECTED})

    def handle(self, resource: Resource) -> StageResult:
        """Translate the document and store it as machine version 1.

        TODO (junior dev) — implement in this order:

          1. IDEMPOTENCY CHECK FIRST — this one saves real money:
                 if self._versions.get_machine_version(resource.resource_id):
                     skip translating, go straight to the return in step 6.
             A redelivered job must never pay for the same document twice.

          2. LOAD + GUARD:
                 document = self._documents.get_document(resource.resource_id)
                 if not self._translator.supports(resource.detected_language,
                                                  self._target_language):
                     raise TranslationError(...)   # permanent, routes to a human
             Check support BEFORE spending anything.

          3. CHUNK, respecting the engine's length limit:
                 chunks = self._chunker.chunk(document.blocks,
                                              max_chars=<engine limit>)
             Chunks must not split mid-sentence, and each chunk must remember
             which block(s) it came from. See the chunker for why.

          4. TRANSLATE IN BATCHES:
                 translated = self._translator.translate_batch(
                     [c.text for c in chunks],
                     source_language=resource.detected_language,
                     target_language=self._target_language)
             ASSERT len(translated) == len(chunks) before using the result.
             A silent length mismatch mis-aligns every block after it and
             produces a document that looks fine until a reviewer reads it.

          5. REASSEMBLE INTO TranslationUnits, aligned to the ORIGINAL blocks:
             Map chunks back to their source blocks and rejoin. Preserve
             `order` and block kind — headings stay headings. This is what makes
             the side-by-side review UI usable at all.

          6. SAVE AS VERSION 1 (machine):
                 self._versions.save_version(ContentVersion(
                     resource_id=..., version_number=1,
                     author_kind=VersionAuthorKind.MACHINE, author_id=None,
                     units=..., engine=self._translator.engine_name))
             Record `engine_name` — six months from now this is the only way to
             answer "did quality change when we switched engines?"

          7. RETURN:
                 StageResult(next_status=ResourceStatus.TRANSLATED,
                             next_stage="store",
                             details={"chunks": len(chunks),
                                      "mean_confidence": <mean or None>})

        PARTIAL FAILURE (long documents, 200 chunks, chunk 180 fails):
        Do NOT save a half-translated version — a reviewer cannot tell a
        partial translation from a bad one. Either the whole document
        translates or the job fails and retries. If long documents fail often
        enough to matter, add per-chunk caching keyed by chunk hash so a retry
        only re-translates what is missing. Measure before building that.
        """
        raise NotImplementedError
