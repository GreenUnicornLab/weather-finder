"""
notify.py — Send weather alerts via macOS notifications and/or log file.

macOS notifications use osascript (AppleScript via subprocess).
No third-party library needed — it's built into macOS.
"""

import subprocess
import logging
from datetime import datetime
from pathlib import Path


def send_notifications(alerts: list[str], config: dict) -> None:
    """
    Send all triggered alerts via the notification channels
    configured in config["notifications"].
    """
    notif_config = config["notifications"]

    for alert in alerts:
        if notif_config.get("macos", False):
            _send_macos_notification(alert)
        if notif_config.get("log", False):
            _log_alert(alert, config)


def send_test_notification(config: dict) -> None:
    """
    Send a fake alert to verify that macOS notifications are working.
    Called by: weather-alert test-notification
    """
    title = "Weather Alert Test"
    message = "This is a test notification."
    print(f"Sending test notification — title: {title!r}, message: {message!r}")
    _send_macos_notification(message, title=title)
    if config.get("notifications", {}).get("log", False):
        _log_alert(message, config)


def _send_macos_notification(message: str, title: str = "Weather Alert") -> None:
    """
    Use osascript to display a macOS native notification.

    The AppleScript command is: display notification "..." with title "..."
    We pass the script as a list element (no shell=True), so we only need
    to escape AppleScript's own quote character: the double-quote.
    """
    safe_message = message.replace('"', '\\"')
    safe_title = title.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        print(f"[notify] osascript failed: {err}")
    else:
        print("[notify] macOS notification sent.")


def _log_alert(message: str, config: dict) -> None:
    """
    Append a timestamped line to the log file specified in config["log"]["path"].
    Creates parent directories if they don't exist.
    """
    log_path = Path(config["log"]["path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    with open(log_path, "a") as f:
        f.write(log_line)
