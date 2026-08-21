import pytest
from backend.modules.pipeline.adapters.translation.chunker import Chunk, Chunker
from backend.modules.pipeline.domain.models import TextBlock


def create_block(order: int, text: str, kind: str = "text") -> TextBlock:
    return TextBlock(order=order, text=text, kind=kind)


def test_chunk_empty_input() -> None:
    chunker = Chunker(max_chars=100)
    assert chunker.chunk(()) == []


def test_chunk_greedy_pack_whole_blocks() -> None:
    chunker = Chunker(max_chars=50)
    b1 = create_block(1, "First sentence.")
    b2 = create_block(2, "Second sentence.")

    chunks = chunker.chunk((b1, b2))
    assert len(chunks) == 1
    assert chunks[0].block_orders == (1, 2)
    assert "First sentence.\n\nSecond sentence." in chunks[0].text


def test_chunk_huge_block_splits_on_sentences() -> None:
    chunker = Chunker(max_chars=100)
    huge_text = "Dr. Jane visited the clinic. She checked the maternal records carefully."
    b1 = create_block(1, huge_text)

    chunks = chunker.chunk((b1,))
    assert len(chunks) >= 1
    for c in chunks:
        assert c.block_orders == (1,)
        assert len(c.text) <= 100


def test_reassemble_mismatch_raises_error() -> None:
    chunker = Chunker(max_chars=100)
    b1 = create_block(1, "Hello")
    chunks = [Chunk(text="Hello", block_orders=(1,))]

    with pytest.raises(ValueError, match="Mismatch"):
        chunker.reassemble((b1,), chunks, ["Habari", "Extra translation"])


def test_reassemble_single_and_multi_blocks() -> None:
    chunker = Chunker(max_chars=100)
    b1 = create_block(1, "First paragraph.")
    b2 = create_block(2, "Second paragraph.")

    chunks = chunker.chunk((b1, b2))
    translations = ["Aya ya kwanza.\n\nAya ya pili."]

    reassembled = chunker.reassemble((b1, b2), chunks, translations)
    assert len(reassembled) == 2
    assert reassembled[0] == (1, "Aya ya kwanza.")
    assert reassembled[1] == (2, "Aya ya pili.")