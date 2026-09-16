"""
PDF fetcher (PDF 3.1) — "accept by upload or URL".

The simplest of the three fetchers: PDFs are static files. The complexity in
the PDF path is entirely in EXTRACTION (text layer vs scanned/OCR), not here.

TWO ENTRY POINTS
  - By URL: download it (this class).
  - By upload: the API route writes the bytes straight to object storage and
    creates the resource already in FETCHED status, skipping this stage. See
    `api/routes_pipeline.py`. Do not try to force an uploaded file through a
    fetcher — there is nothing to fetch.
"""

from __future__ import annotations

import httpx
import pymupdf

from ...domain.enums import SourceType
from ...domain.errors import (
    ExtractionError,
    FetchError,
    PermanentError,
    ProviderRateLimited,
)
from ...ports.fetcher import FetchResult, SourceFetcher


class PdfFetcher(SourceFetcher):
    """Downloads a PDF by URL."""

    def __init__(
        self, *, timeout_seconds: float, max_bytes: int, user_agent: str
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._user_agent = user_agent
        self._client = httpx.Client(
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    @property
    def source_type(self) -> SourceType:
        return SourceType.PDF

    def fetch(self, source_url: str) -> FetchResult:
        """Download a PDF file.

        TODO (junior dev):
          [ ] Stream the download, enforcing max_bytes as you read. Health
              guidelines PDFs are routinely 50-100MB — this limit will be hit
              in real use, so make the error message say so clearly rather than
              just "too large".
          [ ] VERIFY IT IS ACTUALLY A PDF: check the magic bytes (%PDF-) rather
              than trusting the Content-Type header or the .pdf extension.
              Servers mislabel files constantly, and an HTML error page saved
              as "guidelines.pdf" fails confusingly three stages later.
          [ ] Detect encrypted/password-protected PDFs early and raise
              ExtractionError (permanent). Retrying a password prompt five
              times helps nobody.
          [ ] Capture metadata: Content-Length, Last-Modified, and the PDF's
              own /Title, /Author, /CreationDate if cheaply readable.
          [ ] Same status-code mapping as the web fetcher (5xx retryable,
              404/403 permanent).
        """
        try:
            with self._client.stream("GET", source_url) as response:
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_after_seconds = float(retry_after) if retry_after else None
                    raise ProviderRateLimited(
                        f"Rate limited fetching {source_url}",
                        retry_after_seconds=retry_after_seconds,
                    )

                if response.status_code in (404, 403):
                    raise PermanentError(
                        f"{response.status_code} fetching {source_url}"
                    )

                if response.status_code >= 500:
                    raise FetchError(f"{response.status_code} fetching {source_url}")

                response.raise_for_status()

                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > self._max_bytes:
                        raise PermanentError(
                            f"{source_url} exceeded max_bytes={self._max_bytes}"
                        )
                    chunks.append(chunk)

                content = b"".join(chunks)
                if not content.startswith(b"%PDF-"):
                    raise PermanentError(f"{source_url} did not return a PDF")

                metadata: dict[str, object] = {
                    "final_url": str(response.url),
                    "content_type": response.headers.get("content-type", ""),
                    "last_modified": response.headers.get("last-modified"),
                    "etag": response.headers.get("etag"),
                    "content_length": response.headers.get("content-length"),
                }

                try:
                    with pymupdf.open(stream=content, filetype="pdf") as document:
                        if document.is_encrypted:
                            raise ExtractionError(
                                f"Encrypted PDF cannot be processed: {source_url}"
                            )

                        pdf_metadata = document.metadata
                        for key, metadata_key in (
                            ("title", "title"),
                            ("author", "author"),
                            ("creationDate", "creation_date"),
                        ):
                            value = pdf_metadata.get(key)
                            if value:
                                metadata[metadata_key] = value
                except pymupdf.FileDataError as exc:
                    raise ExtractionError(
                        f"Unable to inspect PDF: {source_url}"
                    ) from exc

                return FetchResult(
                    content=content,
                    content_type=response.headers.get("content-type")
                    or "application/pdf",
                    metadata=metadata,
                    existing_captions=None,
                )
        except httpx.TimeoutException as exc:
            raise FetchError(f"Timeout fetching {source_url}") from exc
        except httpx.TransportError as exc:
            raise FetchError(f"Connection error fetching {source_url}") from exc
