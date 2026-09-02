from __future__ import annotations

from uuid import uuid4

from ..adapters.translation.chunker import Chunker
from ..domain.enums import ResourceStatus, VersionAuthorKind
from ..domain.errors import TranslationError
from ..domain.models import ContentVersion, Resource, TranslationUnit
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
    def __init__(
        self,
        *,
        resources: ResourceRepository,
        queue: JobQueue,
        reviews: ReviewRepository,
        documents: DocumentRepository,
        versions: VersionRepository,
        translator: Translator,
        chunker: Chunker,
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
        existing_version = self._versions.get_machine_version(resource.resource_id)
        if existing_version is not None:
            return StageResult(
                next_status=ResourceStatus.TRANSLATED,
                next_stage="store",
                details={"chunks": 0, "reused_version": existing_version.version_id},
            )

        if not resource.detected_language:
            raise TranslationError("resource has no detected language")
        if not self._translator.supports(resource.detected_language, self._target_language):
            raise TranslationError(
                f"{self._translator.engine_name} does not support "
                f"{resource.detected_language!r} to {self._target_language!r}"
            )

        document = self._documents.get_document(resource.resource_id)
        chunks = self._chunker.chunk(document.blocks)
        translated_chunks = self._translator.translate_batch(
            [chunk.text for chunk in chunks],
            source_language=resource.detected_language,
            target_language=self._target_language,
        )
        if len(translated_chunks) != len(chunks):
            raise TranslationError(
                "translator returned a different number of chunks than it received"
            )

        translated_texts = [chunk.text for chunk in translated_chunks]
        translated_blocks = self._chunker.reassemble(
            document.blocks, chunks, translated_texts
        )
        source_by_order = {block.order: block.text for block in document.blocks}
        kind_by_order = {block.order: block.kind for block in document.blocks}
        confidence_by_order = {
            block_order: translated_chunk.confidence
            for chunk, translated_chunk in zip(chunks, translated_chunks, strict=True)
            for block_order in chunk.block_orders
        }
        translated_by_order = dict(translated_blocks)
        if (
            len(translated_blocks) != len(source_by_order)
            or set(translated_by_order) != set(source_by_order)
        ):
            raise TranslationError("chunker did not return one translation for every block")

        units = tuple(
            TranslationUnit(
                order=order,
                kind=kind_by_order[order],
                source_text=source_by_order[order],
                translated_text=translated_text,
                confidence=confidence_by_order.get(order),
            )
            for order, translated_text in sorted(translated_by_order.items())
        )
        self._versions.save_version(
            ContentVersion(
                version_id=str(uuid4()),
                resource_id=resource.resource_id,
                version_number=1,
                author_kind=VersionAuthorKind.MACHINE,
                author_id=None,
                units=units,
                engine=self._translator.engine_name,
            )
        )

        confidences = [
            translated_chunk.confidence
            for translated_chunk in translated_chunks
            if translated_chunk.confidence is not None
        ]
        return StageResult(
            next_status=ResourceStatus.TRANSLATED,
            next_stage="store",
            details={
                "chunks": len(chunks),
                "mean_confidence": sum(confidences) / len(confidences)
                if confidences
                else None,
            },
        )
