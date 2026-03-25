# SysAgent — Product Requirements Document

> **Status:** Draft — In Progress  
> **Author:** Solo Developer

---

## Section 1 — Project Overview

### What Is SysAgent?

SysAgent is a command-line AI agent that lets you ask questions about your Linux system in plain English and get back intelligent, context-aware answers. It combines live system telemetry — CPU, memory, processes, network, disk, kernel parameters — with an LLM-powered reasoning engine that can look up documentation, query external security feeds, and alert you to conditions that matter.

Instead of running `top`, then `dmesg`, then `man proc`, then cross-referencing a CVE database, you ask SysAgent: *"Why is my system sluggish right now, and is there anything I should be concerned about?"* — and it figures out what to look at, retrieves what it needs to know, reasons over the data, and gives you a structured, actionable answer.

### Elevator Pitch

> **SysAgent is an AI-native Linux diagnostic agent that turns raw system telemetry into expert-level insight through natural language — right in your terminal.**

### Motivation

Linux exposes enormous amounts of system information through the `/proc` filesystem, kernel logs, sysfs, network interfaces, and process tables. The challenge has never been data availability — it has been synthesis. A skilled site reliability engineer knows which metrics to correlate, which kernel parameters to check, and which CVEs to worry about. Junior engineers, students, and developers working outside their primary domain do not.

Existing tools solve the *visibility* problem: `htop` shows you CPU and memory. `glances` shows you more of the same with a nicer interface. `dmesg` surfaces kernel messages. `ss` shows socket state. Each tool is excellent at what it does and terrible at everything else. None of them reason. None of them explain. None of them connect what you're seeing to why it's happening or what you should do about it.

SysAgent is built on the premise that the correct abstraction for system diagnostics in 2025 is not a better dashboard — it is a reasoning agent that has read the documentation, knows the kernel, watches your system live, and talks to you in your terminal.

### What Makes SysAgent Different

| Tool | What It Does Well | What It Cannot Do |
|---|---|---|
| `htop` / `top` | Real-time CPU & memory visualization | Explain anomalies, correlate across subsystems |
| `glances` | Broad system overview in one screen | Reason about data, answer questions, retrieve docs |
| `dmesg` | Exposes kernel ring buffer messages | Parse, explain, or act on what it shows |
| `sysdig` | Deep kernel-level tracing and event capture | Natural language interface, LLM reasoning |
| `Datadog` / `Grafana` | Enterprise observability and dashboards | Run locally, explain findings, work without infra |
| **SysAgent** | **AI-driven reasoning over live system + docs + CVEs** | **— (see Non-Goals)** |

SysAgent is not trying to replace any of these tools. It is positioned in a gap none of them occupy: a **conversational, reasoning layer** that sits on top of live system data and makes expert-level diagnosis accessible to anyone working at a terminal.

### A Note on the Name

*SysAgent* evokes an intelligent, autonomous entity embedded directly in your system — one that observes, reasons, and acts.

> **Assumption:** The project is scoped exclusively to Linux for v1. Cross-platform support is not a goal.

> **Assumption:** SysAgent is designed to run with root privileges on a private personal machine, giving it complete visibility into system internals. Non-root operation is supported, but the agent will warn the user that analysis accuracy may be reduced depending on the data required to answer a query.

---

## Section 2 — Problem Statement

### The Core Problem

Linux is one of the most information-rich computing environments ever built. The `/proc` filesystem alone exposes thousands of live data points about processes, memory, CPU scheduling, network state, and kernel configuration. The kernel ring buffer logs hardware events, driver errors, and security warnings in real time. Yet despite this abundance of data, diagnosing what is actually happening on a Linux system — and why — remains a difficult, time-consuming, and expertise-dependent task.

The problem is not access to data. The problem is **interpretation and synthesis**.

A system exhibiting high load, elevated memory pressure, and occasional network packet drops might be suffering from a misconfigured kernel parameter, a runaway process, a known kernel bug, or a CVE-related vulnerability that has gone unpatched. Distinguishing between these causes requires:
- knowing *which* tools to run,
- knowing *how* to read their output,
- knowing *where* to look in the documentation,
- and knowing *what questions to ask* in the first place.

This knowledge is not evenly distributed. It lives in the heads of experienced engineers, in man pages that assume deep prior knowledge, and in kernel mailing lists that are inaccessible to most practitioners.

### Who Is Affected

**Junior sysadmins and operations engineers** are the most acutely affected. They are often the first responders to system incidents but have the least contextual knowledge to act quickly. They tend to follow runbooks and escalate — a slow, expensive process.

