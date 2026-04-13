"""
sysagent/agent/react.py

The ReAct (Reasoning and Acting) orchestration loop.
This is the production agentic engine for SysAgent.

Architecture:
  1. The user's query + full message history is sent to the LLM.
  2. If the LLM returns a final text answer  → return it to the caller.
  3. If the LLM requests a tool call         → execute it, append the
     result to the message history, and loop back to step 1.
  4. A MAX_STEPS circuit breaker prevents infinite loops.
"""

import json

from sysagent.agent.core import get_openai_client
from sysagent.agent.schemas import SYSAGENT_TOOL_SCHEMAS
from sysagent.config import LLM_MODEL, REACT_MAX_STEPS
from sysagent.system.tools import (
    get_system_metrics,
    get_top_processes,
    query_knowledge_base,
    read_journal_tail,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Unified System Prompt
# Merges RAG grounding rules + tool-usage rules + scope-limiting rules
# into a single authoritative directive.
# ---------------------------------------------------------------------------

REACT_SYSTEM_PROMPT = """You are SysAgent, an expert Linux systems engineer and diagnostic assistant.

YOUR SCOPE:
You help engineers with ANYTHING related to Linux systems, including:
- Live system diagnostics: CPU usage, memory, processes, swap, load average, uptime, logs.
- Linux concepts and documentation: explaining what metrics mean, kernel parameters,
  error codes, command flags, system calls, and Linux internals.
- Actionable recommendations based on what the diagnostic tools reveal.

CHARITABLE INTERPRETATION:
When a question is ambiguous but relates to Linux, ALWAYS assume the Linux intent.
Never refuse a question that could reasonably relate to Linux administration or concepts.
To determine if a question is live vs conceptual, use this heuristic:
- If a user asks "What is X?" (e.g., "what is a cpu?", "what is swap?"), treat it as a CONCEPTUAL question and search the knowledge base or explain it.
- If a user asks "How is X?", "What is X usage?", or "Why is X...", treat it as a DIAGNOSTIC question and use your live system tools.

HANDLING TRULY OFF-TOPIC REQUESTS:
Only refuse if the question has absolutely no conceivable relationship to Linux systems
(e.g., cake recipes, sports results, creative writing). In that case respond with:
  "I'm SysAgent, a Linux systems engineer assistant. I can help with live system
  diagnostics, Linux concepts, kernel parameters, logs, and anything Linux-related."
Do NOT call any tools for truly off-topic requests.

HOW TO OPERATE:
1. For questions about CURRENT SYSTEM STATE (e.g. "is my CPU high?", "what's using RAM?"):
   use get_system_metrics, get_top_processes, or read_journal_tail for live data.
2. For questions about LINUX CONCEPTS (e.g. "what is swap?", "what does OOM mean?"):
   use query_knowledge_base to search the Linux documentation database FIRST.
3. STRICT CITATION RULE FOR CONCEPTS:
   - If query_knowledge_base returns relevant documentation, you MUST base your answer on it and state:
     "According to the local system documentation..."
   - If query_knowledge_base returns nothing useful, you MAY use your pre-trained knowledge, but you MUST
     start your answer with: "I couldn't find local documentation for this, but based on general Linux knowledge..."
4. Be concise and precise. You are talking to engineers, not end-users.
"""

# ---------------------------------------------------------------------------
# Tool Dispatcher
# Secure mapping of tool name strings → executable Python functions.
# An unknown tool name will always return a structured error, never a crash.
# ---------------------------------------------------------------------------

TOOL_DISPATCHER = {
    "get_system_metrics": get_system_metrics,
    "get_top_processes": get_top_processes,
    "read_journal_tail": read_journal_tail,
    "query_knowledge_base": query_knowledge_base,
}


# ---------------------------------------------------------------------------
# ReAct Loop
# ---------------------------------------------------------------------------

def run_react_loop(
    query: str,
    model: str = LLM_MODEL,
    verbose: bool = False,
    max_steps: int = REACT_MAX_STEPS,
    messages: list = None,
) -> str:
    """
    The core ReAct orchestration loop.

    Sends the user query to the LLM, processes any tool calls it requests,
    feeds results back into the message history, and repeats until the LLM
    produces a final text answer or the circuit breaker fires.

    Args:
        query:     The user's diagnostic question.
        model:     OpenAI model to use. Defaults to gpt-4o-mini.
        verbose:   If True, prints each tool call to stdout as it executes.
                   Controlled by the -v / --verbose CLI flag.
        max_steps: Maximum number of tool-call rounds before giving up.
                   Prevents infinite loops. Defaults to MAX_STEPS (5).

    Returns:
        The LLM's final diagnostic answer as a plain string.
    """
    query = query.strip()
    if not query:
        return "Please ask a valid question."

    client = get_openai_client()

    # Initialize message history if this is the very first turn
    if messages is None:
        messages = [{"role": "system", "content": REACT_SYSTEM_PROMPT}]
    
    messages.append({"role": "user", "content": query})

    for step in range(max_steps):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=SYSAGENT_TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.0,
        )

        choice = response.choices[0]
        assistant_message = choice.message

        # Persist the assistant's reply (text or tool request) in history
        messages.append(assistant_message)

        # ── Case A: LLM has produced a final text answer ──────────────────
        if choice.finish_reason == "stop":
            return assistant_message.content.strip()

        # ── Case B: LLM is requesting one or more tool calls ──────────────
        if choice.finish_reason == "tool_calls":
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name

                # 1. Parse the arguments JSON string the LLM returned
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    result = {"error": f"Failed to parse tool arguments: {e}"}
                else:
                    # 2. Optionally surface what's happening to the user
                    if verbose:
                        args_display = ", ".join(
                            f"{k}={v!r}" for k, v in tool_args.items()
                        )
                        print(f"  ⚙  [Step {step + 1}/{max_steps}] Calling {tool_name}({args_display})...")

                    # 3. Resolve and execute the tool from the dispatcher
                    tool_fn = TOOL_DISPATCHER.get(tool_name)
                    if tool_fn is None:
                        result = {
                            "error": (
                                f"Unknown tool requested: '{tool_name}'. "
                                f"Valid tools: {list(TOOL_DISPATCHER.keys())}"
                            )
                        }
                    else:
                        try:
                            result = tool_fn(**tool_args)
                        except TypeError as e:
                            # LLM passed wrong argument names or types
                            result = {"error": f"Invalid arguments for '{tool_name}': {e}"}
                        except Exception as e:
                            result = {"error": f"Tool '{tool_name}' failed unexpectedly: {e}"}

                # 4. Feed the result back into the message history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

    # ── Circuit breaker: max_steps exhausted without a final answer ────────
    return (
        f"SysAgent could not reach a conclusion within {max_steps} steps. "
        "The system may be in an unusual state. Please try rephrasing your question."
    )
