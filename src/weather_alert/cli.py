# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
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
from weather_alert.weather import fetch_forecast, fetch_daily_forecast
from weather_alert.rules import evaluate_rules
from weather_alert.notify import send_test_notification, send_weather_notification
from weather_alert.chart import render_daily_table, render_hourly_table, _fmt_day, _fmt_hour
from weather_alert.utils import write_last_run, read_last_run


def cmd_run_once(args) -> None:
    """Fetch weather, print report, evaluate rules, send notifications."""
    from datetime import datetime
    from weather_alert.geocode import geocode

    config = load_config()

    try:
        # ── Resolve location ──────────────────────────────────────
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

        # ── Resolve target time ───────────────────────────────────
        target_time_str = None
        time_label = "now"
        if args.time:
            time_label = "forecast"
            raw = args.time.strip()
            if len(raw) == 5 and ":" in raw:
                today = datetime.now().strftime("%Y-%m-%d")
                target_time_str = f"{today}T{raw}"
            else:
                try:
                    dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
                    target_time_str = dt.strftime("%Y-%m-%dT%H:00")
                except ValueError:
                    print(f"[error] Unrecognised --time format: '{raw}'. Use 'HH:MM' or 'YYYY-MM-DD HH:MM'.")
                    raise SystemExit(1)

        window = getattr(args, "forecast_window", 1)

        # ── Multi-day path (window >= 2) ──────────────────────────
        if window >= 2:
            days = min(window, 16)
            print(f"Fetching {days}-day forecast for {display_name}...")
            daily = fetch_daily_forecast(latitude=latitude, longitude=longitude, forecast_days=days)

            print()
            print(render_daily_table(daily, display_name))
            print()

            # Evaluate alerts per day
            alerts_config = config["alerts"]
            any_alerts = False
            for day in daily:
                day_alerts = []
                if day["rain_probability"] >= alerts_config["rain_probability_threshold"]:
                    day_alerts.append(
                        f"Rain probability {day['rain_probability']}% exceeds threshold of {alerts_config['rain_probability_threshold']}%"
                    )
                if day["wind_max"] >= alerts_config["wind_speed_threshold"]:
                    day_alerts.append(
                        f"Wind {day['wind_max']:.0f} km/h exceeds threshold of {alerts_config['wind_speed_threshold']} km/h"
                    )
                if day["temp_min"] < alerts_config["temperature_min"]:
                    day_alerts.append(
                        f"Min temperature {day['temp_min']}°C below threshold of {alerts_config['temperature_min']}°C"
                    )
                for alert in day_alerts:
                    print(f"⚠️  {_fmt_day(day['date'])}: {alert}")
                    any_alerts = True

            if not any_alerts:
                print("✅ No alerts in forecast window.")
            write_last_run("OK", "Alerts in window" if any_alerts else "No alerts in window")
            return

        # ── Multi-hour path (window 1-24) ─────────────────────────
        lookahead = config["alerts"]["lookahead_hours"]
        fetch_hours = max(window, lookahead + 1)

        print(f"Fetching forecast for {display_name}...")

        try:
            forecast = fetch_forecast(
                latitude=latitude,
                longitude=longitude,
                forecast_hours=fetch_hours,
                target_time_str=target_time_str,
            )
        except RuntimeError as e:
            print(str(e))
            raise SystemExit(1)

        if not forecast:
            print("[error] No forecast data returned.")
            raise SystemExit(1)

        # If window > 1, show the multi-hour table instead of a single-line report
        if window > 1:
            display_hours = forecast[:window]
            print()
            print(render_hourly_table(display_hours, display_name))

            print()
            # Evaluate rules over the window
            alerts = evaluate_rules(forecast[:window], config)
            if alerts:
                for alert in alerts:
                    print(f"⚠️  ALERT: {alert}")
            else:
                print("✅ No alerts triggered.")
            write_last_run("OK", f"{len(alerts)} alert(s) triggered" if alerts else "No alerts")
            return

        # ── Single-hour report (default, window == 1) ─────────────
        current = forecast[0]

        try:
            dt = datetime.strptime(current["time"], "%Y-%m-%dT%H:%M")
            time_str = dt.strftime("%a %d %b, %H:%M")
        except ValueError:
            time_str = current["time"]

        max_rain = max((h.get("precipitation_probability") or 0) for h in forecast)
        snowfall = current.get("snowfall", 0) or 0
        snow_depth = current.get("snow_depth", 0) or 0

        print(f"\n📍 {display_name} — {time_str} ({time_label})")
        print(f"🌡  Temperature:    {current['temperature']}°C  (feels like {current['feels_like']}°C)")
        print(f"💧 Humidity:        {current.get('humidity', 'N/A')}%")
        print(f"🌧  Rain chance:    {max_rain}%  (next {lookahead} hours)")
        print(f"💨 Wind:            {current['wind_speed']} km/h {current.get('wind_direction', '')}")
        if snowfall > 0:
            print(f"❄️  Snowfall:        {snowfall} cm")
        if snow_depth > 0:
            print(f"🏔️  Snow depth:      {snow_depth} cm on ground")

        alerts = evaluate_rules(forecast, config)

        if alerts:
            print()
            for alert in alerts:
                print(f"⚠️  ALERT: {alert}")
        else:
            print("✅ No alerts triggered.")

        send_weather_notification(
            location_line=f"{display_name} — {time_str}",
            current=current,
            max_rain=max_rain,
            lookahead_hours=lookahead,
            alerts=alerts,
            config=config,
        )
        # Record last run status
        if alerts:
            write_last_run("OK", f"{len(alerts)} alert(s) triggered")
        else:
            write_last_run("OK", "No alerts")

    except RuntimeError as e:
        write_last_run("ERROR", str(e).replace("|", "-"))
        raise SystemExit(1)


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


