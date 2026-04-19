"""
tests/system/test_tools.py

Real integration tests for sysagent.system.tools.

Philosophy:
  - We call the REAL functions against the REAL host OS.
    No mocks — mocks give false confidence for system-call wrappers.
  - We assert on STRUCTURE and TYPE, not on specific values,
    since metrics change every second.
  - query_knowledge_base is marked @pytest.mark.integration because
    it requires a live OpenAI API key.
"""

import json
import pytest
import subprocess
import psutil
from sysagent.system.tools import (
    MAX_JOURNAL_LINES,
    MAX_PROCESSES,
    _format_uptime,
    get_system_metrics,
    get_top_processes,
    query_knowledge_base,
    read_journal_tail,
    check_command_exists,
)


# ===========================================================================
# _format_uptime (pure logic — no system calls, deterministic)
# ===========================================================================

class TestFormatUptime:

    def test_zero_seconds(self):
        """A fresh boot with 0s uptime should render as '0m'."""
        assert _format_uptime(0) == "0m"

    def test_minutes_only(self):
        """60 seconds = exactly 1 minute, no hours or days prefix."""
        assert _format_uptime(60) == "1m"

    def test_sub_minute_rounds_down(self):
        """45 seconds is less than a minute and should render as '0m'."""
        assert _format_uptime(45) == "0m"

    def test_hours_and_minutes(self):
        """3661 seconds = 1 hour, 1 minute."""
        assert _format_uptime(3661) == "1h 1m"

    def test_hours_only_no_extra_days(self):
        """3600 seconds = exactly 1 hour, 0 minutes (minutes always present)."""
        assert _format_uptime(3600) == "1h 0m"

    def test_days_hours_minutes(self):
        """90061 seconds = 1 day, 1 hour, 1 minute."""
        assert _format_uptime(90061) == "1d 1h 1m"

    def test_days_no_hours(self):
        """86400 seconds = exactly 1 day, 0 hours (hours omitted when 0)."""
        assert _format_uptime(86400) == "1d 0m"


# ===========================================================================
# get_system_metrics
# ===========================================================================

class TestGetSystemMetrics:

    def test_returns_no_error(self):
        """The happy path should never return an error key."""
        result = get_system_metrics()
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_top_level_keys(self):
        """All five expected top-level sections must be present."""
        result = get_system_metrics()
        assert set(result.keys()) == {"cpu", "memory", "swap", "load_average", "uptime"}

    def test_cpu_section(self):
        """CPU section must have valid numeric fields within sane ranges."""
        cpu = get_system_metrics()["cpu"]
        assert "percent" in cpu
        assert "core_count_logical" in cpu
        assert "core_count_physical" in cpu
        assert isinstance(cpu["percent"], float)
        assert 0.0 <= cpu["percent"] <= 100.0
        assert cpu["core_count_logical"] >= 1
        assert cpu["core_count_physical"] >= 1

    def test_memory_section(self):
        """Memory section must have valid MB values and a sane usage percent."""
        mem = get_system_metrics()["memory"]
        assert "total_mb" in mem
        assert "available_mb" in mem
        assert "used_mb" in mem
        assert "percent" in mem
        assert mem["total_mb"] > 0
        assert 0.0 <= mem["percent"] <= 100.0

    def test_swap_section(self):
        """Swap section must be present. Usage percent must be a valid range."""
        swap = get_system_metrics()["swap"]
        assert "total_mb" in swap
        assert "used_mb" in swap
        assert "percent" in swap
        assert 0.0 <= swap["percent"] <= 100.0

    def test_load_average_section(self):
        """Load average section must have 1m, 5m, and 15m keys as floats."""
        load = get_system_metrics()["load_average"]
        assert set(load.keys()) == {"1m", "5m", "15m"}
        for key, val in load.items():
            assert isinstance(val, float), f"load_average[{key!r}] is not a float"
            assert val >= 0.0

    def test_uptime_is_nonempty_string(self):
        """Uptime must be a non-empty human-readable string."""
        uptime = get_system_metrics()["uptime"]
        assert isinstance(uptime, str)
        assert len(uptime) > 0

    def test_get_system_metrics_exception(self, monkeypatch):
        """Proves that a catastrophic psutil failure is caught and returned as an error dict."""
        def mock_raise(*args, **kwargs):
            raise Exception("Simulated psutil crash")
        
        monkeypatch.setattr(psutil, "cpu_percent", mock_raise)
        result = get_system_metrics()
        
        assert "error" in result
        assert "Simulated psutil crash" in result["error"]


# ===========================================================================
# get_top_processes
# ===========================================================================

