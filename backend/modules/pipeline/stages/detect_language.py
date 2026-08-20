"""
Stage 3: Language detection (PDF 3.3).

Fast, cheap detection with a confidence score. Anything below the configured
threshold (default 0.90) is routed to a HUMAN for confirmation rather than
being guessed at.

WHY THE THRESHOLD IS THE WHOLE POINT
"Bad detection silently poisons the translation step." An English document
misdetected as Swahili skips translation and reaches a reviewer as untranslated
text with no explanation. A Swahili document misdetected as English gets
"translated" into mangled Swahili. Both failures are invisible until a human
wastes time on them — so we spend one cheap human confirmation to avoid it.

The threshold is CONFIGURABLE, not hardcoded. Tune it from real data: if the
confirmation queue is always empty, the threshold is too low to be doing
anything; if it is drowning, it is too high.
"""

from __future__ import annotations

from ..domain.enums import ResourceStatus
from ..domain.models import Resource
from ..ports.job_queue import JobQueue
from ..ports.language_detector import LanguageDetector
from ..ports.repositories import (
    DocumentRepository,
    ResourceRepository,
    ReviewRepository,
)
from .base import Stage, StageResult


class DetectLanguageStage(Stage):
    """Identifies the source language and routes low-confidence cases to a human."""

    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        documents: DocumentRepository,
        detector: LanguageDetector,
        confidence_threshold: float = 0.90,
        target_language: str = "sw",
        max_attempts: int = 5,
    ) -> None:
        super().__init__(
            resources=resources, queue=queue, reviews=reviews, max_attempts=max_attempts
        )
        self._documents = documents
        self._detector = detector
        self._threshold = confidence_threshold
        self._target_language = target_language

    @property
    def name(self) -> str:
        return "detect_language"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        # NEEDS_LANGUAGE_CONFIRMATION is accepted so that a human confirming the
        # language re-enters this stage and continues down the normal path,
        # rather than needing a separate bypass route.
        return frozenset(
            {ResourceStatus.EXTRACTED, ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION}
        )

    def handle(self, resource: Resource) -> StageResult:
        """Detect the language, then route on confidence and on whether it is already Swahili.

        TODO (junior dev) — implement in this order:

          1. SHORT-CIRCUIT A HUMAN CONFIRMATION:
             If `resource.detected_language` is already set by a human
             (source_metadata carries a "language_confirmed_by" marker), trust
             it and skip detection entirely. Do not overwrite a human decision
             with a model's guess — that is an infuriating bug to be on the
             receiving end of.

          2. DETECT on the normalized text:
                 document = self._documents.get_document(resource.resource_id)
                 result = self._detector.detect(document.raw_text)
             Detection runs on extracted text, never on raw HTML — markup and
             boilerplate skew the result toward English.

          3. LOW CONFIDENCE -> HUMAN:
                 if result.confidence < self._threshold:
                     return StageResult(
                         next_status=ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION,
                         next_stage=None,   # stop; a human must act
                         resource_changes={"detected_language": result.language,
                                           "language_confidence": result.confidence},
                         details={"alternatives": result.alternatives},
                     )
             `next_stage=None` is deliberate: the pipeline PARKS the resource.
             Store the alternatives so the human picks from a list.

          4. ALREADY SWAHILI -> SKIP TRANSLATION (PDF 3.4, first bullet):
                 if result.language == self._target_language:
                     next_status=LANGUAGE_DETECTED, next_stage="store"
             Note this transition goes straight to `store`, bypassing translate.
             `state_machine.py` allows LANGUAGE_DETECTED -> STORED precisely
             for this case. It still gets reviewed — skipping MT is not
             skipping human review.

          5. OTHERWISE -> TRANSLATE:
                 next_status=LANGUAGE_DETECTED, next_stage="translate"

        TESTING NOTE: this stage is pure routing logic over a tiny interface,
        so it is trivial to test with a fake detector — write tests for all four
        branches above (confirmed / low confidence / already-Swahili / normal).
        No network, no model download. There is no excuse for this stage being
        untested.
        """
        if resource.source_metadata.get("language_confirmed_by") and resource.detected_language:
            language = resource.detected_language
            return StageResult(
                next_status=ResourceStatus.LANGUAGE_DETECTED,
                next_stage="store" if language == self._target_language else "translate",
                resource_changes={"detected_language": language},
            )

        document = self._documents.get_document(resource.resource_id)
        result = self._detector.detect(document.raw_text)
        changes = {
            "detected_language": result.language,
            "language_confidence": result.confidence,
        }
        if result.confidence < self._threshold:
            return StageResult(
                next_status=ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION,
                resource_changes=changes,
                details={"alternatives": result.alternatives},
            )
        return StageResult(
            next_status=ResourceStatus.LANGUAGE_DETECTED,
            next_stage="store" if result.language == self._target_language else "translate",
            resource_changes=changes,
        )
