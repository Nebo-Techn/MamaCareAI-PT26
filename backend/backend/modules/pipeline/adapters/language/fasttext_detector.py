"""
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

    def __init__(
        self, *, model_path: str, max_chars: int = 5000, top_k: int = 3
    ) -> None:
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
