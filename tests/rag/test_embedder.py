import pytest
from unittest.mock import MagicMock, patch
from sysagent.rag.embedder import get_embeddings, EMBEDDING_BATCH_SIZE
from sysagent.config import EMBEDDING_MODEL
import os
import openai


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_openai(num_texts: int, vector_dim: int = 8):
    """
    Builds a mock OpenAI client whose embeddings.create() returns fake vectors.

    Each fake vector is a list of floats with length `vector_dim`. Using a
    small dimension (8) keeps test data tiny while still exercising all the
    real code paths that iterate over response.data.
    """
    fake_vectors = [[float(i)] * vector_dim for i in range(num_texts)]

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=v) for v in fake_vectors]

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    return mock_client, fake_vectors


# ---------------------------------------------------------------------------
# Unit tests (no network, no API key required)
# ---------------------------------------------------------------------------

def test_raises_on_empty_input():
    """
    Validates that passing an empty list raises ValueError immediately,
    before any API call is made.
    """
    with pytest.raises(ValueError, match="must not be empty"):
        get_embeddings([])


def test_returns_list_of_lists(monkeypatch):
    """
    Validates that get_embeddings returns a list of lists (i.e. a list of
    embedding vectors), one per input text.
    """
    texts = ["hello", "world"]
    mock_client, _ = _make_mock_openai(len(texts))

    with patch("sysagent.rag.embedder.OpenAI", return_value=mock_client):
        result = get_embeddings(texts)

    assert isinstance(result, list)
    assert all(isinstance(v, list) for v in result)


def test_output_length_matches_input(monkeypatch):
    """
    Validates that the number of returned vectors equals the number of
    input texts — the order-preserving contract of the function.
    """
    texts = ["alpha", "beta", "gamma", "delta", "epsilon"]
    mock_client, _ = _make_mock_openai(len(texts))

    with patch("sysagent.rag.embedder.OpenAI", return_value=mock_client):
        result = get_embeddings(texts)

    assert len(result) == len(texts)


def test_single_text_input():
    """
    Validates that a single-element list is handled correctly — edge case
    where the batch is exactly size 1.
    """
    texts = ["just one"]
    mock_client, _ = _make_mock_openai(len(texts))

    with patch("sysagent.rag.embedder.OpenAI", return_value=mock_client):
        result = get_embeddings(texts)

    assert len(result) == 1
    assert isinstance(result[0], list)


def test_batching_splits_large_input():
    """
    Validates that inputs larger than EMBEDDING_BATCH_SIZE trigger multiple
    API calls. With EMBEDDING_BATCH_SIZE=100 and 250 texts, we expect
    ceil(250 / 100) = 3 calls to embeddings.create().
    """
    num_texts = EMBEDDING_BATCH_SIZE * 2 + 50  # 250 for batch size of 100
    texts = [f"text {i}" for i in range(num_texts)]
    expected_calls = -(-num_texts // EMBEDDING_BATCH_SIZE)  # ceiling division

    # Build a mock that returns the right number of vectors per batch call
    mock_response_factory = MagicMock()
    def create_side_effect(model, input):
        fake_response = MagicMock()
        fake_response.data = [MagicMock(embedding=[0.1] * 8) for _ in input]
        return fake_response

    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = create_side_effect

    with patch("sysagent.rag.embedder.OpenAI", return_value=mock_client):
        result = get_embeddings(texts)

    assert mock_client.embeddings.create.call_count == expected_calls
    assert len(result) == num_texts


def test_correct_model_is_used():
    """
    Validates that the correct embedding model from config.py is passed to
    the API. Using the wrong model at ingestion vs. retrieval time would
    produce incompatible vector spaces.
    """
    texts = ["check the model"]
    mock_client, _ = _make_mock_openai(len(texts))

    with patch("sysagent.rag.embedder.OpenAI", return_value=mock_client):
        get_embeddings(texts)

    call_kwargs = mock_client.embeddings.create.call_args
    assert call_kwargs.kwargs["model"] == EMBEDDING_MODEL


# ---------------------------------------------------------------------------
# Unit tests: Edge cases & Errors
# ---------------------------------------------------------------------------

def test_raises_on_missing_api_key(monkeypatch):
    """
    Validates that a clear ValueError is raised if OPENAI_API_KEY is not set.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is not set"):
        get_embeddings(["valid text"])


def test_raises_on_empty_string_in_list(monkeypatch):
    """
    Validates that the API call is prevented if the batch contains an empty
    or whitespace-only string, which would cause an API crash.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "fake_key")
    with pytest.raises(ValueError, match="whitespace-only strings"):
        get_embeddings(["hello", "   \n  ", "world"])


def test_raises_on_non_string_types(monkeypatch):
    """
    Validates that passing non-string items (e.g. None, int) raises a clear
    ValueError before any API call is made. Without this guard, the code
    would crash with a cryptic AttributeError when calling .strip() on a
    non-string type.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "fake_key")
    with pytest.raises(ValueError, match="only strings"):
        get_embeddings(["valid", None, "also valid"])

    with pytest.raises(ValueError, match="only strings"):
        get_embeddings([1, 2, 3])


def test_propagates_api_errors(monkeypatch):
    """
    Validates that critical API errors (like RateLimitError or AuthenticationError)
    are propagated to the caller and not swallowed.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "fake_key")
    
    mock_client = MagicMock()
    # Simulate a RateLimitError
    mock_client.embeddings.create.side_effect = openai.RateLimitError(
        message="Too many requests",
        response=MagicMock(),
        body=None
    )

    with patch("sysagent.rag.embedder.OpenAI", return_value=mock_client):
        with pytest.raises(openai.RateLimitError):
            get_embeddings(["valid text"])

# ---------------------------------------------------------------------------
# Integration test (hits the real OpenAI API — requires OPENAI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_get_embeddings_real_api():
    """
    Integration test: calls the live OpenAI API to verify the full pipeline.

    Checks:
    - The API key is valid and the request succeeds.
    - The model name in config.py is accepted by OpenAI.
    - Each returned vector has the expected dimensionality (1536 for
      text-embedding-3-small).
    - Output length matches input length.

    Run with:
        pytest tests/rag/test_embedder.py -m integration -s
    """
    EXPECTED_DIM = 1536  # Fixed output dimension for text-embedding-3-small

    texts = [
        "The Linux kernel manages memory through a paging mechanism.",
        "The OOM killer terminates processes when the system runs out of memory.",
    ]

    result = get_embeddings(texts)

    # Shape checks
    assert len(result) == len(texts), "One vector per input text expected"
    for i, vector in enumerate(result):
        assert isinstance(vector, list), f"Vector {i} is not a list"
        assert len(vector) == EXPECTED_DIM, (
            f"Vector {i} has wrong dimension: expected {EXPECTED_DIM}, got {len(vector)}"
        )
        assert all(isinstance(x, float) for x in vector), (
            f"Vector {i} contains non-float values"
        )

    print(f"\n--- Real API embedding stats ---")
    print(f"Texts embedded  : {len(texts)}")
    print(f"Vector dimension: {len(result[0])}")
    print(f"First 5 values  : {result[0][:5]}")
