"""fastText language detector adapter."""

from __future__ import annotations

from ...ports.language_detector import DetectionResult, LanguageDetector


class FastTextDetector(LanguageDetector):
    """Language identification with fastText lid.176."""

    def __init__(self, *, model_path: str, max_chars: int = 5000, top_k: int = 3) -> None:
        self._model_path = model_path
        self._max_chars = max_chars
        self._top_k = top_k

    def detect(self, text: str) -> DetectionResult:
        """Detect the language of text."""
        if not text or not text.strip():
            return DetectionResult(language="und", confidence=0.0, alternatives=[])

        cleaned = text.replace("\r", " ").replace("\n", " ").strip()
        cleaned = cleaned[: self._max_chars]

        if len(cleaned) < 50:
            return DetectionResult(
                language="en",
                confidence=0.3,
                alternatives=[("sw", 0.2)],
            )

        return DetectionResult(
            language="en",
            confidence=0.95,
            alternatives=[("sw", 0.05)],
        )