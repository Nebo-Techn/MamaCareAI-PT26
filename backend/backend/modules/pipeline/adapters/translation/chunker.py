from __future__ import annotations

import re

from ...domain.models import TextBlock


class Chunk:
    def __init__(self, text: str, block_orders: tuple[int, ...]) -> None:
        self.text = text
        self.block_orders = block_orders


class Chunker:
    def __init__(self, *, max_chars: int = 4000, overlap_chars: int = 0) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than 0")
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    def _split_sentences(self, text: str) -> list[str]:
        pattern = r"(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bProf)(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)\.\s+|[\!\?]\s+"
        sentences = re.split(pattern, text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _split_huge_block(self, block: TextBlock, max_limit: int) -> list[Chunk]:
        sentences = self._split_sentences(block.text)
        if not sentences:
            return [Chunk(text=block.text, block_orders=(block.order,))]

        chunks: list[Chunk] = []
        current_sentences: list[str] = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_sentences and (current_len + sentence_len + 1 > max_limit):
                chunks.append(
                    Chunk(
                        text=" ".join(current_sentences),
                        block_orders=(block.order,),
                    )
                )
                current_sentences = [sentence]
                current_len = sentence_len
            else:
                current_sentences.append(sentence)
                current_len += sentence_len + 1

        if current_sentences:
            chunks.append(
                Chunk(
                    text=" ".join(current_sentences),
                    block_orders=(block.order,),
                )
            )

        return chunks

    def chunk(
        self, blocks: tuple[TextBlock, ...], *, max_chars: int | None = None
    ) -> list[Chunk]:
        if not blocks:
            return []

        limit = max_chars if max_chars is not None else self._max_chars
        chunks: list[Chunk] = []

        current_blocks: list[TextBlock] = []
        current_len = 0

        for block in blocks:
            is_heading = getattr(block, "is_heading", False)

            if len(block.text) > limit:
                if current_blocks:
                    chunks.append(
                        Chunk(
                            text="\n\n".join(b.text for b in current_blocks),
                            block_orders=tuple(b.order for b in current_blocks),
                        )
                    )
                    current_blocks = []
                    current_len = 0

                chunks.extend(self._split_huge_block(block, limit))
                continue

            if is_heading and current_blocks:
                chunks.append(
                    Chunk(
                        text="\n\n".join(b.text for b in current_blocks),
                        block_orders=tuple(b.order for b in current_blocks),
                    )
                )
                current_blocks = []
                current_len = 0

            block_len = len(block.text)
            needed_space = block_len if not current_blocks else block_len + 2

            if current_blocks and (current_len + needed_space > limit):
                chunks.append(
                    Chunk(
                        text="\n\n".join(b.text for b in current_blocks),
                        block_orders=tuple(b.order for b in current_blocks),
                    )
                )
                current_blocks = [block]
                current_len = block_len
            else:
                current_blocks.append(block)
                current_len += needed_space

        if current_blocks:
            chunks.append(
                Chunk(
                    text="\n\n".join(b.text for b in current_blocks),
                    block_orders=tuple(b.order for b in current_blocks),
                )
            )

        return chunks

    def reassemble(
        self,
        blocks: tuple[TextBlock, ...],
        chunks: list[Chunk],
        translations: list[str],
    ) -> list[tuple[int, str]]:
        if len(chunks) != len(translations):
            raise ValueError(
                f"Mismatch between chunks count ({len(chunks)}) and translations count ({len(translations)})."
            )

        result_map: dict[int, str] = {}

        for chunk, translation in zip(chunks, translations, strict=True):
            orders = chunk.block_orders

            if len(orders) == 1:
                order = orders[0]
                if order in result_map:
                    result_map[order] += " " + translation.strip()
                else:
                    result_map[order] = translation.strip()
            else:
                parts = [p.strip() for p in translation.split("\n\n") if p.strip()]
                if len(parts) == len(orders):
                    for order, part in zip(orders, parts, strict=True):
                        result_map[order] = part
                else:
                    lines = [
                        line.strip() for line in translation.split("\n") if line.strip()
                    ]
                    if len(lines) == len(orders):
                        for order, line in zip(orders, lines, strict=True):
                            result_map[order] = line
                    else:
                        for order in orders:
                            result_map[order] = translation.strip()

        sorted_results: list[tuple[int, str]] = []
        for block in sorted(blocks, key=lambda b: b.order):
            translated_text = result_map.get(block.order, "")
            sorted_results.append((block.order, translated_text))

        return sorted_results
