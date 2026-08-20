""""
fastText-based language detector — PIPE-19.

ASSUMPTIONS (verify against the real `ports/language.py` / domain models
before merging — these are educated guesses, not confirmed contracts):

- A port interface named `LanguageDetector` exists with a `detect(text: str)`
  method that returns something exposing `.language` (ISO 639-1/2 code, e.g.
  "sw", "en") and `.confidence` (float 0.0-1.0), matching the
  `detected_language` / `language_confidence` fields already present on the
  `Resource` domain model in sql_repositories.py.
- fastText's pretrained language-identification model is used
  (https://fasttext.cc/docs/en/language-identification.html), loaded from a
  local path rather than downloaded at runtime (matches the "free stack,
  local-first" pattern used elsewhere in this pipeline — see NLLB-200 and
  sentence-transformers in ARCHITECTURE.md).
- `fasttext` (pip package `fasttext-wheel` or `fasttext`) is an approved
  dependency — not yet confirmed in requirements.txt.

If the real port differs (different method name, different result shape,
different confidence threshold behavior), this file needs to be adjusted to
match it exactly — do not merge without checking.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# fastText's pretrained label format is "__label__<iso-code>"
_FASTTEXT_LABEL_PREFIX = "__label__"

# Below this confidence, treat the detection as unreliable rather than
# confidently wrong — callers (e.g. the detect_language stage) can decide
# whether to route low-confidence resources to manual review.
DEFAULT_MIN_CONFIDENCE = 0.5


class LanguageDetectionError(Exception):
    """Raised when detection cannot be performed (empty text, model load failure)."""


@dataclass(frozen=True)
class DetectionResult:
    """Result of a language detection call."""

    language: str      # ISO 639-1/2 code, e.g. "sw", "en", "fr"
    confidence: float  # 0.0-1.0
    is_reliable: bool  # confidence >= configured threshold


class FastTextLanguageDetector:
    """
    Language detector backed by fastText's pretrained lid.176 model.

    Loads the model once (lazily, thread-safely) and reuses it across calls —
    fastText model load is expensive (seconds), detection itself is fast
    (sub-millisecond), so a single shared instance should back the whole
    pipeline process rather than being re-instantiated per resource.
    """

    def __init__(
        self,
        model_path: str | Path,
        *,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ) -> None:
        self._model_path = Path(model_path)
        self._min_confidence = min_confidence
        self._model = None
        self._load_lock = threading.Lock()

        if not self._model_path.exists():
            raise LanguageDetectionError(
                f"fastText model not found at '{self._model_path}'. "
                f"Download lid.176.bin (or the smaller lid.176.ftz) from "
                f"https://fasttext.cc/docs/en/language-identification.html "
                f"and set the path via config, not by downloading at runtime."
            )

    def _ensure_loaded(self):
        if self._model is not None:
            return self._model

        with self._load_lock:
            if self._model is not None:
                return self._model
            try:
                import fasttext
            except ImportError as e:
                raise LanguageDetectionError(
                    "fasttext package is not installed. "
                    "Add 'fasttext-wheel' (or 'fasttext') to requirements.txt."
                ) from e

            logger.info("Loading fastText language model from %s", self._model_path)
            self._model = fasttext.load_model(str(self._model_path))
            return self._model

    def detect(self, text: str) -> DetectionResult:
        """
        Detect the primary language of `text`.

        Raises LanguageDetectionError for empty/whitespace-only input rather
        than silently returning a meaningless guess.
        """
        if text is None or not text.strip():
            raise LanguageDetectionError("Cannot detect language of empty text.")

        model = self._ensure_loaded()

        # fastText chokes on embedded newlines; it expects single-line input.
        cleaned = " ".join(text.strip().split())

        labels, probabilities = model.predict(cleaned, k=1)

        if not labels:
            raise LanguageDetectionError("fastText returned no prediction.")

        raw_label = labels[0]
        confidence = float(probabilities[0])
        language = raw_label.removeprefix(_FASTTEXT_LABEL_PREFIX)

        return DetectionResult(
            language=language,
            confidence=confidence,
            is_reliable=confidence >= self._min_confidence,
        )

    def detect_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Convenience batch wrapper. Order is preserved; empty strings raise."""
        return [self.detect(t) for t in texts]
"
fastText language detector (PDF 3.3: "fastText lid.176").

Model: lid.176.bin (~130MB) or lid.176.ftz (~900KB, quantized, slightly less
accurate). Start with the quantized one — it is small enough to commit to
model storage and fast enough that this stage never shows up in a latency
profile.

A NOTE ON SWAHILI DETECTION THAT WILL COST YOU A DAY IF YOU HIT IT COLD:
Swahili ("sw") is frequently confused with other Bantu languages, and
code-switched Swahili-English text — extremely common in Tanzanian health
material, and exactly what this project ingests — often detects as English with
middling confidence. That is precisely why the confidence threshold and the
human confirmation path exist. Do not "fix" this by lowering the threshold;
route the uncertain cases to a person, which is what the design already says
to do.
"""

from __future__ import annotations

from ...ports.language_detector import DetectionResult, LanguageDetector


class FastTextDetector(LanguageDetector):
    """Language identification with fastText lid.176."""

    def __init__(self, *, model_path: str, max_chars: int = 5000, top_k: int = 3) -> None:
        # TODO: load the model ONCE here. It is ~130MB; loading per call would
        # make the cheapest stage in the pipeline the slowest.
        self._model_path = model_path
        # Detection does not need the whole document — a few thousand
        # characters is plenty, and truncating keeps this stage genuinely cheap.
        self._max_chars = max_chars
        self._top_k = top_k

    def detect(self, text: str) -> DetectionResult:
        """Detect the language of `text`.

        TODO (junior dev):
          [ ] PREPROCESS: strip URLs, email addresses, and long digit runs.
              They are language-neutral noise that drags every prediction
              toward English.
          [ ] REPLACE NEWLINES WITH SPACES. fastText's predict() raises on
              input containing newlines — a genuinely surprising failure that
              will look like a corrupt-document bug.
          [ ] Truncate to self._max_chars.
          [ ] SHORT TEXT GUARD: below ~50 characters, return the prediction
              with a deliberately low confidence. fastText is unreliable on
              short strings, and an over-confident wrong answer here poisons
              the translation step — the exact failure PDF 3.3 warns about.
          [ ] Call predict(text, k=self._top_k) to get alternatives too.
          [ ] STRIP THE "__label__" PREFIX. Nothing outside this file should
              ever see a fastText-specific format.
          [ ] Return DetectionResult(language, confidence, alternatives), with
              alternatives ordered most-likely first for the confirmation UI.
          [ ] NEVER RAISE on empty or odd input — return low confidence and let
              the stage route it to a human. A crash here dead-letters a
              document that a person could have resolved in five seconds.
        """
        raise NotImplementedError
