"""
Port: Translator — machine translation into Swahili (PDF 3.4).

This port is the reason PDF section 6's open question ("self-hosted NLLB-200
versus a cloud MT API?") does not block development. Both are adapters behind
this interface. Build against the port now, decide the engine later, and
switch by changing one config value.

BATCH, DON'T LOOP
`translate_batch` takes a list, not a single string. A per-block loop against a
cloud API is N HTTP round trips for one document, which is both slow and the
fastest way to hit a rate limit. Implementations should send blocks in batches
the provider accepts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslatedChunk:
    """One translated piece, carrying the provider's confidence if it gives one."""

    text: str
    confidence: float | None = None


class Translator(ABC):
    """Translates text into a target language."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Stable identifier recorded on every version, e.g. "nllb-200-distilled-600M".

        This is what lets us answer "did quality change when we switched
        engines in March?" six months from now. Include the model version —
        "google" is not enough, "google-translate-v3" is.
        """

    @abstractmethod
    def supports(self, source_language: str, target_language: str) -> bool:
        """Return True if this engine can translate this language pair.

        The stage checks this before calling. An engine that cannot handle the
        pair should be caught here, not by parsing an error message afterwards.
        """
        raise NotImplementedError

    @abstractmethod
    def translate_batch(
        self,
        texts: list[str],
        *,
        source_language: str,
        target_language: str = "sw",
    ) -> list[TranslatedChunk]:
        """Translate several pieces of text at once.

        Contract every implementation MUST honour:
          - Return EXACTLY as many results as inputs, in the SAME order.
            Alignment by index is how translations get matched back to their
            source blocks; a dropped element silently corrupts a whole document.
          - Never merge or split the caller's items. Length limits are handled
            by `adapters/translation/chunker.py` before this is called.
          - Raise `ProviderRateLimited` (retryable, with retry_after when known)
            for 429/quota responses.
          - Raise `TranslationError` for unsupported pairs and malformed input.
          - Set `confidence` to None when the provider does not supply one.
            Do not invent a number — a fabricated confidence would mis-sort the
            human review queue, which is the one thing it is used for.

        TODO (junior dev): make this safely retryable. A retry must re-translate
        cleanly, never append to a half-finished result.
        """
        raise NotImplementedError
