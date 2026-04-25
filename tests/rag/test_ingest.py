import pytest
import os
import json
from unittest.mock import patch, MagicMock
import chromadb
from sysagent.rag.ingest import ingest_all, get_text_md5
from sysagent.rag.extractor import extract_man_text
from sysagent.rag.chunker import chunk_text
from sysagent.rag.embedder import get_embeddings
from sysagent.rag.store import query_closest_chunks

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
         patch("sysagent.rag.ingest.get_rst_files") as m_rst_files, \
         patch("sysagent.rag.ingest.extract_rst_text") as m_rst_extract, \
         patch("sysagent.rag.ingest.chunk_text") as m_chunk, \
         patch("sysagent.rag.ingest.get_embeddings") as m_embed, \
         patch("sysagent.rag.ingest.upsert_chunks") as m_store:
        
        yield m_pages, m_extract, m_rst_files, m_rst_extract, m_chunk, m_embed, m_store


def test_ingest_all_new_file(mock_config, mock_components):
    """
    Validates that a new file successfully triggers extraction, chunking,
    embedding, storing, and importantly, saves the hash to the manifest.
    """
    m_pages, m_extract, m_rst_files, m_rst_extract, m_chunk, m_embed, m_store = mock_components
    
    m_rst_files.return_value = []
    
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
    m_pages, m_extract, m_rst_files, m_rst_extract, m_chunk, m_embed, m_store = mock_components
    m_rst_files.return_value = []
    
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
    m_pages, m_extract, m_rst_files, m_rst_extract, m_chunk, m_embed, m_store = mock_components
    m_rst_files.return_value = []
    
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

def test_ingest_all_skips_kernel_docs_gracefully(mock_config, mock_components, monkeypatch, capsys):
    """
    Validates that the ingestion loop gracefully skips kernel documentation
    if KERNEL_DOCS_PATH is None or does not exist, without crashing.
    """
    m_pages, m_extract, m_rst_files, m_rst_extract, m_chunk, m_embed, m_store = mock_components
    
    # Mock KERNEL_DOCS_PATH to None
    monkeypatch.setattr("sysagent.rag.ingest.KERNEL_DOCS_PATH", None)
    
    # Ensure man page processing doesn't do anything
    m_pages.return_value = []
    
    ingest_all()
    
    captured = capsys.readouterr()
    assert "Kernel Documentation not found. Skipping kernel ingestion phase." in captured.out
    m_rst_files.assert_not_called()
    m_rst_extract.assert_not_called()


@pytest.mark.integration
def test_ingest_e2e_integration(tmp_path, monkeypatch):
    """
    Live End-to-End test of the pipeline! 
    Uses REAL extraction, chunking, embedding (OpenAI), and storing (Chroma)
    but points the destination directories to a temporary folder to keep it safe.
    """
    temp_manifest_path = tmp_path / "manifest.json"
    temp_chroma_dir = tmp_path / "chroma_db"
    
    # Reroute the entire app into /tmp for this test
    monkeypatch.setattr("sysagent.rag.ingest.MANIFEST_PATH", temp_manifest_path)
    monkeypatch.setattr("sysagent.rag.store.CHROMA_DB_DIR", temp_chroma_dir)
    
    # Limit scope to robust commands to save API costs. We test two different
    # commands to ensure Semantic search can actually pick the correct one.
    monkeypatch.setattr("sysagent.rag.ingest.MAN_SECTIONS", ["1"])
    monkeypatch.setattr("sysagent.rag.ingest.get_man_pages_in_section", lambda x: ["pwd", "whoami"])
    monkeypatch.setattr("sysagent.rag.ingest.KERNEL_DOCS_PATH", None)
    
    # 1. Baseline Truth
    raw_text = extract_man_text("pwd", "1")
    expected_chunks = chunk_text(raw_text)
    
    # 2. RUN FULL PIPELINE END-TO-END
    ingest_all()
    
    # 3. Proof 1 (Hash Tracking Saved Correctly)
    with open(temp_manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        assert manifest["man1/pwd"] == get_text_md5(raw_text)
        
    # 4. Proof 2 (ChromaDB physically stored the data matching chunk outputs)
    client = chromadb.PersistentClient(path=str(temp_chroma_dir))
    collection = client.get_collection("sysagent_core_knowledge")
    
    db_results = collection.get(where={
        "$and": [
            {"source": "man1"},
            {"topic": "pwd"}
        ]
    })
    db_chunks = db_results["documents"]
    
    assert len(db_chunks) == len(expected_chunks)
    assert set(db_chunks) == set(expected_chunks)
    
    # 5. Proof 3 (Semantic Search actually works)
    query_vector = get_embeddings(["print working directory"])[0]
    semantic_results = query_closest_chunks(query_vector, n_results=1)
    
    # Validates our store updates didn't break things and we can truly find 'pwd'.
    # Because whoami is also in the database but completely unrelated to the query, 
    # the mathematical closest chunk must explicitly be 'pwd'.
    assert len(semantic_results) == 1
    assert "[man1:pwd]" in semantic_results[0]
    assert "[man1:whoami]" not in semantic_results[0]
