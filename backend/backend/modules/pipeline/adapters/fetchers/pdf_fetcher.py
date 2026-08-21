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

from ...domain.enums import SourceType
from ...ports.fetcher import FetchResult, SourceFetcher


class PdfFetcher(SourceFetcher):
    """Downloads a PDF by URL."""

    def __init__(
        self, *, timeout_seconds: float, max_bytes: int, user_agent: str
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._user_agent = user_agent

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
        raise NotImplementedError
