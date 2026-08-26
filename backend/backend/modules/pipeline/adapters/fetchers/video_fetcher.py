"""
Video fetcher (PDF 3.1) — "pull metadata via platform APIs, fetch existing
captions where available, otherwise queue the audio for ASR (Whisper); isolate
ASR in its own autoscaling worker pool since it is the most expensive step".

THE SINGLE MOST IMPORTANT OPTIMIZATION IN THIS PIPELINE
Always check for existing captions first. A YouTube video with human-authored
captions gives better text than Whisper would produce, for free, in under a
second — versus minutes of GPU time. Do this before downloading a single byte
of audio.

Caption quality order, best first:
  1. Human-authored captions in the source language  <- best text available
  2. Auto-generated captions                          <- usually beats nothing
  3. ASR on the audio                                 <- expensive; last resort

Note that (2) is a judgement call: auto-captions are already machine output, so
translating them means machine-translating a machine transcript, and errors
compound. For MATERNAL HEALTH CONTENT, where a misheard dosage or symptom is a
real harm, prefer running our own ASR over trusting platform auto-captions, and
flag anything caption-derived for closer human review. Record which path was
used in metadata so reviewers know what they are looking at.
"""

from __future__ import annotations

from ...domain.enums import SourceType
from ...ports.fetcher import FetchResult, SourceFetcher


class VideoFetcher(SourceFetcher):
    """Fetches video metadata plus captions, or the audio track for ASR."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_bytes: int,
        prefer_captions: bool = True,
        trust_auto_captions: bool = False,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._prefer_captions = prefer_captions
        # Default False for health content — see the module docstring.
        self._trust_auto_captions = trust_auto_captions

    @property
    def source_type(self) -> SourceType:
        return SourceType.VIDEO

    def fetch(self, source_url: str) -> FetchResult:
        """Fetch captions if available, otherwise the audio track.

        TODO (junior dev) — implement in this order:

          1. METADATA via the platform API (yt-dlp covers most platforms):
             title, description, duration, upload date, channel, LICENCE.
             The licence field matters — much of YouTube is not republishable,
             and the compliance gate reads what we record here.

          2. DURATION GUARD before downloading anything:
             refuse videos over a configured max (start around 2 hours).
             One 6-hour conference recording can occupy an ASR worker for
             an hour and starve everything behind it.

          3. CAPTIONS FIRST:
                 - human-authored in the source language -> use it
                 - auto-generated -> use ONLY if trust_auto_captions
                 Return FetchResult(existing_captions=<text>, ...).
             The extract stage sees this and skips ASR entirely.

          4. NO USABLE CAPTIONS -> download AUDIO ONLY.
             Audio-only (m4a/opus), never the video stream. We need the
             speech; the pixels are 95% of the bytes and 0% of the value.

          5. RETURN with `content` = audio bytes and a metadata flag telling
             the extract stage that ASR is required. The ASR extractor picks it
             up via the registry's priority chain.

        WHY THIS FETCHER MAY BE SLOW: it is doing network I/O against a
        third-party platform with its own rate limits. Expect 429s, honour
        Retry-After, and never let ASR work share a worker pool with cheap
        stages — that is the whole point of stage isolation.
        """
        raise NotImplementedError
