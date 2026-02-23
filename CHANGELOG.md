# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-02-23

### Added
- Initial release
- Current weather report: temperature, feels-like, humidity, wind direction, rain chance, snowfall
- Location lookup by name via Open-Meteo Geocoding API (`--location`)
- macOS native notifications via osascript (no third-party library)
- Alert rules: rain probability, wind speed, feels-like temperature
- Multi-day forecast table up to 16 days (`--forecast-window N`)
- Multi-hour forecast table up to 24 hours
- Snowfall and snow depth display (shown only when non-zero)
- Forecast for a specific time (`--time`)
- Retry logic: 3 attempts with 5-second delay on API failures
- Failure logging with timestamped `[ERROR]` lines
- Cron scheduling: `install-schedule` / `uninstall-schedule`
- `status` command showing cron state, last run time, and log file size
- No API key required (Open-Meteo)
