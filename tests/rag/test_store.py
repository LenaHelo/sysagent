import pytest
import chromadb
from unittest.mock import patch
from sysagent.rag.store import upsert_chunks, query_closest_chunks, get_chroma_client


@pytest.fixture
def ephemeral_chroma():
    """
    Overrides the real persistent ChromaDB client with a fast, in-memory client.
    This prevents unit tests from polluting the real ~/.config/sysagent data directory.
    """
    client = chromadb.EphemeralClient()
    
    # ChromaDB's EphemeralClient retains memory across tests in the same process.
    # We must explicitly delete the collection to ensure a clean slate per test.
    from sysagent.config import CHROMA_COLLECTION_NAME
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass # Collection didn't exist yet
        
    with patch("sysagent.rag.store.get_chroma_client", return_value=client):
        yield client


def test_upsert_and_query_success(ephemeral_chroma):
    """
    Validates the happy path: inserting chunks and successfully retrieving the
    closest one based on semantic similarity.
    """
    chunks = [
        "The quick brown fox jumps over the lazy dog.",
        "A database is an organized collection of data.",
    ]
    # Fake 3-dimensional embeddings just for testing
    embeddings = [
        [0.1, 0.9, 0.1],  # represents the animal sentence
        [0.9, 0.1, 0.1],  # represents the database sentence
    ]

    # Insert into the in-memory DB
    upsert_chunks("test_source", "test_topic", chunks, embeddings)

    # Query with a vector close to the "database" sentence
    query_vector = [0.8, 0.2, 0.1]
    
    # We ask for only 1 result to explicitly check ranking
    results = query_closest_chunks(query_vector, n_results=1)

    assert len(results) == 1
    assert "organized collection of data" in results[0]


def test_upsert_mismatched_lengths(ephemeral_chroma):
    """
    Validates that a mismatched length between chunks and embeddings raises a ValueError.
    """
    chunks = ["one", "two"]
    embeddings = [[0.1, 0.2, 0.3]] # Missing one

    with pytest.raises(ValueError, match="Mismatched list lengths"):
        upsert_chunks("man1", "ls", chunks, embeddings)


def test_upsert_empty_list(ephemeral_chroma):
    """
    Validates that passing empty lists does not crash.
    """
    # Should safely return without error
    upsert_chunks("man1", "ls", [], [])
    
    # Ensure collection is empty
    assert len(query_closest_chunks([0.1, 0.1, 0.1])) == 0


def test_upsert_is_idempotent(ephemeral_chroma):
    """
    Validates that calling upsert twice with the exact same source+topic
    does not duplicate data in the database.
    """
    chunks = ["Linux is a kernel"]
    embeddings = [[0.5, 0.5, 0.5]]
    
    # Call twice
    upsert_chunks("man1", "linux", chunks, embeddings)
    upsert_chunks("man1", "linux", chunks, embeddings)

    # If it duplicated, querying for it might return multiple copies
    # We query for top 5, but we should only get 1 result back.
    results = query_closest_chunks([0.5, 0.5, 0.5], n_results=5)
    assert len(results) == 1
    assert results[0] == f"[man1:linux]\n{chunks[0]}"


def test_query_on_empty_db(ephemeral_chroma):
    """
    Validates that querying a completely empty database returns an empty list,
    not a KeyError or IndexError wrapper.
    """
    results = query_closest_chunks([0.1, 0.2, 0.3], n_results=5)
    assert results == []


def test_upsert_respects_batch_size(ephemeral_chroma, monkeypatch):
    """
    Validates that bulk-inserting arrays larger than the DB's batch limit
    is properly chunked and saved without crashing.
    """
    # Force max_batch_size to a tiny number to trigger multiple loop iterations
    mock_batch_size = 2
    monkeypatch.setattr(ephemeral_chroma, "get_max_batch_size", lambda: mock_batch_size)

    chunks = ["chunk a", "chunk b", "chunk c", "chunk d", "chunk e"]
    embeddings = [[0.1, 0.1, 0.1]] * 5
    
    # Needs 3 batches (2, 2, 1)
    upsert_chunks("man1", "testing", chunks, embeddings)
    
    # Query back using same vector to get all 5
    results = query_closest_chunks([0.1, 0.1, 0.1], n_results=10)
    assert len(results) == 5

    
def test_query_dimension_mismatch(ephemeral_chroma):
    """
    Validates that searching with a vector size that doesn't match the
    established database size gracefully throws our custom ValueError.
    """
    chunks = ["valid chunk"]
    upsert_chunks("man1", "dim_test", chunks, [[0.5, 0.5, 0.5]]) # DB is locked to size 3
    
    # Try querying with a size 2 array
    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        query_closest_chunks([0.5, 0.5], n_results=1)


def test_metadata_is_saved(ephemeral_chroma):
    """
    Validates that the source and topic metadata is attached correctly.
    (We access the raw client here to bypass the utility function and verify DB truth).
    """
    upsert_chunks("man8", "mount", ["mount command description"], [[1.0, 1.0, 1.0]])

    from sysagent.config import CHROMA_COLLECTION_NAME
    collection = ephemeral_chroma.get_collection(CHROMA_COLLECTION_NAME)
    
    raw_results = collection.get()
    
    # Ensure metadata is exactly what we expect
    assert len(raw_results["metadatas"]) == 1
    assert raw_results["metadatas"][0] == {"source": "man8", "topic": "mount"}
