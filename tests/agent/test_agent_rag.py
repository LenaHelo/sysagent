import pytest
from sysagent.rag.embedder import get_embeddings
from sysagent.rag.store import upsert_chunks
from sysagent.agent.core import ask_sysagent

@pytest.mark.integration
def test_agent_needle_in_a_haystack(tmp_path, monkeypatch):
    """
    Validates that the LLM strictly obeys the RAG pipeline by injecting
    an impossible synthetic fact and ensuring the LLM cites it flawlessly.
    """
    temp_chroma_dir = tmp_path / "chroma_e2e_db"
    
    # 1. Reroute the DB securely to a temp directory to avoid touching real XDG files
    monkeypatch.setattr("sysagent.rag.store.CHROMA_DB_DIR", temp_chroma_dir)
    
    # 2. Create the Needle (A completely impossible synthetic fact)
    needle_text = (
        "The sysagent_warp_drive command is a highly classified utility "
        "used exclusively to restart the flux capacitor on the mlo5eyye sector 7G. "
        "If abused or run without root space privileges, it causes a temporal anomaly."
    )
    
    # 3. Use real OpenAI embeddings to insert the needle into the Vector DB
    needle_embedding = get_embeddings([needle_text])[0]
    upsert_chunks(
        source="man8",
        topic="sysagent_warp_drive",
        chunks=[needle_text],
        embeddings=[needle_embedding]
    )
    
    # 4. Query the Live Agent
    # The agent knows nothing of this command via training data! It MUST use RAG.
    question = 'Please provide an exact, word-for-word quote from the documentation explaining what the sysagent_warp_drive command does and what happens if abused.'
    answer = ask_sysagent(question)
    
    print(f"\n\n--- LLM ANSWER ---\n{answer}\n------------------\n")
    
    # 5. Assert the LLM physically generated text corresponding to our injected truth
    ans_lower = answer.lower()
    assert "flux capacitor" in ans_lower
    assert "sector 7g" in ans_lower
    assert "temporal anomaly" in ans_lower

@pytest.mark.integration
def test_agent_refuses_untrained_knowledge(tmp_path, monkeypatch):
    """
    Validates that the LLM explicitly refuses to answer a question about a very
    well-known Linux command if that command is not present in the RAG database.
    """
    temp_chroma_dir = tmp_path / "chroma_empty_db"
    
    # 1. Start with an entirely empty, isolated database
    monkeypatch.setattr("sysagent.rag.store.CHROMA_DB_DIR", temp_chroma_dir)
    
    # 2. Ask about a universally known fact that the LLM obviously knows from pre-training
    question = "What does the 'ls' command do in Linux?"
    answer = ask_sysagent(question)
    
    print(f"\n\n--- LLM ANSWER (NEGATIVE TEST) ---\n{answer}\n------------------\n")
    
    # 3. Assert the LLM obeys our systemic rule to play dumb rather than hallucinate
    ans_lower = answer.lower()
    assert "i don't know" in ans_lower or "provided context" in ans_lower


def test_agent_missing_api_key(monkeypatch):
    """Ensure ask_sysagent fails explicitly if API key is removed."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        ask_sysagent("Is the sky blue?")


def test_agent_empty_query():
    """Ensure sending a blank space query avoids an OpenAI API crash."""
    response = ask_sysagent("    \n  ")
    assert response == "Please ask a valid question."


@pytest.mark.integration
def test_agent_supreme_truth_contradiction(tmp_path, monkeypatch):
    """
    Tests that the LLM will obey rule 3 of our System Prompt and perfectly follow
    the provided context even if it is completely contradictory to its pre-trained reality.
    """
    temp_chroma_dir = tmp_path / "chroma_contradiction_db"
    monkeypatch.setattr("sysagent.rag.store.CHROMA_DB_DIR", temp_chroma_dir)
    
    # 1. The supreme truth manipulation
    fake_docs = "To cleanly reboot a Linux machine, you must type 'sudo meow -x' and nothing else."
    fake_embedding = get_embeddings([fake_docs])[0]
    
    upsert_chunks(
        source="man8",
        topic="fake_reboot",
        chunks=[fake_docs],
        embeddings=[fake_embedding]
    )
    
    # 2. Query against reality
    query = "How do I cleanly reboot a Linux machine?"
    answer = ask_sysagent(query).lower()
    
    print(f"\n\n--- LLM ANSWER (SUPREME TRUTH TEST) ---\n{answer}\n------------------\n")

    # 3. Assert the LLM surrendered to the documentation
    assert "sudo meow -x" in answer
