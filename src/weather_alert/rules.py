# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
rules.py — Evaluate alert conditions against the fetched forecast.

Each check_* function receives a slice of the forecast list and a threshold,
and returns a human-readable alert string if the condition is triggered,
or None if everything looks fine.

evaluate_rules() calls all checks and returns a list of triggered alerts.
"""

from typing import Optional

TEMPERATURE_LOOKAHEAD_HOURS: int = 3  # hours used for temperature/feels-like checks


def check_rain(
    forecast: list[dict],
    threshold: int,
    lookahead_hours: int,
) -> str | None:
    """Check if precipitation probability exceeds threshold in the lookahead window.

    Args:
        forecast: List of hourly forecast dicts.
        threshold: Precipitation probability percent to trigger (inclusive).
        lookahead_hours: Number of hours ahead to examine.

    Returns:
        Alert message string if triggered, None otherwise.
    """
    window = forecast[:lookahead_hours]
    for hour in window:
        prob = hour.get("precipitation_probability", 0) or 0
        if prob >= threshold:
            return (
                f"Rain likely: {prob}% chance at {hour['time']} "
                f"(threshold: {threshold}%)"
            )
    return None


def check_wind(forecast: list[dict], threshold: float) -> str | None:
    """Check if wind speed in the next hour exceeds the threshold.

    Args:
        forecast: List of hourly forecast dicts.
        threshold: Wind speed in km/h to trigger (inclusive).

    Returns:
        Alert message string if triggered, None otherwise.
    """
    if not forecast:
        return None
    next_hour = forecast[0]
    speed = next_hour.get("wind_speed", 0) or 0
    if speed >= threshold:
        return (
            f"High wind: {speed} km/h at {next_hour['time']} "
            f"(threshold: {threshold} km/h)"
        )
    return None


def check_temperature(forecast: list[dict], min_temp: float) -> str | None:
    """Check if temperature drops below minimum in the next TEMPERATURE_LOOKAHEAD_HOURS hours.

    Args:
        forecast: List of hourly forecast dicts.
        min_temp: Minimum temperature in °C (exclusive lower bound).

    Returns:
        Alert message string if triggered, None otherwise.
    """
    window = forecast[:TEMPERATURE_LOOKAHEAD_HOURS]
    for hour in window:
        temp = hour.get("temperature", float("inf"))
        if temp is not None and temp < min_temp:
            return (
                f"Cold temperature: {temp}°C at {hour['time']} "
                f"(min temperature: {min_temp}°C)"
            )
    return None


def check_feels_like(
    forecast: list[dict],
    min_feels_like: float,
) -> str | None:
    """Check if apparent temperature drops below minimum in the next 3 hours.

    Args:
        forecast: List of hourly forecast dicts.
        min_feels_like: Minimum apparent temperature in °C (exclusive lower bound).

    Returns:
        Alert message string if triggered, None otherwise.
    """
    window = forecast[:TEMPERATURE_LOOKAHEAD_HOURS]
    for hour in window:
        feels = hour.get("feels_like", float("inf"))
        if feels is not None and feels < min_feels_like:
            return (
                f"Feels very cold: {feels}°C at {hour['time']} "
                f"(min feels-like: {min_feels_like}°C)"
            )
    return None


def evaluate_rules(forecast: list[dict], config: dict) -> list[str]:
    """Run all configured alert checks against a forecast.

    Args:
        forecast: List of hourly forecast dicts.
        config: Loaded configuration dict (must contain 'alerts' section).

    Returns:
        List of triggered alert message strings. Empty if no alerts.
    """
    alerts_config = config["alerts"]

    checks = [
        check_rain(
            forecast,
            threshold=alerts_config["rain_probability_threshold"],
            lookahead_hours=alerts_config["lookahead_hours"],
        ),
        check_wind(
            forecast,
            threshold=alerts_config["wind_speed_threshold"],
        ),
        check_temperature(
            forecast,
            min_temp=alerts_config["temperature_min"],
        ),
        check_feels_like(
            forecast,
            min_feels_like=alerts_config["feels_like_min"],
        ),
    ]

    # Filter out None values (rules that didn't trigger)
    return [alert for alert in checks if alert is not None]
