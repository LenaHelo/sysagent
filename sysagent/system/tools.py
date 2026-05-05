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

import os
import subprocess
import time
import psutil
from datetime import datetime, timezone

# --- Hard limits (protect LLM context window) ---
MAX_PROCESSES = 20
MAX_JOURNAL_LINES = 200


# ---------------------------------------------------------------------------
# Tool 1: OS Information
# ---------------------------------------------------------------------------

def get_os_info() -> dict:
    """
    Returns detailed information about the host operating system.
    Includes distribution name, version, kernel release, and hostname.
    """
    import platform
    try:
        distro = "Unknown Linux"
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break

        return {
            "distribution": distro,
            "kernel_version": platform.release(),
            "hostname": platform.node(),
            "architecture": platform.machine(),
        }
    except Exception as e:
        return {"error": f"get_os_info failed: {e}"}


# ---------------------------------------------------------------------------
# Tool 2: System Metrics
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
        own_pid = os.getpid()
        results = []
        for proc in procs:
            try:
                entry = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "user": proc.username(),
                    "cpu_percent": round(proc.cpu_percent(), 2),
                    "memory_percent": round(proc.memory_percent(), 2),
                    "status": proc.status(),
                }
                if proc.pid == own_pid:
                    entry["is_sysagent"] = True
                results.append(entry)
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

