"""
sysagent/main.py

Entry point for SysAgent — the AI-powered Linux diagnostic assistant.

Starts an interactive conversational session. The full message history is
preserved for the lifetime of the session, so the agent understands follow-up
questions in context.

Usage:
    python -m sysagent.main          # Standard mode (silent tool execution)
    python -m sysagent.main -v       # Verbose mode (shows each tool call)
"""

import argparse
import sys

from dotenv import load_dotenv
from prompt_toolkit import PromptSession

from sysagent.agent.react import REACT_SYSTEM_PROMPT, run_react_loop

BANNER = """
╔════════════════════════════════════════════╗
║      SysAgent — Linux Engineer AI          ║
║  Ask anything about your Linux system.     ║
║                                            ║
║  Submit  : Alt+Enter  (or Esc then Enter)  ║
║  Quit    : Type 'exit' or press Ctrl+C     ║
╚════════════════════════════════════════════╝
"""


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="SysAgent — AI-powered Linux diagnostic assistant."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print each tool call as it executes (e.g. ⚙ Calling get_system_metrics()).",
    )
    args = parser.parse_args()

    print(BANNER)

    # The shared message history for this session.
    # Initialized once here and passed into every run_react_loop call,
    # giving the LLM full conversational context on every follow-up question.
    
    import platform
    import os
    
    distro = "Unknown Linux"
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    distro = line.split("=", 1)[1].strip().strip('"')
                    break
                    
    kernel = platform.release()
    dynamic_prompt = f"You are SysAgent, running directly on {distro} (Kernel {kernel}).\n\n{REACT_SYSTEM_PROMPT}"
    
    messages = [{"role": "system", "content": dynamic_prompt}]
    session = PromptSession(multiline=True)

    while True:
        try:
            print("\n" + "─" * 45) # Visual separator for multiline blocks
            user_input = session.prompt("› ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye.")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            sys.exit(0)

        print()  # breathing room before the answer
        answer = run_react_loop(
            query=user_input,
            verbose=args.verbose,
            messages=messages,
        )
        print(answer)
        print()  # breathing room after the answer


if __name__ == "__main__":
    main()
