"""
PDF text-layer extractor (PDF 3.1: PyMuPDF).

THE CHEAP PATH. A PDF with a real text layer needs no OCR at all — extraction
is milliseconds and the text is exact. Registered at priority 100 so it always
gets first refusal.

ITS MOST IMPORTANT JOB IS KNOWING WHEN TO SAY NO.
`can_handle` must return False for scanned PDFs so the registry falls through
to OCR. An over-eager `can_handle` that returns True for a scanned document
extracts 20 characters of page-number noise, OCR never runs, and the document
fails the quality gate for reasons nobody can see. Be honest about declining.
"""

from __future__ import annotations

from ...domain.models import NormalizedDocument
from ...ports.extractor import ContentExtractor


class PdfTextExtractor(ContentExtractor):
    """Extracts embedded text from PDFs that have a text layer."""

    def __init__(self, *, min_chars_per_page: float = 100.0) -> None:
        # Below this average, the PDF is treated as scanned and handed to OCR.
        # Tune it on real documents from the source register.
        self._min_chars_per_page = min_chars_per_page

    def can_handle(self, content_type: str, content: bytes) -> bool:
        """True only for PDFs with a usable text layer.

        TODO (junior dev):
          [ ] Check the %PDF- magic bytes.
          [ ] Open with PyMuPDF and sample the FIRST FEW PAGES ONLY (3 is
              plenty) — do not extract the entire document just to decide.
          [ ] Return True only if average characters per sampled page exceeds
              `min_chars_per_page`.
          [ ] Watch for the mixed case: a born-digital cover page followed by
              scanned content. Sampling only page 1 gets this wrong. Sample
              from across the document, not just the front.
          [ ] Never raise from `can_handle` — a corrupt file returns False and
              lets the chain continue to the next candidate.
        """
        raise NotImplementedError

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict[str, object]
    ) -> NormalizedDocument:
        """Extract structured text from the PDF's text layer.

        TODO (junior dev):
          [ ] Use PyMuPDF `page.get_text("dict")` — it gives font size, weight,
              and position per span, which is what lets you infer structure.
          [ ] INFER HEADINGS from font size relative to the document's body
              size (a span notably larger/bolder than the median = heading).
              PDFs have no semantic markup, so this heuristic is all there is.
          [ ] STRIP REPEATED HEADERS/FOOTERS: text appearing at the same
              position on most pages is page furniture, not content. Detect and
              drop it, or every translated document is peppered with the
              publication title and a page number.
          [ ] HANDLE MULTI-COLUMN LAYOUTS. Naive extraction reads straight
              across both columns and interleaves two sentences into nonsense.
              Sort blocks by (column, y-position), not by y alone. WHO and
              ministry guidance PDFs are frequently two-column — this will
              come up.
          [ ] Join hyphenated line breaks ("preg-\\nnancy" -> "pregnancy").
          [ ] Merge lines into paragraphs; a PDF line break is usually not a
              paragraph break.
          [ ] Metadata: PDF /Title, /Author, /CreationDate, page count.
          [ ] NFC normalize; PDF text is a common source of odd Unicode.
        """
        raise NotImplementedError
