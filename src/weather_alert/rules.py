"""
rules.py — Evaluate alert conditions against the fetched forecast.

Each check_* function receives a slice of the forecast list and a threshold,
and returns a human-readable alert string if the condition is triggered,
or None if everything looks fine.

evaluate_rules() calls all checks and returns a list of triggered alerts.
"""

from typing import Optional


def check_rain(forecast: list[dict], threshold: int, lookahead_hours: int) -> Optional[str]:
    """
    Trigger if precipitation_probability exceeds `threshold` in
    the next `lookahead_hours` hours.
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


def check_wind(forecast: list[dict], threshold: float) -> Optional[str]:
    """
    Trigger if windspeed in the next hour exceeds `threshold` km/h.
    We only look one hour ahead for wind because it changes quickly.
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


def check_temperature(forecast: list[dict], min_temp: float) -> Optional[str]:
    """
    Trigger if temperature_2m drops below `min_temp` in the next 3 hours.
    """
    window = forecast[:3]
    for hour in window:
        temp = hour.get("temperature", float("inf"))
        if temp is not None and temp < min_temp:
            return (
                f"Cold temperature: {temp}°C at {hour['time']} "
                f"(min: {min_temp}°C)"
            )
    return None


def check_feels_like(forecast: list[dict], min_feels_like: float) -> Optional[str]:
    """
    Trigger if apparent_temperature drops below `min_feels_like` in next 3 hours.
    Feels-like (wind chill / heat index) can diverge significantly from actual temp.
    """
    window = forecast[:3]
    for hour in window:
        feels = hour.get("feels_like", float("inf"))
        if feels is not None and feels < min_feels_like:
            return (
                f"Feels very cold: {feels}°C at {hour['time']} "
                f"(min feels-like: {min_feels_like}°C)"
            )
    return None


def evaluate_rules(forecast: list[dict], config: dict) -> list[str]:
    """
    Run all checks against the forecast using thresholds from config.
    Returns a list of alert strings (empty list = no alerts).
    """
    alerts_config = config["alerts"]
    alerts = []

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
