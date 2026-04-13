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

from sysagent.agent.react import REACT_SYSTEM_PROMPT, run_react_loop

BANNER = """
╔════════════════════════════════════════════╗
║      SysAgent — Linux Engineer AI          ║
║  Ask anything about your Linux system.     ║
║  Type 'exit' or press Ctrl+C to quit.      ║
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
    messages = [{"role": "system", "content": REACT_SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("› ").strip()
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
