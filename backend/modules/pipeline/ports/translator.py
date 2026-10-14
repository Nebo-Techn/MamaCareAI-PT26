from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from ..domain.errors import ProviderRateLimited, TransientError, TranslationError

__all__ = [
    "MalformedTranslationOutput",
    "ProviderRateLimited",
    "TranslatedChunk",
    "TranslationBatchResult",
    "TranslationConfigurationError",
    "TranslationError",
    "TranslationProviderUnavailable",
    "Translator",
    "UnsupportedLanguagePair",
    "validate_translation_output",
]


@dataclass(frozen=True, slots=True)
class TranslatedChunk:
    text: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise MalformedTranslationOutput(
                f"Translated chunk text must be str, got {type(self.text).__name__}"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise MalformedTranslationOutput(
                f"Translated chunk confidence must be within [0, 1], got {self.confidence}"
            )


@dataclass(frozen=True, slots=True)
class TranslationBatchResult:
    engine: str
    source_language: str
    target_language: str
    chunks: tuple[TranslatedChunk, ...]

    @property
    def texts(self) -> list[str]:
        return [chunk.text for chunk in self.chunks]


class TranslationProviderUnavailable(TransientError):
    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        engine: str | None = None,
    ) -> None:
        super().__init__(message, resource_id=resource_id)
        self.engine = engine


class UnsupportedLanguagePair(TranslationError):
    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        engine: str | None = None,
        source_language: str | None = None,
        target_language: str | None = None,
    ) -> None:
        super().__init__(message, resource_id=resource_id)
        self.engine = engine
        self.source_language = source_language
        self.target_language = target_language


class TranslationConfigurationError(TranslationError):
    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        engine: str | None = None,
    ) -> None:
        super().__init__(message, resource_id=resource_id)
        self.engine = engine


class MalformedTranslationOutput(TranslationError):
    def __init__(
        self,
        message: str,
        *,
        resource_id: str | None = None,
        engine: str | None = None,
    ) -> None:
        super().__init__(message, resource_id=resource_id)
        self.engine = engine


def validate_translation_output(
    inputs: Sequence[str],
    outputs: Sequence[object],
    *,
    engine: str | None = None,
) -> tuple[TranslatedChunk, ...]:
    if len(outputs) != len(inputs):
        raise MalformedTranslationOutput(
            f"Translator returned a different number of chunks than inputs "
            f"({len(outputs)} != {len(inputs)})",
            engine=engine,
        )
    chunks: list[TranslatedChunk] = []
    for index, (source, chunk) in enumerate(zip(inputs, outputs)):
        if not isinstance(source, str):
            raise MalformedTranslationOutput(
                f"Input {index} is {type(source).__name__}, expected str",
                engine=engine,
            )
        if not isinstance(chunk, TranslatedChunk):
            raise MalformedTranslationOutput(
                f"Result {index} is {type(chunk).__name__}, expected TranslatedChunk",
                engine=engine,
            )
        if source.strip() and not chunk.text.strip():
            raise MalformedTranslationOutput(
                f"Result {index} is empty for a non-empty input", engine=engine
            )
        chunks.append(chunk)
    return tuple(chunks)


class Translator(ABC):
    @property
    @abstractmethod
    def engine_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def supports(self, source_language: str, target_language: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def translate_batch(
        self,
        texts: list[str],
        *,
        source_language: str,
        target_language: str = "sw",
    ) -> list[TranslatedChunk]:
        raise NotImplementedError

    def translate(
        self,
        texts: Sequence[str],
        *,
        source_language: str,
        target_language: str = "sw",
    ) -> TranslationBatchResult:
        engine = self.engine_name
        inputs = list(texts)
        if not all(isinstance(text, str) for text in inputs):
            raise MalformedTranslationOutput(
                "Translation inputs must all be strings",
                engine=engine,
            )
        if not self.supports(source_language, target_language):
            raise UnsupportedLanguagePair(
                f"{engine} does not support {source_language!r} -> {target_language!r}",
                engine=engine,
                source_language=source_language,
                target_language=target_language,
            )
        outputs = (
            self.translate_batch(
                inputs,
                source_language=source_language,
                target_language=target_language,
            )
            if inputs
            else []
        )
        return TranslationBatchResult(
            engine=engine,
            source_language=source_language,
            target_language=target_language,
            chunks=validate_translation_output(inputs, outputs, engine=engine),
        )
