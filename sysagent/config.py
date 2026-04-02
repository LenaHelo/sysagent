import os
from pathlib import Path

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
#   Sourced from /usr/share/doc/linux-doc/ (RST format)
#   Requires: apt install linux-doc
#   Requires: RSTExtractor implementation in sysagent/rag/extractor.py

# --- Chunking & Embedding Variables ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"

# --- Retrieval Limits ---
# Controls how many discrete chunks are injected into the LLM context window
TOP_K_RESULTS = 5
