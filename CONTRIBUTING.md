# Contributing

## Development Setup

```bash
git clone https://github.com/GreenUnicorn/weather-finder.git
cd weather-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config.toml.example config.toml
# Edit config.toml with your location
```

## Running Tests

```bash
pytest -q
```

All tests run without network access (API calls are mocked).

## Code Style Expectations

- **Type hints** on every function signature
- **Google-style docstrings** on every function and module
- **Single responsibility** — functions should do one thing; aim for under 40 lines
- **Named constants** instead of magic numbers at module level
- **Specific exceptions** — avoid bare `except:` or `except Exception:` in application code
- **No new dependencies** — keep the stdlib + `requests` footprint

## Making Changes

1. Create a branch: `git checkout -b feat/my-feature`
2. Write or update tests for your change
3. Ensure `pytest -q` passes
4. Commit with a descriptive message using conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for code improvements
   - `docs:` for documentation changes
5. Push and open a pull request

## Project Structure

```
src/weather_alert/
├── cli.py       — Entry point and all CLI commands
├── config.py    — TOML config loader and validator
├── weather.py   — Open-Meteo API: hourly and daily forecast
├── geocode.py   — Place-name → coordinates lookup
├── rules.py     — Alert rule evaluation
├── notify.py    — macOS notifications and log output
├── chart.py     — ASCII forecast tables
└── utils.py     — Shared: retry logic, last-run tracking
```
