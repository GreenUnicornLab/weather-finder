"""
weather.py — Fetch hourly weather forecast from Open-Meteo.

Open-Meteo is free and requires no API key. We request the next
forecast_hours hours of data and return a clean list of dicts.

API docs: https://open-meteo.com/en/docs
"""

import requests
from datetime import datetime, timezone


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Fields we care about from the hourly forecast
HOURLY_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "windspeed_10m",
    "weathercode",
    "relativehumidity_2m",
]


def fetch_forecast(latitude: float, longitude: float, forecast_hours: int = 6) -> list[dict]:
    """
    Fetch hourly forecast from Open-Meteo and return a list of dicts,
    one per hour, for the next `forecast_hours` hours.

    Each dict has keys: time, temperature, feels_like,
    precipitation_probability, wind_speed, weathercode.

    Raises requests.HTTPError on API error.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "forecast_days": 1,
        "timezone": "auto",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return _parse_hourly(data, forecast_hours)


def _parse_hourly(data: dict, forecast_hours: int) -> list[dict]:
    """
    Extract the next `forecast_hours` hours from the raw API response.

    The API returns parallel arrays indexed by hour. We zip them into
    a list of dicts for easier processing downstream.
    """
    hourly = data["hourly"]
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    feels = hourly["apparent_temperature"]
    precip = hourly["precipitation_probability"]
    wind = hourly["windspeed_10m"]
    codes = hourly["weathercode"]
    humidity = hourly["relativehumidity_2m"]

    now = datetime.now(timezone.utc)
    result = []

    for i, time_str in enumerate(times):
        # Open-Meteo returns ISO-8601 strings without timezone when timezone=auto
        # We compare by index position: the first entry is the current hour
        if i >= forecast_hours:
            break
        result.append({
            "time": time_str,
            "temperature": temps[i],
            "feels_like": feels[i],
            "precipitation_probability": precip[i],
            "wind_speed": wind[i],
            "weathercode": codes[i],
            "humidity": humidity[i],
        })

    return result
