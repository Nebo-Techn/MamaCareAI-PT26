"""
OCR extractor (PDF 3.1: Tesseract or a cloud OCR service) — the fallback for
scanned documents.

Registered at priority 50, so it only runs when `PdfTextExtractor.can_handle`
returns False. That is the whole fallback mechanism: priorities plus an honest
`can_handle`, no if-statements in any stage.

EXPENSIVE AND CPU-HEAVY. Roughly 1-5 seconds per page on Tesseract. A 200-page
scanned guideline is a multi-minute job, which is exactly why OCR/ASR belong in
their own autoscaling worker pool (PDF section 4).

QUALITY WARNING THAT MATTERS FOR THIS PROJECT: OCR output is noisy, and the
noise lands on numbers and units first — the very things that carry meaning in
maternal health guidance. A misread dosage or gestational week is a real harm,
not a typo. Always record an OCR confidence score and flag low-confidence
documents for closer human review. Never let OCR output reach publication
without a human having seen it.
"""

from __future__ import annotations

from ...domain.models import NormalizedDocument
from ...ports.extractor import ContentExtractor


class PdfOcrExtractor(ContentExtractor):
    """Runs OCR over scanned PDFs and images."""

    def __init__(self, *, languages: str = "eng+swa", dpi: int = 300) -> None:
        # Tesseract language packs. "swa" is Swahili — install it, and include
        # the source language too, since we OCR non-Swahili sources as well.
        self._languages = languages
        # 300 DPI is the sweet spot. Lower loses small text; higher costs a lot
        # of CPU for little accuracy gain.
        self._dpi = dpi

    def can_handle(self, content_type: str, content: bytes) -> bool:
        """True for PDFs and images. The last resort in the chain.

        TODO: accept application/pdf and image/*. Because this is the
        lowest-priority extractor, it only ever gets asked after the cheap
        options have declined — so it can afford to be permissive.
        """
        raise NotImplementedError

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict[str, object]
    ) -> NormalizedDocument:
        """OCR each page into text blocks.

        TODO (junior dev):
          [ ] Render each page to an image at self._dpi (PyMuPDF `get_pixmap`).
          [ ] PREPROCESS before OCR — this is where accuracy is won:
              grayscale, deskew, and binarize. Skipping preprocessing on a
              phone-photographed document costs far more accuracy than any
              Tesseract flag will win back.
          [ ] Run Tesseract with the configured languages.
          [ ] CAPTURE PER-WORD CONFIDENCE (`image_to_data`), average it per
              page, and put both the page scores and the document mean into
              metadata. This drives review prioritization.
          [ ] Build TextBlocks. Structure inference is weaker here than with a
              text layer — use font height from the OCR data for headings, and
              accept that most blocks will be paragraphs.
          [ ] PROCESS PAGES IN PARALLEL (a bounded process pool). OCR is
              CPU-bound, so this is a genuine near-linear speedup — but bound
              it, or a 200-page document spawns 200 processes and takes the
              worker down.
          [ ] Raise ExtractionError if the mean confidence is below a floor
              (~60%). Text that bad is not worth a translation call or a
              reviewer's time.
          [ ] Set metadata["ocr"] = True. Reviewers must know they are reading
              OCR output — it changes how carefully they check the numbers.
        """
        raise NotImplementedError
