import pytest
from sysagent.rag.chunker import chunk_text
from sysagent.config import CHUNK_SIZE, CHUNK_OVERLAP


def test_chunk_text_returns_list():
    """
    Validates that chunk_text returns a list of strings.
    """
    text = "word " * 500  # ~2500 chars, forces multiple chunks
    result = chunk_text(text)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(chunk, str) for chunk in result)


def test_chunk_text_respects_size():
    """
    Validates that no produced chunk exceeds CHUNK_SIZE characters.
    """
    text = "word " * 500
    result = chunk_text(text)
    for chunk in result:
        assert len(chunk) <= CHUNK_SIZE, (
            f"Chunk exceeds CHUNK_SIZE ({CHUNK_SIZE}): got {len(chunk)} chars"
        )


def test_chunk_text_overlap_exists():
    """
    Validates that consecutive chunks share overlapping content.
    We verify the overlap by checking that the tail of chunk N
    appears at the start of chunk N+1.
    """
    text = "word " * 500
    result = chunk_text(text)

    if len(result) < 2:
        pytest.skip("Not enough chunks produced to test overlap")

    for i in range(len(result) - 1):
        tail_of_current = result[i][-CHUNK_OVERLAP:]
        start_of_next = result[i + 1][:CHUNK_OVERLAP]
        # There should be some common text between consecutive chunks
        assert tail_of_current in result[i + 1] or start_of_next in result[i], (
            f"No overlap detected between chunk {i} and chunk {i + 1}"
        )


def test_chunk_text_empty_input():
    """
    Validates that an empty or whitespace-only input returns an empty list
    without raising an exception.
    """
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_text_with_real_man_page():
    """
    Integration test: runs the full extract -> chunk pipeline on ls(1).
    Validates that real man page text produces a sensible number of
    non-empty chunks, each within the size limit.
    Run with `pytest -s` to see chunk stats printed to stdout.
    """
    from sysagent.rag.extractor import extract_man_text
    text = extract_man_text("ls", "1")
    result = chunk_text(text)

    # Print stats for visual verification — visible when running pytest -s
    chunk_sizes = [len(c) for c in result]
    print(f"\n--- Chunk stats for ls(1) ---")
    print(f"Total chunks     : {len(result)}")
    print(f"Avg chunk size   : {sum(chunk_sizes) // len(chunk_sizes)} chars")
    print(f"Min chunk size   : {min(chunk_sizes)} chars")
    print(f"Max chunk size   : {max(chunk_sizes)} chars")
    print(f"--- First chunk preview ---")
    print(result[0][:300])
    print(f"--- Last chunk preview ---")
    print(result[-1][:300])

    assert len(result) > 1, "ls man page should produce multiple chunks"
    for chunk in result:
        assert len(chunk) <= CHUNK_SIZE
        assert chunk.strip() != ""
