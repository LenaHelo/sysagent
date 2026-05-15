import sys
import requests
from sysagent.config import SLACK_WEBHOOK_URL

def send_slack_alert(text: str) -> bool:
    """
    Sends a markdown-formatted message to the configured Slack webhook.
    Returns True if successful, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        raise ValueError("SLACK_WEBHOOK_URL is not configured in the environment.")
        
    payload = {
        "text": text
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.Timeout:
        print("Error: Slack webhook request timed out.", file=sys.stderr)
        return False
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to Slack webhook.", file=sys.stderr)
        return False
    except requests.exceptions.HTTPError as e:
        print(f"Error: Slack webhook returned HTTP error: {e}", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error: An unexpected error occurred while sending Slack alert: {e}", file=sys.stderr)
        return False
