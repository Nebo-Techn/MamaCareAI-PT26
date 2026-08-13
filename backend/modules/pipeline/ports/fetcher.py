"""
Port: SourceFetcher — download the raw bytes of a resource (PDF 3.1).

One implementation per SourceType: web, video, PDF. The ingest stage never
knows which one it is holding; the registry picks it by source type.

LISKOV SUBSTITUTION — read this before writing an adapter
Every fetcher must be safely usable anywhere the stage expects a fetcher. That
means an adapter may NOT strengthen preconditions or invent new failure modes:
  - it raises FetchError (retryable) or a PermanentError subclass, nothing else
  - it never returns None to mean failure
  - it never calls sys.exit / os._exit, and never blocks forever (always a timeout)
If your video fetcher "works, but the caller has to check a special flag
afterwards", it is not substitutable and the stage will eventually mishandle it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..domain.enums import SourceType


@dataclass(frozen=True, slots=True)
class FetchResult:
    """What a fetcher hands back to the ingest stage.

    `content` is bytes, not a parsed object — parsing is the extractor's job.
    Keeping fetch and parse separate means a parser bug can be fixed and
    re-run against already-downloaded bytes without re-hitting the source.
    """

    content: bytes
    content_type: str                       # MIME type, e.g. "text/html", "application/pdf"
    # Provenance the fetcher learned for free while fetching: final URL after
    # redirects, HTTP headers, video duration, publisher, license string...
    metadata: dict[str, object] = field(default_factory=dict)
    # Set by video fetchers when captions already exist, so we can skip ASR
    # entirely — ASR is the most expensive step in the pipeline (PDF 3.1).
    existing_captions: str | None = None


class SourceFetcher(ABC):
    """Downloads one resource from its origin. Does not parse it."""

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Which source type this fetcher handles. Used by the registry."""

    @abstractmethod
    def fetch(self, source_url: str) -> FetchResult:
        """Download `source_url` and return its bytes plus any metadata.

        Contract every implementation MUST honour:
          - Apply a hard timeout. A hung fetch holds a worker slot hostage.
          - Enforce a max download size. An unbounded read is how one 4GB PDF
            takes down a worker pod.
          - Raise `FetchError` for transient failures (timeout, 5xx, reset).
          - Raise a `PermanentError` for 404 / 403 / unparseable URL.
          - Be safe to call twice with the same URL (no side effects at source).

        TODO (junior dev): before writing any adapter, read
        `adapters/fetchers/web_fetcher.py` — it documents the robots.txt and
        rate-limit rules that apply to every fetcher, not just the web one.
        """
        raise NotImplementedError
