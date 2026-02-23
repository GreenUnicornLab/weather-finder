# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
geocode.py — Look up coordinates for a place name using Open-Meteo Geocoding API.

Free, no API key required.
API docs: https://open-meteo.com/en/docs/geocoding-api
"""

import requests
from weather_alert.utils import with_retry

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(place: str) -> dict:
    """Look up coordinates for a place name using Open-Meteo Geocoding.

    Args:
        place: Human-readable place name, e.g. 'Tokyo' or 'London, UK'.

    Returns:
        Dict with keys: latitude (float), longitude (float), name (str).
        The name is a canonical 'City, Region, Country' string.

    Raises:
        SystemExit: If no results are found for the place name.
        RuntimeError: If all API retry attempts fail.
    """
    params = {
        "name": place,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    def _call():
        r = requests.get(GEOCODING_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    data = with_retry(_call, label=f"Geocoding API for '{place}'")

    results = data.get("results")
    if not results:
        print(f'[error] Location "{place}" not found. Try a more specific name.')
        raise SystemExit(1)

    result = results[0]
    # Build a human-readable canonical name: "City, Country" (include admin1 region if available)
    name_parts = [result.get("name", place)]
    if result.get("admin1"):
        name_parts.append(result["admin1"])
    if result.get("country"):
        name_parts.append(result["country"])
    canonical_name = ", ".join(name_parts)

    return {
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "name": canonical_name,
    }
