"""
cli.py — Command-line interface for weather-alert.

We use argparse (stdlib) rather than click because:
- No extra dependency to install
- Sufficient for 4 simple subcommands
- Easier for beginners to read and understand

Commands:
  weather-alert run-once            — fetch + evaluate + notify
  weather-alert test-notification   — send a fake alert
  weather-alert install-schedule    — install launchd plist
  weather-alert uninstall-schedule  — remove launchd plist
"""

import argparse
import sys
from pathlib import Path

from weather_alert.config import load_config
from weather_alert.weather import fetch_forecast
from weather_alert.rules import evaluate_rules
from weather_alert.notify import send_notifications, send_test_notification


def cmd_run_once(args) -> None:
    """Fetch weather, evaluate rules, send alerts if triggered."""
    config = load_config()

    location = config["location"]
    print(f"Fetching forecast for {location['name']} "
          f"({location['latitude']}, {location['longitude']})...")

    forecast = fetch_forecast(
        latitude=location["latitude"],
        longitude=location["longitude"],
        forecast_hours=config["alerts"]["lookahead_hours"] + 1,
    )

    alerts = evaluate_rules(forecast, config)

    if alerts:
        print(f"{len(alerts)} alert(s) triggered:")
        for alert in alerts:
            print(f"  • {alert}")
        send_notifications(alerts, config)
    else:
        print("No alerts. Weather looks fine.")


def cmd_test_notification(args) -> None:
    """Send a fake alert to verify macOS notifications work."""
    config = load_config()
    send_test_notification(config)


def cmd_install_schedule(args) -> None:
    """Install the launchd plist to ~/Library/LaunchAgents/."""
    import shutil
    import subprocess

    # Find the template relative to this file
    template_path = Path(__file__).parent.parent.parent / "launchd" / "com.user.weather-alert.plist.template"
    if not template_path.exists():
        # Try relative to cwd (when running from project root)
        template_path = Path("launchd/com.user.weather-alert.plist.template")

    if not template_path.exists():
        print(f"Error: plist template not found at {template_path}")
        sys.exit(1)

    # Find the weather-alert binary
    binary = shutil.which("weather-alert")
    if not binary:
        print("Error: weather-alert not found in PATH. Is it installed? Run: pip install -e .")
        sys.exit(1)

    # Resolve log directory to an absolute path
    config = load_config()
    log_path = Path(config["log"]["path"]).resolve()
    log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Read template and substitute placeholders
    template = template_path.read_text()
    plist_content = (
        template
        .replace("{{WEATHER_ALERT_BINARY}}", binary)
        .replace("{{LOG_DIR}}", str(log_dir))
    )

    # Write to ~/Library/LaunchAgents/
    dest = Path.home() / "Library" / "LaunchAgents" / "com.user.weather-alert.plist"
    dest.write_text(plist_content)
    print(f"Plist written to: {dest}")

    # Load with launchctl
    result = subprocess.run(
        ["launchctl", "load", str(dest)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("Launchd job loaded. weather-alert will run every hour.")
    else:
        print(f"Warning: launchctl load failed: {result.stderr.strip()}")


def cmd_uninstall_schedule(args) -> None:
    """Unload and remove the launchd plist."""
    import subprocess

    dest = Path.home() / "Library" / "LaunchAgents" / "com.user.weather-alert.plist"

    if not dest.exists():
        print(f"Plist not found at {dest}. Nothing to uninstall.")
        return

    result = subprocess.run(
        ["launchctl", "unload", str(dest)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("Launchd job unloaded.")
    else:
        print(f"Warning: launchctl unload returned: {result.stderr.strip()}")

    dest.unlink()
    print(f"Removed: {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="weather-alert",
        description="macOS weather alert tool using Open-Meteo",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.required = True

    subparsers.add_parser("run-once", help="Fetch weather and send alerts if triggered")
    subparsers.add_parser("test-notification", help="Send a test macOS notification")
    subparsers.add_parser("install-schedule", help="Install launchd job (runs every hour)")
    subparsers.add_parser("uninstall-schedule", help="Remove launchd job")

    args = parser.parse_args()

    commands = {
        "run-once": cmd_run_once,
        "test-notification": cmd_test_notification,
        "install-schedule": cmd_install_schedule,
        "uninstall-schedule": cmd_uninstall_schedule,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
