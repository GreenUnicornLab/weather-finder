# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-03-17

### Fixed
- `app/app.py`: catch `LocationNotFoundError` instead of `SystemExit` when geocoding fails (was swallowing all location errors silently)
- `app/app.py`: add missing `temperature_min` key to fallback config, preventing `KeyError` when `load_config()` fails
- `src/weather_alert/ski.py`: `best_weeks_to_ski()` now sorts by `avg_snow_depth` (was incorrectly sorting by `avg_snowfall`)
- `src/weather_alert/history.py`: fix `ValueError` crash in `date_range_for_years()` when called on Feb 29 of a leap year targeting a non-leap year
- `src/weather_alert/cli.py`: `weather-alert history` is now non-blocking (uses `Popen` like `weather-alert ski`)
- `Makefile`: `install` target now uses `.venv/bin/pip` instead of bare `pip`
- `app/ski.py`: removed dependency on private `_`-prefixed functions; `ski.py` now exposes `day_offset`, `ski_season_week`, `week_label` as public API
- `analysis.py`, `app/history.py`: `strftime` day format is now platform-safe (`%-d` on POSIX, `%#d` on Windows)

### Added
- `pyproject.toml`: `pandas` added to `[ui]` extras; `ruff` and `types-requests` added to `[dev]` extras
- `tests/test_history.py`: edge-case test for Feb 29 → non-leap-year `date_range_for_years`
- `tests/test_ski.py`: strengthened sort-key test so it only passes with the correct `avg_snow_depth` sort
- `tests/test_weather.py`: numerical assertion on `snow_depth_cm` value in daily forecast

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
