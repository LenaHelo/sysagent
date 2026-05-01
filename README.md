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
- [ ] **Security Posture Review**: Integration with external security feeds to cross-reference live kernel versions with known CVEs and vulnerabilities.
- [ ] **Packaging & Distribution**: Support for `pip install` to provide a global `sysagent` command and easier environment setup.
- [ ] **Advanced System Inspection**: Integration of deeper diagnostic tools (e.g., `perf`, `strace`, or `ebpf`-based tracing) for advanced performance and behavioral analysis.
- [ ] **Rich Terminal UI**: Move beyond plain text with structured tables, color-coded status panels, and high-scannability diagnostic reports.



## **📺 Demo**
*(Demo GIF/Video Placeholder)*

---

Developed as part of the **Generative AI Developer Growth Lab** | Place-IL
