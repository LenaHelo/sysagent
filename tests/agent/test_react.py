"""
tests/agent/test_react.py

End-to-End integration tests for the ReAct loop.
These tests use the live OpenAI API and real local system tools to prove
the autonomous loop can decide, execute, ingest, and summarize in a single
blocking function call.
"""

import pytest
from unittest.mock import MagicMock
from sysagent.agent.react import run_react_loop

@pytest.mark.integration
def test_react_loop_e2e_health_check():
    """
    Proves the loop can handle a basic health check request end-to-end.
    The LLM must invoke get_system_metrics, ingest the JSON, and return a text summary.
    """
    prompt = "what is the cpu?"
    
    # This will block while the LLM thinks, asks for a tool call, 
    # executes it locally, and generates the final text.
    answer = run_react_loop(prompt, verbose=True)  # Turning verbose ON so you see the tool execution too
    
    print("\n" + "="*50)
    print("🤖 LLM FINAL ANSWER:")
    print("="*50)
    print(answer)
    print("="*50 + "\n")
    
    assert isinstance(answer, str)
    assert len(answer) > 0
    assert "could not reach a conclusion" not in answer  # Ensure it didn't hit the breaker
    
    # The answer should mention aspects of the system metrics
    answer_lower = answer.lower()
    assert any(term in answer_lower for term in ["cpu", "memory", "ram", "load", "percent"]), \
        f"LLM did not incorporate metrics into answer: '{answer}'"


@pytest.mark.integration
def test_react_loop_circuit_breaker():
    """
    Proves the loop aborts and returns the fallback message if max_steps is hit.
    We enforce this by setting max_steps=0, instantly triggering the breaker.
    """
    answer = run_react_loop("What is my CPU?", max_steps=0)
    
    assert isinstance(answer, str)
    assert "could not reach a conclusion within 0 steps" in answer

@pytest.mark.integration
def test_react_loop_vague_multi_step():
    """
    Tests the loop's ability to chain reasoning. 
    A vague complaint like 'the server feels sluggish' should prompt the LLM 
    to first check metrics, realize it's slow (or normal), and then check top processes,
    making it a multi-step sequence.
    """
    prompt = "Users are complaining the server feels kind of sluggish right now. Can you investigate root causes?"
    
    print("\n" + "="*50)
    print("🧠 TESTING MULTI-STEP REASONING")
    print("="*50)
    
    answer = run_react_loop(prompt, verbose=True)
    
    print("\n" + "="*50)
    print("🤖 LLM FINAL ANSWER:")
    print("="*50)
    print(answer)
    print("="*50 + "\n")
    
    assert isinstance(answer, str)
    assert len(answer) > 0


# ===========================================================================
# Unit Tests (no API calls — fast, free, deterministic)
# ===========================================================================

def test_react_empty_query():
    """The empty-query guard must short-circuit before any API call is made."""
    assert run_react_loop("") == "Please ask a valid question."


def test_react_whitespace_query():
    """A whitespace-only query must be caught by the same guard."""
    assert run_react_loop("   ") == "Please ask a valid question."


def test_react_unknown_tool_does_not_crash(monkeypatch):
    """
    If the LLM hallucinates a tool name not in TOOL_DISPATCHER, the loop must
    feed a structured error back to the LLM and reach a graceful conclusion.
    Uses monkeypatching to avoid any real API cost.
    """
    # --- Fake first response: LLM requests a tool that doesn't exist ---
    fake_tool_call = MagicMock()
    fake_tool_call.id = "call_fake_001"
    fake_tool_call.function.name = "get_disk_usage"  # Not in TOOL_DISPATCHER
    fake_tool_call.function.arguments = "{}"

    fake_msg_tool = MagicMock()
    fake_msg_tool.tool_calls = [fake_tool_call]

    fake_choice_tool = MagicMock()
    fake_choice_tool.finish_reason = "tool_calls"
    fake_choice_tool.message = fake_msg_tool

    fake_resp_1 = MagicMock()
    fake_resp_1.choices = [fake_choice_tool]

    # --- Fake second response: LLM gives up gracefully with text ---
    fake_msg_stop = MagicMock()
    fake_msg_stop.content = "Disk usage tool is unavailable. Cannot retrieve that information."
    fake_msg_stop.tool_calls = None

    fake_choice_stop = MagicMock()
    fake_choice_stop.finish_reason = "stop"
    fake_choice_stop.message = fake_msg_stop

    fake_resp_2 = MagicMock()
    fake_resp_2.choices = [fake_choice_stop]

    # Wire a mock client that returns the two responses in sequence
    mock_create = MagicMock(side_effect=[fake_resp_1, fake_resp_2])
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create
    monkeypatch.setattr("sysagent.agent.react.get_openai_client", lambda: mock_client)

    result = run_react_loop("What is my disk usage?")

    assert isinstance(result, str)
    assert len(result) > 0
    assert "could not reach a conclusion" not in result
    # Exactly 2 API round-trips: one for the tool request, one for the final answer
    assert mock_create.call_count == 2


# ===========================================================================
# Integration Tests (real API + patched tools)
# ===========================================================================

@pytest.mark.integration
def test_react_out_of_scope_stops_without_tool_call():
    """
    An off-topic question must trigger the REACT_SYSTEM_PROMPT scope refusal
    via the full loop, proving the finish_reason == 'stop' path fires immediately
    with no tool execution whatsoever.
    """
    answer = run_react_loop("Can you write me a chocolate cake recipe?")

    assert isinstance(answer, str)
    assert len(answer) > 0
    assert "could not reach a conclusion" not in answer

    answer_lower = answer.lower()
    assert any(w in answer_lower for w in ["linux", "diagnostic", "sysagent", "only"]), \
        f"Expected a scope refusal from the loop, but got: '{answer}'"


@pytest.mark.integration
def test_react_tool_error_produces_graceful_answer(monkeypatch):
    """
    When a tool returns {"error": "..."}, the loop must feed that error JSON
    to the LLM and converge to a graceful text answer — not crash or hang.
    Proves the error dict is a valid signal the LLM can reason about.
    """
    from sysagent.agent.react import TOOL_DISPATCHER

    def broken_metrics():
        return {"error": "psutil internal failure: mocked kernel panic"}

    # Replace only get_system_metrics in the dispatcher; leave all others intact
    broken_dispatcher = {**TOOL_DISPATCHER, "get_system_metrics": broken_metrics}
    monkeypatch.setattr("sysagent.agent.react.TOOL_DISPATCHER", broken_dispatcher)

    answer = run_react_loop("How is my CPU doing right now?", verbose=True)

    assert isinstance(answer, str)
    assert len(answer) > 0
    # The loop must not silently crash — it must produce a meaningful response
