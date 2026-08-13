"""
Cloud MT translator (PDF 3.4) — Google / AWS / Azure Translate.

"cloud MT for reliability and broad language coverage".

WHEN TO CHOOSE THIS OVER NLLB
  - Broad language coverage matters more than per-call cost.
  - You do not want to operate a model (no GPU, no ops time).
  - The provider returns a confidence score, which improves review
    prioritization.

WHEN NOT TO
  - DATA PRIVACY: this sends content to a third party. For public health
    guidance that is fine. If the corpus ever includes anything sensitive,
    this decision needs explicit sign-off in docs/DECISIONS.md.
  - COST: per-character billing means a large corpus gets expensive quickly,
    and docs/ARCHITECTURE.md states no budget is provisioned. Estimate before
    switching: characters x rate, not "it is only a few dollars".

ONE CLASS, MULTIPLE PROVIDERS: keep provider differences to a small internal
strategy rather than three near-identical classes. If a provider needs
genuinely different behaviour, give it its own subclass — do not grow an
if-chain here.
"""

from __future__ import annotations

from ...ports.translator import TranslatedChunk, Translator


class CloudTranslator(Translator):
    """Translation via a managed cloud MT API."""

    def __init__(
        self,
        *,
        provider: str,              # "google" | "aws" | "azure"
        api_key: str | None = None,
        region: str | None = None,
        batch_size: int = 16,
        timeout_seconds: float = 30.0,
    ) -> None:
        # TODO: build the provider client ONCE here. Also VALIDATE CREDENTIALS
        # at construction — the container builds this at startup, so a missing
        # key should fail the process immediately rather than at job 400.
        self._provider = provider
        self._api_key = api_key
        self._region = region
        self._batch_size = batch_size
        self._timeout = timeout_seconds

    @property
    def engine_name(self) -> str:
        """TODO: include the API version, e.g. "google-translate-v3" — "google"
        alone will not tell you which engine produced a translation next year."""
        raise NotImplementedError

    def supports(self, source_language: str, target_language: str) -> bool:
        """TODO: check against the provider's supported-languages list, and
        CACHE it. Fetching the list on every call adds a round trip to every
        translation for information that changes maybe twice a year."""
        raise NotImplementedError

    def translate_batch(
        self, texts: list[str], *, source_language: str, target_language: str = "sw"
    ) -> list[TranslatedChunk]:
        """Translate a batch via the provider API.

        TODO (junior dev):
          [ ] Use the provider's BATCH endpoint. A loop of single-text calls is
              N round trips and the fastest route to a rate limit.
          [ ] Respect the provider's per-request limits (both item count and
              total characters) — split into sub-requests as needed.
          [ ] Return EXACTLY len(texts) results in the SAME ORDER.
          [ ] MAP ERRORS PROPERLY, this is the part that gets skipped:
                  429 / quota   -> ProviderRateLimited(retry_after_seconds=...)
                                   read Retry-After; blind backoff wastes time
                                   the provider already told you about
                  5xx / timeout -> TransientError
                  400 / bad pair-> TranslationError (permanent)
                  401 / 403     -> PermanentError, and make the message say
                                   "check credentials" — that failure will
                                   otherwise be misread as a code bug
          [ ] Store the provider's confidence when it supplies one; None when
              it does not. Never invent a value.
          [ ] LOG CHARACTER COUNTS PER CALL. Cloud MT is billed per character,
              and a runaway loop is much cheaper to catch in a metric than on
              an invoice.
        """
        raise NotImplementedError
