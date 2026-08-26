"""
Passthrough translator — for local development and tests.

Returns the input text with a marker prefix instead of translating it.

WHY THIS EXISTS AND WHY IT IS NOT A HACK
It lets the whole pipeline run end to end — submit a URL, watch it reach the
review queue — with no model download, no API key, and no GPU. A new trainee
can clone the repo and see the system work on day one, which is worth a great
deal in an 8-week program with four people onboarding at once.

It is also the Liskov Substitution Principle as a working test: if the pipeline
behaves correctly with this Translator swapped in, the stages genuinely do not
depend on any particular engine's behaviour.

NEVER SET THIS IN PRODUCTION. `container.build_translator` should refuse to
build it when the environment is production — a marker-prefixed "translation"
reaching a real reader is exactly the kind of embarrassing failure that config
guards exist to prevent.
"""

from __future__ import annotations

from ...ports.translator import TranslatedChunk, Translator


class PassthroughTranslator(Translator):
    """Fake translator: echoes input with a visible marker."""

    def __init__(self, *, marker: str = "[sw] ") -> None:
        # Visible on purpose. If this text ever reaches a review UI, everyone
        # sees instantly that translation was not actually configured.
        self._marker = marker

    @property
    def engine_name(self) -> str:
        """TODO: return "passthrough" — and make sure it is recorded on the
        version, so nobody later mistakes this output for real translation."""
        raise NotImplementedError

    def supports(self, source_language: str, target_language: str) -> bool:
        """TODO: return True for everything. It is a fake; it "handles" all pairs."""
        raise NotImplementedError

    def translate_batch(
        self, texts: list[str], *, source_language: str, target_language: str = "sw"
    ) -> list[TranslatedChunk]:
        """TODO: return [TranslatedChunk(text=self._marker + t, confidence=None)
        for t in texts].

        Note it honours the contract exactly: same length, same order. A fake
        that breaks the contract makes tests pass that should fail — which is
        worse than having no fake at all.
        """
        raise NotImplementedError
