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

## Elevator Pitch

SysAgent is an AI-native Linux diagnostic agent that turns raw system telemetry into expert-level insight through natural language — right in your terminal 

---

## The Problem: Linux Troubleshooting is Tedious

- **Complex Tooling**: Requires memorizing esoteric flags for tools like `ps`, `top`, `dmesg`, and `journalctl`.
- **Information Overload**: Raw telemetry provides data, but lacks synthesis and interpretation.
- **Expertise Dependency**: Junior engineers cannot act independently; senior engineers are interruption-taxed.
- **Disconnected Context**: Engineers spend 20–40% of diagnostic time reading docs in a browser instead of acting in the terminal.

---

## The Solution: SysAgent

SysAgent autonomously gathers live system telemetry and cross-references it with official Linux kernel documentation to give you actionable, context-aware diagnostic advice—all without leaving the command line.

- 🧑‍💻 **Virtual IT Specialist**: Guides the user step-by-step using natural language to solve complex system problems.

---

## Core Capabilities

- 🧠 **ReAct Orchestration**: The agent thinks, observes, and acts in a continuous loop until it finds the root cause.
- 📊 **Live Telemetry**: Executes actual read-only system commands (CPU, memory, logs) to understand the *current* system state.
- 📚 **Grounded Diagnostics (RAG)**: Retrieves context from an indexed database of official Linux kernel documentation and man pages.
- 🛡️ **Proactive Security Audits (Ubuntu)**: Autonomous CVE vulnerability scanning cross-referenced with local package states.
- ⏱️ **Scheduled Reporting**: Headless execution via systemd timers with automated alerts sent to Slack.

---

## How it Works: Architecture

1. **User Query**: Engineer asks a natural language question.
2. **ReAct Loop (LLM)**: SysAgent decides which tools to run using OpenAI.
3. **OS Layer**: Safely executes read-only data-gathering commands (e.g., `ps aux`).
4. **Vector DB Retrieval**: Queries a local ChromaDB for relevant kernel docs and man pages.
5. **Final Output**: Synthesizes the live data and docs into a structured report.

---

## Under the Hood: The ReAct Engine

*SysAgent is not a simple chatbot. It uses an autonomous reasoning loop to formulate an execution plan, run system tools, and evaluate the results iteratively until the root cause is found.*


---

## Under the Hood: Safe Telemetry

*A major concern with AI agents is security. SysAgent does not execute arbitrary `bash` commands. It is strictly sandboxed to predefined, read-only Python functions that gracefully handle errors.*



---

## Demo: SysAgent in Action

<!-- Remember: Use an animated GIF so it exports perfectly to PowerPoint! -->
![SysAgent Demo](demo.gif)

*SysAgent autonomously diagnosing a high-CPU process and citing documentation.*

---

## Project Status (Completed in v1)

SysAgent is an actively evolving open-source project.

- **Core ReAct loop** and system telemetry tools.
- **Vector database integration** for Linux kernel docs & man pages.
- **Robust context management** and CLI experience.
- **Proactive Security Audits**: Autonomous CVE vulnerability scans (Ubuntu only).
- **Scheduled Headless Audits**: Automated reporting pipelines with Slack integration.

---

## Roadmap & Next Steps

**🚧 In Progress / Next Up:**
- **Interactive Onboarding**: Automatically prompt for configuration on first boot.
- **Packaging & Distribution**: Global `sysagent` command via `pip install`.
- **Advanced System Inspection**: Integration of deep diagnostic tools (`perf`, `ebpf`).
- **Rich Terminal UI**: Structured tables and color-coded status panels.

---

## Thank You

**SysAgent: AI-Powered Linux Diagnostic Assistant**

*Code & Documentation:*
[github.com/LenaHelo/sysagent](https://github.com/LenaHelo/sysagent)

| GitHub Repository | Connect on LinkedIn |
| :---: | :---: |
| ![w:200 GitHub Repo](repo_qrcode.png) | ![w:200 LinkedIn Profile](linkedin_qrcode.png) |

*Questions?*

---
