from langchain_text_splitters import RecursiveCharacterTextSplitter
from sysagent.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str) -> list[str]:
    """
    Splits a clean string of man page text into overlapping chunks for embedding.

    This is the second step in the RAG ingestion pipeline, receiving the output of
    extract_man_text() and preparing it for the embedding API.

    The splitter uses a priority-ordered list of separators:
      1. Double newlines (paragraph breaks) — preferred split point
      2. Single newlines
      3. Spaces
      4. Individual characters (last resort, avoids cutting mid-word where possible)

    This ensures that chunks respect natural language boundaries wherever possible,
    rather than splitting mechanically at a fixed character index.

    The chunk size and overlap are read from config.py to ensure a single source of truth.
    Overlap ensures that context is not lost when a concept (e.g., a flag description)
    straddles a chunk boundary.

    Args:
        text (str): The clean, normalized text of a man page (output of extract_man_text).

    Returns:
        list[str]: A list of overlapping text chunks, each at most CHUNK_SIZE characters.
                   Returns an empty list if the input text is empty.
    """
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    return splitter.split_text(text)
