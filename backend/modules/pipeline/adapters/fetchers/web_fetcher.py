"""
Web fetcher (PDF 3.1) — "a crawler/fetcher service (Scrapy, or Playwright for
JavaScript-heavy pages) pulls HTML, respects robots.txt, and pushes raw HTML to
object storage".

TWO STRATEGIES, AND WHEN EACH IS RIGHT
  - Plain HTTP (httpx): fast, cheap, works for most static health-ministry and
    NGO pages. START HERE.
  - Playwright: renders JavaScript. Necessary for SPA-style sites, but it costs
    a browser process per page — roughly 100x the resources. Use it only when
    the plain fetch demonstrably returns an empty shell.

Do not reach for Playwright by default. Measure first: fetch the page plainly,
and if the extracted text is near-empty, fall back. That fallback is a
priority-ordered registry decision, not an if-statement in this file.

ROBOTS.TXT IS NOT OPTIONAL. `settings.respect_robots_txt` defaults to True and
must stay True. We are building a public-health resource for a named
organization; ignoring robots.txt is both an ethical and a reputational
problem, and it is exactly the kind of thing that gets the project's access
revoked at the worst moment.
"""

from __future__ import annotations

from ...domain.enums import SourceType
from ...ports.fetcher import FetchResult, SourceFetcher


class WebFetcher(SourceFetcher):
    """Fetches HTML over plain HTTP."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_bytes: int,
        user_agent: str,
        respect_robots: bool = True,
    ) -> None:
        # TODO: create ONE httpx.Client here and reuse it. A new client per
        # request throws away connection pooling and TLS session reuse, which
        # is most of the cost of an HTTPS request.
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._user_agent = user_agent
        self._respect_robots = respect_robots

    @property
    def source_type(self) -> SourceType:
        return SourceType.WEB

    def fetch(self, source_url: str) -> FetchResult:
        """Download a web page.

        TODO (junior dev) — implement in this order:

          1. ROBOTS.TXT CHECK (when enabled):
                 urllib.robotparser, CACHED PER DOMAIN.
             Re-fetching robots.txt before every page doubles your request
             count against the site you are trying to be polite to.
             Disallowed -> raise PermanentError, and record the reason in
             metadata so the compliance gate can see it later.

          2. RATE LIMIT: minimum delay between requests to the same domain
             (start at ~1 second). Track last-request-time per domain.

          3. GET with timeout, following redirects, sending the User-Agent.

          4. ENFORCE MAX SIZE WHILE STREAMING:
                 for chunk in response.iter_bytes(): ...
             Abort as soon as the accumulated size exceeds max_bytes.

          5. MAP STATUS CODES ONTO OUR ERROR TYPES:
                 2xx           -> success
                 429           -> ProviderRateLimited (honour Retry-After)
                 5xx / timeout -> FetchError          (retryable)
                 404 / 403     -> PermanentError      (do not retry)

          6. COLLECT METADATA WHILE IT IS FREE:
                 final URL after redirects, Content-Type, Last-Modified, ETag,
                 <title>, and any licence/copyright meta tags.
             That last one feeds the compliance gate. Capturing it now costs
             nothing; going back for it months later means re-fetching every page.

          7. RETURN FetchResult(content=<raw bytes>, ...).
             Raw HTML — do NOT parse here. Parsing is the extractor's job, and
             keeping them separate means a parser fix can be re-run against
             already-downloaded bytes.
        """
        raise NotImplementedError