def cmd_status(args) -> None:
    """Show cron job status, last run info, and log file size."""
    import subprocess

    config = load_config()
    log_path = Path(config["log"]["path"])
    log_dir = log_path.parent

    # Check cron
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    cron_installed = result.returncode == 0 and "weather-alert" in result.stdout
    cron_status = "✅ Installed" if cron_installed else "❌ Not installed"

    # Read last run
    last = read_last_run(log_dir)
    if last:
        last_run_time = last["timestamp"]
        if last["status"] == "OK":
            if "alert" in last["detail"].lower() and not last["detail"].startswith("No"):
                last_result = f"⚠️  {last['detail']}"
            else:
                last_result = f"✅ {last['detail']}"
        else:
            last_result = f"❌ {last['detail']}"
    else:
        last_run_time = "Never"
        last_result = "—"

    # Log file size
    if log_path.exists():
        size_kb = log_path.stat().st_size // 1024
        log_info = f"{log_path} ({size_kb} KB)"
    else:
        log_info = f"{log_path} (not created yet)"

    sep = "─" * 45
    print(f"\n🔧 Weather Alert — Status")
    print(sep)
    print(f"  Cron job:    {cron_status}")
    print(f"  Last run:    {last_run_time}")
    print(f"  Last result: {last_result}")
    print(f"  Log file:    {log_info}")
    print(sep)


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
    p_run.add_argument(
        "--forecast-window",
        metavar="N",
        type=int,
        default=1,
        help="Hours (1-24) or days (2-16) to show as a forecast table. Default: 1 (current hour only).",
    )
    subparsers.add_parser("test-notification", help="Send a test macOS notification")
    subparsers.add_parser("install-schedule", help="Install cron job (runs every hour)")
    subparsers.add_parser("uninstall-schedule", help="Remove cron job")
    subparsers.add_parser("status", help="Show cron job status and last run info")

    args = parser.parse_args()

    commands = {
        "run-once": cmd_run_once,
        "test-notification": cmd_test_notification,
        "install-schedule": cmd_install_schedule,
        "uninstall-schedule": cmd_uninstall_schedule,
        "status": cmd_status,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
