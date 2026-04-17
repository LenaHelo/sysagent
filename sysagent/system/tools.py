"""
sysagent/system/tools.py

Live system data collection tools for the SysAgent ReAct loop.

Design rules:
  - All tools are READ-ONLY. No mutations to the host system.
  - All tools return a plain Python dict (JSON-serializable).
  - All tools catch exceptions and return {"error": "..."} so the
    agent can reason about a failure rather than crash.
  - Hard limits on output size are enforced in code, never delegated
    to the LLM or the caller.
"""

import subprocess
import time
import psutil
from datetime import datetime, timezone

# --- Hard limits (protect LLM context window) ---
MAX_PROCESSES = 20
MAX_JOURNAL_LINES = 200


# ---------------------------------------------------------------------------
# Tool 1: System Metrics
# ---------------------------------------------------------------------------

def get_system_metrics() -> dict:
    """
    Returns a snapshot of the host system's vital signs.

    Captures:
      - CPU utilization (%) — 1-second non-blocking sample
      - Memory: total, available, used, usage %
      - Swap: total, used, usage %
      - Load average: 1m, 5m, 15m
      - System uptime in human-readable form
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        load_1, load_5, load_15 = psutil.getloadavg()
        boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        uptime_seconds = int((now - boot_time).total_seconds())
        uptime_str = _format_uptime(uptime_seconds)

        return {
            "cpu": {
                "percent": cpu_percent,
                "core_count_logical": psutil.cpu_count(logical=True),
                "core_count_physical": psutil.cpu_count(logical=False),
            },
            "memory": {
                "total_mb": round(mem.total / 1024 / 1024, 1),
                "available_mb": round(mem.available / 1024 / 1024, 1),
                "used_mb": round(mem.used / 1024 / 1024, 1),
                "percent": mem.percent,
            },
            "swap": {
                "total_mb": round(swap.total / 1024 / 1024, 1),
                "used_mb": round(swap.used / 1024 / 1024, 1),
                "percent": swap.percent,
            },
            "load_average": {
                "1m": round(load_1, 2),
                "5m": round(load_5, 2),
                "15m": round(load_15, 2),
            },
            "uptime": uptime_str,
        }
    except Exception as e:
        return {"error": f"get_system_metrics failed: {e}"}


# ---------------------------------------------------------------------------
# Tool 2: Top Processes
# ---------------------------------------------------------------------------

def get_top_processes(sort_by: str = "cpu", limit: int = 10) -> dict:
    """
    Returns the top N processes sorted by CPU or memory usage.

    Args:
        sort_by: "cpu" or "memory". Defaults to "cpu".
        limit:   Number of processes to return. Capped at MAX_PROCESSES (20).
    """
    if sort_by not in ("cpu", "memory"):
        return {"error": f"Invalid sort_by value '{sort_by}'. Must be 'cpu' or 'memory'."}

    limit = min(limit, MAX_PROCESSES)

    try:
        # Pass 1: initialize the CPU percent counter for each process.
        # psutil calculates CPU% by diffing two snapshots over time.
        # The very first call always returns 0.0 — we discard it.
        procs = list(psutil.process_iter(["pid", "name", "username", "memory_percent", "status"]))
        for proc in procs:
            try:
                proc.cpu_percent()  # seed the counter, result discarded
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Wait for the counters to accumulate a meaningful sample
        time.sleep(0.5)

        # Pass 2: read the real CPU% values now that we have a delta
        results = []
        for proc in procs:
            try:
                results.append({
                    "pid": proc.pid,
                    "name": proc.name(),
                    "user": proc.username(),
                    "cpu_percent": round(proc.cpu_percent(), 2),
                    "memory_percent": round(proc.memory_percent(), 2),
                    "status": proc.status(),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process may have exited between pass 1 and pass 2 — skip it
                continue

        # Sort by the requested metric
        sort_key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        results.sort(key=lambda p: p[sort_key], reverse=True)

        return {
            "sort_by": sort_by,
            "limit": limit,
            "processes": results[:limit],
        }
    except Exception as e:
        return {"error": f"get_top_processes failed: {e}"}


# ---------------------------------------------------------------------------
# Tool 3: Journal Tail
# ---------------------------------------------------------------------------

def read_journal_tail(unit: str = None, lines: int = 50) -> dict:
    """
    Returns the most recent lines from the systemd journal.

    Args:
        unit:  Optional systemd unit name to filter by (e.g., "nginx.service").
               If None, returns from the system-wide journal.
        lines: Number of lines to return. Capped at MAX_JOURNAL_LINES (200).
    """
    lines = min(lines, MAX_JOURNAL_LINES)

    cmd = ["journalctl", "--no-pager", "--output=short-iso", f"-n{lines}"]
    if unit:
        cmd += ["--unit", unit]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            return {"error": f"journalctl exited with code {result.returncode}: {stderr}"}

        output = result.stdout.strip()
        if not output:
            label = f"unit '{unit}'" if unit else "system journal"
            return {"unit": unit, "lines_requested": lines, "entries": [], "note": f"No entries found for {label}."}

        return {
            "unit": unit,
            "lines_requested": lines,
            "entries": output.splitlines(),
        }
    except FileNotFoundError:
        return {"error": "journalctl not found. This tool requires a systemd-based Linux system."}
    except subprocess.TimeoutExpired:
        return {"error": "journalctl timed out after 10 seconds."}
    except Exception as e:
        return {"error": f"read_journal_tail failed: {e}"}


# ---------------------------------------------------------------------------
# Tool 4: Query Knowledge Base (RAG)
# ---------------------------------------------------------------------------

def query_knowledge_base(query: str, topic_filter: str = None) -> dict:
    """
    Performs a semantic search against the SysAgent ChromaDB knowledge base.

    This is the bridge between the live ReAct loop and the RAG pipeline.
    The LLM provides a natural-language query; this tool handles embedding
    and vector retrieval transparently.

    Args:
        query: A natural-language search term (e.g., "OOM killer process selection").
        topic_filter: Optional command or topic name to isolate the search (e.g., "ls").
    """
    # Import here to avoid circular imports at module load time
    from sysagent.rag.embedder import get_embeddings
    from sysagent.rag.store import query_closest_chunks
    from sysagent.config import TOP_K_RESULTS

    if not query or not query.strip():
        return {"error": "query must be a non-empty string."}

    try:
        query_vector = get_embeddings([query.strip()])[0]
        chunks = query_closest_chunks(
            query_vector, 
            n_results=TOP_K_RESULTS, 
            topic_filter=topic_filter
        )

        if not chunks:
            return {
                "query": query,
                "results_found": 0,
                "documents": [],
                "note": "No relevant documentation found in the knowledge base.",
            }

        return {
            "query": query,
            "results_found": len(chunks),
            "documents": [
                {"index": i + 1, "content": chunk}
                for i, chunk in enumerate(chunks)
            ],
        }
    except Exception as e:
        return {"error": f"query_knowledge_base failed: {e}"}


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------

def _format_uptime(seconds: int) -> str:
    """Converts a raw second count into a human-readable uptime string."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
