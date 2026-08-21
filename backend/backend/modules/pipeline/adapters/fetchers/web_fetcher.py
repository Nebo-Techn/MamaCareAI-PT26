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

import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx

from ...domain.enums import SourceType
from ...domain.errors import FetchError, PermanentError, ProviderRateLimited
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
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._user_agent = user_agent
        self._respect_robots = respect_robots
        self._client = httpx.Client(
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
            transport=transport,
        )
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request_time: dict[str, float] = {}
        self._min_delay_seconds = 1.0

    @property
    def source_type(self) -> SourceType:
        return SourceType.WEB

    def _get_robots_parser(self, domain: str) -> urllib.robotparser.RobotFileParser:
        if domain not in self._robots_cache:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(f"https://{domain}/robots.txt")
            try:
                parser.read()
            except Exception:  # noqa: BLE001, S110 - intentional: fail open
                # An unreachable robots.txt must not block every fetch on a
                # domain that has no robots.txt at all.
                pass
            self._robots_cache[domain] = parser
        return self._robots_cache[domain]

    def _respect_rate_limit(self, domain: str) -> None:
        last = self._last_request_time.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < self._min_delay_seconds:
                time.sleep(self._min_delay_seconds - elapsed)
        self._last_request_time[domain] = time.monotonic()

    def fetch(self, source_url: str) -> FetchResult:
        domain = urlparse(source_url).netloc

        if self._respect_robots and domain:
            parser = self._get_robots_parser(domain)
            if not parser.can_fetch(self._user_agent, source_url):
                raise PermanentError(f"robots.txt disallows fetching {source_url}")

        self._respect_rate_limit(domain)

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
                metadata: dict[str, object] = {
                    "final_url": str(response.url),
                    "content_type": response.headers.get("content-type", ""),
                    "last_modified": response.headers.get("last-modified"),
                    "etag": response.headers.get("etag"),
                }

                return FetchResult(
                    content=content,
                    content_type=response.headers.get("content-type", "text/html"),
                    metadata=metadata,
                )
        except httpx.TimeoutException as exc:
            raise FetchError(f"Timeout fetching {source_url}") from exc
        except httpx.TransportError as exc:
            raise FetchError(f"Connection error fetching {source_url}") from exc
