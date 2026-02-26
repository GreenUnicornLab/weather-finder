# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
history.py — Fetch historical daily weather data from Open-Meteo Archive API.
API docs: https://open-meteo.com/en/docs/historical-weather-api
"""

import requests
from datetime import date, timedelta
from weather_alert.utils import with_retry

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "snowfall_sum",
    "snow_depth_max",
    "windspeed_10m_max",
]

def date_range_for_years(years: int) -> tuple[date, date]:
    """Return (start_date, end_date) for the past N years ending yesterday."""
    end = date.today() - timedelta(days=1)
    start = end.replace(year=end.year - years)
    return start, end

def fetch_historical(
    latitude: float,
    longitude: float,
    years: int = 50,
) -> list[dict]:
    """Fetch daily historical weather data from Open-Meteo Archive API.

    Returns a list of dicts, one per day, with keys:
        date (datetime.date), temp_max, temp_min, temp_mean (float, celsius),
        precipitation (float, mm), snowfall (float, cm),
        snow_depth_max (float, cm), wind_max (float, km/h)

    Raises RuntimeError if all retries fail.
    For N=50 years this is ~18,250 rows returned in a single API response.
    """
    start, end = date_range_for_years(years)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto",
    }

    def _call() -> dict:
        r = requests.get(ARCHIVE_API_URL, params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    data = with_retry(_call, label="Open-Meteo historical archive API")
    return _parse_daily(data)

def _parse_daily(data: dict) -> list[dict]:
    """Parse the Open-Meteo archive response into a list of daily record dicts."""
    daily = data["daily"]
    dates      = daily["time"]
    temp_max   = daily["temperature_2m_max"]
    temp_min   = daily["temperature_2m_min"]
    temp_mean  = daily["temperature_2m_mean"]
    precip     = daily["precipitation_sum"]
    snowfall   = daily["snowfall_sum"]
    snow_depth = daily["snow_depth_max"]
    wind_max   = daily["windspeed_10m_max"]

    records = []
    for i, date_str in enumerate(dates):
        records.append({
            "date":           date.fromisoformat(date_str),
            "temp_max":       float(temp_max[i])    if temp_max[i]    is not None else 0.0,
            "temp_min":       float(temp_min[i])    if temp_min[i]    is not None else 0.0,
            "temp_mean":      float(temp_mean[i])   if temp_mean[i]   is not None else 0.0,
            "precipitation":  float(precip[i])      if precip[i]      is not None else 0.0,
            "snowfall":       float(snowfall[i])    if snowfall[i]    is not None else 0.0,
            "snow_depth_max": float(snow_depth[i])  if snow_depth[i]  is not None else 0.0,
            "wind_max":       float(wind_max[i])    if wind_max[i]    is not None else 0.0,
        })
    return records
