"""
Chunker (PDF 3.4) — split long documents for translation, WITHOUT destroying them.

"Long documents are split for translation (MT APIs have length limits) and
reassembled while preserving structure — headings and paragraphs matter for
later human review, so content should not be flattened to a single block."

READ THIS BEFORE YOU WRITE THE OBVIOUS VERSION.
The obvious implementation is `text[i:i+4000]`, and it is wrong in three ways
that all surface late:

  1. It splits mid-sentence. MT quality collapses on a fragment, because the
     model no longer has the clause it needs to choose grammar. Swahili is
     particularly unforgiving here: noun-class agreement propagates across a
     sentence, so half a sentence translates into something a Swahili speaker
     reads as broken.
  2. It splits mid-word, producing character soup at every boundary.
  3. It loses the mapping back to source blocks, so the side-by-side review UI
     cannot align anything and the feedback loop cannot diff anything.

So: split on BLOCK boundaries first, sentence boundaries second, and never
below that. Always carry the source block indices along.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...domain.models import TextBlock


@dataclass(frozen=True, slots=True)
class Chunk:
    """A translation-sized piece of text plus the blocks it came from.

    `block_orders` is what makes reassembly possible. Without it you have
    translated text and no idea where it belongs.
    """

    text: str
    block_orders: tuple[int, ...]  # source TextBlock.order values in this chunk


class Chunker:
    """Splits blocks into engine-sized chunks and puts them back together."""

    def __init__(self, *, max_chars: int = 4000, overlap_chars: int = 0) -> None:
        self._max_chars = max_chars
        # Overlap helps RAG retrieval; for TRANSLATION it is usually 0, because
        # overlapping text gets translated twice and then has to be
        # de-duplicated on reassembly. Do not copy a RAG chunker here — they
        # look similar and want opposite things.
        self._overlap_chars = overlap_chars

    def chunk(
        self, blocks: tuple[TextBlock, ...], *, max_chars: int | None = None
    ) -> list[Chunk]:
        """Group blocks into chunks under the engine's character limit.

        TODO (junior dev) — implement in this order:

          1. GREEDY PACK WHOLE BLOCKS: accumulate blocks until adding the next
             would exceed max_chars, then start a new chunk. Most paragraphs
             are far smaller than the limit, so most chunks hold several whole
             blocks and no splitting is needed at all.

          2. A SINGLE BLOCK OVER THE LIMIT (rare but real — a wall-of-text
             page): split it on SENTENCE boundaries. Handle Swahili and
             English punctuation, and watch for abbreviations ("Dr.", "e.g.")
             that a naive `.split(".")` treats as sentence ends.

          3. NEVER SPLIT BELOW A SENTENCE. If one sentence somehow exceeds the
             limit, send it whole and let the engine truncate — a truncated
             sentence is at least diagnosable, whereas a mid-word split is
             silent corruption.

          4. NEVER MERGE A HEADING INTO A PARAGRAPH CHUNK if you can avoid it.
             Headings translate better with their own context, and the review
             UI aligns them separately.

          5. ALWAYS populate `block_orders`. A chunk without it cannot be
             reassembled.

        TEST THIS FILE HARD. It is pure functions over data — no I/O, no mocks
        — so there is no excuse for gaps. Cover: empty input, one huge block,
        many tiny blocks, a block exactly at the limit, and a block one
        character over.
        """
        raise NotImplementedError

    def reassemble(
        self,
        blocks: tuple[TextBlock, ...],
        chunks: list[Chunk],
        translations: list[str],
    ) -> list[tuple[int, str]]:
        """Map translated chunks back onto source block orders.

        Returns (block_order, translated_text) pairs, ready to become
        TranslationUnits.

        TODO (junior dev):
          [ ] ASSERT len(chunks) == len(translations) FIRST. If they differ,
              raise — do not zip and hope. `zip` silently truncates to the
              shorter list, which drops the tail of a document with no error
              at all. That is the worst kind of bug: quiet, plausible, and
              only visible to a reviewer who happens to notice a missing
              section.
          [ ] For a chunk covering ONE block: pair the translation with it.
          [ ] For a chunk covering SEVERAL blocks: split the translated text
              back out per block. This is the genuinely hard case, because the
              engine may not preserve your separators. Mitigate it by
              translating multi-block chunks as separate list ITEMS in
              `translate_batch` rather than as one joined string — then no
              splitting is needed and this problem disappears. Prefer that
              approach; it is why the port takes a list.
          [ ] Return pairs sorted by block_order, with every source block
              accounted for.
        """
        raise NotImplementedError
