import os
from openai import OpenAI
from dotenv import load_dotenv
from sysagent.config import EMBEDDING_MODEL

# Load OPENAI_API_KEY from the .env file in the project root
load_dotenv()

# Maximum number of texts to send to the OpenAI API in a single request.
# OpenAI recommends batches of up to 100 for text-embedding-3-small.
# Staying within this limit avoids rate-limit errors and keeps latency predictable.
EMBEDDING_BATCH_SIZE = 100       


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Converts a list of text strings into vector embeddings using the OpenAI API.

    This is used at two points in the RAG pipeline:
      1. During ingestion: to embed man page chunks before storing them in ChromaDB.
      2. During retrieval: to embed the user's query so it can be compared against stored chunks.

    The function processes texts in batches of EMBEDDING_BATCH_SIZE to avoid hitting
    API rate limits and to minimize the number of network round-trips.

    The same model (EMBEDDING_MODEL from config.py) MUST be used at both ingestion and
    retrieval time. Mixing models would produce incompatible vector spaces, causing
    incorrect similarity results.

    Args:
        texts (list[str]): A list of text strings to embed. Must not be empty,
                           must not contain non-string items, and must not contain
                           empty or whitespace-only strings.

    Returns:
        list[list[float]]: A list of embedding vectors, one per input text,
                           in the same order as the input.

    Raises:
        ValueError: If the texts list is empty, contains non-strings, or contains
                    empty/whitespace-only strings, or if OPENAI_API_KEY is not set.
        openai.AuthenticationError: If OPENAI_API_KEY is invalid.

    Note:
        text-embedding-3-small has a hard limit of 8,191 tokens per text (~32,000 chars).
        Texts exceeding this limit will cause the entire batch to fail. Always pass
        pre-chunked text (e.g. output from chunker.chunk_text()) to stay well within this limit.
    """
    if not texts:
        raise ValueError("texts list must not be empty")

    # Guard against non-string types — calling .strip() on None or int gives AttributeError
    if any(not isinstance(text, str) for text in texts):
        raise ValueError("texts list must contain only strings")

    # Guard against completely empty strings in the batch
    if any(not text.strip() for text in texts):
        raise ValueError("texts list must not contain empty or whitespace-only strings")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)
    all_embeddings = []

    # Process in batches to stay within API limits
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        # The API returns embeddings in the same order as the input
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
