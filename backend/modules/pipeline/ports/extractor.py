"""
Port: ContentExtractor — raw bytes in, NormalizedDocument out (PDF 3.2).

This is the layer that hides source-type complexity from everything
downstream. HTML, PDF text layers, OCR output, and video transcripts all leave
here in the same shape.

OPEN/CLOSED IN ACTION
Supporting a new format (say, .docx) means adding one new extractor class and
one registry line. It must require zero edits to `stages/extract.py`. If you
find yourself adding an `elif` to the extract stage, the design has been
violated — push the difference down into an adapter instead.

CHAIN OF FALLBACK (PDF 3.1)
Some sources need more than one attempt in order: PDF text layer first, OCR
only if the text layer comes back empty; video captions first, ASR only if
there are none. That ordering is expressed by `can_handle` + priority in the
registry, not by if-statements in the stage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.models import NormalizedDocument


class ContentExtractor(ABC):
    """Turns fetched bytes into the common normalized schema."""

    @abstractmethod
    def can_handle(self, content_type: str, content: bytes) -> bool:
        """Return True if this extractor can process the given payload.

        Cheap check only — sniff the MIME type and at most the first few bytes.
        Do NOT parse the whole document here; the registry may call this on
        several extractors before choosing one.

        TODO: this is what makes the fallback chain work. The PDF text-layer
        extractor should return False for a scanned PDF with no text layer, so
        the registry falls through to the OCR extractor automatically.
        """
        raise NotImplementedError

    @abstractmethod
    def extract(
        self,
        resource_id: str,
        content: bytes,
        *,
        metadata: dict[str, object],
    ) -> NormalizedDocument:
        """Produce a NormalizedDocument from raw bytes.

        Contract every implementation MUST honour:
          - Preserve document STRUCTURE as TextBlocks (headings vs paragraphs).
            Do not return one giant paragraph — the review UI and the
            translation chunker both depend on this structure (PDF 3.4).
          - Preserve reading order in `TextBlock.order`, starting at 0.
          - Strip boilerplate (nav bars, cookie banners, page headers/footers)
            but never strip content.
          - Normalize Unicode (NFC) and fix mojibake. Swahili text carrying
            broken encodings poisons both translation and search.
          - Raise `ExtractionError` when no usable text can be produced —
            never return a document with zero blocks and call it success.
        """
        raise NotImplementedError
