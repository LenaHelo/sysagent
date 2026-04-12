"""
tests/agent/test_tool_selection.py

Tests "Tool Selection Isolation".
Proves that the LLM understands our JSON tool schemas and can accurately map
natural language user intent to the correct function call and arguments,
WITHOUT testing the actual loop execution.
"""

import json
import pytest
from sysagent.agent.core import get_openai_client, REACT_SYSTEM_PROMPT
from sysagent.agent.schemas import SYSAGENT_TOOL_SCHEMAS

@pytest.fixture
def openai_client():
    """Provides a real OpenAI client for integration testing tool selection."""
    return get_openai_client()

def ask_for_tool(client, user_query: str) -> dict:
    """Helper to send a query and return exactly what tool the AI decided to call."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ],
        tools=SYSAGENT_TOOL_SCHEMAS,
        temperature=0.0
    )
    
    msg = response.choices[0].message
    
    # 1. Ensure the LLM decided to call a tool, not answer directly
    assert msg.tool_calls is not None, f"Expected a tool call, but LLM replied: {msg.content}"
    assert len(msg.tool_calls) > 0
    
    # 2. Extract the tool decision
    tool_call = msg.tool_calls[0]
    return {
        "name": tool_call.function.name,
        "arguments": json.loads(tool_call.function.arguments)
    }

# --- The Granular Intent Tests ---

@pytest.mark.integration
def test_intent_system_health(openai_client):
    """'Is my system healthy?' -> Should map to get_system_metrics"""
    decision = ask_for_tool(openai_client, "Give me a quick health check of this server.")
    assert decision["name"] == "get_system_metrics"

@pytest.mark.integration
def test_intent_cpu_hog(openai_client):
    """'What's using my CPU?' -> Should map to get_top_processes(sort_by='cpu')"""
    decision = ask_for_tool(openai_client, "What is eating up all my CPU right now?")
    assert decision["name"] == "get_top_processes"
    assert decision["arguments"]["sort_by"] == "cpu"

@pytest.mark.integration
def test_intent_memory_hog(openai_client):
    """'Why am I out of memory?' -> Should map to get_top_processes(sort_by='memory')"""
    decision = ask_for_tool(openai_client, "The server is out of RAM. What process is causing this?")
    assert decision["name"] == "get_top_processes"
    assert decision["arguments"]["sort_by"] == "memory"

@pytest.mark.integration
def test_intent_service_crash(openai_client):
    """'Why did nginx crash?' -> Should map to read_journal_tail(unit='nginx.service')"""
    decision = ask_for_tool(openai_client, "Why did my nginx server crash 5 minutes ago?")
    assert decision["name"] == "read_journal_tail"
    
    # The LLM is smart enough to append '.service' if the schema implies it
    args = decision["arguments"]
    assert "unit" in args
    assert "nginx" in args["unit"]

@pytest.mark.integration
def test_intent_rag_lookup(openai_client):
    """'What does this error mean?' -> Should map to query_knowledge_base"""
    decision = ask_for_tool(openai_client, "I saw something about 'swappiness=60' in the metrics. What does swappiness do in Linux?")
    assert decision["name"] == "query_knowledge_base"
    assert "swappiness" in decision["arguments"]["query"].lower()


@pytest.mark.integration
def test_intent_out_of_scope_does_not_trigger_tools(openai_client):
    """
    An off-topic request must NEVER invoke a diagnostic tool.
    The LLM must decline politely using only a text response.
    Proves that the scope-limiting clause in REACT_SYSTEM_PROMPT works.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": "Can you give me a chocolate cake recipe?"}
        ],
        tools=SYSAGENT_TOOL_SCHEMAS,
        temperature=0.0
    )

    choice = response.choices[0]

    # The LLM must reply with text, not a tool call
    assert choice.finish_reason == "stop", (
        f"Expected text reply but got finish_reason='{choice.finish_reason}'. "
        f"Tool called: {choice.message.tool_calls}"
    )
    assert choice.message.tool_calls is None

    # The reply must acknowledge the scope limitation
    reply = choice.message.content.lower()
    assert any(word in reply for word in ["linux", "diagnostic", "system", "specialize", "assist"]), (
        f"Expected a redirect/decline, but got: {choice.message.content}"
    )
