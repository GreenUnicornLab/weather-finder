"""
cli.py — Command-line interface for weather-alert.

We use argparse (stdlib) rather than click because:
- No extra dependency to install
- Sufficient for 4 simple subcommands
- Easier for beginners to read and understand

Commands:
  weather-alert run-once            — fetch + evaluate + notify
  weather-alert test-notification   — send a fake alert
  weather-alert install-schedule    — install cron job
  weather-alert uninstall-schedule  — remove cron job
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from weather_alert.config import load_config
from weather_alert.weather import fetch_forecast
from weather_alert.rules import evaluate_rules
from weather_alert.notify import send_test_notification, send_weather_notification


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
    else:
        print("✅ No alerts triggered.")

    # Always send the full weather summary as a macOS notification
    send_weather_notification(
        location_line=f"{display_name} — {time_str}",
        current=current,
        max_rain=max_rain,
        lookahead_hours=lookahead,
        alerts=alerts,
        config=config,
    )


def cmd_test_notification(args) -> None:
    """Send a fake alert to verify macOS notifications work."""
    config = load_config()
    send_test_notification(config)


def cmd_install_schedule(args) -> None:
    """Install an hourly cron job to run weather-alert run-once."""
    import shutil
    import subprocess

    # Resolve the weather-alert binary path
    binary = shutil.which("weather-alert")
    if not binary:
        print("[error] Could not find weather-alert binary. Make sure it is installed with pip install -e .")
        raise SystemExit(1)

    # Resolve the logs directory to an absolute path
    config = load_config()
    log_path = Path(config["log"]["path"]).resolve()
    log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    cron_log = log_dir / "cron.log"

    # Build the cron line: run at minute 0 of every hour
    cron_line = f"0 * * * * {binary} run-once >> {cron_log} 2>&1"

    # Read the existing crontab (empty string if none exists yet)
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
    )
    # crontab -l exits non-zero when no crontab exists — treat that as empty
    existing = result.stdout if result.returncode == 0 else ""

    # Guard against double-installation
    if "weather-alert" in existing:
        print("[schedule] Already installed. Run uninstall-schedule first.")
        raise SystemExit(0)

    # Append the new line (ensure there is a trailing newline before appending)
    updated = existing.rstrip("\n")
    if updated:
        updated += "\n"
    updated += cron_line + "\n"

    # Write back via crontab -
    write_result = subprocess.run(
        ["crontab", "-"],
        input=updated,
        capture_output=True,
        text=True,
    )
    if write_result.returncode != 0:
        print(f"[error] Failed to write crontab: {write_result.stderr.strip()}")
        raise SystemExit(1)

    print("[schedule] Cron job installed. weather-alert will run every hour.")
    print("[schedule] To verify: crontab -l")


def cmd_uninstall_schedule(args) -> None:
    """Remove the weather-alert cron job."""
    import subprocess

    # Read current crontab
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # No crontab at all — nothing to remove
        print("[schedule] No crontab found. Nothing to remove.")
        return

    lines = result.stdout.splitlines(keepends=True)
    filtered = [line for line in lines if "weather-alert" not in line]

    if len(filtered) == len(lines):
        print("[schedule] No weather-alert cron job found. Nothing to remove.")
        return

    # Write filtered lines back (or clear the crontab if now empty)
    updated = "".join(filtered)
    write_result = subprocess.run(
        ["crontab", "-"],
        input=updated,
        capture_output=True,
        text=True,
    )
    if write_result.returncode != 0:
        print(f"[error] Failed to write crontab: {write_result.stderr.strip()}")
        raise SystemExit(1)

    print("[schedule] Cron job removed.")


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
    subparsers.add_parser("install-schedule", help="Install cron job (runs every hour)")
    subparsers.add_parser("uninstall-schedule", help="Remove cron job")

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
