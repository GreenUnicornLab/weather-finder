# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
test_rules.py — Unit tests for each rule check.

We use hardcoded fake forecast dicts — no API calls here.
The principle: each test focuses on one rule and one boundary condition.
"""

import pytest
from weather_alert.rules import (
    check_rain,
    check_wind,
    check_temperature,
    check_feels_like,
    evaluate_rules,
    evaluate_daily_rules,
)


# ---------------------------------------------------------------------------
# Helpers: build minimal fake forecast hours
# ---------------------------------------------------------------------------

def make_hour(
    time="2024-01-01T12:00",
    temperature=15.0,
    feels_like=14.0,
    precipitation_probability=0,
    wind_speed=10.0,
    weathercode=0,
) -> dict:
    return {
        "time": time,
        "temperature": temperature,
        "feels_like": feels_like,
        "precipitation_probability": precipitation_probability,
        "wind_speed": wind_speed,
        "weathercode": weathercode,
    }


# ---------------------------------------------------------------------------
# check_rain
# ---------------------------------------------------------------------------

def test_rain_triggers_when_above_threshold():
    forecast = [make_hour(precipitation_probability=75)]
    result = check_rain(forecast, threshold=50, lookahead_hours=3)
    assert result is not None
    assert "75%" in result


def test_rain_does_not_trigger_when_below_threshold():
    forecast = [make_hour(precipitation_probability=30)]
    result = check_rain(forecast, threshold=50, lookahead_hours=3)
    assert result is None


def test_rain_triggers_at_exact_threshold():
    """Threshold is >=, so exactly at threshold should trigger."""
    forecast = [make_hour(precipitation_probability=50)]
    result = check_rain(forecast, threshold=50, lookahead_hours=3)
    assert result is not None


def test_rain_respects_lookahead_hours():
    """Rain beyond the lookahead window should NOT trigger an alert."""
    # Hour 0 and 1 are fine, hour 3 (index 2) has rain but lookahead=2
    forecast = [
        make_hour(time="T00", precipitation_probability=10),
        make_hour(time="T01", precipitation_probability=10),
        make_hour(time="T02", precipitation_probability=90),  # outside window
    ]
    result = check_rain(forecast, threshold=50, lookahead_hours=2)
    assert result is None


# ---------------------------------------------------------------------------
# check_wind
# ---------------------------------------------------------------------------

def test_wind_triggers_when_above_threshold():
    forecast = [make_hour(wind_speed=45.0)]
    result = check_wind(forecast, threshold=30.0)
    assert result is not None
    assert "45" in result


def test_wind_does_not_trigger_when_below_threshold():
    forecast = [make_hour(wind_speed=20.0)]
    result = check_wind(forecast, threshold=30.0)
    assert result is None


def test_wind_only_checks_next_hour():
    """Wind rule only checks forecast[0]; second hour's high wind is ignored."""
    forecast = [
        make_hour(time="T00", wind_speed=10.0),
        make_hour(time="T01", wind_speed=60.0),
    ]
    result = check_wind(forecast, threshold=30.0)
    assert result is None


def test_wind_empty_forecast_returns_none():
    result = check_wind([], threshold=30.0)
    assert result is None


# ---------------------------------------------------------------------------
# check_temperature
# ---------------------------------------------------------------------------

def test_temperature_triggers_when_below_min():
    forecast = [make_hour(temperature=2.0)]
    result = check_temperature(forecast, min_temp=5.0)
    assert result is not None
    assert "2.0" in result


def test_temperature_does_not_trigger_when_above_min():
    forecast = [make_hour(temperature=10.0)]
    result = check_temperature(forecast, min_temp=5.0)
    assert result is None


def test_temperature_checks_up_to_3_hours():
    forecast = [
        make_hour(time="T00", temperature=10.0),
        make_hour(time="T01", temperature=10.0),
        make_hour(time="T02", temperature=1.0),   # hour 3 (index 2), within window
        make_hour(time="T03", temperature=-5.0),  # hour 4, outside 3-hour window
    ]
    result = check_temperature(forecast, min_temp=5.0)
    assert result is not None
    assert "1.0" in result


# ---------------------------------------------------------------------------
# check_feels_like
# ---------------------------------------------------------------------------

def test_feels_like_triggers_when_below_min():
    forecast = [make_hour(feels_like=-3.0)]
    result = check_feels_like(forecast, min_feels_like=2.0)
    assert result is not None
    assert "-3.0" in result


def test_feels_like_does_not_trigger_when_above_min():
    forecast = [make_hour(feels_like=10.0)]
    result = check_feels_like(forecast, min_feels_like=2.0)
    assert result is None


# ---------------------------------------------------------------------------
# evaluate_rules (integration-style, still no network)
# ---------------------------------------------------------------------------

