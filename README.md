# SysAgent

### AI-native Linux diagnostic agent that turns raw system telemetry into expert-level insight through natural language.

---

## 🌟 Overview
**SysAgent** is a conversational CLI tool designed to help you understand and diagnose your Linux system. Instead of manually correlating output from dozens of individual tools like `top`, `dmesg`, and `ss`, you can ask SysAgent questions in plain English. 

It uses an autonomous **ReAct orchestration loop** to:
1.  **Collect live system telemetry** (CPU, memory, processes, logs).
2.  **Retrieve relevant documentation** via **RAG** (Retrieval-Augmented Generation) over an indexed corpus of man pages and Linux kernel documentation.
3.  **Provide structured, grounded, and actionable diagnostic reports** directly in your terminal.

## ✨ Key Features
- **Natural Language Diagnostics**: Resolve complex system issues without needing to memorize tool-specific command syntax.
- **Agentic Reasoning Loop**: An autonomous agent that decides which data to collect and which leads to follow to answer your query.
- **Kernel Documentation RAG**: Grounded diagnostics using a local vector store indexed with Linux kernel docs and man pages.
- **Grounded Diagnostics**: High-fidelity reports based on live system telemetry and official Linux documentation.
- **Proactive Security Audits (Ubuntu Only)**: Autonomous CVE vulnerability scanning cross-referenced with live OS telemetry to identify unpatched risks using the Ubuntu Security API.
- **Headless Proactive Auditing**: Schedule SysAgent to run autonomously in the background via systemd and dispatch beautifully formatted diagnostic reports directly to Slack webhooks.
- **Native Global CLI**: Install seamlessly via `pipx` to run `sysagent` from anywhere on your system, without manually managing Python virtual environments.
- **Interactive Boot Wizard**: Zero-touch onboarding that automatically configures API keys, RAG databases, and background systemd timers on your first run.

## 🛠️ Tech Stack
- **Language:** Python 3.10+
- **LLM Provider:** OpenAI (GPT-4o-mini default)
- **Vector Database:** ChromaDB
- **Telemetry:** `psutil` and native Linux `/proc` / `/sys` interfaces.
- **CLI Framework:** `prompt_toolkit`.

## 🚀 Getting Started

We provide two distinct workflows depending on how you intend to use SysAgent.

### 🧑‍💻 For Users (Recommended)

**1. Global Installation**
This installs SysAgent as a globally available terminal command using `pipx`, so you can run it from any directory without manually managing virtual environments.
```bash
sudo apt install pipx
git clone https://github.com/LenaHelo/sysagent.git
cd sysagent
pipx install .
```

**2. Zero-Touch Configuration**
SysAgent features an **Interactive Boot Wizard** that handles configuration on its first run. Simply type `sysagent` in your terminal, and the wizard will guide you through setting your API keys, Slack Webhooks, and RAG configuration. 

*(The configuration is safely stored in a global location `~/.config/sysagent/.env` to ensure the tool works seamlessly everywhere).*

---

### 🛠️ For Developers

If you are developing or modifying SysAgent, you may prefer a local virtual environment and direct environment variable management.

**1. Local Installation**
```bash
git clone https://github.com/LenaHelo/sysagent.git
cd sysagent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**2. Developer Configuration**
To bypass the interactive boot wizard entirely and avoid touching the global user configuration, you can inject your developer keys directly via the shell before running the app:
```bash
export SYSAGENT_OPENAI_API_KEY="sk-your-dev-key"
sysagent
```
*(Note: SysAgent intentionally ignores local `.env` files to prevent configuration hijacking when the tool is executed inside other software projects).*

---

## **⚙️ Integrations & Setup**

All of these features can be configured seamlessly using the **Interactive Boot Wizard** on your first run. If you need to prepare for them, or manage them later, here are the details:

### 1. Kernel Documentation (RAG)
During the Boot Wizard, SysAgent will ask for the path to your Linux Kernel Documentation. If you don't have it downloaded, you can fetch it using one of two methods:

**Option 1 (System Package):**
```bash
sudo apt install linux-doc
```
*(The path to provide the wizard is usually `/usr/share/doc/linux-doc/Documentation`)*

**Option 2 (Manual Clone):**
Use this if the system package is missing. This command dynamically fetches the specific documentation for your currently running kernel version without downloading the entire kernel source tree:
```bash
KERNEL_VERSION=$(uname -r | cut -d. -f1,2)
git clone --depth 1 --branch v${KERNEL_VERSION} --filter=blob:none --sparse https://github.com/torvalds/linux.git kernel-source
cd kernel-source && git sparse-checkout set Documentation
```
*(The path to provide the wizard is the absolute path to this new `kernel-source/Documentation` folder)*

### 2. Slack Webhooks
To receive proactive audit reports in Slack, you need to configure an Incoming Webhook:
1. Go to your Slack workspace and open the **App Directory**.
2. Search for **Incoming WebHooks** and add it to your workspace.
3. Choose the channel where you want SysAgent to post its reports.
4. Copy the generated Webhook URL (it starts with `https://hooks.slack.com/services/...`).
5. Paste this URL into the SysAgent Boot Wizard when prompted!

### 3. Systemd Scheduling
You do not need to write systemd service or timer files manually! 

During the Boot Wizard, if you provide a Slack Webhook, SysAgent will ask if you want to enable background audits. It will ask for your preferred frequency (daily, weekly, monthly) and time, and then **automatically generate, install, and enable the systemd timers for you**.

*(To ensure the timer runs even when you aren't logged in, run `loginctl enable-linger $USER`)*

To manually disable the timer later, simply run:
```bash
systemctl --user disable --now sysagent.timer
```

## **💻 Usage**
To start the interactive diagnostic session, run:
```bash
# Standard mode (silent tool execution)
sysagent

# Verbose mode (shows agent's internal reasoning and tool calls)
sysagent -v  # or --verbose
```

### Headless Execution
```bash
# Run a headless audit manually and print the report to stdout
sysagent --cron

# Run a headless audit manually and send the report to Slack
sysagent --cron --notify slack
```

## **📁 Project Structure**
```
├── sysagent/           # Core application package
│   ├── agent/          # LLM reasoning and ReAct loop logic
│   ├── rag/            # Vector database, embeddings, and ingestion pipeline
│   ├── system/         # Live system telemetry and diagnostic tools
│   └── main.py         # Application entry point
├── docs/               # Project documentation and PRD
├── scripts/            # Utility and maintenance scripts
├── tests/              # Comprehensive test suite
├── requirements.txt    # Project dependencies
└── README.md           # This file
```

## 🗺️ Roadmap
- [x] **Interactive Onboarding**: Automatically prompt for missing API keys and configuration on first boot so users don't have to manually edit `.env` files.
- [x] **Packaging & Distribution**: Support for `pip install` to provide a global `sysagent` command and easier environment setup.
- [ ] **Advanced System Inspection**: Integration of deeper diagnostic tools (e.g., `perf`, `strace`, or `ebpf`-based tracing) for advanced performance and behavioral analysis.
- [ ] **Rich Terminal UI**: Move beyond plain text with structured tables, color-coded status panels, and high-scannability diagnostic reports.



## **📺 Demo**
*(Demo GIF/Video Placeholder)*

---

Developed as part of the **Generative AI Developer Growth Lab** | Place-IL
