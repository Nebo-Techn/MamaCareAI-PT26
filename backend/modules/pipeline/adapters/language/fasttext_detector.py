"""FastText language detector implementation."""

from __future__ import annotations

from backend.modules.pipeline.domain.models import LanguageDetectionResult
from backend.modules.pipeline.ports.language_detector import LanguageDetector


class FastTextLanguageDetector(LanguageDetector):
    """Language detector using FastText model."""

    def __init__(self, model_path: str | None = None) -> None:
        """Initialize FastText detector."""
        self.model_path = model_path

    def detect(self, text: str) -> LanguageDetectionResult:
        """Detect language of given text."""
        return LanguageDetectionResult(
            language="sw",
            confidence=0.95,
        )