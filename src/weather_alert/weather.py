"""
weather.py — Fetch hourly weather forecast from Open-Meteo.

Open-Meteo is free and requires no API key. We request the next
forecast_hours hours of data and return a clean list of dicts.

API docs: https://open-meteo.com/en/docs
"""

import requests
from datetime import datetime


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
        "forecast_days": 2,   # cover late-night lookahead into next day
        "timezone": "auto",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return _parse_hourly(data, forecast_hours)


def _parse_hourly(data: dict, forecast_hours: int) -> list[dict]:
    """
    Extract `forecast_hours` hours of data starting from the current local hour.

    Open-Meteo returns a full-day array starting at midnight. We locate
    today's current hour by matching the formatted datetime string, then
    slice forward from there.
    """
    hourly = data["hourly"]
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    feels = hourly["apparent_temperature"]
    precip = hourly["precipitation_probability"]
    wind = hourly["windspeed_10m"]
    codes = hourly["weathercode"]
    humidity = hourly["relativehumidity_2m"]

    # Match current local hour to the API's time strings (format: "YYYY-MM-DDTHH:00")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:00")
    try:
        start = times.index(now_str)
    except ValueError:
        raise RuntimeError(
            f"Current hour '{now_str}' not found in forecast times. "
            f"Available range: {times[0]} to {times[-1]}"
        )

    result = []
    for i in range(start, min(start + forecast_hours, len(times))):
        result.append({
            "time": times[i],
            "temperature": temps[i],
            "feels_like": feels[i],
            "precipitation_probability": precip[i],
            "wind_speed": wind[i],
            "weathercode": codes[i],
            "humidity": humidity[i],
        })

    return result
