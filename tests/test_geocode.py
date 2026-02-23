# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
test_geocode.py — Unit tests for geocode.py.

All tests mock with_retry — no real network calls.
"""

import pytest

from weather_alert.geocode import LocationNotFoundError, geocode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_geocode_response(results: list) -> dict:
    return {"results": results} if results else {}


def _make_result(name="Tokyo", admin1="Tokyo", country="Japan", lat=35.6895, lon=139.6917) -> dict:
    return {
        "name": name,
        "admin1": admin1,
        "country": country,
        "latitude": lat,
        "longitude": lon,
    }


# ---------------------------------------------------------------------------
# geocode — successful cases
# ---------------------------------------------------------------------------

def test_geocode_returns_latitude_longitude_name(monkeypatch):
    payload = _make_geocode_response([_make_result()])
    monkeypatch.setattr("weather_alert.geocode.with_retry", lambda fn, **kw: payload)

    result = geocode("Tokyo")

    assert result["latitude"] == pytest.approx(35.6895)
    assert result["longitude"] == pytest.approx(139.6917)
    assert "Tokyo" in result["name"]


def test_geocode_canonical_name_includes_region_and_country(monkeypatch):
    payload = _make_geocode_response([_make_result(name="London", admin1="England", country="United Kingdom")])
    monkeypatch.setattr("weather_alert.geocode.with_retry", lambda fn, **kw: payload)

    result = geocode("London")

    assert "London" in result["name"]
    assert "England" in result["name"]
    assert "United Kingdom" in result["name"]


def test_geocode_canonical_name_without_admin1(monkeypatch):
    """If admin1 is absent, canonical name should be City, Country."""
    raw = _make_result()
    raw.pop("admin1", None)
    raw["admin1"] = None  # API may return null
    payload = {"results": [raw]}
    monkeypatch.setattr("weather_alert.geocode.with_retry", lambda fn, **kw: payload)

    result = geocode("Tokyo")

    # admin1 is falsy, so it should be omitted
    assert "None" not in result["name"]
    assert "Tokyo" in result["name"]


def test_geocode_uses_first_result_only(monkeypatch):
    """geocode must only use results[0], ignoring subsequent matches."""
    payload = _make_geocode_response([
        _make_result(name="Paris", admin1="Île-de-France", country="France", lat=48.8566, lon=2.3522),
        _make_result(name="Paris", admin1="Texas", country="United States", lat=33.6609, lon=-95.5555),
    ])
    monkeypatch.setattr("weather_alert.geocode.with_retry", lambda fn, **kw: payload)

    result = geocode("Paris")

    assert result["latitude"] == pytest.approx(48.8566)


# ---------------------------------------------------------------------------
# geocode — not found
# ---------------------------------------------------------------------------

def test_geocode_raises_location_not_found_when_empty_results(monkeypatch):
    monkeypatch.setattr(
        "weather_alert.geocode.with_retry",
        lambda fn, **kw: {"results": []},
    )
    with pytest.raises(LocationNotFoundError, match="not found"):
        geocode("xyznonexistent")


def test_geocode_raises_location_not_found_when_no_results_key(monkeypatch):
    monkeypatch.setattr(
        "weather_alert.geocode.with_retry",
        lambda fn, **kw: {},
    )
    with pytest.raises(LocationNotFoundError):
        geocode("xyznonexistent")


def test_location_not_found_is_value_error():
    """LocationNotFoundError must be a subclass of ValueError."""
    assert issubclass(LocationNotFoundError, ValueError)


# ---------------------------------------------------------------------------
# geocode — no longer raises SystemExit
# ---------------------------------------------------------------------------

def test_geocode_does_not_raise_system_exit_on_missing_location(monkeypatch):
    """After FIX 3, geocode must raise LocationNotFoundError, not SystemExit."""
    monkeypatch.setattr(
        "weather_alert.geocode.with_retry",
        lambda fn, **kw: {},
    )
    with pytest.raises(LocationNotFoundError):
        geocode("nonexistent place")

    # Verify SystemExit is NOT raised
    try:
        geocode("nonexistent place")
    except LocationNotFoundError:
        pass  # expected
    except SystemExit:
        pytest.fail("geocode raised SystemExit — should raise LocationNotFoundError instead")
