"""
Port: LanguageDetector — identify the source language and how sure we are (PDF 3.3).

The confidence score is not decoration. Bad detection silently poisons
translation: an English document mislabelled as Swahili skips translation
entirely and lands in the review queue as gibberish nobody can explain.
That is why every implementation must return a real confidence, and why the
stage routes anything below the threshold to a human instead of guessing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Detected language plus the model's confidence in it."""

    language: str  # ISO 639-1 where possible ("en", "fr", "sw")
    confidence: float  # 0.0 - 1.0
    # Runner-up candidates, most likely first. Shown to the human confirming a
    # low-confidence result so they pick from a list instead of typing a guess.
    alternatives: tuple[tuple[str, float], ...] = ()


class LanguageDetector(ABC):
    """Detects the language of normalized text."""

    @abstractmethod
    def detect(self, text: str) -> DetectionResult:
        """Return the most likely language of `text` with a confidence score.

        Contract every implementation MUST honour:
          - `confidence` is a real probability in [0.0, 1.0]. If the underlying
            library does not give one, do NOT hardcode 1.0 — that defeats the
            entire threshold mechanism. Return the library's score or 0.0.
          - Be fast and cheap. This runs on every single resource; it is not
            the place for an LLM call (PDF 3.3 specifies fastText lid.176).
          - Truncate long input yourself (a few thousand characters is plenty
            for detection) rather than pushing a whole book through the model.
          - Never raise on short/empty text — return low confidence instead and
            let the stage route it to a human.

        TODO (junior dev): normalize the model's language codes to one scheme
        before returning. fastText emits "__label__sw"; strip the prefix here
        so nothing downstream ever sees a model-specific format.
        """
        raise NotImplementedError
