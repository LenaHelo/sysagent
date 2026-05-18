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



## 🛠️ Tech Stack
- **Language:** Python 3.10+
- **LLM Provider:** OpenAI (GPT-4o-mini default)
- **Vector Database:** ChromaDB
- **Telemetry:** `psutil` and native Linux `/proc` / `/sys` interfaces.
- **CLI Framework:** `prompt_toolkit`.

## 🚀 Getting Started

### Prerequisites
- Linux OS (Debian/Ubuntu family recommended for v1).
- Python 3.10 or higher.
- An OpenAI API Key.

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/LenaHelo/sysagent.git
   cd sysagent
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### **Configuration**
1. **Environment Variables**: Create a `.env` file in the root directory:
   ```bash
   touch .env
   ```
2. **Setup RAG Sources**:
   - **Required**: Add your `OPENAI_API_KEY=your_key_here`.
   - **Optional (Kernel Docs)**: Set `KERNEL_DOCS_PATH` to your documentation folder. 
     *   **Option 1 (System Package)**: `sudo apt install linux-doc` (the path is usually `/usr/share/doc/linux-doc/Documentation`).
     *   **Option 2 (Manual Clone)**: Use this if the system package is missing. This command will dynamically fetch the documentation for your currently running kernel version:
         ```bash
         KERNEL_VERSION=$(uname -r | cut -d. -f1,2)
         git clone --depth 1 --branch v${KERNEL_VERSION} --filter=blob:none --sparse https://github.com/torvalds/linux.git kernel-source
         cd kernel-source && git sparse-checkout set Documentation
         ```

## **💻 Usage**
To start the interactive diagnostic session, run:
```bash
# Standard mode (silent tool execution)
python3 -m sysagent.main

# Verbose mode (shows agent's internal reasoning and tool calls)
python3 -m sysagent.main -v  # or --verbose
```

### Headless Proactive Auditing
SysAgent can run autonomously in the background to perform scheduled health and security audits. It can forward these reports to external platforms.

#### Setting up a Slack Webhook
To receive reports in Slack, you need to configure an Incoming Webhook:
1. Go to your Slack workspace and open the **App Directory**.
2. Search for **Incoming WebHooks** and add it to your workspace.
3. Choose the channel where you want SysAgent to post its reports.
4. Copy the generated Webhook URL (it starts with `https://hooks.slack.com/services/...`).
5. Open the `.env` file in the SysAgent directory and add your URL:
   ```env
   SLACK_WEBHOOK_URL="your_copied_url_here"
   ```

```bash
# Run a headless audit and print the markdown report to stdout
python3 -m sysagent.main --cron

# Run a headless audit and send the report to Slack
python3 -m sysagent.main --cron --notify slack
```

#### Scheduling with systemd
To run SysAgent on a schedule (e.g., daily at 8:00 AM), we recommend using **user-level systemd timers** for better logging and error handling without requiring root privileges.

1. **Create the systemd user directory** (if it doesn't exist):
   ```bash
   mkdir -p ~/.config/systemd/user/
   ```

2. **Create a Service File (`~/.config/systemd/user/sysagent.service`)**:
   ```ini
   [Unit]
   Description=SysAgent Proactive Audit Service

   [Service]
   Type=oneshot
   # Replace with the actual absolute path to your cloned repository
   WorkingDirectory=/absolute/path/to/sysagent
   ExecStart=/absolute/path/to/sysagent/.venv/bin/python -m sysagent.main --cron --notify slack
   ```

3. **Create a Timer File (`~/.config/systemd/user/sysagent.timer`)**:
   ```ini
   [Unit]
   Description=Run SysAgent Proactive Audit Daily

   [Timer]
   OnCalendar=*-*-* 08:00:00
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

4. **Enable and Start the Timer**:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now sysagent.timer
   ```
   *(To ensure the timer runs even when you aren't logged in, run `loginctl enable-linger $USER`)*

5. **Disable the Timer** (to stop receiving scheduled reports):
   ```bash
   systemctl --user disable --now sysagent.timer
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
- [ ] **Interactive Onboarding**: Automatically prompt for missing API keys and configuration on first boot so users don't have to manually edit `.env` files.
- [ ] **Packaging & Distribution**: Support for `pip install` to provide a global `sysagent` command and easier environment setup.
- [ ] **Advanced System Inspection**: Integration of deeper diagnostic tools (e.g., `perf`, `strace`, or `ebpf`-based tracing) for advanced performance and behavioral analysis.
- [ ] **Rich Terminal UI**: Move beyond plain text with structured tables, color-coded status panels, and high-scannability diagnostic reports.



## **📺 Demo**
*(Demo GIF/Video Placeholder)*

---

Developed as part of the **Generative AI Developer Growth Lab** | Place-IL
