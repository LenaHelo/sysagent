#!/usr/bin/env python3
"""
Directive Discovery Script
==========================
A one-time utility that scans all .rst files in the Linux kernel Documentation/
directory and reports every unique Sphinx directive found, ranked by frequency.

The output of this script is used to manually categorize directives into
DROP (structural metadata) or PASSTHROUGH (content wrappers) lists, which are
then hardcoded into sysagent/rag/extractor.py.

Usage:
    # Reads KERNEL_DOCS_PATH from .env automatically:
    python scripts/discover_rst_directives.py

    # Or pass the path explicitly:
    python scripts/discover_rst_directives.py /path/to/linux/Documentation
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sysagent.config import KERNEL_DOCS_PATH

# RST directive pattern: matches ".. directive-name::" at the start of a line.
# Captures the name part (e.g., "toctree", "c:function", "kernel-doc").
DIRECTIVE_RE = re.compile(r"^\.\.\s+([a-zA-Z][a-zA-Z0-9_:-]*)::.*$")


def discover_directives(docs_path: Path) -> dict[str, set[str]]:
    """
    Walks all .rst files under docs_path and collects every unique directive.

    Returns:
        A dict mapping directive_name -> set of relative file paths where it
        appears. This lets us report both frequency (len of set) and examples.
    """
    directive_files: dict[str, set[str]] = defaultdict(set)
    rst_files = list(docs_path.rglob("*.rst"))

    if not rst_files:
        print(f"[WARNING] No .rst files found under: {docs_path}")
        return {}

    print(f"Scanning {len(rst_files):,} .rst files under: {docs_path}\n")

    for rst_file in rst_files:
        try:
            text = rst_file.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  [SKIP] Cannot read {rst_file}: {e}")
            continue

        for line in text.splitlines():
            m = DIRECTIVE_RE.match(line.strip())
            if m:
                directive_name = m.group(1).lower()
                # Store relative path for traceability
                directive_files[directive_name].add(
                    str(rst_file.relative_to(docs_path))
                )

    return directive_files


def print_report(directive_files: dict[str, set[str]]) -> None:
    """Prints a human-readable, frequency-ranked directive report."""
    if not directive_files:
        print("No directives found.")
        return

    # Sort by frequency descending, then alphabetically for ties
    ranked = sorted(directive_files.items(), key=lambda x: (-len(x[1]), x[0]))

    print(f"{'Directive':<35} {'Files':>6}  {'Example File'}")
    print("-" * 90)
    for name, files in ranked:
        example = sorted(files)[0]  # deterministic example
        print(f"  {name:<33} {len(files):>6}  {example}")

    print("-" * 90)
    print(f"\nTotal unique directives found: {len(ranked)}")
    print("\nNext step:")
    print("  Review the list above and classify each directive in")
    print("  sysagent/rag/extractor.py as either DROP or PASSTHROUGH.")


def main() -> None:
    # Accept an explicit path as a CLI argument, otherwise fall back to config
    if len(sys.argv) > 1:
        docs_path = Path(sys.argv[1])
    elif KERNEL_DOCS_PATH is not None:
        docs_path = KERNEL_DOCS_PATH
    else:
        print("[ERROR] No kernel docs path provided.")
        print("  Either set KERNEL_DOCS_PATH in your .env file, or pass the path as an argument:")
        print("  python scripts/discover_rst_directives.py /path/to/linux/Documentation")
        sys.exit(1)

    if not docs_path.exists():
        print(f"[ERROR] Path does not exist: {docs_path}")
        print("  Download the kernel docs first (e.g.: sudo apt install linux-doc)")
        sys.exit(1)

    if not docs_path.is_dir():
        print(f"[ERROR] Path is not a directory: {docs_path}")
        sys.exit(1)

    directive_files = discover_directives(docs_path)
    print_report(directive_files)


if __name__ == "__main__":
    main()