**Developers working on performance-sensitive software** (database engines, networking stacks, embedded systems) frequently need to understand kernel behavior that is outside their primary expertise. They know their code; they do not know `perf`, `ftrace`, or `/proc/sys/net`.

**Computer science students and researchers** working on OS-level projects lack the institutional knowledge that comes with years of production experience. They waste hours learning tool syntax when the goal is to understand system behavior.

**Senior SREs and DevOps engineers** — though experienced — spend significant time on repetitive diagnostics: correlating metrics, pulling documentation, and verifying whether a current system state matches a known bad pattern. Automation here is high-leverage.

### In What Contexts

These problems surface most acutely in three scenarios:

1. **Incident response** — A system is behaving unexpectedly and time is short. The engineer must identify the cause quickly, often without access to runbooks that cover the specific condition.

2. **Performance tuning** — A developer or administrator is trying to improve throughput, reduce latency, or optimize resource usage. This requires iterating across kernel parameters, process scheduling, and I/O configuration — domains that interact in non-obvious ways.

3. **Security posture review** — An operator wants to know whether any running processes, kernel versions, or configuration states expose the system to known vulnerabilities. Today this requires cross-referencing multiple external sources manually.

### The Cost

| Problem | Cost |
|---|---|
| Slow incident diagnosis | Mean time to resolution (MTTR) increases; outages extend |
| Manual documentation lookup | Engineers spend 20–40% of diagnostic time reading docs rather than acting |
| CVE blind spots | Unpatched vulnerabilities persist because the connection between system state and known advisories is never made |
| Expertise dependency | Junior engineers cannot act independently; senior engineers are interruption-taxed |
| Context switching between tools | Cognitive overhead of juggling `top`, `dmesg`, `ss`, `perf`, `journalctl` simultaneously increases error rate |

---

## Section 3 — Target Users

### Persona 1 — Alex, Junior Sysadmin

| | |
|---|---|
| **Role** | Junior Systems Administrator at a mid-size company |
| **Technical Level** | Intermediate — comfortable with Linux basics, limited kernel/internals knowledge |
| **Experience** | 1–2 years in operations; manages a small fleet of Linux servers |

**Goals**
- Diagnose and resolve system issues independently without always escalating to seniors
- Build confidence working with Linux internals
- Reduce time spent hunting through man pages and Stack Overflow during incidents

**Pain Points**
- Knows *something* is wrong but doesn’t know which tool to run or which metric to trust
- Man pages and kernel documentation assume knowledge he doesn’t yet have
- Feels slow and exposed during incidents; relies heavily on runbooks that don’t always apply
- No easy way to connect a symptom (e.g. high iowait) to a root cause without senior help

**User Story**
*As Alex, I want to ask “why is this server slow right now?” and receive a grounded, step-by-step explanation, so that I can resolve incidents independently without waiting for senior help.*

---

### Persona 2 — Priya, Senior SRE / DevOps Engineer

| | |
|---|---|
| **Role** | Senior Site Reliability Engineer at a tech company |
| **Technical Level** | Advanced — deep knowledge of Linux, distributed systems, and observability tooling |
| **Experience** | 7+ years; owns reliability for production infrastructure |

**Goals**
- Speed up repetitive diagnostic workflows (the ones she could do in her sleep but still take time)
- Quickly surface CVEs or security advisories relevant to current kernel versions and running services
- Reduce interruptions caused by junior team members asking diagnostic questions she has answered before

**Pain Points**
- Existing tools show data but require her brain to do all the synthesis
- CVE tracking is a manual, error-prone process — she has to cross-reference NVD, vendor feeds, and kernel changelogs herself
- Spends time being an “on-call encyclopedia” for her team instead of doing higher-leverage work
- No single tool connects live system state to documentation and security intelligence

**User Story**
*As Priya, I want SysAgent to cross-reference my current kernel version against known CVEs and surface any relevant advisories, so that I can assess my security posture without manually querying multiple external databases.*

---

### Persona 3 — Sam, CS Student / Researcher

| | |
|---|---|
| **Role** | Third-year CS undergraduate or graduate researcher |
| **Technical Level** | Intermediate-to-advanced — strong in theory, building hands-on Linux experience |
| **Experience** | Works on OS coursework, kernel modules, or systems research projects |

**Goals**
- Understand what the kernel is actually doing in response to their code or experiments
- Learn Linux internals faster without getting stuck on tool syntax
- Validate hypotheses about system behavior (scheduling, memory allocation, I/O) quickly

