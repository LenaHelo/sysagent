import pytest
import os
import json
from unittest.mock import patch, MagicMock
from sysagent.rag.ingest import ingest_all, get_text_md5

@pytest.fixture
def mock_config(tmp_path):
    """
    Mocks the config to point the manifest to a temporary directory
    to prevent polluting the user's ~/.config.
    """
    manifest_path = tmp_path / "ingestion_manifest.json"
    with patch("sysagent.rag.ingest.MANIFEST_PATH", manifest_path):
        with patch("sysagent.rag.ingest.MAN_SECTIONS", ["99"]):
            yield manifest_path

@pytest.fixture
def mock_components():
    """Mocks all downstream heavy components."""
    with patch("sysagent.rag.ingest.get_man_pages_in_section") as m_pages, \
         patch("sysagent.rag.ingest.extract_man_text") as m_extract, \
         patch("sysagent.rag.ingest.chunk_text") as m_chunk, \
         patch("sysagent.rag.ingest.get_embeddings") as m_embed, \
         patch("sysagent.rag.ingest.upsert_chunks") as m_store:
        
        yield m_pages, m_extract, m_chunk, m_embed, m_store


def test_ingest_all_new_file(mock_config, mock_components):
    """
    Validates that a new file successfully triggers extraction, chunking,
    embedding, storing, and importantly, saves the hash to the manifest.
    """
    m_pages, m_extract, m_chunk, m_embed, m_store = mock_components
    
    m_pages.return_value = ["test_topic"]
    m_extract.return_value = "hello world"
    m_chunk.return_value = ["hello", "world"]
    m_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
    
    ingest_all()
    
    m_extract.assert_called_once_with("test_topic", "99")
    m_chunk.assert_called_once_with("hello world")
    m_embed.assert_called_once_with(["hello", "world"])
    m_store.assert_called_once_with(
        source="man99",
        topic="test_topic",
        chunks=["hello", "world"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]]
    )
    
    # Assert manifest was updated
    manifest_path = mock_config
    assert manifest_path.exists()
    with open(manifest_path, "r") as f:
        data = json.load(f)
        assert data["man99/test_topic"] == get_text_md5("hello world")


def test_ingest_all_skips_unchanged(mock_config, mock_components):
    """
    Validates the idempotent nature of the pipeline. If a hash already exists
    in the manifest, all downstream tools should be skipped to save costs.
    """
    m_pages, m_extract, m_chunk, m_embed, m_store = mock_components
    
    # Pre-populate manifest with the completed hash
    manifest_path = mock_config
    text_content = "same content as last time"
    hash_val = get_text_md5(text_content)
    
    with open(manifest_path, "w") as f:
        json.dump({"man99/test_topic": hash_val}, f)
        
    m_pages.return_value = ["test_topic"]
    m_extract.return_value = text_content
    
    ingest_all()
    
    # Crucially, downstream functions MUST NOT have been called
    m_chunk.assert_not_called()
    m_embed.assert_not_called()
    m_store.assert_not_called()


def test_ingest_all_handles_extraction_errors(mock_config, mock_components):
    """
    Validates that a crash on one file doesn't crash the entire pipeline queue.
    """
    m_pages, m_extract, m_chunk, m_embed, m_store = mock_components
    
    # Two pages: first crashes, second succeeds
    m_pages.return_value = ["crash_topic", "good_topic"]
    
    def side_effect_extract(topic, section):
        if topic == "crash_topic":
            raise RuntimeError("Corrupted groff file")
        return "good data"
        
    m_extract.side_effect = side_effect_extract
    m_chunk.return_value = ["good", "data"]
    
    ingest_all()
    
    # The pipeline should have survived and successfully processed the good topic
    m_store.assert_called_once()
    kwargs = m_store.call_args.kwargs
    assert kwargs["topic"] == "good_topic"
