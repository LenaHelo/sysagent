import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Directory Paths ---
# Use ~/.config/sysagent for all persistent application data
USER_HOME = Path.home()
SYSAGENT_DATA_DIR = USER_HOME / ".config" / "sysagent"
CHROMA_DB_DIR = SYSAGENT_DATA_DIR / "chroma_db"
MANIFEST_PATH = SYSAGENT_DATA_DIR / "ingestion_manifest.json"

# --- RAG Ingestion Preferences ---
CHROMA_COLLECTION_NAME = "sysagent_core_knowledge"

# MAN_SECTIONS defines the active corpus for the RAG ingestion pipeline.
# Phase 1 (Micro-MVP): Only man1 and man8 to validate the pipeline.
MAN_SECTIONS = ["1", "8"]

# --- Deferred Data Sources ---
# Uncomment sections below as the project expands:
#
# Phase 2 — Additional man sections:
#   "4"  — Special device files (/dev/*)
#   "5"  — File formats and config files (/etc/fstab, etc.)
#   "7"  — Miscellaneous (ip(7), boot(7), etc.)
#
# Phase 3 — Advanced (requires new RSTExtractor):
#   "2"  — Linux system calls (fork, mmap, execve...)
#   "3"  — C library functions (malloc, pthread...) — large corpus, use with caution
#
# Phase 3 — Kernel documentation:
# Path to the Linux kernel Documentation/ directory (RST source files).
# Set KERNEL_DOCS_PATH in your .env file to enable this ingestion source.
# Example: KERNEL_DOCS_PATH=/usr/share/doc/linux-doc/Documentation
# If unset or the path does not exist, kernel doc ingestion is skipped gracefully.
_raw_kernel_docs_path = os.getenv("KERNEL_DOCS_PATH", "").strip()
KERNEL_DOCS_PATH: Path | None = Path(_raw_kernel_docs_path) if _raw_kernel_docs_path else None

# --- Chunking & Embedding Variables ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"

# --- Retrieval Limits ---
# Controls how many discrete chunks are injected into the LLM context window
TOP_K_RESULTS = 10

# --- LLM Configuration ---
# The model used for all chat completions (RAG mode and ReAct loop).
# Change this one line to switch the entire application to a different model.
LLM_MODEL = "gpt-4o-mini"

# Maximum number of tool-call iterations in a single ReAct loop run.
# Acts as a circuit breaker to prevent infinite loops.
REACT_MAX_STEPS = 5
