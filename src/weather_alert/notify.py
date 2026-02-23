# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
notify.py — Send weather alerts via macOS notifications and/or log file.

macOS notifications use osascript (AppleScript via subprocess).
No third-party library needed — it's built into macOS.
"""

import subprocess
from datetime import datetime
from pathlib import Path


def send_notifications(alerts: list[str], config: dict) -> None:
    """Send triggered alerts via all configured notification channels.

    Args:
        alerts: List of alert message strings to send.
        config: Loaded configuration dict with 'notifications' section.
    """
    notif_config = config["notifications"]

    for alert in alerts:
        if notif_config.get("macos", False):
            _send_macos_notification("Weather Alert", alert)
        if notif_config.get("log", False):
            _log_alert(alert, config)


def send_test_notification(config: dict) -> None:
    """Send a hardcoded test notification to verify macOS setup.

    Args:
        config: Loaded configuration dict with 'notifications' section.
    """
    title = "Weather Alert Test"
    message = "This is a test notification."
    print(f"Sending test notification — title: {title!r}, message: {message!r}")
    _send_macos_notification(title, message)
    if config.get("notifications", {}).get("log", False):
        _log_alert(message, config)


def _send_macos_notification(title: str, message: str) -> None:
    """Display a macOS native notification using osascript.

    Passes title and message via environment variables to prevent AppleScript
    injection through untrusted strings (e.g. weather data containing quotes
    or backslashes).

    Args:
        title: Notification title string.
        message: Notification body string.
    """
    import os

    script = (
        'display notification (system attribute "WA_MSG") '
        'with title (system attribute "WA_TITLE")'
    )
    env = {**os.environ, "WA_TITLE": title, "WA_MSG": message}

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        env=env,
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
    """Send a full weather summary as a macOS notification.

    Always fires on every run-once, regardless of alert state.

    Args:
        location_line: Display string like 'New York — Mon 23 Feb, 15:00'.
        current: Current-hour forecast dict with temperature, feels_like, etc.
        max_rain: Maximum precipitation probability across the lookahead window.
        lookahead_hours: Window size used for rain probability display.
        alerts: List of triggered alert strings (empty = no alerts).
        config: Loaded configuration dict with 'notifications' section.
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
    """Append a timestamped alert line to the configured log file.

    Args:
        message: Text to log.
        config: Loaded configuration dict with 'log.path' key.
    """
    log_path = Path(config["log"]["path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    try:
        with open(log_path, "a") as f:
            f.write(log_line)
    except OSError as e:
        print(f"[notify] Failed to write log: {e}")
