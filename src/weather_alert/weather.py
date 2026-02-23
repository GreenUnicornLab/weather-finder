# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
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
    "winddirection_10m",
    "weathercode",
    "relativehumidity_2m",
    "snowfall",
    "snow_depth",
]


def degrees_to_compass(degrees: float) -> str:
    """
    Convert a wind direction in degrees (0-360) to a 16-point compass label.
    0° = N, 90° = E, 180° = S, 270° = W.
    """
    compass = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW",
    ]
    # Each segment is 360/16 = 22.5 degrees wide
    index = round(degrees / 22.5) % 16
    return compass[index]


def fetch_forecast(latitude: float, longitude: float, forecast_hours: int = 6, target_time_str: str | None = None) -> list[dict]:
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
        "forecast_days": 7,
        "timezone": "auto",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    return _parse_hourly(data, forecast_hours, target_time_str=target_time_str)


def _parse_hourly(data: dict, forecast_hours: int, target_time_str: str | None = None) -> list[dict]:
    """
    Extract `forecast_hours` hours of data starting from a given or current hour.

    Open-Meteo returns a full-day array starting at midnight. We locate
    the target hour by matching the formatted datetime string, then
    slice forward from there.

    If target_time_str is provided, use it as the start time; otherwise
    use the current local hour.
    """
    hourly = data["hourly"]
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    feels = hourly["apparent_temperature"]
    precip = hourly["precipitation_probability"]
    wind = hourly["windspeed_10m"]
    wind_dir_deg = hourly["winddirection_10m"]
    codes = hourly["weathercode"]
    humidity = hourly["relativehumidity_2m"]
    snowfall = hourly["snowfall"]
    snow_depth = hourly["snow_depth"]

    if target_time_str is not None:
        lookup_str = target_time_str
        time_label = "requested"
    else:
        lookup_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        time_label = "current"

    try:
        start = times.index(lookup_str)
    except ValueError:
        raise RuntimeError(
            f"Requested time '{lookup_str}' not found in forecast times. "
            f"Available range: {times[0]} to {times[-1]}\n"
            f"[error] Requested time is outside the available forecast window (7 days)."
        )

    result = []
    for i in range(start, min(start + forecast_hours, len(times))):
        result.append({
            "time": times[i],
            "temperature": temps[i],
            "feels_like": feels[i],
            "precipitation_probability": precip[i],
            "wind_speed": wind[i],
            "wind_direction": degrees_to_compass(wind_dir_deg[i]),
            "weathercode": codes[i],
            "humidity": humidity[i],
            "snowfall": (snowfall[i] or 0),
            "snow_depth": round((snow_depth[i] or 0) * 100, 1),  # convert m → cm
        })

    return result


# Open-Meteo uses terrain-based elevation correction automatically when latitude/longitude
# are provided, so mountain locations like Sierra Nevada return accurate temperature and
# snowfall data without any extra configuration.

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "snowfall_sum",
    "snow_depth_max",
    "windspeed_10m_max",
    "winddirection_10m_dominant",
]


def fetch_daily_forecast(latitude: float, longitude: float, forecast_days: int = 7) -> list[dict]:
    """
    Fetch a daily aggregated forecast from Open-Meteo.

    Returns a list of dicts, one per day, with keys:
      date, temp_max, temp_min, precip_mm, rain_probability,
      snowfall_cm, snow_depth_cm, wind_max, wind_direction
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARIABLES),
        "forecast_days": forecast_days,
        "timezone": "auto",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    daily = data["daily"]
    dates = daily["time"]

    result = []
    for i, date_str in enumerate(dates):
        result.append({
            "date": date_str,
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "precip_mm": daily["precipitation_sum"][i] or 0,
            "rain_probability": daily["precipitation_probability_max"][i] or 0,
            "snowfall_cm": daily["snowfall_sum"][i] or 0,
            "snow_depth_cm": round((daily["snow_depth_max"][i] or 0) * 100, 1),
            "wind_max": daily["windspeed_10m_max"][i],
            "wind_direction": degrees_to_compass(daily["winddirection_10m_dominant"][i] or 0),
        })

    return result
