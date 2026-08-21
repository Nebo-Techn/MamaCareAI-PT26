"""
HTML extractor — web page to NormalizedDocument.

THE HARD PART IS NOT PARSING HTML. IT IS DECIDING WHAT IS CONTENT.
A health-ministry page is maybe 15% article and 85% navigation, cookie banner,
sidebar, related links, and footer. Feed all of it downstream and you pay to
translate a cookie banner into Swahili and then ask a human to review it.

Use a readability-style main-content extractor (trafilatura is the strongest
option for this and handles multilingual pages well) rather than hand-written
BeautifulSoup selectors. Hand-written selectors work on the one site you tested
and break on the next, and you will be maintaining forty of them by Sprint 4.

TABLES (see docs/DECISIONS.md): health documents put dosages and schedules in
tables, and flattening them destroys the row/column meaning that carries the
safety-critical information. Each `<tr>` is serialized as a `list_item` with
cells joined by " | ", and the document is flagged in `source_metadata` as
containing tables so reviewers look closely.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

import chardet
import trafilatura

from ...domain.errors import ExtractionError
from ...domain.models import NormalizedDocument, TextBlock
from ...ports.extractor import ContentExtractor

# Zero-width / formatting characters that should never appear in extracted text.
_ZERO_WIDTH = "\u200b\u200c\u200d\ufeff"
_WHITESPACE_RE = re.compile(r"\s+")
_CHARSET_IN_HTML_RE = re.compile(
    rb'<meta[^>]+charset\s*=\s*["\']?\s*([a-zA-Z0-9_\-]+)',
    re.IGNORECASE,
)
_BLOCK_TAG_TO_KIND = {
    "head": "heading",
    "p": "paragraph",
    "quote": "paragraph",
    "code": "paragraph",
    "item": "list_item",
    "row": "list_item",
    "figcaption": "caption",
    "figure": "caption",
}

# Minimum total characters across blocks. Below this the extraction is
# boilerplate leftovers ("cookie", "accept", a lone nav link) masquerading as
# content — an empty extraction is a failure, not a success with no content.
_MIN_EXTRACTED_CHARS = 40


class HtmlExtractor(ContentExtractor):
    """Extracts the main article content from an HTML page."""

    def can_handle(self, content_type: str, content: bytes) -> bool:
        """True for HTML payloads.

        Servers mislabel content, so do not trust the header alone — also sniff
        for an opening "<html" / "<!doctype html" tag in the first ~1KB.
        """
        if "text/html" in (content_type or "").lower():
            return True
        head = content[:1024].lower()
        return b"<html" in head or b"<!doctype html" in head

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict[str, object]
    ) -> NormalizedDocument:
        """Turn HTML into structured blocks.

        Order of operations matters:
          1. decode correctly (HTTP header charset -> <meta> tag -> chardet)
          2. let trafilatura drop nav/header/footer/cookie banners
          3. build TextBlocks preserving structure, in document order
          4. serialize table rows, flag the document as containing tables
          5. metadata from trafilatura (title, author, date, canonical, lang)
          6. normalize (NFC, collapse whitespace, strip zero-width)
          7. raise ExtractionError on empty / below-quality extraction
        """
        html_text = self._decode(content, metadata)

        extracted = trafilatura.bare_extraction(
            html_text,
            output_format="python",
            with_metadata=True,
        )
        if extracted is None or extracted.body is None:
            raise ExtractionError(
                f"No extractable content in {resource_id}",
                resource_id=resource_id,
            )

        blocks, contains_tables = self._build_blocks(extracted.body)

        if not blocks:
            raise ExtractionError(
                f"Extraction of {resource_id} produced no usable blocks",
                resource_id=resource_id,
            )
        total_chars = sum(len(block.text) for block in blocks)
        if total_chars < _MIN_EXTRACTED_CHARS:
            raise ExtractionError(
                f"Extraction of {resource_id} below quality bar "
                f"({total_chars} chars < {_MIN_EXTRACTED_CHARS})",
                resource_id=resource_id,
            )

        source_metadata = dict(metadata)
        if extracted.language:
            source_metadata["language"] = extracted.language
        if contains_tables:
            source_metadata["contains_tables"] = True

        return NormalizedDocument(
            resource_id=resource_id,
            title=extracted.title,
            author=extracted.author,
            published_date=self._parse_date(extracted.date),
            blocks=tuple(blocks),
            source_metadata=source_metadata,
        )

    # --- helpers ------------------------------------------------------------

    @staticmethod
    def _decode(content: bytes, metadata: dict[str, object]) -> str:
        charset = HtmlExtractor._charset_from_header(
            str(metadata.get("content_type", ""))
        )
        if charset is None:
            charset = HtmlExtractor._charset_from_html(content)
        if charset is None:
            detected = chardet.detect(content)
            charset = detected.get("encoding")
        try:
            return content.decode(charset or "utf-8")
        except (LookupError, UnicodeDecodeError):
            return content.decode("utf-8", errors="replace")

    @staticmethod
    def _charset_from_header(content_type: str) -> str | None:
        match = re.search(
            r"charset\s*=\s*([a-zA-Z0-9_\-]+)", content_type, re.IGNORECASE
        )
        return match.group(1) if match else None

    @staticmethod
    def _charset_from_html(content: bytes) -> str | None:
        match = _CHARSET_IN_HTML_RE.search(content[:4096])
        return match.group(1).decode("ascii") if match else None

    @staticmethod
    def _build_blocks(
        body,
    ) -> tuple[list[TextBlock], bool]:
        """Walk trafilatura's article tree and emit TextBlocks in order."""
        blocks: list[TextBlock] = []
        contains_tables = False
        order = 0
        for el in body.iter():
            kind = _BLOCK_TAG_TO_KIND.get(el.tag)
            if kind is None:
                continue
            if el.tag == "row":
                contains_tables = True
                text = HtmlExtractor._row_to_text(el)
            elif el.tag == "figure":
                # trafilatura usually drops figures; only keep one if it has text.
                text = HtmlExtractor._text_of(el)
            else:
                text = HtmlExtractor._text_of(el)
            text = HtmlExtractor._normalize(text)
            if not text:
                continue
            blocks.append(TextBlock(order=order, kind=kind, text=text))
            order += 1
        return blocks, contains_tables

    @staticmethod
    def _row_to_text(row) -> str:
        cells = [HtmlExtractor._text_of(cell) for cell in row]
        return " | ".join(c for c in cells if c)

    @staticmethod
    def _text_of(el) -> str:
        return "".join(el.itertext()).strip()

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        text = text.translate(str.maketrans("", "", _ZERO_WIDTH))
        return _WHITESPACE_RE.sub(" ", text).strip()

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
