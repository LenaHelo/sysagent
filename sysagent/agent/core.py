import os
from openai import OpenAI
from sysagent.config import TOP_K_RESULTS
from sysagent.rag.embedder import get_embeddings
from sysagent.rag.store import query_closest_chunks

# The strict system prompt forcing the LLM to ground itself in RAG context (single-shot mode)
SYSTEM_PROMPT = """You are SysAgent, an expert Linux diagnostic assistant.
Your instructions are strict:
1. You must answer the user's question using ONLY the provided documentation context below.
2. If the context does not contain the answer, say "I don't know based on the provided context." Do not guess.
3. If the context contradicts your pre-trained knowledge, treat the context as the supreme truth.
4. Do NOT correct typos, formatting, or grammar found in the context. Use the exact terminology, strings, and unusual characters exactly as provided.
"""

# The system prompt for the ReAct agentic loop (tool-calling mode)
REACT_SYSTEM_PROMPT = """You are SysAgent, a specialized Linux system diagnostic assistant.

Your capabilities and STRICT boundaries:
1. Your ONLY purpose is to diagnose Linux systems. You have tools to inspect CPU, memory,
   processes, system logs, and a Linux documentation knowledge base.
2. Always use your tools to gather real data before answering. Do not rely on pre-trained
   knowledge for system state — the host's actual data is the only truth.
3. If the user's request is unrelated to Linux system diagnostics (e.g., recipes, general
   knowledge, creative writing), politely decline and redirect them. Do NOT call any tools
   for off-topic requests.
4. Be concise and precise. You are talking to engineers, not end-users.
"""
def get_openai_client() -> OpenAI:
    """Returns an authenticated OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=api_key)

def ask_sysagent(query: str, model: str = "gpt-4o-mini") -> str:
    """
    Main orchestration function for the RAG-enabled Agent.
    1. Embeds the user question.
    2. Retrieves the closest documentation chunks from ChromaDB.
    3. Feeds context to the LLM to generate a grounded answer.
    """
    query = query.strip()
    if not query:
        return "Please ask a valid question."

    # 1. Embed the query to create a mathematical search vector
    query_vector = get_embeddings([query])[0]
    
    # 2. Retrieve top matching chunks from our database
    semantic_results = query_closest_chunks(query_vector, n_results=TOP_K_RESULTS)
    
    # 3. Format the context for the LLM
    context_blocks = []
    for i, chunk in enumerate(semantic_results):
        # We wrap each chunk clearly so the LLM knows it's a discrete document piece
        formatted_chunk = f"--- DOCUMENT {i+1} ---\n{chunk}\n-------------------"
        context_blocks.append(formatted_chunk)
        
    compiled_context = "\n\n".join(context_blocks)
    
    # 4. Construct the prompt
    user_prompt = f"Context:\n{compiled_context}\n\nUser Question: {query}"
    # 5. Ask OpenAI
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0 # Strict determinism for diagnostics
    )
    
    return response.choices[0].message.content.strip()
