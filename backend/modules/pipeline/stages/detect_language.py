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
    """Detect a resource's language and route it to the next pipeline stage."""

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
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        self._threshold = confidence_threshold
        self._target_language = target_language

    @property
    def name(self) -> str:
        return "detect_language"

    @property
    def accepts(self) -> frozenset[ResourceStatus]:
        return frozenset(
            {ResourceStatus.EXTRACTED, ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION}
        )

    def handle(self, resource: Resource) -> StageResult:
        """Detect the language and choose the next stage."""
        confirmed_by = resource.source_metadata.get("language_confirmed_by")
        if confirmed_by and resource.detected_language:
            language = resource.detected_language
            confidence = resource.language_confidence
            details: dict[str, object] = {"language_confirmed_by": confirmed_by}
        else:
            document = self._documents.get_document(resource.resource_id)
            result = self._detector.detect(document.raw_text)
            language = result.language
            confidence = result.confidence
            if confidence < self._threshold:
                return StageResult(
                    next_status=ResourceStatus.NEEDS_LANGUAGE_CONFIRMATION,
                    next_stage=None,
                    resource_changes={
                        "detected_language": language,
                        "language_confidence": confidence,
                    },
                    details={"alternatives": result.alternatives},
                )
            details = {"alternatives": result.alternatives}

        next_stage = (
            "store"
            if language.casefold() == self._target_language.casefold()
            else "translate"
        )
        return StageResult(
            next_status=ResourceStatus.LANGUAGE_DETECTED,
            next_stage=next_stage,
            resource_changes={
                "detected_language": language,
                "language_confidence": confidence,
            },
            details=details,
        )