class TestGetTopProcesses:

    def test_default_sort_returns_no_error(self):
        """Default call (sort_by='cpu') must not return an error."""
        result = get_top_processes()
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_top_level_keys(self):
        """Result must have sort_by, limit, and processes keys."""
        result = get_top_processes(sort_by="cpu", limit=5)
        assert set(result.keys()) == {"sort_by", "limit", "processes"}

    def test_returns_correct_number_of_processes(self):
        """Returned process list must not exceed the requested limit."""
        result = get_top_processes(sort_by="cpu", limit=5)
        assert len(result["processes"]) <= 5

    def test_process_entry_structure(self):
        """Each process entry must have all required fields with correct types."""
        result = get_top_processes(sort_by="cpu", limit=3)
        for proc in result["processes"]:
            assert "pid" in proc
            assert "name" in proc
            assert "user" in proc
            assert "cpu_percent" in proc
            assert "memory_percent" in proc
            assert "status" in proc
            assert isinstance(proc["pid"], int)
            assert isinstance(proc["cpu_percent"], float)
            assert isinstance(proc["memory_percent"], float)
            assert proc["cpu_percent"] >= 0.0
            assert proc["memory_percent"] >= 0.0

    def test_sorted_by_cpu(self):
        """Processes must be in descending order of cpu_percent."""
        result = get_top_processes(sort_by="cpu", limit=10)
        cpus = [p["cpu_percent"] for p in result["processes"]]
        assert cpus == sorted(cpus, reverse=True), "Processes not sorted by CPU descending"

    def test_sorted_by_memory(self):
        """Processes must be in descending order of memory_percent."""
        result = get_top_processes(sort_by="memory", limit=10)
        mems = [p["memory_percent"] for p in result["processes"]]
        assert mems == sorted(mems, reverse=True), "Processes not sorted by memory descending"

    def test_invalid_sort_by_returns_error(self):
        """An invalid sort_by value must return a structured error dict."""
        result = get_top_processes(sort_by="disk")
        assert "error" in result
        assert "disk" in result["error"]

    def test_limit_is_hard_capped(self):
        """Passing a limit above MAX_PROCESSES must not return more than MAX_PROCESSES."""
        result = get_top_processes(sort_by="cpu", limit=9999)
        assert result["limit"] == MAX_PROCESSES
        assert len(result["processes"]) <= MAX_PROCESSES

    def test_get_top_processes_exception(self, monkeypatch):
        """Proves that a catastrophic psutil.process_iter failure is caught and
        returned as a structured error dict rather than crashing the agent."""
        def mock_raise(*args, **kwargs):
            raise Exception("Simulated process_iter crash")

        monkeypatch.setattr(psutil, "process_iter", mock_raise)
        result = get_top_processes(sort_by="cpu", limit=5)

        assert "error" in result
        assert "Simulated process_iter crash" in result["error"]


# ===========================================================================
# read_journal_tail
# ===========================================================================

class TestReadJournalTail:

    def test_returns_no_error(self):
        """The happy path must not return an error key."""
        result = read_journal_tail(lines=10)
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_top_level_keys(self):
        """Result must always have unit, lines_requested, and either entries or note."""
        result = read_journal_tail(lines=10)
        assert "unit" in result
        assert "lines_requested" in result
        assert "entries" in result or "note" in result

    def test_returns_list_of_strings(self):
        """Each entry must be a string (one journal line per entry)."""
        result = read_journal_tail(lines=10)
        if "entries" in result:
            assert isinstance(result["entries"], list)
            for entry in result["entries"]:
                assert isinstance(entry, str)

    def test_respects_line_limit(self):
        """Returned entries must never exceed the requested line count."""
        result = read_journal_tail(lines=5)
        if "entries" in result:
            assert len(result["entries"]) <= 5

    def test_lines_hard_capped(self):
        """Requesting more than MAX_JOURNAL_LINES must be silently capped."""
        result = read_journal_tail(lines=9999)
        assert result["lines_requested"] == MAX_JOURNAL_LINES

    def test_unit_filter_is_accepted(self):
        """Filtering by a known systemd unit must not raise or return a tool error."""
        # We use 'systemd-journald' as it exists on all systemd systems.
        result = read_journal_tail(unit="systemd-journald.service", lines=5)
        # It may have no entries on some systems, but must never return "error"
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["unit"] == "systemd-journald.service"

    def test_nonexistent_unit_returns_note(self):
        """An unknown unit should return a note about no entries, not a crash."""
        result = read_journal_tail(unit="totally-fake-unit-xyz.service", lines=5)
        # journalctl exits 0 with no output for unknown units
        assert "error" not in result
        assert "entries" in result or "note" in result

    def test_read_journal_tail_timeout(self, monkeypatch):
        """Proves that if journalctl hangs, we catch the timeout instead of hanging the LLM."""
        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="journalctl", timeout=10)
        
        monkeypatch.setattr(subprocess, "run", mock_run)
        result = read_journal_tail(lines=5)
        
        assert "error" in result
        assert "timed out" in result["error"]

    def test_read_journal_tail_not_found(self, monkeypatch):
        """Proves that running on a system without systemd returns a graceful error."""
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("No such file or directory: 'journalctl'")
        
        monkeypatch.setattr(subprocess, "run", mock_run)
        result = read_journal_tail(lines=5)
        
        assert "error" in result
        assert "journalctl not found" in result["error"]

    def test_read_journal_tail_exit_error(self, monkeypatch):
        """Proves that journalctl exit codes != 0 are captured safely."""
        def mock_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], 
                returncode=1, 
                stdout="", 
                stderr="Failed to read journal: Permission denied"
            )
        
        monkeypatch.setattr(subprocess, "run", mock_run)
        result = read_journal_tail(lines=5)
        
        assert "error" in result
        assert "exited with code 1" in result["error"]
        assert "Permission denied" in result["error"]


