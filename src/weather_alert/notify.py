# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
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
    _send_macos_notification("Weather Alert Test", "This is a test notification.")
    if config.get("notifications", {}).get("log", False):
        _log_alert(message, config)


def _send_macos_notification(title: str, message: str) -> None:
    """
    Use osascript to display a macOS native notification.
    Caller supplies both title and message as plain strings.
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


def send_weather_notification(
    location_line: str,
    current: dict,
    max_rain: int,
    lookahead_hours: int,
    alerts: list[str],
    config: dict,
) -> None:
    """
    Always send a macOS notification with the full weather summary.
    Called on every run-once regardless of whether alerts triggered.

    Title:   "📍 Barcelona — Tue 24 Feb, 14:00"
    Message: "🌡 12.3°C (feels 9.1°C) · 💧 67% · 🌧 0% rain · 💨 18 km/h NW · ✅ No alerts"
             or with alerts:
             "🌡 12.3°C (feels 9.1°C) · 💧 67% · 🌧 65% rain · 💨 18 km/h NW · ⚠️ Rain above threshold"
    """
    if not config.get("notifications", {}).get("macos", False):
        return

    title = f"📍 {location_line}"

    temp = current.get("temperature", "?")
    feels = current.get("feels_like", "?")
    humidity = current.get("humidity", "?")
    wind_speed = current.get("wind_speed", "?")
    wind_dir = current.get("wind_direction", "")

    # Build alert suffix
    if alerts:
        # Strip long detail from alert strings — keep just the key phrase
        alert_summary = ", ".join(
            a.split(":")[0] if ":" in a else a for a in alerts
        )
        alert_part = f"⚠️ {alert_summary}"
    else:
        alert_part = "✅ No alerts"

    message = (
        f"🌡 {temp}°C (feels {feels}°C) · "
        f"💧 {humidity}% · "
        f"🌧 {max_rain}% rain · "
        f"💨 {wind_speed} km/h {wind_dir} · "
        f"{alert_part}"
    )

    _send_macos_notification(title, message)

    if config.get("notifications", {}).get("log", False):
        _log_alert(f"Notification sent: {message}", config)


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