def test_evaluate_rules_returns_all_triggered():
    """All rules trigger with extreme values."""
    forecast = [
        make_hour(
            precipitation_probability=90,
            wind_speed=50,
            temperature=-5,
            feels_like=-10,
        )
    ]
    config = {
        "alerts": {
            "rain_probability_threshold": 50,
            "wind_speed_threshold": 30,
            "temperature_min": 5,
            "feels_like_min": 2,
            "lookahead_hours": 3,
        }
    }
    alerts = evaluate_rules(forecast, config)
    assert any("Rain" in a for a in alerts), "Expected a rain alert"
    assert any("wind" in a.lower() for a in alerts), "Expected a wind alert"
    assert any("Cold" in a for a in alerts), "Expected a temperature alert"
    assert any("cold" in a.lower() for a in alerts), "Expected a feels-like alert"


def test_evaluate_rules_returns_empty_when_no_trigger():
    """No rules trigger with comfortable values."""
    forecast = [
        make_hour(
            precipitation_probability=10,
            wind_speed=10,
            temperature=20,
            feels_like=18,
        )
    ]
    config = {
        "alerts": {
            "rain_probability_threshold": 50,
            "wind_speed_threshold": 30,
            "temperature_min": 5,
            "feels_like_min": 2,
            "lookahead_hours": 3,
        }
    }
    alerts = evaluate_rules(forecast, config)
    assert alerts == []


# ---------------------------------------------------------------------------
# degrees_to_compass
# ---------------------------------------------------------------------------

from weather_alert.weather import degrees_to_compass


def test_compass_north():
    assert degrees_to_compass(0) == "N"

def test_compass_north_wraparound():
    assert degrees_to_compass(360) == "N"

def test_compass_east():
    assert degrees_to_compass(90) == "E"

def test_compass_south():
    assert degrees_to_compass(180) == "S"

def test_compass_west():
    assert degrees_to_compass(270) == "W"

def test_compass_northeast():
    assert degrees_to_compass(45) == "NE"

def test_compass_southwest():
    assert degrees_to_compass(225) == "SW"

def test_compass_nne():
    assert degrees_to_compass(22.5) == "NNE"


# ---------------------------------------------------------------------------
# Boundary: values exactly at threshold should trigger (>= semantics)
# ---------------------------------------------------------------------------

def test_wind_triggers_at_exact_threshold():
    """Wind rule uses >= so exactly at threshold must trigger."""
    forecast = [make_hour(wind_speed=30.0)]
    result = check_wind(forecast, threshold=30.0)
    assert result is not None


def test_temperature_does_not_trigger_at_exact_min():
    """Temperature rule uses < so exactly at min_temp must NOT trigger."""
    forecast = [make_hour(temperature=5.0)]
    result = check_temperature(forecast, min_temp=5.0)
    assert result is None


def test_feels_like_does_not_trigger_at_exact_min():
    """Feels-like rule uses < so exactly at min must NOT trigger."""
    forecast = [make_hour(feels_like=2.0)]
    result = check_feels_like(forecast, min_feels_like=2.0)
    assert result is None


# ---------------------------------------------------------------------------
# evaluate_daily_rules
# ---------------------------------------------------------------------------

def make_day(
    date="2024-01-01",
    rain_probability=0,
    wind_max=10.0,
    temp_min=10.0,
    temp_max=20.0,
) -> dict:
    return {
        "date": date,
        "rain_probability": rain_probability,
        "wind_max": wind_max,
        "temp_min": temp_min,
        "temp_max": temp_max,
    }


_DAILY_CONFIG = {
    "alerts": {
        "rain_probability_threshold": 50,
        "wind_speed_threshold": 30,
        "temperature_min": 5,
    }
}


def test_daily_rules_no_alerts():
    day = make_day(rain_probability=20, wind_max=10, temp_min=15)
    assert evaluate_daily_rules(day, _DAILY_CONFIG) == []


def test_daily_rules_rain_triggers():
    day = make_day(rain_probability=60)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert any("Rain" in a for a in alerts)


def test_daily_rules_wind_triggers():
    day = make_day(wind_max=50)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert any("Wind" in a for a in alerts)


def test_daily_rules_temp_min_triggers():
    day = make_day(temp_min=-3)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert any("Min temperature" in a for a in alerts)


def test_daily_rules_all_trigger():
    day = make_day(rain_probability=80, wind_max=60, temp_min=-10)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert len(alerts) == 3


def test_daily_rules_rain_at_exact_threshold_triggers():
    day = make_day(rain_probability=50)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert any("Rain" in a for a in alerts)


def test_daily_rules_wind_at_exact_threshold_triggers():
    day = make_day(wind_max=30.0)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert any("Wind" in a for a in alerts)


def test_daily_rules_temp_at_exact_min_no_trigger():
    """temp_min uses < so exactly at threshold must NOT trigger."""
    day = make_day(temp_min=5.0)
    alerts = evaluate_daily_rules(day, _DAILY_CONFIG)
    assert not any("Min temperature" in a for a in alerts)
