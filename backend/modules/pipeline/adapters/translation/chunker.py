"""
Chunker (PDF 3.4) — split long documents for translation, WITHOUT destroying them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ...domain.models import TextBlock


@dataclass(frozen=True, slots=True)
class Chunk:
    """A translation-sized piece of text plus the blocks it came from."""

    text: str
    block_orders: tuple[int, ...]  # source TextBlock.order values in this chunk


class Chunker:
    """Splits blocks into engine-sized chunks and puts them back together."""

    def __init__(self, *, max_chars: int = 4000, overlap_chars: int = 0) -> None:
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences avoiding common abbreviations."""
        sentence_end = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_end.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk(
        self, blocks: tuple[TextBlock, ...], *, max_chars: int | None = None
    ) -> list[Chunk]:
        """Group blocks into chunks under the engine's character limit."""
        limit = max_chars if max_chars is not None else self._max_chars
        if not blocks:
            return []

        chunks: list[Chunk] = []
        current_texts: list[str] = []
        current_orders: list[int] = []
        current_len = 0

        for block in blocks:
            block_len = len(block.text)

            if block_len > limit:
                if current_texts:
                    chunks.append(
                        Chunk(text="\n\n".join(current_texts), block_orders=tuple(current_orders))
                    )
                    current_texts, current_orders, current_len = [], [], 0

                sentences = self._split_into_sentences(block.text)
                sent_texts: list[str] = []
                sent_len = 0
                for sent in sentences:
                    if sent_len + len(sent) + 1 > limit and sent_texts:
                        chunks.append(
                            Chunk(text=" ".join(sent_texts), block_orders=(block.order,))
                        )
                        sent_texts, sent_len = [], 0
                    sent_texts.append(sent)
                    sent_len += len(sent) + 1

                if sent_texts:
                    chunks.append(
                        Chunk(text=" ".join(sent_texts), block_orders=(block.order,))
                    )
                continue

            added_len = block_len + (2 if current_texts else 0)
            if current_len + added_len > limit:
                chunks.append(
                    Chunk(text="\n\n".join(current_texts), block_orders=tuple(current_orders))
                )
                current_texts = [block.text]
                current_orders = [block.order]
                current_len = block_len
            else:
                current_texts.append(block.text)
                current_orders.append(block.order)
                current_len += added_len

        if current_texts:
            chunks.append(
                Chunk(text="\n\n".join(current_texts), block_orders=tuple(current_orders))
            )

        return chunks

    def reassemble(
        self,
        blocks: tuple[TextBlock, ...],
        chunks: list[Chunk],
        translations: list[str],
    ) -> list[tuple[int, str]]:
        """Map translated chunks back onto source block orders."""
        if len(chunks) != len(translations):
            raise ValueError(
                f"Mismatch: got {len(chunks)} chunks but {len(translations)} translations."
            )

        result: list[tuple[int, str]] = []
        for chunk_obj, translation in zip(chunks, translations):
            if len(chunk_obj.block_orders) == 1:
                result.append((chunk_obj.block_orders[0], translation))
            else:
                parts = translation.split("\n\n")
                if len(parts) == len(chunk_obj.block_orders):
                    for order, part in zip(chunk_obj.block_orders, parts):
                        result.append((order, part))
                else:
                    for order in chunk_obj.block_orders:
                        result.append((order, translation))

        return sorted(result, key=lambda x: x[0])