**Pain Points**
- Knows the theory but struggles to map it to what `/proc`, `perf`, or `ftrace` is showing
- Documentation is scattered across man pages, kernel.org, and academic papers
- No interactive way to ask “why is the scheduler behaving like this?” and get a grounded answer
- Wastes significant time on tooling rather than the actual research question

**User Story**
*As Sam, I want to ask “what is the kernel doing with memory right now, and why?” and get an answer that references actual documentation, so that I can validate my understanding of OS concepts against live system behaviour.*

---

### Persona 4 — Daniel, Performance-Sensitive Developer

| | |
|---|---|
| **Role** | Software engineer working on a performance-critical application (database, game server, network service) |
| **Technical Level** | Advanced in their domain (C++, Rust, Go); Linux internals are secondary knowledge |
| **Experience** | 4–6 years of software development; occasional need to go deep into kernel behavior |

**Goals**
- Understand how the kernel interacts with their application under load (scheduling, memory, syscall overhead)
- Tune kernel parameters (e.g. `net.core.somaxconn`, huge pages, CPU affinity) without deep sysadmin expertise
- Quickly determine whether a performance anomaly is in their code or the system beneath it

**Pain Points**
- Kernel tuning requires domain knowledge he doesn’t have and can’t afford to fully acquire
- Has to context-switch between his application profiler and a different world of Linux tooling
- Documentation for kernel parameters is dense, often incomplete, and spread across multiple sources
- Cannot easily answer: “is this a known issue, or is it something I’m doing wrong?”

**User Story**
*As Daniel, I want to ask “is my network throughput being limited by a kernel parameter?” and get a specific, actionable answer, so that I can tune my system without needing to become a Linux internals expert.*

---

### Primary Target for v1

SysAgent is designed for **a single user on a private Linux machine** — not for teams, fleets, or production infrastructure. Given this scope, the primary target is a **technically capable individual (developer, CS student, or Linux enthusiast)** who runs Linux as their personal OS and wants to understand and diagnose their own system without being a full-time systems expert.

This maps most closely to **Sam** and **Daniel**, with the following defining traits:
- They own the machine they’re running SysAgent on — full access, no approval chains
- They are learning or building something, and the system is both a tool and an object of curiosity
- Their goals are personal: faster debugging, understanding internals, tuning their own workloads
- They have no runbook, no team, and no on-call rotation — just themselves and the terminal

**Alex** (Junior Sysadmin) and **Priya** (Senior SRE) are valid secondary personas for future versions, once the tool is extended to support multi-machine or team-oriented workflows.

---

## Section 4 — Goals and Non-Goals

### Goals (v1)

These define what success looks like for the first release. Every item below must be demonstrable in a live terminal session.

| # | Goal | Success Looks Like |
|---|---|---|
| G1 | Natural language query interface | User types a question in plain English; the agent returns a structured, accurate answer grounded in live system data |
| G2 | Live system data collection | Agent reads CPU, memory, disk, network, process, and kernel state in real time from `/proc`, `/sys`, and system calls. Running with root privileges provides complete visibility; non-root operation is supported but may reduce data access for certain subsystems |
| G3 | Agentic reasoning loop | Agent autonomously decides which tools to invoke, in what order, to answer a query — without the user specifying steps |
| G4 | Documentation retrieval (RAG) | Agent retrieves relevant content from an indexed corpus of man pages and kernel documentation to augment its answers |
| G5 | Security advisory lookup | Agent can surface CVEs or kernel advisories relevant to the current kernel version or running software |
| G6 | Rich, readable CLI output | Responses use structured formatting (tables, panels, colour) appropriate to a terminal environment |
| G7 | Session context persistence | Within a single session, the agent retains conversational context so follow-up questions build on prior exchanges. Context does not persist across sessions by default |
| G8 | Offline-capable core | Live system data collection and local documentation retrieval (RAG) work without internet access. Features requiring external services — CVE lookups, kernel changelogs, LLM API calls — degrade gracefully: SysAgent still returns a useful answer from local data and notes that external data is unavailable, rather than failing silently or crashing. |
| G9 | End-to-end demo in under 5 minutes | The full value proposition — query → reasoning → retrieval → answer — is demonstrable in a short session |

---

### Non-Goals (v1)

These are explicitly out of scope for the first version. Listing them prevents scope creep.

