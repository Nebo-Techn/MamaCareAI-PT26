"""
Registries — how the pipeline picks a fetcher or extractor WITHOUT if-statements.

THE PROBLEM THIS SOLVES
The naive version of this pipeline has, in `extract.py`:

    if source_type == "pdf":
        ...
    elif source_type == "web":
        ...
    elif source_type == "video":
        ...

Every new format edits that function. Every edit risks the formats that already
worked. Six months later it is 200 lines nobody wants to touch.

THE FIX (Open/Closed Principle)
Adapters register themselves against a capability. Stages ask the registry.
Adding .docx support = write one adapter + one registration line. Zero edits to
any stage. That is the difference between a codebase that grows and one that
calcifies — and with four people working in parallel it is also what stops two
trainees from conflicting in the same function every sprint.

TODO (junior dev): implement both registries, then write the tests in
`tests/pipeline/test_registry.py`. They need no I/O at all — register two fake
extractors and assert the right one is chosen, including the fallback order.
"""

from __future__ import annotations

from .domain.enums import SourceType
from .ports.extractor import ContentExtractor
from .ports.fetcher import SourceFetcher


class FetcherRegistry:
    """Maps a SourceType to the fetcher that handles it."""

    def __init__(self) -> None:
        self._fetchers: dict[SourceType, SourceFetcher] = {}

    def register(self, fetcher: SourceFetcher) -> None:
        """Register a fetcher under its declared `source_type`.

        TODO: raise on a duplicate registration rather than silently
        overwriting. A silent overwrite means the wrong fetcher runs and the
        symptom shows up three stages later, where it makes no sense.
        """
        raise NotImplementedError

    def get(self, source_type: SourceType) -> SourceFetcher:
        """Return the fetcher for a source type.

        TODO: raise `UnsupportedSourceType` (permanent, no retry) when nothing
        is registered. Do not return None — a None here becomes an
        AttributeError two frames away with no useful message.
        """
        raise NotImplementedError


class ExtractorRegistry:
    """Chooses an extractor by capability, with an ordered fallback chain.

    Priority is what implements the design doc's fallback rules WITHOUT any
    stage knowing about them:

        PDF text layer (priority 100)  -> OCR (priority 50)
        video captions (priority 100)  -> ASR (priority 50)

    The registry tries candidates from highest priority down and picks the
    first whose `can_handle` returns True. The expensive option is simply the
    lowest-priority one, so we only pay for OCR/ASR when the cheap path
    genuinely cannot handle the file.
    """

    def __init__(self) -> None:
        # Highest priority first once sorted.
        self._extractors: list[tuple[int, ContentExtractor]] = []

    def register(self, extractor: ContentExtractor, *, priority: int = 50) -> None:
        """Add an extractor to the chain.

        TODO: insert and keep the list sorted by priority DESCENDING, so
        `select` is a simple first-match scan. Sorting on registration (once)
        beats sorting on every job (thousands of times).
        """
        raise NotImplementedError

    def select(self, content_type: str, content: bytes) -> ContentExtractor:
        """Return the highest-priority extractor that can handle this payload.

        TODO:
          [ ] Scan in priority order, return the first `can_handle` == True.
          [ ] Raise `ExtractionError` (permanent) if none can handle it —
              include the content_type in the message so the failure is
              diagnosable from the log line alone.
          [ ] Log which extractor was chosen at DEBUG. When someone asks "why
              did this scanned PDF come out empty?", the answer is usually
              "the text-layer extractor claimed it", and this log is how you
              find that out in one minute instead of an afternoon.
        """
        raise NotImplementedError
