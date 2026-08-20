"""
Caption extractor — turns existing video captions into a NormalizedDocument.

The cheap video path (priority 100). If `VideoFetcher` found captions, this
extractor handles the resource and ASR never runs. That is minutes of GPU time
saved per video, which over a corpus is the difference between a pipeline that
runs on free tier and one that does not.

CAPTIONS ARE NOT PROSE. They arrive as timed fragments broken at display
boundaries, not sentence boundaries:

    00:01 "Habari, leo tutazungumza"
    00:03 "kuhusu afya ya mama"

Translating those fragments individually produces garbage, because neither
fragment is a complete clause. The core job of this file is reassembling
fragments into sentences BEFORE anything downstream sees them.
"""

from __future__ import annotations

from ...domain.models import NormalizedDocument
from ...ports.extractor import ContentExtractor


class CaptionExtractor(ContentExtractor):
    """Parses WebVTT/SRT captions into readable, timestamped blocks."""

    def can_handle(self, content_type: str, content: bytes) -> bool:
        """True when the resource carries captions.

        TODO: detect "text/vtt", "application/x-subrip", or a WEBVTT header in
        the first bytes. The extract stage passes captions through as the
        content when `FetchResult.existing_captions` was set.
        """
        raise NotImplementedError

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict[str, object]
    ) -> NormalizedDocument:
        """Parse captions and reassemble them into sentences.

        TODO (junior dev):
          [ ] Parse WebVTT/SRT (webvtt-py, or a small parser — the format is
              simple enough to handle directly).
          [ ] DE-DUPLICATE ROLLING CAPTIONS. Auto-generated captions repeat
              overlapping text on consecutive cues; naive concatenation
              produces every phrase two or three times.
          [ ] MERGE FRAGMENTS INTO SENTENCES using punctuation and gap
              duration (a pause over ~2s usually means a new thought). This is
              the most important step in the file — get it wrong and every
              downstream translation is fragment soup.
          [ ] Build one TextBlock per reassembled sentence/paragraph, keeping
              `start_seconds`/`end_seconds` from the first and last cue.
              Timestamps let a reviewer jump to the exact moment in the video
              to check a translation — worth preserving.
          [ ] Strip speaker labels and sound annotations ("[music]",
              ">> SPEAKER:") — they are not content and should not be
              translated.
          [ ] Record metadata["caption_source"] = "human" | "auto". Reviewers
              must know whether they are reviewing a human transcript or a
              machine one, since auto-captions carry their own error rate.
        """
        raise NotImplementedError
