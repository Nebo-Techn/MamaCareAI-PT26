"""
ASR extractor (PDF 3.1: Whisper) — transcribing audio when there are no captions.

PRIORITY 50: the last resort, and THE MOST EXPENSIVE STEP IN THE ENTIRE
PIPELINE. Everything about how this file is deployed follows from that:

  - It must run in its OWN worker pool, so a queue of videos cannot starve PDF
    or web processing. (PDF section 4: "a video ASR failure never blocks PDF
    processing".)
  - That pool autoscales separately and is the only one that needs GPU.
  - Its queue depth is worth its own dashboard panel — it is the stage most
    likely to develop a backlog.

MODEL SIZE IS A REAL TRADE-OFF, NOT A DETAIL
  tiny/base   : fast, poor on accented and non-English speech
  small/medium: the practical sweet spot for Swahili
  large-v3    : best quality, needs a GPU to be usable

Whisper's Swahili performance is noticeably weaker than its English
performance. For MATERNAL HEALTH CONTENT, mishearing a number or a drug name is
a genuine safety issue — so treat ASR output as lower-trust than any other
extraction path, record confidence, and make sure reviewers know what they are
reading.
"""

from __future__ import annotations

from ...domain.models import NormalizedDocument
from ...ports.extractor import ContentExtractor


class AsrExtractor(ContentExtractor):
    """Transcribes audio to text using Whisper."""

    def __init__(self, *, model_size: str = "small", device: str = "cpu") -> None:
        # TODO: load the model ONCE, at construction, and reuse it. Loading
        # Whisper per job adds tens of seconds to every single transcription.
        self._model_size = model_size
        self._device = device

    def can_handle(self, content_type: str, content: bytes) -> bool:
        """True for audio payloads. TODO: accept audio/* and video/* containers."""
        raise NotImplementedError

    def extract(
        self, resource_id: str, content: bytes, *, metadata: dict[str, object]
    ) -> NormalizedDocument:
        """Transcribe audio into timestamped text blocks.

        TODO (junior dev):
          [ ] Write the audio to a temp file (Whisper wants a path) and CLEAN
              IT UP in a `finally`. Leaked temp files fill the worker's disk
              over a few days and the failure looks nothing like an ASR bug.
          [ ] Run transcription with the language hint when we already know it
              from platform metadata — it improves accuracy and saves Whisper's
              own detection pass.
          [ ] Build TextBlocks from Whisper's segments, keeping start/end
              times, and merge short segments into sentences (same reasoning as
              `caption_extractor.py`).
          [ ] Record avg_logprob / no_speech_prob per segment as a confidence
              proxy, and put the document mean in metadata.
          [ ] Set metadata["asr"] = True and metadata["asr_model"] = <size>, so
              reviewers and the quality report can distinguish ASR-derived text.
          [ ] Consider `faster-whisper` (CTranslate2) — same quality, several
              times faster on CPU. On a free-tier/no-GPU budget that is the
              difference between viable and not.
          [ ] Guard on duration: refuse audio over the configured maximum
              rather than letting one long recording occupy a worker for hours.

        COST CONTROL: cache transcriptions by the audio's content hash. The
        same video submitted twice must never be transcribed twice — dedup at
        ingestion should catch this, but ASR is expensive enough to deserve a
        second line of defence.
        """
        raise NotImplementedError
