import os
from prompt_toolkit import prompt
from openai import OpenAI, AuthenticationError

from sysagent.config import SYSAGENT_DATA_DIR, global_env_path

def validate_openai_key(api_key: str) -> bool:
    """Performs a lightweight validation of the OpenAI API key."""
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()
        return True
    except AuthenticationError:
        return False
    except Exception as e:
        print(f"  [!] API error during validation: {e}")
        return False

def run_boot_wizard() -> None:
    print("\n" + "="*50)
    print("Welcome to SysAgent! Let's get you set up.")
    print("="*50 + "\n")
    
    # 1. OpenAI API Key
    while True:
        api_key = prompt("Enter your OpenAI API Key (starts with sk-): ", is_password=True).strip()
        if not api_key:
            print("  [!] API Key is required.")
            continue
            
        print("  [*] Validating key...")
        if validate_openai_key(api_key):
            print("  [+] Key is valid!\n")
            break
        else:
            print("  [!] Invalid API Key. Please try again.\n")

    # 2. Slack Webhook (Optional)
    slack_webhook = prompt("Enter a Slack Webhook URL for proactive audit reports (optional, press Enter to skip): ").strip()
    if slack_webhook and not slack_webhook.startswith("https://hooks.slack.com/services/"):
        print("  [!] That doesn't look like a standard Slack webhook URL, but we'll save it anyway.")
    print()

    # 3. Kernel Docs Path (Optional)
    default_docs = "/usr/share/doc/linux-doc/Documentation"
    docs_prompt = f"Enter the path to your Linux Kernel Documentation (optional, default: {default_docs}): "
    kernel_docs = prompt(docs_prompt).strip()
    if not kernel_docs:
        kernel_docs = default_docs
    if not os.path.exists(kernel_docs):
        print(f"  [!] Note: The path '{kernel_docs}' does not exist on this system currently.")
    print()

    # 4. Save to .env
    print("  [*] Saving configuration to global .env...")
    os.makedirs(SYSAGENT_DATA_DIR, exist_ok=True)
    
    env_content = f"""SYSAGENT_OPENAI_API_KEY="{api_key}"\n"""
    if slack_webhook:
        env_content += f"""SYSAGENT_SLACK_WEBHOOK_URL="{slack_webhook}"\n"""
    if kernel_docs:
        env_content += f"""SYSAGENT_KERNEL_DOCS_PATH="{kernel_docs}"\n"""
        
    with open(global_env_path, "w") as f:
        f.write(env_content)
        
    # Inject into current os.environ so the app can continue immediately
    os.environ["SYSAGENT_OPENAI_API_KEY"] = api_key
    os.environ["SYSAGENT_SLACK_WEBHOOK_URL"] = slack_webhook
    os.environ["SYSAGENT_KERNEL_DOCS_PATH"] = kernel_docs

    # 4.5 Scheduled Systemd Audit Generation
    if slack_webhook:
        enable_audit = prompt("Would you like to enable proactive background audits via systemd? [Y/n]: ").strip().lower()
        if enable_audit in ('', 'y', 'yes'):
            while True:
                freq = prompt("Frequency of the audit (daily, weekly, monthly) [daily]: ").strip().lower()
                if not freq or freq in ('daily', 'weekly', 'monthly'):
                    if not freq:
                        freq = "daily"
                    break
                print("  [!] Please enter 'daily', 'weekly', or 'monthly'.\n")
                
            audit_time = prompt(f"At what time should the {freq} audit run? (Format HH:MM, default: 08:00): ").strip()
            if not audit_time:
                audit_time = "08:00"
                
            if freq == "weekly":
                on_calendar = f"Mon *-*-* {audit_time}:00"
            elif freq == "monthly":
                on_calendar = f"*-*-01 {audit_time}:00"
            else:
                on_calendar = f"*-*-* {audit_time}:00"
                freq = "daily"
                
            print("  [*] Setting up systemd timer...")
            import shutil
            import subprocess
            from pathlib import Path
            import sys
            
            # Find executable path
            sysagent_path = shutil.which("sysagent")
            if not sysagent_path:
                sysagent_path = f"{sys.executable} -m sysagent.main"
                
            systemd_dir = Path.home() / ".config" / "systemd" / "user"
            systemd_dir.mkdir(parents=True, exist_ok=True)
            
            service_content = f"""[Unit]
Description=SysAgent Proactive Audit Service

[Service]
Type=oneshot
ExecStart={sysagent_path} --cron --notify slack
"""
            timer_content = f"""[Unit]
Description=Run SysAgent Proactive Audit {freq.capitalize()}

[Timer]
OnCalendar={on_calendar}
Persistent=true

[Install]
WantedBy=timers.target
"""
            (systemd_dir / "sysagent.service").write_text(service_content)
            (systemd_dir / "sysagent.timer").write_text(timer_content)
            
            try:
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
                subprocess.run(["systemctl", "--user", "enable", "--now", "sysagent.timer"], check=True, capture_output=True)
                print(f"  [+] Systemd timer enabled successfully. Your {freq} audit is scheduled for {audit_time}.\n")
            except subprocess.CalledProcessError as e:
                print(f"  [!] Failed to enable systemd timer: {e.stderr.decode().strip()}\n")
            except FileNotFoundError:
                print("  [!] systemctl command not found. You may need to enable the timer manually.\n")

    # 5. Initial Ingestion
    ingest_choice = prompt("Would you like to build the initial knowledge database (man pages and kernel docs) now? [Y/n]: ").strip().lower()
    if ingest_choice in ('', 'y', 'yes'):
        print("\n  [*] Starting initial ingestion...")
        # Temporarily inject the standard OPENAI_API_KEY for the embedder
        os.environ["OPENAI_API_KEY"] = api_key
        try:
            from sysagent.rag.ingest import ingest_all
            ingest_all()
            print("  [+] Ingestion complete!\n")
        except Exception as e:
            print(f"  [!] Ingestion failed: {e}\n")

    print("="*50)
    print("Setup complete! Starting SysAgent...\n")
