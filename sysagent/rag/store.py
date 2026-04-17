import os
import chromadb
from chromadb.errors import InvalidArgumentError
from sysagent.config import CHROMA_DB_DIR, CHROMA_COLLECTION_NAME, TOP_K_RESULTS


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Returns a persistent ChromaDB client pointing to the standard config directory.
    Creates the directory if it does not exist.
    """
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DB_DIR))


def get_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    """
    Returns the core SysAgent knowledge collection, creating it if necessary.
    """
    return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)


def upsert_chunks(
    source: str,
    topic: str,
    chunks: list[str],
    embeddings: list[list[float]]
) -> None:
    """
    Inserts or updates text chunks into ChromaDB with their corresponding embeddings.
    
    Uses deterministic IDs (e.g., man1_ls_chunk_0) to enable idempotent ingestion.
    If the script runs twice on the same file, `.upsert()` simply overwrites the
    existing records rather than creating duplicates.

    Args:
        source (str): The origin of the data (e.g., "man1", "kernel_doc").
        topic (str): The specific subject (e.g., "ls", "oom_killer").
        chunks (list[str]): The plain text chunks.
        embeddings (list[list[float]]): The float vectors from OpenAI. Must exactly
                                        match the length of `chunks`.
    
    Raises:
        ValueError: If `chunks` and `embeddings` lists have different lengths.
    """
    if not chunks:
        return

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Mismatched list lengths: {len(chunks)} chunks vs {len(embeddings)} embeddings"
        )

    client = get_chroma_client()
    collection = get_collection(client)
    
    ids = [f"{source}_{topic}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": source, "topic": topic} for _ in chunks]

    # If doing a massive bulk-insert (like 100,000 chunks), SQLite will crash if we
    # pass all variables in a single SQL parameter query. 
    # We defensively chunk the request into safe batches depending on the OS limits.
    max_batch_size = client.get_max_batch_size()
    
    for i in range(0, len(chunks), max_batch_size):
        batch_ids = ids[i : i + max_batch_size]
        batch_embeddings = embeddings[i : i + max_batch_size]
        batch_documents = chunks[i : i + max_batch_size]
        batch_metadatas = metadatas[i : i + max_batch_size]
        
        collection.upsert(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas
        )


def query_closest_chunks(
    query_embedding: list[float],
    n_results: int = TOP_K_RESULTS,
    topic_filter: str = None
) -> list[str]:
    """
    Given an embedded search query, retrieves the most semantically similar text
    chunks from the vector database.

    Args:
        query_embedding (list[float]): The single embedding vector for the user's query.
        n_results (int): Max number of chunks to return (default: TOP_K_RESULTS).

    Returns:
        list[str]: A list of text chunks, ordered by relevance (most relevant first).
                   Returns an empty list if the collection is completely empty.
    """
    if not query_embedding:
        return []

    client = get_chroma_client()
    collection = get_collection(client)
    
    # Chroma returns nested lists because it supports querying multiple embeddings at once.
    # We only pass a single query_embedding, so we unpack the first element.
    # Build the query arguments dynamically
    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results
    }
    
    # Apply strict metadata filtering if the LLM provided a topic
    if topic_filter:
        query_kwargs["where"] = {"topic": topic_filter}

    try:
        results = collection.query(**query_kwargs)
    except InvalidArgumentError as e:
        # Chroma raises this if, e.g., the user changes the embedding model size in config.py
        if "dimension" in str(e).lower():
            raise ValueError(
                f"Embedding dimension mismatch! You attempted to search with a "
                f"{len(query_embedding)}-dimensional vector, but the vector database "
                f"was originally built with a different model. Run ingestion again to reset. "
                f"(Original error: {e})"
            ) from e
        raise e
    
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    
    if not documents or not documents[0]:
        return []
        
    formatted_results = []
    for doc, meta in zip(documents[0], metadatas[0]):
        src = meta.get("source", "unknown") if meta else "unknown"
        top = meta.get("topic", "unknown") if meta else "unknown"
        formatted_results.append(f"[{src}:{top}]\n{doc}")
        
    return formatted_results
