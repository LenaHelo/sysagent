import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sysagent.rag.store import get_chroma_client, get_collection
from sysagent.rag.embedder import get_embeddings

def debug_query():
    client = get_chroma_client()
    collection = get_collection(client)
    
    print(f"Total chunks in collection: {collection.count()}")
    
    query = "how does KSM save memory?"
    print(f"\nQuerying for: '{query}'")
    
    embeddings = get_embeddings([query])
    
    results = collection.query(
        query_embeddings=embeddings,
        n_results=10
    )
    
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    if not documents:
        print("No documents returned!")
        return
        
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        print(f"\n--- Result {i+1} (Distance: {dist}) ---")
        print(f"Metadata: {meta}")
        print(f"Snippet: {doc[:200]}...")

if __name__ == "__main__":
    debug_query()
