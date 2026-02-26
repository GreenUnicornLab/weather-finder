# Weather Alert 🌤️

A macOS CLI tool that fetches hourly weather forecasts for any location and sends native notifications when alert conditions are met. Built on [Open-Meteo](https://open-meteo.com) — free, no API key required.

## Features

- 🌡️ Current weather report — temperature, feels-like, humidity, wind direction, rain chance, snowfall
- 🔔 Configurable alert rules with macOS native notifications (rain, wind, feels-like)
- 📅 Multi-day forecast up to 16 days (`--forecast-window`)
- ⏱️ Multi-hour forecast up to 24 hours (`--forecast-window 12`)
- 📍 Location by name — `--location "Tokyo"` or `--location "Soldeu, Andorra"`
- 🏔️ Mountain/elevation-aware forecasts (Open-Meteo terrain correction)
- ⏰ Hourly background scheduling via cron
- 🔓 No API key required

## Requirements

- macOS
- Python 3.11+

## Installation

```bash
git clone https://github.com/GreenUnicorn/weather-finder.git
cd weather-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

```bash
cp config.toml.example config.toml
```

Open `config.toml` and set your location coordinates and alert thresholds:

```toml
[location]
latitude = 40.7128
longitude = -74.0060
name = "New York"

[alerts]
rain_probability_threshold = 50   # percent
wind_speed_threshold = 30         # km/h
feels_like_min = 2                # celsius
lookahead_hours = 3
```

Find your coordinates at [latlong.net](https://www.latlong.net).

## Usage

```bash
# Current weather report for configured location
weather-alert run-once

# Weather for a named location
weather-alert run-once --location "Barcelona"

# 7-day forecast table
weather-alert run-once --location "Soldeu, Andorra" --forecast-window 7

# 12-hour forecast table
weather-alert run-once --location "London" --forecast-window 12

# Forecast for a specific time today
weather-alert run-once --location "Barcelona" --time "15:00"

# Forecast for a specific date and time
weather-alert run-once --location "Tokyo" --time "2026-02-25 09:00"

# Test macOS notifications
weather-alert test-notification

# Install hourly cron job
weather-alert install-schedule

# Remove cron job
weather-alert uninstall-schedule
```

### Example output

```
📍 New York — Mon 23 Feb, 15:00 (now)
🌡  Temperature:    8.4°C  (feels like 5.1°C)
💧 Humidity:        63%
🌧  Rain chance:    10%  (next 3 hours)
💨 Wind:            18 km/h NW
✅ No alerts triggered.
[notify] macOS notification sent.
```

## Scheduling

`weather-alert install-schedule` installs a cron job that runs `weather-alert run-once` every hour at minute 0:

```
0 * * * * /path/to/weather-alert run-once >> /path/to/logs/cron.log 2>&1
```

Output is appended to `logs/cron.log`. To remove the job:

```bash
weather-alert uninstall-schedule
```

> **macOS permission note:** If notifications don't appear when run from cron, go to
> **System Settings → Notifications → Terminal** and enable *Allow Notifications*.

## Dashboard

Run the visual weather dashboard locally:

```bash
pip install -e ".[ui]"
streamlit run app/app.py
```

Then open http://localhost:8501 in your browser.

Features:
- Search any location by name
- Current conditions hero card with large temperature display
- 1 / 3 / 7 / 16-day forecast selector
- Interactive temperature range and precipitation charts (Plotly)
- Alert indicators when thresholds are exceeded
- Apple-inspired dark UI — no Streamlit defaults visible

## Historical Analysis

Analyse up to 80 years of weather history for any location:

```bash
weather-alert history --location "Soldeu, Andorra" --years 50
```

Opens an interactive Streamlit dashboard with:
- **Temperature trends** — annual max/min range with warming trend line
- **Precipitation history** — year-by-year rainfall with wettest year highlighted
- **Snowfall patterns** — annual snowfall totals and snow day counts
- **Monthly climatology** — average conditions per calendar month
- **Extreme events** — hottest day, coldest day, most rain, most snow on record

Data source: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5 reanalysis, 10 km resolution, free).

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
src/weather_alert/
├── cli.py       — entry point, all CLI commands
├── config.py    — TOML config loader and validator
├── weather.py   — Open-Meteo API (hourly + daily forecast)
├── geocode.py   — place-name → coordinates lookup
├── rules.py     — alert rule evaluation
├── notify.py    — macOS notifications and log output
└── chart.py     — ASCII forecast tables
```

## Credits

Built with [Open-Meteo](https://open-meteo.com) — free weather API, no key required.
Developed by GreenUnicorn with [Claude](https://claude.ai) (Anthropic).
