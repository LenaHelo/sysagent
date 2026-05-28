---
marp: true
theme: default
class: lead
paginate: true
backgroundColor: #ffffff
style: |
  section {
    font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  }
  h1 {
    color: #2c3e50;
    margin-bottom: 0.1em;
  }
  h2 {
    color: #34495e;
    border-bottom: 2px solid #ecf0f1;
    padding-bottom: 10px;
  }
  h3 {
    color: #7f8c8d;
    font-weight: 400;
    margin-top: 0;
  }
  code {
    background-color: #f4f6f8;
    color: #e74c3c;
    padding: 2px 5px;
    border-radius: 4px;
  }
---

# SysAgent
### AI-Powered Linux Diagnostic Assistant

**Lena Helo**
Software Engineer

---

## Background Story


---

## What is SysAgent?

SysAgent is an **AI-native Linux diagnostic agent** that turns raw system telemetry into expert-level insight through natural language — right in your terminal.

---
## The Problem

- **Complex Tooling**: Requires memorizing esoteric flags for tools like `ps`, `top`, `dmesg`, and `journalctl`.
- **Information Overload**: Raw telemetry provides data, but lacks synthesis and interpretation.
- **Expertise Dependency**: Junior engineers cannot act independently; senior engineers are interruption-taxed.
- **Disconnected Context**: Engineers spend 20–40% of diagnostic time reading docs in a browser instead of acting in the terminal.
- **CVE Blind Spots**: Unpatched vulnerabilities persist because the connection between system state and known advisories is never made.


---

## SysAgent Solves This - Key Features

- 🗣️ **Natural Language Interface**: Query your system using plain English instead of memorizing complex tool flags.
---
- 🧠 **ReAct Orchestration Loop**: The agent thinks, selects tools, observes results, and iterates autonomously until it finds the root cause.
---
- 📊 **Live System Telemetry**: Reads real-time data directly from `/proc`, `/sys`, and `psutil`.

- 📚 **Grounded RAG Diagnostics**: Answers backed by a locally indexed vector store of kernel docs and man pages.
---
- 🛡️ **Proactive CVE Scanning** *(Ubuntu)*: Cross-references your kernel version against the Ubuntu Security API.
---
- ⏱️ **Headless Scheduled Auditing**: Runs autonomously via systemd timers and pushes formatted reports to Slack.
---

- 🌍 **Run Anywhere** — Functions natively as a global CLI command across your entire system. In addition to Zero-touch onboarding via an interactive boot wizard 
---


## Demo

<!-- Remember: Use an animated GIF so it exports perfectly to PowerPoint! -->
---

## Under the Hood: Flow of Operations

1. **User Query**: Engineer asks a natural language question.
2. **ReAct Loop Begins**: LLM formulates a diagnostic plan based on the query.
3. **Live Telemetry**: Agent safely executes read-only tools (e.g., `ps`, `top`) to gather current system state.
4. **Context Retrieval (RAG)**: Queries local vector DB for relevant kernel docs or security advisories.
5. **Synthesis**: Synthesizes the live data and docs into a structured, actionable report.

---

## Engineering Challenges

### 1 — Idempotent RAG Ingestion

A naive RAG pipeline re-embeds the entire document corpus on every run — slow startup and wasted OpenAI API costs on unchanged files.
<!-- 
SPEAKER NOTES:
Implemented a hash-based differential sync. Each document is fingerprinted before ingestion. On subsequent runs, only documents whose content hash has changed are re-embedded. Unchanged documents are skipped entirely.
Result: A corpus of ~5,000 files ingests in seconds on repeat runs, with near-zero API cost. 
-->

---

## Engineering Challenges

### 2 — LLM Tool Sandboxing

Giving an LLM root access to a `run_bash()` tool would be catastrophic — a hallucination could wipe the filesystem.


<!-- 
SPEAKER NOTES:
**Design Decision:** The agent is never given a generic shell tool. Instead, it can only call a strict whitelist of hardcoded, read-only Python functions . These functions are physically incapable of writing, deleting, or modifying system state — regardless of what the LLM instructs.
SysAgent can have deep system visibility while remaining provably safe by design. 
-->

---

## Summary & What's Next

### 🔭 Leveling Up:
- **Multi-Machine Support**: SSH-based remote host diagnostics from a single control plane.
- **Broader Distro Support**: Extending beyond Debian/Ubuntu to Fedora, Arch, and other Linux distributions.
- **Local LLM Support**: Running fully offline with a local model (e.g. via Ollama) for complete privacy, no cloud dependency.

- **Cross-Platform Support**: Extending beyond Linux to macOS and other UNIX-like systems.

---

## Thank You



| GitHub Repository | Connect on LinkedIn |
| :---: | :---: |
| ![w:200 GitHub Repo](repo_qrcode.png) | ![w:200 LinkedIn Profile](linkedin_qrcode.png) |


---
