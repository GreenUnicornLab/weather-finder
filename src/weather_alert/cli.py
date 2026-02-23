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
from datetime import datetime
from pathlib import Path

from weather_alert.config import load_config
from weather_alert.weather import fetch_forecast
from weather_alert.rules import evaluate_rules
from weather_alert.notify import send_notifications, send_test_notification


def cmd_run_once(args) -> None:
    """Fetch weather, evaluate rules, send alerts if triggered."""
    from datetime import datetime
    from weather_alert.geocode import geocode

    config = load_config()

    # Resolve location: --location flag overrides config.toml
    if args.location:
        loc = geocode(args.location)
        latitude = loc["latitude"]
        longitude = loc["longitude"]
        display_name = loc["name"]
    else:
        location = config["location"]
        latitude = location["latitude"]
        longitude = location["longitude"]
        display_name = location["name"]

    # Resolve target time: --time flag or current hour
    target_time_str = None
    time_label = "now"
    if args.time:
        time_label = "forecast"
        raw = args.time.strip()
        # Accept "HH:MM" (assume today) or "YYYY-MM-DD HH:MM"
        if len(raw) == 5 and ":" in raw:
            # Just HH:MM — use today's date
            today = datetime.now().strftime("%Y-%m-%d")
            target_time_str = f"{today}T{raw}"
        else:
            # Full datetime — parse and reformat
            try:
                dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
                target_time_str = dt.strftime("%Y-%m-%dT%H:00")
            except ValueError:
                print(f"[error] Unrecognised --time format: '{raw}'. Use 'HH:MM' or 'YYYY-MM-DD HH:MM'.")
                raise SystemExit(1)

    print(f"Fetching forecast for {display_name}...")

    try:
        forecast = fetch_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_hours=config["alerts"]["lookahead_hours"] + 1,
            target_time_str=target_time_str,
        )
    except RuntimeError as e:
        print(str(e))
        raise SystemExit(1)

    if not forecast:
        print("[error] No forecast data returned.")
        raise SystemExit(1)

    current = forecast[0]

    # Parse and format the display time
    try:
        dt = datetime.strptime(current["time"], "%Y-%m-%dT%H:%M")
        time_str = dt.strftime("%a %d %b, %H:%M")
    except ValueError:
        time_str = current["time"]

    # Max rain across the lookahead window
    max_rain = max(
        (h.get("precipitation_probability") or 0) for h in forecast
    )
    lookahead = config["alerts"]["lookahead_hours"]

    # Print weather report
    print(f"\n📍 {display_name} — {time_str} ({time_label})")
    print(f"🌡  Temperature:    {current['temperature']}°C  (feels like {current['feels_like']}°C)")
    print(f"💧 Humidity:        {current.get('humidity', 'N/A')}%")
    print(f"🌧  Rain chance:    {max_rain}%  (next {lookahead} hours)")
    print(f"💨 Wind:            {current['wind_speed']} km/h {current.get('wind_direction', '')}")

    # Evaluate rules
    alerts = evaluate_rules(forecast, config)

    if alerts:
        print()
        for alert in alerts:
            print(f"⚠️  ALERT: {alert}")
        send_notifications(alerts, config)
    else:
        print("✅ No alerts triggered.")


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

    p_run = subparsers.add_parser("run-once", help="Fetch weather and send alerts if triggered")
    p_run.add_argument(
        "--location",
        metavar="PLACE",
        default=None,
        help='Look up coordinates by place name, e.g. "Tokyo" or "London, UK"',
    )
    p_run.add_argument(
        "--time",
        metavar="TIME",
        default=None,
        help='Forecast for a specific time, e.g. "15:00" or "2026-02-25 09:00"',
    )
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