def query_knowledge_base(query: str, source_filter: str = None) -> dict:
    """
    Performs a semantic search against the SysAgent ChromaDB knowledge base.

    This is the bridge between the live ReAct loop and the RAG pipeline.
    The LLM provides a natural-language query; this tool handles embedding
    and vector retrieval transparently.

    Args:
        query: A natural-language search term (e.g., "OOM killer process selection").
        source_filter: Optional corpus to isolate the search (e.g., "kernel", "man").
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
            source_filter=source_filter
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


# ---------------------------------------------------------------------------
# Tool 5: Check Command Exists
# ---------------------------------------------------------------------------

def check_command_exists(command_name: str) -> dict:
    """
    Checks if a command or executable exists on the system PATH.
    """
    import shutil
    if not command_name or not command_name.strip():
        return {"error": "command_name must be a non-empty string."}
        
    try:
        command_name = command_name.strip()
        path = shutil.which(command_name)
        return {
            "command": command_name,
            "exists": path is not None,
            "path": path,
            "note": f"The command '{command_name}' is installed." if path else f"The command '{command_name}' is NOT installed."
        }
    except Exception as e:
        return {"error": f"check_command_exists failed: {e}"}


# ---------------------------------------------------------------------------
# Private Helper: Paginated CVE Fetch
# ---------------------------------------------------------------------------

def _fetch_paginated_cves(source_package: str, priority: str) -> list:
    """
    Fetches all CVEs from the Ubuntu Security API for a given source package
    and priority level, handling pagination automatically.

    Args:
        source_package: Ubuntu source package name (e.g., 'linux', 'linux-hwe-6.8').
        priority:       Severity level — 'high' or 'critical'.

    Returns:
        A flat list of raw CVE dicts from the API.

    Raises:
        RuntimeError: If the very first API page fails (network error, timeout,
                      or bad response). Mid-pagination errors are tolerated —
                      we return whatever we already collected.
    """
    import requests
    import time
    import sys

    BASE_URL = "https://ubuntu.com/security/cves.json"
    all_cves = []
    offset = 0
    global_retries_left = 1
    partial_warning = False

    while True:
        try:
            response = requests.get(
                BASE_URL,
                params={
                    "package":  source_package,
                    "priority": priority,
                    "offset":   offset,
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            if global_retries_left > 0:
                global_retries_left -= 1
                page_num = (offset // 20) + 1
                print(f"\n[SysAgent] Ubuntu Security API connection slow (fetching page {page_num}). Trying once more...\n", file=sys.stderr)
                time.sleep(2)
                continue
            
            # Exhausted retries
            if offset == 0:
                raise RuntimeError(
                    f"Ubuntu Security API unreachable for package='{source_package}' "
                    f"priority='{priority}': {e}"
                ) from e
            
            # Mid-pagination failure — return what we already have with a warning.
            partial_warning = True
            break

        page_cves = data.get("cves", [])
        all_cves.extend(page_cves)

        total_results = data.get("total_results", 0)
        offset += len(page_cves)

        # Stop when we've collected everything or the server returned an empty page
        if offset >= total_results or not page_cves:
            break

    return all_cves, partial_warning


# ---------------------------------------------------------------------------
# Tool 6: Ubuntu CVE Check
# ---------------------------------------------------------------------------

def check_ubuntu_cves() -> dict:
    """
    Queries the Ubuntu Security API for unpatched High and Critical CVEs
    affecting the host's currently running kernel.

    Steps:
      1. Identifies the host's kernel version, Ubuntu release codename, and
         the upstream source package that built the running kernel binary.
      2. Fetches all High + Critical CVEs for that source package via a
         paginated API loop.
      3. Filters results: only 'needed' (no patch exists) and 'released'
         (patch exists but may not be installed) statuses are surfaced.
         For 'released' CVEs, checks locally whether a kernel upgrade is
         pending via 'apt list --upgradable'. If no upgrade is pending, the
         patch is already installed and the CVE is silently discarded.
      4. Returns a concise, LLM-ready summary dict.

    Note: Requires a Debian/Ubuntu system with dpkg, lsb_release, and apt.
    """
    import requests

    # --- Step 1: Identify host context ---
    try:
        kernel_version = subprocess.check_output(
            ["uname", "-r"], text=True, timeout=5
        ).strip()
    except Exception as e:
        return {"error": f"check_ubuntu_cves: could not read kernel version: {e}"}

    try:
        os_codename = subprocess.check_output(
            ["lsb_release", "-cs"], text=True, timeout=5
        ).strip()
    except FileNotFoundError:
        return {"error": "check_ubuntu_cves: lsb_release not found. This tool requires an Ubuntu/Debian system."}
    except Exception as e:
        return {"error": f"check_ubuntu_cves: could not read OS codename: {e}"}

    try:
        # "dpkg -S /boot/vmlinuz-6.8.0-110-generic" →
        # "linux-image-6.8.0-110-generic: /boot/vmlinuz-6.8.0-110-generic"
        dpkg_out = subprocess.check_output(
            ["dpkg", "-S", f"/boot/vmlinuz-{kernel_version}"],
            text=True, stderr=subprocess.DEVNULL, timeout=5
        ).strip()
        binary_package = dpkg_out.split(":")[0].strip()

        # Resolve binary package → source package name
        # e.g. "linux-image-6.8.0-110-generic" → "linux" or "linux-hwe-6.8"
        source_package = subprocess.check_output(
            ["dpkg-query", "-f=${source:Package}", "-W", binary_package],
            text=True, timeout=5
        ).strip()

        # dpkg-query returns empty string if the Source field is absent,
        # which means the binary package IS the source package.
        if not source_package:
            source_package = binary_package

        # The Ubuntu API tracks vulnerabilities under the base kernel package
        # (e.g., 'linux' or 'linux-hwe-6.8'). If the kernel is signed for Secure Boot,
        # dpkg reports 'linux-signed' or 'linux-hwe-6.8-signed'. The API rejects 
        # '-signed' packages with a 422 error, so we must strip the suffix.
        if source_package.endswith("-signed"):
            source_package = source_package[:-7]

    except FileNotFoundError:
        return {"error": "check_ubuntu_cves: dpkg not found. This tool requires a Debian/Ubuntu system."}
    except Exception as e:
        return {"error": f"check_ubuntu_cves: could not resolve kernel source package: {e}"}

    import concurrent.futures

    # --- Step 2: Fetch all High and Critical CVEs (paginated) concurrently ---
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_high = executor.submit(_fetch_paginated_cves, source_package, "high")
            future_crit = executor.submit(_fetch_paginated_cves, source_package, "critical")
            
            high_cves, high_warn = future_high.result()
            critical_cves, crit_warn = future_crit.result()
            
        all_raw_cves = high_cves + critical_cves
        had_partial_warning = high_warn or crit_warn
    except RuntimeError as e:
        return {"error": f"check_ubuntu_cves: API call failed — {e}"}

    if not all_raw_cves:
        return {
            "kernel_version":      kernel_version,
            "os_codename":         os_codename,
            "source_package":      source_package,
            "total_vulnerabilities": 0,
            "vulnerabilities":     [],
            "note": "Ubuntu Security API returned no High or Critical CVEs for this kernel, or the API was unreachable.",
        }

    # --- Step 3: Check locally if a kernel upgrade is pending ---
    # This is used to classify 'released' CVEs: if Ubuntu published a fix
    # but the user hasn't run 'apt upgrade', they are still exposed.
    try:
        upgradable_out = subprocess.check_output(
            ["apt", "list", "--upgradable"],
            text=True, stderr=subprocess.DEVNULL, timeout=15
        )
        kernel_upgrade_pending = any(
            "linux-image" in line
            for line in upgradable_out.splitlines()
        )
    except Exception:
        # Can't determine — report 'released' CVEs conservatively
        kernel_upgrade_pending = None

    # --- Step 4: Filter CVEs by codename and patch status ---
    vulnerabilities = []

    for cve in all_raw_cves:
        cve_id      = cve.get("id", "Unknown")
        priority    = cve.get("priority", "unknown")
        description = cve.get("description", "No description available.")[:300]

        # The API returns all packages affected by this CVE.
        # We only care about our source package.
        for pkg in cve.get("packages", []):
            if pkg.get("name") != source_package:
                continue

            # Inside that package, find the status row for our OS release.
            for status_entry in pkg.get("statuses", []):
                if status_entry.get("release_codename") != os_codename:
                    continue

                status = status_entry.get("status")

                if status == "needed":
                    vulnerabilities.append({
                        "cve_id":       cve_id,
                        "priority":     priority.upper(),
                        "description":  description,
                        "patch_status": "No patch released by Ubuntu yet.",
                        "action":       "Monitor Ubuntu Security Notices (https://ubuntu.com/security/notices) for updates.",
                    })

                elif status == "released":
                    if kernel_upgrade_pending is True:
                        vulnerabilities.append({
                            "cve_id":       cve_id,
                            "priority":     priority.upper(),
                            "description":  description,
                            "patch_status": "Patch released by Ubuntu but NOT yet installed on this machine.",
                            "action":       "Run: sudo apt update && sudo apt upgrade",
                        })
                    elif kernel_upgrade_pending is False:
                        # No pending kernel upgrade → patch is already installed. Safe.
                        pass
                    else:
                        # Could not determine upgrade state — report conservatively.
                        vulnerabilities.append({
                            "cve_id":       cve_id,
                            "priority":     priority.upper(),
                            "description":  description,
                            "patch_status": "Patch released by Ubuntu. Install status could not be determined.",
                            "action":       "Run: sudo apt update && sudo apt upgrade to ensure the fix is applied.",
                        })

                # All other statuses (DNE, ignored, deferred, needs-triage) are silently discarded.
                break  # Found our codename entry — no need to scan further statuses.
            break  # Found our source package — no need to scan further packages.

    result = {
        "kernel_version":        kernel_version,
        "os_codename":           os_codename,
        "source_package":        source_package,
        "total_vulnerabilities": len(vulnerabilities),
        "vulnerabilities":       vulnerabilities,
    }
    
    if had_partial_warning:
        result["warning"] = "Partial data returned due to API timeouts."
        
    return result
