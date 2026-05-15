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
    parser.add_argument(
        "--cron",
        action="store_true",
        help="Run headlessly for scheduled audits without the interactive REPL.",
    )
    parser.add_argument(
        "--notify",
        type=str,
        choices=["slack"],
        help="Where to push the scheduled audit report.",
    )
    args = parser.parse_args()

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

    if args.cron:
        print("Starting proactive audit...", file=sys.stderr)
        
        target_platform = args.notify if args.notify else "standard markdown"
        audit_prompt = (
            f"Perform a complete proactive system health check. Analyze current CPU, memory, "
            f"load average, top processes, and unpatched kernel CVEs. Produce a concise "
            f"Executive Summary report formatted specifically for {target_platform}. "
            f"CRITICAL: DO NOT use markdown tables under any circumstances; use aligned code blocks or bulleted lists instead."
        )
        
        try:
            answer = run_react_loop(
                query=audit_prompt,
                verbose=args.verbose,
                messages=messages,
            )
        except Exception as e:
            answer = f"🚨 **SysAgent Critical Alert**\nScheduled audit failed to complete.\n**Error:** `{str(e)}`\n*Please investigate the host manually.*"
            exit_code = 1
        else:
            exit_code = 0
            
        if not args.notify:
            print("\n" + answer)
            
        if args.notify == "slack":
            from sysagent.system.notifiers import send_slack_alert
            print("Sending report to Slack...", file=sys.stderr)
            try:
                success = send_slack_alert(answer)
                if not success:
                    exit_code = 1
            except ValueError as e:
                print(f"Configuration Error: {e}", file=sys.stderr)
                sys.exit(1)
                
        sys.exit(exit_code)

    print(BANNER)
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
