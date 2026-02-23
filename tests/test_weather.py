# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
test_weather.py — Unit tests for weather.py.

All tests use in-memory fake API payloads — no network calls.
"""

import pytest

from weather_alert.weather import (
    degrees_to_compass,
    _parse_hourly,
    fetch_daily_forecast,
    fetch_forecast,
)


# ---------------------------------------------------------------------------
# degrees_to_compass — already exercised in test_rules.py for basic values,
# but we add edge-case coverage here.
# ---------------------------------------------------------------------------

def test_compass_just_below_360():
    assert degrees_to_compass(359.9) == "N"


def test_compass_boundary_22_5():
    assert degrees_to_compass(22.5) == "NNE"


def test_compass_south_exact():
    assert degrees_to_compass(180) == "S"


# ---------------------------------------------------------------------------
# _parse_hourly — unit tests with fake response dict
# ---------------------------------------------------------------------------

def _make_hourly_payload(n: int = 5, base_time: str = "2024-01-01T00:00") -> dict:
    """Build a minimal Open-Meteo hourly response with n entries."""
    from datetime import datetime, timedelta

    base = datetime.strptime(base_time, "%Y-%m-%dT%H:%M")
    times = [(base + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(n)]

    return {
        "hourly": {
            "time": times,
            "temperature_2m": [10.0 + i for i in range(n)],
            "apparent_temperature": [9.0 + i for i in range(n)],
            "precipitation_probability": [0] * n,
            "windspeed_10m": [5.0] * n,
            "winddirection_10m": [0.0] * n,
            "weathercode": [0] * n,
            "relativehumidity_2m": [70] * n,
            "snowfall": [0.0] * n,
            "snow_depth": [0.0] * n,
        }
    }


def test_parse_hourly_returns_correct_count():
    data = _make_hourly_payload(n=10)
    result = _parse_hourly(data, forecast_hours=4, target_time_str="2024-01-01T00:00")
    assert len(result) == 4


def test_parse_hourly_maps_field_names():
    data = _make_hourly_payload(n=3)
    result = _parse_hourly(data, forecast_hours=1, target_time_str="2024-01-01T00:00")
    hour = result[0]
    assert "time" in hour
    assert "temperature" in hour
    assert "feels_like" in hour
    assert "precipitation_probability" in hour
    assert "wind_speed" in hour
    assert "wind_direction" in hour
    assert "humidity" in hour
    assert "snowfall" in hour
    assert "snow_depth" in hour


def test_parse_hourly_temperature_values():
    data = _make_hourly_payload(n=3)
    result = _parse_hourly(data, forecast_hours=2, target_time_str="2024-01-01T00:00")
    assert result[0]["temperature"] == 10.0
    assert result[1]["temperature"] == 11.0


def test_parse_hourly_wind_direction_converted():
    data = _make_hourly_payload(n=2)
    # 0 degrees = North
    result = _parse_hourly(data, forecast_hours=1, target_time_str="2024-01-01T00:00")
    assert result[0]["wind_direction"] == "N"


def test_parse_hourly_raises_on_unknown_target_time():
    data = _make_hourly_payload(n=5)
    with pytest.raises(RuntimeError, match="not found in forecast times"):
        _parse_hourly(data, forecast_hours=1, target_time_str="1990-01-01T00:00")


def test_parse_hourly_snow_depth_converted_to_cm():
    """snow_depth from API is in metres; _parse_hourly must convert to cm."""
    data = _make_hourly_payload(n=2)
    data["hourly"]["snow_depth"] = [0.25, 0.0]  # 0.25 m = 25 cm
    result = _parse_hourly(data, forecast_hours=1, target_time_str="2024-01-01T00:00")
    assert result[0]["snow_depth"] == 25.0


def test_parse_hourly_raises_on_missing_hourly_key():
    """If API response is missing 'hourly', raise RuntimeError."""
    with pytest.raises(RuntimeError, match="Unexpected API response structure"):
        _parse_hourly({}, forecast_hours=1, target_time_str="2024-01-01T00:00")


def test_parse_hourly_handles_none_precip():
    """precipitation_probability may be None in the API; should default to 0."""
    data = _make_hourly_payload(n=2)
    data["hourly"]["precipitation_probability"] = [None, None]
    result = _parse_hourly(data, forecast_hours=1, target_time_str="2024-01-01T00:00")
    # The raw None is stored as-is; evaluate rules handle None via `or 0`
    assert result[0]["precipitation_probability"] is None


# ---------------------------------------------------------------------------
# fetch_forecast — mock with_retry to return fake payload
# ---------------------------------------------------------------------------

@pytest.fixture()
def hourly_payload():
    return _make_hourly_payload(n=24, base_time="2024-01-01T00:00")


def test_fetch_forecast_returns_list(hourly_payload):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "weather_alert.weather.with_retry",
            lambda fn, **kw: hourly_payload,
        )
        result = fetch_forecast(
            latitude=51.5,
            longitude=-0.1,
            forecast_hours=3,
            target_time_str="2024-01-01T00:00",
        )
    assert isinstance(result, list)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# fetch_daily_forecast — mock with_retry to return fake daily payload
# ---------------------------------------------------------------------------

def _make_daily_payload(n: int = 3) -> dict:
    from datetime import date, timedelta

    base = date(2024, 1, 1)
    dates = [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]

    return {
        "daily": {
            "time": dates,
            "temperature_2m_max": [15.0] * n,
            "temperature_2m_min": [5.0] * n,
            "precipitation_sum": [0.0] * n,
            "precipitation_probability_max": [20] * n,
            "snowfall_sum": [0.0] * n,
            "snow_depth_max": [0.0] * n,
            "windspeed_10m_max": [10.0] * n,
            "winddirection_10m_dominant": [90.0] * n,  # East
        }
    }


def test_fetch_daily_forecast_returns_correct_count():
    payload = _make_daily_payload(n=5)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "weather_alert.weather.with_retry",
            lambda fn, **kw: payload,
        )
        result = fetch_daily_forecast(latitude=51.5, longitude=-0.1, forecast_days=5)
    assert len(result) == 5


def test_fetch_daily_forecast_field_names():
    payload = _make_daily_payload(n=1)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "weather_alert.weather.with_retry",
            lambda fn, **kw: payload,
        )
        result = fetch_daily_forecast(latitude=51.5, longitude=-0.1, forecast_days=1)
    day = result[0]
    for key in ("date", "temp_max", "temp_min", "precip_mm", "rain_probability",
                "snowfall_cm", "snow_depth_cm", "wind_max", "wind_direction"):
        assert key in day, f"Missing key: {key}"


def test_fetch_daily_forecast_wind_direction_converted():
    payload = _make_daily_payload(n=1)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "weather_alert.weather.with_retry",
            lambda fn, **kw: payload,
        )
        result = fetch_daily_forecast(latitude=51.5, longitude=-0.1, forecast_days=1)
    assert result[0]["wind_direction"] == "E"  # 90 degrees


def test_fetch_daily_forecast_raises_on_bad_response():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "weather_alert.weather.with_retry",
            lambda fn, **kw: {},
        )
        with pytest.raises(RuntimeError, match="Unexpected API response structure"):
            fetch_daily_forecast(latitude=51.5, longitude=-0.1, forecast_days=1)
