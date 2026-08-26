from __future__ import annotations

from ...ports.translator import TranslatedChunk, Translator


class PassthroughTranslator(Translator):
    def __init__(self, *, marker: str = "[sw] ") -> None:
        self._marker = marker

    @property
    def engine_name(self) -> str:
        return "passthrough"

    def supports(self, source_language: str, target_language: str) -> bool:
        return True

    def translate_batch(
        self, texts: list[str], *, source_language: str, target_language: str = "sw"
    ) -> list[TranslatedChunk]:
        return [TranslatedChunk(text=f"{self._marker}{text}") for text in texts]