| # | Non-Goal | Rationale |
|---|---|---|
| NG1 | Multi-machine / remote host monitoring | SysAgent operates on the local machine only; SSH-based or agent-daemon architectures are a v2 concern |
| NG2 | macOS, Windows, or BSD support | The tool is Linux-specific by design; cross-platform support would require significant abstraction effort |
| NG3 | A graphical or web-based UI | The CLI is the intentional interface; a GUI would dilute the terminal-native identity and add unnecessary scope |
| NG4 | Persistent alerting daemon / background service | Alerting in v1 is query-triggered, not continuous; a background watchdog is a future feature |
| NG5 | Multi-user or role-based access control | SysAgent has no internal user management or permission model. OS-level privileges are handled by Linux directly: root access is strongly recommended for full visibility, but non-root operation is permitted with a degraded data warning |
| NG6 | Writing or modifying system configuration | SysAgent is read-only in v1; it observes and advises but does not make changes to the system |
| NG7 | Custom LLM fine-tuning or local model training | SysAgent uses an existing LLM provider or local model via API; training custom models is out of scope |
| NG8 | Containerised or Kubernetes workload introspection | Container-native tooling (e.g. cgroup v2 namespacing, pod-level metrics) is deferred to a future version |

> **Note on NG6 (read-only):** This is a deliberate safety and trust decision for v1. SysAgent may run with root privileges for comprehensive visibility, but uses that access exclusively to read — never to modify system state. A tool that can modify system state carries significantly higher risk and requires a different trust model. Actuation capabilities may be revisited in v2 with appropriate safeguards.

---

## Section 5 — Key Features

---

### Feature 1 — Natural Language Query Interface
**Priority:** P0

**Description**
The primary way a user interacts with SysAgent is by typing a question or instruction in plain English at the CLI. There is no need to know which tool to run, which flag to pass, or how to parse the output. The user simply describes what they want to understand, and SysAgent handles the rest.

**User Problem Solved**
Users currently must know the right tool for each question before they can get an answer. This creates a high barrier for anyone outside the Linux expert tier, and slows down even experienced users who have to switch context constantly.

---

### Feature 2 — Live System Data Collection
**Priority:** P0

**Description**
SysAgent reads real-time system state from the Linux kernel interfaces: `/proc`, `/sys`, network socket tables, hardware sensors, and process metadata. This includes CPU usage and scheduling state, memory and swap statistics, disk I/O, open file descriptors, network connections, running processes, and key kernel parameters. Data is collected on demand, at query time, to ensure answers reflect the current system state.

**User Problem Solved**
Diagnostic value comes from live data. A tool that reasons over stale snapshots cannot reliably answer questions about what is happening right now. Live collection ensures SysAgent’s answers are grounded in reality, not a cached approximation.

---

### Feature 3 — Agentic Reasoning Loop
**Priority:** P0

**Description**
SysAgent operates as an autonomous agent: given a user query, it decides which data to collect, which documentation to retrieve, and which external sources to consult — iterating across these steps until it can produce a well-grounded answer. The user does not direct these steps. The agent plans and executes them internally, presenting only the final result (and optionally a reasoning trace).

**User Problem Solved**
Multi-step diagnostics today require the user to manually orchestrate a series of tool invocations and mentally synthesize the results. The agentic loop eliminates this orchestration burden entirely.

---

### Feature 4 — Documentation Retrieval (RAG over Kernel Docs and Man Pages)
**Priority:** P0

**Description**
SysAgent maintains a locally indexed corpus of Linux man pages and kernel documentation. On first run, SysAgent reads man page files directly from the local filesystem (typically `/usr/share/man/`), splits them into chunks, converts each chunk into a semantic embedding, and saves the resulting vector index to disk. All subsequent queries search this local index — no internet access required.

Kernel documentation is handled separately: it ships with the kernel source package (e.g. under `/usr/share/doc/linux-doc/`) and is not always installed by default. SysAgent will check for its presence at setup time and either index it if available, prompt the user to install it, or fall back to an online source if the package is missing.

When answering a query, SysAgent retrieves the most relevant documentation chunks from the index and incorporates them into its reasoning, grounding answers in actual reference material rather than LLM training data alone.

**User Problem Solved**
Documentation lookup is one of the most time-consuming parts of Linux diagnostics. Users know what they’re seeing but not what it means. RAG brings the documentation directly into the answer, without the user having to leave the terminal or know where to look.

---

### Feature 5 — Rich CLI Output
**Priority:** P0

**Description**
SysAgent formats its output using terminal-native rich text: structured tables for tabular data, panels and borders for sections, syntax highlighting for code and kernel parameters, and colour coding for severity levels. Output is designed to be scannable at a glance and readable in detail. The formatting library adapts to terminal width and colour support. Additionally, SysAgent should support an optional file export mode (e.g., `--output report.txt`) to save the full diagnostic reasoning trace and findings to disk for later review.