# ===========================================================================
# check_command_exists
# ===========================================================================

class TestCheckCommandExists:

    def test_existing_command(self):
        """A common Linux binary should return exists=True and a path."""
        result = check_command_exists("ls")
        assert "error" not in result
        assert result["command"] == "ls"
        assert result["exists"] is True
        assert result["path"] is not None
        assert "installed" in result["note"]

    def test_missing_command(self):
        """A fake binary should return exists=False and path=None."""
        result = check_command_exists("somefakecommandxyz123")
        assert "error" not in result
        assert result["command"] == "somefakecommandxyz123"
        assert result["exists"] is False
        assert result["path"] is None
        assert "NOT installed" in result["note"]

    def test_empty_string_returns_error(self):
        """Empty string must return an error."""
        result = check_command_exists("   ")
        assert "error" in result
        assert "non-empty string" in result["error"]


# ===========================================================================
# JSON Serializability Contract
# ===========================================================================

def test_all_tools_are_json_serializable():
    """
    Contract test: every tool's output must be serializable to JSON.

    The ReAct loop passes tool results directly to json.dumps() before
    sending them to the OpenAI API. A single non-serializable value
    (e.g. a datetime object, a psutil type, a Path) would crash the
    entire agent at runtime with a silent TypeError.

    This test catches that class of bug at the tools layer, not in production.
    """
    results = [
        ("get_system_metrics",     get_system_metrics()),
        ("get_top_processes(cpu)",  get_top_processes(sort_by="cpu", limit=3)),
        ("get_top_processes(mem)",  get_top_processes(sort_by="memory", limit=3)),
        ("read_journal_tail",       read_journal_tail(lines=5)),
        ("check_command_exists(ls)", check_command_exists("ls")),
    ]
    for tool_name, result in results:
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"'{tool_name}' returned non-JSON-serializable data: {e}")


# ===========================================================================
# query_knowledge_base  (integration — requires OPENAI_API_KEY + ChromaDB)
# ===========================================================================

@pytest.mark.integration
def test_query_knowledge_base_returns_results(tmp_path, monkeypatch):
    """
    Proves query_knowledge_base correctly embeds a query, hits ChromaDB,
    and returns a structured result with documents.
    We inject a known needle so the assertion is deterministic.
    """
    from sysagent.rag.embedder import get_embeddings
    from sysagent.rag.store import upsert_chunks

    temp_chroma_dir = tmp_path / "chroma_tools_test"
    monkeypatch.setattr("sysagent.rag.store.CHROMA_DB_DIR", temp_chroma_dir)

    # Inject a needle into an isolated temp DB
    needle = "The sysagent_turbo_wrench is used to tighten the flux manifold on sector 9Z."
    embedding = get_embeddings([needle])[0]
    upsert_chunks(source="man8", topic="turbo_wrench", chunks=[needle], embeddings=[embedding])

    result = query_knowledge_base("sysagent_turbo_wrench flux manifold")

    assert "error" not in result, f"Unexpected error: {result.get('error')}"
    assert result["results_found"] >= 1
    assert isinstance(result["documents"], list)

    # The needle must surface in the top results
    combined_text = " ".join(doc["content"] for doc in result["documents"]).lower()
    assert "flux manifold" in combined_text
    assert "sector 9z" in combined_text


@pytest.mark.integration
def test_query_knowledge_base_empty_db_returns_note(tmp_path, monkeypatch):
    """
    An empty ChromaDB should return results_found=0 and a note,
    rather than raising an exception.
    """
    temp_chroma_dir = tmp_path / "chroma_empty"
    monkeypatch.setattr("sysagent.rag.store.CHROMA_DB_DIR", temp_chroma_dir)

    result = query_knowledge_base("OOM killer process eviction")

    assert "error" not in result
    assert result["results_found"] == 0
    assert "note" in result


def test_query_knowledge_base_empty_query_returns_error():
    """An empty or whitespace-only query must return a structured error dict."""
    result = query_knowledge_base("   ")
    assert "error" in result
