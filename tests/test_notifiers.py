import pytest
from unittest.mock import patch, MagicMock
import requests
from sysagent.system.notifiers import send_slack_alert

@patch("sysagent.system.notifiers.SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
@patch("requests.post")
def test_send_slack_alert_success(mock_post):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    result = send_slack_alert("Hello Slack")
    
    assert result is True
    mock_post.assert_called_once_with(
        "https://hooks.slack.com/services/test",
        json={"text": "Hello Slack"},
        timeout=10
    )

@patch("sysagent.system.notifiers.SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
@patch("requests.post")
def test_send_slack_alert_http_error(mock_post):
    mock_post.side_effect = requests.exceptions.HTTPError("404 Not Found")
    result = send_slack_alert("Hello Slack")
    assert result is False

@patch("sysagent.system.notifiers.SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
@patch("requests.post")
def test_send_slack_alert_timeout(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout()
    result = send_slack_alert("Hello Slack")
    assert result is False

@patch("sysagent.system.notifiers.SLACK_WEBHOOK_URL", "")
def test_send_slack_alert_missing_config():
    with pytest.raises(ValueError, match="SLACK_WEBHOOK_URL is not configured"):
        send_slack_alert("Hello Slack")