**User Problem Solved**
Raw text output from diagnostic tools is difficult to parse under time pressure. Well-structured, visually differentiated output reduces cognitive load and speeds up decision-making, especially during incidents.

---

### Feature 6 — External API Integration (CVE Lookup and Kernel Security Advisories)
**Priority:** P1

**Description**

**Why do CVEs matter for SysAgent?**
Every Linux system is running a specific kernel version (readable via `uname -r`, e.g. `5.15.0-91-generic`). New CVEs affecting the Linux kernel are discovered regularly. Some are minor, while others are serious — allowing privilege escalation (a normal user becoming root), remote code execution, or denial of service. If your kernel version falls within the affected range of a known CVE and you haven't patched it, your system is vulnerable.

The average system administrator has no easy way to ask: "given my exact kernel version, which known CVEs apply to me right now, and how severe are they?" They'd have to manually check the NVD website, cross-reference their version, and interpret the results. This is tedious, and most people don't do it routinely. 

SysAgent fills this gap — the agent reads your kernel version from the live system, queries CVE data sources, and tells you plainly: *"you are running kernel 5.15.0-91, which is affected by 3 known CVEs, one of which is rated 7.8 out of 10 severity and has a patch available."*

**Where does GitHub come in?**
There are two relevant data sources on GitHub for this feature:
1. **The Linux kernel source code:** The official mirror of the Linux kernel lives at `github.com/torvalds/linux`. Every change ever made to the kernel is tracked as a commit here, with a message, timestamp, and exact files changed. When a vulnerability is patched, that patch appears as a commit. The GitHub Search API lets SysAgent search those commits (by keyword, date, file path, etc). The agent can ask GitHub: *"show me recent commits to the memory management subsystem"* and get back a list of changes that might explain a behavior seen on the system.
2. **A dedicated CVE tracking repository:** Kernel maintainer Greg Kroah-Hartman maintains a repository at `github.com/gregkh/kernel-cves` that maps CVE IDs directly to affected kernel version ranges in a structured, machine-readable format. Instead of parsing the NVD's full database, SysAgent queries this repository to ask a specific question: *"is kernel version 5.15.0-91 listed as affected by any CVEs?"* and gets a clean, structured answer back.

**How it all fits together in SysAgent**
When you ask SysAgent something like *"is my system secure?"* or *"are there any known vulnerabilities I should know about?"*, here is what happens under the hood:

1. The live system tool reads your kernel version via `uname -r`
2. The GitHub tool queries `github.com/gregkh/kernel-cves` with that version number
3. It finds any matching CVEs and retrieves their IDs
4. It optionally queries the NIST NVD API to get the full details and severity scores for each CVE
5. The agent reasons over all of that and produces a plain English summary: which CVEs affect you, how serious they are, whether patches exist, and what you should do

The result is something that previously required specialized security tooling or manual research, delivered in a conversational interface in seconds. That's the value of combining live system data with external security intelligence through an LLM agent.

---

### Feature 7 — Alerting and Notification Layer
**Priority:** P1

**Description**
SysAgent can push notifications to external services (e.g. a desktop notification, a webhook, or a messaging service) when a query result crosses a defined threshold or reveals a condition of interest. In v1, alerting is query-triggered rather than continuous — the user runs a query, and if the result warrants an alert, it is dispatched.

> **Open Decision:** The specific external services to integrate for alerting (e.g. Telegram, Email, ntfy.sh, Slack, webhooks) are yet to be decided. This will be evaluated and selected during development once the core local agent is stable.

**User Problem Solved**
Not all diagnostic findings need to be silently consumed at the terminal. Some results — a kernel OOM event, a CVE match, a runaway process — warrant immediate attention beyond the terminal window. The alerting layer makes it possible to act on SysAgent’s findings even when the user is not watching.

---

### Feature 8 — Session History and Context Persistence
**Priority:** P1

**Description**
Within a session, SysAgent retains the full conversation history, enabling follow-up questions that build on prior exchanges. A user can ask “what is causing the high CPU usage?” and follow up with “is this a known issue?” without re-establishing context. Context does not persist after the session ends.

> **Future Consideration:** Cross-session persistence (saving and reloading conversation history between runs) is not committed to for v1, but may be worth implementing if a lightweight storage mechanism presents itself naturally during development.

**User Problem Solved**
Diagnostic workflows are rarely single-turn. Users iterate, narrow down, and follow leads. Without context persistence, every follow-up question would require re-stating all prior context — making multi-step diagnosis tedious and error-prone.

---

### Feature Priority Summary

