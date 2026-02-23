# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
geocode.py — Look up coordinates for a place name using Open-Meteo Geocoding API.

Free, no API key required.
API docs: https://open-meteo.com/en/docs/geocoding-api
"""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(place: str) -> dict:
    """
    Look up coordinates for a place name.

    Returns a dict with keys: latitude, longitude, name
    where name is the canonical "City, Country" string.

    Raises SystemExit with a clear message if not found.
    """
    params = {
        "name": place,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    response = requests.get(GEOCODING_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

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
