# SysAgent Scheduling & Reporting Feature

The goal is to allow SysAgent to run completely headlessly on a schedule (via systemd timers) and push proactive system health, performance, and security reports to a designated platform like Slack or Discord.

## User Review Required
Please review the updated implementation plan which focuses solely on the core pipeline (`--cron` flag + notifiers) as requested.

## Answered Questions (For the Record)
> 1. The scheduled job will **always** send a report, acting exactly like an automated CLI query.
> 2. We will support **Slack first**, ensure the entire pipeline works perfectly, and only then add **Discord**.
> 3. **NEW:** We will build an interactive Setup Wizard to configure the scheduling directly from Python, rather than deferring it.

## Proposed Architecture

### 1. New Headless CLI Flag (`--cron`)
We will add a new argument to `main.py` (e.g., `python -m sysagent.main --cron --notify slack`). 
When this flag is present, the script will:
- Skip the interactive `prompt_toolkit` terminal.
- Pass a hardcoded "Audit Prompt" to the `run_react_loop`.
- Example prompt: *"Perform a complete proactive system health check. Analyze current CPU, memory, load average, top processes, and unpatched kernel CVEs. Produce a concise Executive Summary report in markdown."*

### 2. Notifier Dispatcher (`sysagent.system.notifiers`)
We will create a new module responsible for taking the LLM's final generated string and pushing it to the outside world.

#### Slack & Discord Integration
- Use **Slack Incoming Webhooks** and **Discord Webhooks**.
- Both APIs work identically: they accept a POST request with a JSON payload containing the message.
- The notifier module will check the `.env` file for the requested webhook URL and route the LLM's markdown output accordingly.

### 3. Environment Variables
We will update the `requirements.txt` (to include `requests` if not already present) and update the local `.env` template to include:
```env
# Notifications
# Notifications
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
# DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..." (Deferred to Phase 2)
```

## Phase 3: Interactive Setup Wizard (NEW)

To make SysAgent user-friendly, we will build a Python setup script that handles the OS-level scheduling for the user.

### Open Questions (For User Review)
> [!IMPORTANT]
> **1. Root vs User Timers:** Creating system-wide timers in `/etc/systemd/system/` requires the user to run the setup with `sudo`. Alternatively, we can create user-level timers in `~/.config/systemd/user/` which don't require root, but they only run reliably if the user's session is active (or if `loginctl enable-linger` is set). Should the wizard require `sudo` and install globally, or install locally as the current user?
> 
> **2. Priority:** Should we build this Setup Wizard right now, or should we finish adding the Discord webhook (Phase 2) first?

### Proposed Logic
1. Add a `--setup` flag to `main.py`.
2. When run, it prompts the user interactively:
   - "Do you want to enable Slack notifications? [y/N]" -> Prompts for webhook URL.
   - "Do you want to run SysAgent on a schedule? (e.g., daily, hourly, none)"
3. It automatically writes the `.env` file to save the webhooks.
4. It dynamically generates `sysagent.service` and `sysagent.timer` files.
5. It uses `subprocess` to write these files to the OS and execute `systemctl daemon-reload` and `systemctl enable --now sysagent.timer`.

## Proposed Changes

### Core Logic
#### [MODIFY] [main.py](file:///home/lena/repos/sysagent/sysagent/main.py)
Add `--cron` and `--notify [slack|discord]` CLI arguments. When present, bypass the REPL, run a single proactive audit loop, and pass the result to the notification dispatcher.

#### [NEW] [notifiers.py](file:///home/lena/repos/sysagent/sysagent/system/notifiers.py)
Implement `send_slack_alert(text: str)`. (Discord alert will be added after Slack is fully verified).

#### [MODIFY] [config.py](file:///home/lena/repos/sysagent/sysagent/config.py)
Update to load the new webhook environment variables securely.

### Documentation
#### [MODIFY] [README.md](file:///home/lena/repos/sysagent/README.md)
Add a "Scheduled Audits (Systemd Timers)" section explaining how the user can manually create `.service` and `.timer` units and configure the `.env` file to enable headless reporting.

## Verification Plan

### Automated Tests
- Unit tests for the `notifiers.py` module (mocking `requests.post`).
- End-to-end dry run passing `--cron --notify slack` with a mock webhook.

### Manual Verification
- We will set up a test Slack/Discord webhook and trigger the agent manually via the CLI to verify formatting.
- We will configure a test systemd timer to ensure the agent executes successfully in a background, non-TTY environment.