| # | Feature | Priority |
|---|---|---|
| 1 | Natural language query interface | P0 |
| 2 | Live system data collection | P0 |
| 3 | Agentic reasoning loop | P0 |
| 4 | Documentation retrieval (RAG) | P0 |
| 5 | Rich CLI output | P0 |
| 6 | External API integration (CVEs, changelogs) | P1 |
| 7 | Alerting and notification layer | P1 |
| 8 | Session history and context persistence | P1 |

---

## Section 6 — Conceptual Architecture Overview

SysAgent’s architecture is designed around a central autonomous intelligence coordinating various specialized data gatherers. It is built as a modular command-line application that runs entirely on the host Linux machine.

The architecture consists of six major logical components:

### 1. The CLI Interface Layer
This is the user’s entry point. It captures natural language queries and handles the structured, rich text display of the results. It is responsible for formatting tables, syntax highlighting, and presenting the reasoning trace. Crucially, the CLI layer also manages the local session context, ensuring the agent remembers what was discussed earlier in the conversation.

### 2. The Reasoning / Agent Layer
The core brain of SysAgent. Powered by a Large Language Model (LLM), this layer takes the user’s query and breaks it down into an execution plan. It decides which tools to call, in what order, and how to synthesize the data returned. It acts as the orchestrator: it does not know the system state directly, but it knows *how* to ask the other layers to find out.

### 3. The Live System Data Layer
A collection of specialized tools executed by the Agent Layer to observe the local machine. This layer directly interfaces with Linux OS primitives: reading `/proc` and `/sys` file systems, probing network states, and checking performance metrics. It operates entirely locally and requires root privileges for comprehensive visibility. It is the grounding truth of SysAgent’s diagnostics.

### 4. The Documentation Retrieval Layer (RAG)
This component provides the "book smarts." It manages a local vector database containing embedded chunks of Linux man pages and kernel documentation. When the Agent Layer needs to understand what a specific kernel parameter does, it queries this layer. Because the corpus is indexed locally, this layer functions completely offline.

### 5. The External Data Integration Layer
Responsible for interacting with the outside world. This layer handles API calls to external services like the NVD for CVE details, or GitHub for querying the `torvalds/linux` commit history and `gregkh/kernel-cves` mapping repository. Along with the Alerting Layer (and the LLM itself, if using a cloud API), it requires internet access. It is designed to degrade gracefully: if offline, it simply informs the Agent Layer that external data is unavailable.

### 6. The Alerting Layer
An outbound communication channel. Once the Agent Layer reaches a conclusion that breaches a specific threshold or warrants immediate attention (e.g., a critical unpatched CVE), this layer reformats the finding and dispatches it. If the destination is an external service (like Telegram or a webhook), this layer will require internet access. The exact destinations are abstracted from the core reasoning loop.

### How They Interact (The Flow)
When a user asks, *"Why is my server slow?"*:
1. The **CLI Interface** captures the text and passes it to the **Reasoning Layer**.
2. The **Reasoning Layer** requests current CPU/memory/process state from the **Live System Data Layer**.
3. Upon identifying anomalous patterns in the data (e.g., high `iowait`), the **Reasoning Layer** queries the **Documentation Retrieval Layer** to understand relevant kernel parameters.
4. If a potential vulnerability is spotted based on kernel version, it asks the **External Data Integration Layer** for known CVEs.
5. Finally, the **Reasoning Layer** synthesizes the findings, optionally triggers the **Alerting Layer** if an emergency is detected, and sends a formatted response back to the **CLI Interface**.

### Architectural Constraints
- **Host-Native:** SysAgent runs directly on the target Linux system. It does not use a central monitoring daemon or remote scraping agent architecture in v1.
- **Offline Capable:** The CLI, Live System Data, and Documentation Retrieval layers must function offline. The LLM component may also run offline depending on the final deployment choice.
- **Read-Only Posture:** To maintain safety and trust, the architecture strictly forbids any component from mutating system state or writing configuration files.
- **Zero-Infrastructure Footprint:** SysAgent must not require heavy external databases (e.g., PostgreSQL) or continuous background daemons to operate. Any local state (RAG vector index, session history) must be stored in lightweight, serverless formats (e.g., SQLite, local JSON) in standard user directories.
- **Bounded Tool Context (Data Pruning):** Linux diagnostic commands (like `dmesg` or network dumps) can produce massive outputs. The data layer must enforce strict truncation, filtering, or summarization *before* passing results to the reasoning layer to prevent exhausting the LLM's context window token limits.
- **Graceful Privilege Degradation:** While root access is recommended for maximum visibility, the system data layer must handle `Permission Denied` errors gracefully. Rather than crashing, restricted states are passed back to the reasoning layer, allowing the LLM to explain the visibility limitation to the user.
- **Distro-Agnostic Core with Tiered Support:** The fragmented Linux ecosystem (differing package managers, log paths, config files) is a massive parsing challenge. The reasoning core must remain agnostic, while the system data layer abstracts the underlying OS. For v1, the tool will officially target and test against only one distribution family (e.g., Debian/Ubuntu), issuing a "best effort" warning on unsupported distros.

