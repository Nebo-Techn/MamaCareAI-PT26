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
"""

from __future__ import annotations

from ...domain.models import NormalizedDocument
from ...ports.extractor import ContentExtractor


class HtmlExtractor(ContentExtractor):
    """Extracts the main article content from an HTML page."""

    def can_handle(self, content_type: str, content: bytes) -> bool:
        """True for HTML payloads.

        TODO: check content_type for "text/html" OR sniff for "<html" in the
        first ~1KB. Servers mislabel content, so do not trust the header alone.
        """
        raise NotImplementedError

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict[str, object]
    ) -> NormalizedDocument:
        """Turn HTML into structured blocks.

        TODO (junior dev) — implement in this order:

          1. DECODE CORRECTLY. Charset from the HTTP header, then the <meta>
             tag, then chardet as a last resort. Getting this wrong is how
             Swahili text arrives as "Ã¤" soup that survives all the way into
             the vector store.

          2. MAIN CONTENT EXTRACTION (trafilatura or readability-lxml). Drop
             nav, header, footer, aside, cookie banners, "related articles".

          3. BUILD TEXTBLOCKS, PRESERVING STRUCTURE:
                 <h1>-<h6>       -> kind="heading"
                 <p>             -> kind="paragraph"
                 <li>            -> kind="list_item"
                 <figcaption>    -> kind="caption"
             Set `order` in document order, starting at 0.
             DO NOT flatten to one string. Health guidance is
             heavily structured ("Danger signs:" followed by a list), and a
             reviewer comparing a flattened wall of text to the original cannot
             do their job.

          4. TABLES: a real decision, not an oversight. Health documents put
             dosages and schedules in tables, and flattening them destroys the
             row/column meaning that carries the safety-critical information.
             Start by serializing each row as a list_item and FLAGGING the
             document in metadata as containing tables, so reviewers look
             closely. Log a proper decision in docs/DECISIONS.md.

          5. METADATA: <title>, author/byline, published date (JSON-LD or
             <meta> tags), canonical URL, language attribute if present.

          6. NORMALIZE: unicodedata.normalize("NFC", ...), collapse runs of
             whitespace, strip zero-width characters.

          7. Raise ExtractionError if what is left is below the quality bar —
             an empty extraction is a failure, not a success with no content.
        """
        raise NotImplementedError
