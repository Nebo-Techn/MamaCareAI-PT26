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

import re
import unicodedata
from datetime import UTC, datetime, timedelta, timezone

import pymupdf

from ...domain.errors import ExtractionError
from ...domain.models import NormalizedDocument, TextBlock
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
        if not content.startswith(b"%PDF-"):
            return False

        try:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                if document.is_encrypted:
                    return False

                page_count = len(document)
                if page_count == 0:
                    return False
                if page_count <= 2:
                    sample_indexes = range(page_count)
                else:
                    sample_indexes = (0, page_count // 2, page_count - 1)

                total_chars = sum(
                    len(document[index].get_text()) for index in sample_indexes
                )
                average_chars = total_chars / len(sample_indexes)
                return average_chars > self._min_chars_per_page
        except (pymupdf.FileDataError, RuntimeError, ValueError):
            return False

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
        def normalize(text: str) -> str:
            return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()

        def parse_creation_date(value: object) -> datetime | None:
            if not isinstance(value, str) or not value:
                return None
            value = value.removeprefix("D:")
            match = re.match(
                r"(?P<date>\d{4}(?:\d{2}){0,5})"
                r"(?P<tz>Z|[+-]\d{2}'?\d{2}'?)?$",
                value,
            )
            if not match:
                return None
            date_value = match.group("date")
            date_value = date_value.ljust(14, "0")
            try:
                parsed = datetime.strptime(
                    date_value, "%Y%m%d%H%M%S"
                ).replace(tzinfo=UTC)
            except ValueError:
                return None
            offset = match.group("tz")
            if offset in (None, "Z"):
                return parsed.replace(tzinfo=UTC)
            offset_match = re.match(r"([+-])(\d{2})'?(\d{2})'?", offset)
            if offset_match is None:
                return None
            minutes = int(offset_match.group(2)) * 60 + int(offset_match.group(3))
            if offset_match.group(1) == "-":
                minutes = -minutes
            return parsed.replace(tzinfo=timezone(timedelta(minutes=minutes)))

        try:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                if document.is_encrypted:
                    raise ExtractionError(
                        f"Encrypted PDF cannot be extracted: {resource_id}",
                        resource_id=resource_id,
                    )

                pages: list[list[dict[str, object]]] = []
                page_line_counts: dict[tuple[str, str], set[int]] = {}
                font_sizes: list[float] = []

                for page_number, page in enumerate(document):
                    page_data = page.get_text("dict")
                    lines: list[dict[str, object]] = []
                    page_height = float(page.rect.height)
                    for block in page_data.get("blocks", []):
                        if block.get("type") != 0:
                            continue
                        for line in block.get("lines", []):
                            spans = [
                                span
                                for span in line.get("spans", [])
                                if normalize(str(span.get("text", "")))
                            ]
                            if not spans:
                                continue
                            text = normalize("".join(str(span.get("text", "")) for span in spans))
                            if not text:
                                continue
                            bbox = line.get("bbox", (0, 0, 0, 0))
                            sizes = [
                                float(span.get("size", 0.0))
                                for span in spans
                                if span.get("size") is not None
                            ]
                            size = max(sizes, default=0.0)
                            font_names = " ".join(
                                str(span.get("font", "")).lower() for span in spans
                            )
                            flags = max(
                                int(span.get("flags", 0)) for span in spans
                            )
                            line_info = {
                                "text": text,
                                "x": float(bbox[0]),
                                "y": float(bbox[1]),
                                "bottom": float(bbox[3]),
                                "width": float(page.rect.width),
                                "height": page_height,
                                "size": size,
                                "bold": bool(flags & 16) or "bold" in font_names,
                                "italic": bool(flags & 2) or "italic" in font_names,
                            }
                            lines.append(line_info)
                            if size:
                                font_sizes.append(size)
                            zone = "top" if float(bbox[1]) <= page_height * 0.15 else "body"
                            if float(bbox[3]) >= page_height * 0.85:
                                zone = "bottom"
                            if zone != "body":
                                page_line_counts.setdefault((text, zone), set()).add(
                                    page_number
                                )
                    pages.append(lines)

                repeated_furniture = {
                    key
                    for key, page_numbers in page_line_counts.items()
                    if len(page_numbers) >= 2
                }

                body_size = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 0.0
                ordered_lines: list[dict[str, object]] = []
                for page_lines in pages:
                    filtered = [
                        line
                        for line in page_lines
                        if (
                            line["text"],
                            "top" if line["y"] <= line["height"] * 0.15 else "bottom"
                            if line["bottom"] >= line["height"] * 0.85
                            else "body",
                        )
                        not in repeated_furniture
                    ]
                    if not filtered:
                        continue
                    min_x = min(float(line["x"]) for line in filtered)
                    max_x = max(float(line["x"]) for line in filtered)
                    wide_gap = max_x - min_x > float(filtered[0]["width"]) * 0.35
                    if wide_gap:
                        midpoint = (min_x + max_x) / 2
                        left = sorted(
                            (line for line in filtered if line["x"] <= midpoint),
                            key=lambda line: (line["y"], line["x"]),
                        )
                        right = sorted(
                            (line for line in filtered if line["x"] > midpoint),
                            key=lambda line: (line["y"], line["x"]),
                        )
                        ordered_lines.extend(left + right)
                    else:
                        ordered_lines.extend(
                            sorted(filtered, key=lambda line: (line["y"], line["x"]))
                        )

                blocks: list[TextBlock] = []
                paragraph: list[dict[str, object]] = []

                def flush_paragraph() -> None:
                    if not paragraph:
                        return
                    text = str(paragraph[0]["text"])
                    for line in paragraph[1:]:
                        next_text = str(line["text"])
                        if text.endswith("-") and next_text[:1].islower():
                            text = text[:-1] + next_text
                        else:
                            text = f"{text} {next_text}"
                    text = normalize(text)
                    if text:
                        blocks.append(
                            TextBlock(order=len(blocks), kind="paragraph", text=text)
                        )
                    paragraph.clear()

                for line in ordered_lines:
                    text = str(line["text"])
                    is_heading = (
                        body_size > 0
                        and float(line["size"]) >= body_size * 1.25
                        and (bool(line["bold"]) or float(line["size"]) >= body_size * 1.4)
                        and len(text) <= 180
                    )
                    list_item = bool(re.match(r"^(?:[-*•]|\d+[.)])\s+", text))
                    caption = bool(
                        re.match(r"^(?:figure|table)\s+\d+", text, re.IGNORECASE)
                    )
                    if is_heading or list_item or caption:
                        flush_paragraph()
                        kind = "heading" if is_heading else "list_item" if list_item else "caption"
                        blocks.append(TextBlock(order=len(blocks), kind=kind, text=text))
                    else:
                        paragraph.append(line)
                flush_paragraph()

                if not blocks:
                    raise ExtractionError(
                        f"Extraction of {resource_id} produced no usable blocks",
                        resource_id=resource_id,
                    )

                pdf_metadata = document.metadata
                source_metadata = dict(metadata)
                source_metadata["page_count"] = len(document)
                title = pdf_metadata.get("title") or None
                author = pdf_metadata.get("author") or None
                creation_date = pdf_metadata.get("creationDate")
                if title:
                    source_metadata["title"] = title
                if author:
                    source_metadata["author"] = author
                if creation_date:
                    source_metadata["creation_date"] = creation_date

                return NormalizedDocument(
                    resource_id=resource_id,
                    title=title,
                    author=author,
                    published_date=parse_creation_date(creation_date),
                    blocks=tuple(blocks),
                    source_metadata=source_metadata,
                )
        except ExtractionError:
            raise
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise ExtractionError(
                f"Unable to extract PDF content for {resource_id}",
                resource_id=resource_id,
            ) from exc