---

## Section 8 — Success Metrics

To evaluate whether SysAgent is successful, we define the following **Product Quality Metrics** to measure the core functionality and reliability of the agentic loop.

| Metric | Target / Success Condition | How it is Measured |
|---|---|---|
| **Agent Reasoning Correctness** | >90% of queries result in the correct set of diagnostic tools being called. | Manual evaluation across a test suite of 20 common diagnostic scenarios (e.g., high CPU, OOM killer, disk full). |
| **Documentation Accuracy (RAG)** | >85% of queries requiring documentation successfully retrieve and cite the correct man page or kernel doc chunk. | Manual review of the context chunks passed to the LLM during the 20-scenario test suite. |
| **Response Grounding** | 0% hallucination of system state or CVE details. | The LLM must explicitly refuse to answer if the underlying data layer or external API fails to return the required information. |
| **System Introspection Speed** | <15 seconds from query to final answer (excluding external API network latency). | Logged execution time from the moment the user hits `Enter` to the moment the UI renders the final response. |
| **Context Window Stability** | 0% of queries fail due to `ContextWindowExceeded` or `MaxTokens` errors. | Feeding deliberately massive outputs (e.g., full `dmesg`) to ensure the framing and pruning logic holds. |
| **Tool Call Efficiency** | < 1 unnecessary tool call per query on average. | Count of executed tools vs. optimal required tools across the 20-scenario test suite. |
| **Graceful Failure Rate** | 100% of tool execution errors (e.g., `Permission Denied`) are caught and explained to the user without hard crashing. | Injecting simulated permission and missing binary errors during development testing. |
| **Offline Resilience** | 100% success rate answering local diagnostic queries when the network interface is disabled. | Running the local-only subset of the test suite with the network interface down. |

---

## Section 9 — Risks and Mitigations

SysAgent is an ambitious project operating on a compressed development timeline. The following risks have been identified along with strategies to mitigate them.

| Risk | Severity | Mitigation Strategy |
|---|---|---|
| **Fragmented Linux Ecosystem** (Different package managers, log paths, and tools across distros cause parsing errors) | High | **Targeted Support (v1):** The Live System Data Layer will be built and tested exclusively against the Debian/Ubuntu family for the MVP. Other distros will trigger a "best effort / unsupported" warning rather than guaranteeing accuracy. |
| **LLM Context Window Exhaustion** (Live data outputs like `dmesg` or `journalctl` are too large, causing crashes or high API costs) | High | **Aggressive Pruning:** The data layer will strictly truncate, filter, or summarize outputs *before* sending them to the LLM (e.g., `tail -n 50`, `grep ERR`). |
| **Hallucination on Critical Security Data** (The agent confidently states a system is patched when it is actually vulnerable) | High | **Strict Grounding Prompts:** The agent will be instructed to explicitly cite its sources (e.g., specific CVE IDs from the GitHub API) and refuse to answer if the API lookup fails or returns ambiguous results. |
| **Scope Creep / Timeline Pressure** (Getting lost in building a perfect local RAG pipeline instead of completing the core loop) | Medium | **API-First Fallbacks:** If the local RAG indexing proves too complex to stabilize in time for v1, development will fall back to querying an external LLM for theoretical knowledge, sacrificing the strict offline requirement to ensure a working MVP. |
| **Permissions / Sandboxing Issues** (Running untested LLM-generated commands as root could break the host filesystem) | Extreme | **Code-Level Sandboxing:** SysAgent *must* run as root to genuinely diagnose the system (e.g., reading `/var/log/syslog` or full `dmesg`). However, the agent will *never* be given access to a generic `execute_bash` tool. Instead, safety is enforced in code: the LLM is restricted to calling specific, hardcoded Python/Go wrapper functions (like `read_file(path)` or `get_processes()`) that physically cannot write to or delete from the filesystem. |
| **Agent Infinite Looping** (The LLM gets confused by an error, retries the same tool repeatedly, and deadlocks the app) | High | **Iteration Limits & Fail-Fast Prompts:** Hardcode a maximum tool-call limit (e.g., 5 calls per query). The system prompt will explicitly instruct the agent to return its best assessment rather than blindly retrying a failed command. |
| **Missing Host Dependencies** (The host machine lacks expected binaries like `strace`, `lsof`, or `curl`, breaking the agent's tools) | High | **Graceful Fallbacks:** The Live Data Layer must transparently fall back to reading raw `/proc` or `/sys` files when high-level tools are missing, or at minimum, gracefully report the missing dependency (e.g., `apt install strace`) to the user instead of crashing. |

## Section 10 — Open Questions

As development begins, the following technical and product direction questions remain unresolved. They must be answered during the implementation phase.

1. **LLM Provider:** Should SysAgent default to a local, computationally heavy model (e.g., via Ollama/Llama 3) to guarantee 100% privacy, or leverage a cloud API (e.g., OpenAI/Anthropic/Google) for vastly superior reasoning speed and tool-calling reliability?
2. **Alerting Destinations:** Which specific outbound services will be supported in v1 for the Alerting Layer? (e.g., Telegram, Slack, generic Webhooks, desktop `notify-send`)?
3. **RAG Index Invalidation:** When the user updates their system (e.g., `apt upgrade` installs a new kernel), how does the agent know the local man page/kernel doc vector index is stale and needs to be rebuilt? Does it check hashes on startup, or require a manual `--reindex` flag?
4. **Binary Distribution:** Will SysAgent be distributed as a standalone compiled binary (e.g., written in Go/Rust), or a Python package requiring `pip install` and virtual environments?
5. **File Export Formatting:** If the user passes an `--output report.txt` flag, should the exported report contain raw markdown, stripped plain text, or an HTML-rendered version of the rich CLI output?
6. **Scheduled Diagnostics (Systemd Timers):** Should SysAgent support an automated scheduling feature in v1 (e.g., `sysagent schedule "check CVEs" --every 1w`) that automatically generates native Linux `systemd` `.service` and `.timer` files for recurring background diagnostics, or strictly remain an interactive, user-triggered tool?
7. **Interactive vs. Autonomous Execution:** If the agent decides to run a potentially heavy (but read-only) command like `tcpdump` or a massive recursive `grep`, should the CLI pause and prompt the user for explicit confirmation (`[y/N]`), or is the read-only sandbox trusted to execute all commands autonomously for maximum speed?
8. **Streaming "Thought" Output:** Because LLM tool execution can take 10–20 seconds, how should the CLI handle the waiting UX? Should it stream the agent's internal thought process to the screen in real-time (*"Thinking... running ps aux... reading syslog..."*) to provide visibility, or just display a clean spinner?
9. **Dynamic Log Targeting:** When the agent needs to read a massive file like `/var/log/syslog` or `journalctl` output, how does it target the right data without blowing up the context window? Does it rely on basic `tail` and `grep` heuristics, or do we implement dynamic chunking and local vector search for logs similar to the RAG implementation?
10. **Cross-Session Persistence:** Feature 8 dictates that context is cleared when the CLI session ends. If a lightweight state storage mechanism (like SQLite or a local JSON file) is established during development, should SysAgent implement an optional `--resume <session_id>` flag to reload previous conversations, or strictly remain an ephemeral single-shot tool?

---

## Section 11 — Appendix

### Glossary of Terms
- **Agentic Loop:** A software pattern where an AI (the LLM) is given a goal, independently decides which tools to execute to gather information, evaluates the results, and repeats the process until the goal is met.
- **RAG (Retrieval-Augmented Generation):** A technique that improves LLM answers by searching a local database for relevant documents (like man pages) and injecting them into the prompt so the LLM doesn't have to guess or hallucinate.
- **Vector Store:** A specialized database that stores text as mathematical embeddings, allowing the system to search for meaning (e.g., finding docs about "memory management" even if the query says "RAM is full").
- **Context Window:** The maximum amount of text an LLM can process at one time. If passed too much live system data (like a 10,000-line log file), the model will crash or "forget" earlier instructions.

### External API Dependencies
For features requiring internet access, SysAgent relies on the following third-party APIs:
- **GitHub Search API** (`api.github.com/search/commits`) — Used for scanning recent changes to the `torvalds/linux` kernel repository.
- **Kernel CVE Mapping** (`github.com/gregkh/kernel-cves`) — Used as a structured, machine-readable index to cross-reference the user's running kernel against known vulnerabilities.
- **NIST NVD API** (`services.nvd.nist.gov/rest/public/cves`) — Used to pull detailed severity (CVSS) scores and patch statuses for specific CVEs.
