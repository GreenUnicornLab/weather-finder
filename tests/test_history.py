# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""Tests for history.py — date_range_for_years, _parse_daily, fetch_historical."""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from weather_alert.history import date_range_for_years, _parse_daily, fetch_historical


# ---------------------------------------------------------------------------
# Shared mock API response
# ---------------------------------------------------------------------------

MOCK_API_RESPONSE = {
    "daily": {
        "time": ["2023-01-01", "2023-01-02"],
        "temperature_2m_max":  [4.0,  5.0],
        "temperature_2m_min":  [-1.0, 0.0],
        "temperature_2m_mean": [1.5,  2.5],
        "precipitation_sum":   [2.0,  0.5],
        "snowfall_sum":        [1.0,  0.0],
        "snow_depth_max":      [10.0, 9.0],
        "windspeed_10m_max":   [25.0, 18.0],
    }
}


# ---------------------------------------------------------------------------
# date_range_for_years
# ---------------------------------------------------------------------------

class TestDateRangeForYears:

    def test_end_date_is_yesterday(self):
        """end date must be exactly today minus one day."""
        _, end = date_range_for_years(10)
        assert end == date.today() - timedelta(days=1)

    def test_start_date_is_n_years_before_end(self):
        """start date must be N years before end (same month and day)."""
        years = 10
        start, end = date_range_for_years(years)
        assert start.year == end.year - years
        assert start.month == end.month
        assert start.day == end.day

    def test_returns_tuple_of_two_date_objects(self):
        """Return value must be a 2-tuple of datetime.date instances."""
        result = date_range_for_years(5)
        assert isinstance(result, tuple)
        assert len(result) == 2
        start, end = result
        assert isinstance(start, date)
        assert isinstance(end, date)

    def test_start_before_end(self):
        """start must always be strictly before end."""
        start, end = date_range_for_years(1)
        assert start < end

    def test_single_year_span(self):
        """Passing years=1 gives a ~365-day range."""
        start, end = date_range_for_years(1)
        delta = end - start
        # A 1-year span is 365 or 366 days depending on leap year
        assert 365 <= delta.days <= 366

    def test_fifty_years(self):
        """years=50 produces a start date 50 years before yesterday."""
        start, end = date_range_for_years(50)
        assert start.year == end.year - 50


# ---------------------------------------------------------------------------
# _parse_daily
# ---------------------------------------------------------------------------

class TestParseDaily:

    def test_returns_list_of_dicts(self):
        """_parse_daily must return a list."""
        result = _parse_daily(MOCK_API_RESPONSE)
        assert isinstance(result, list)

    def test_length_matches_input_dates(self):
        """One dict per date entry in the API response."""
        result = _parse_daily(MOCK_API_RESPONSE)
        assert len(result) == 2

    def test_required_keys_present(self):
        """Each record must contain all 8 required keys."""
        expected_keys = {
            "date", "temp_max", "temp_min", "temp_mean",
            "precipitation", "snowfall", "snow_depth_max", "wind_max",
        }
        result = _parse_daily(MOCK_API_RESPONSE)
        for record in result:
            assert set(record.keys()) == expected_keys

    def test_date_is_date_object(self):
        """The 'date' field must be a datetime.date instance, not a string."""
        result = _parse_daily(MOCK_API_RESPONSE)
        for record in result:
            assert isinstance(record["date"], date)

    def test_date_values_are_correct(self):
        """Parsed dates must match the input strings."""
        result = _parse_daily(MOCK_API_RESPONSE)
        assert result[0]["date"] == date(2023, 1, 1)
        assert result[1]["date"] == date(2023, 1, 2)

    def test_numeric_values_are_floats(self):
        """All non-date fields must be float instances."""
        result = _parse_daily(MOCK_API_RESPONSE)
        float_keys = ["temp_max", "temp_min", "temp_mean",
                      "precipitation", "snowfall", "snow_depth_max", "wind_max"]
        for record in result:
            for key in float_keys:
                assert isinstance(record[key], float), (
                    f"Expected float for key '{key}', got {type(record[key])}"
                )

    def test_values_match_api_data(self):
        """Numeric values must correspond exactly to the API payload."""
        result = _parse_daily(MOCK_API_RESPONSE)
        r0 = result[0]
        assert r0["temp_max"]       == 4.0
        assert r0["temp_min"]       == -1.0
        assert r0["temp_mean"]      == 1.5
        assert r0["precipitation"]  == 2.0
        assert r0["snowfall"]       == 1.0
        assert r0["snow_depth_max"] == 10.0
        assert r0["wind_max"]       == 25.0

    def test_none_api_values_become_zero(self):
        """None values in the API response must be coerced to 0.0."""
        api_response_with_nones = {
            "daily": {
                "time": ["2023-06-01"],
                "temperature_2m_max":  [None],
                "temperature_2m_min":  [None],
                "temperature_2m_mean": [None],
                "precipitation_sum":   [None],
                "snowfall_sum":        [None],
                "snow_depth_max":      [None],
                "windspeed_10m_max":   [None],
            }
        }
        result = _parse_daily(api_response_with_nones)
        assert len(result) == 1
        r = result[0]
        assert r["temp_max"]       == 0.0
        assert r["temp_min"]       == 0.0
        assert r["temp_mean"]      == 0.0
        assert r["precipitation"]  == 0.0
        assert r["snowfall"]       == 0.0
        assert r["snow_depth_max"] == 0.0
        assert r["wind_max"]       == 0.0

    def test_mixed_none_and_valid_values(self):
        """Only None entries become 0.0; valid values are preserved."""
        response = {
            "daily": {
                "time": ["2023-03-01"],
                "temperature_2m_max":  [10.0],
                "temperature_2m_min":  [None],
                "temperature_2m_mean": [5.0],
                "precipitation_sum":   [None],
                "snowfall_sum":        [0.0],
                "snow_depth_max":      [None],
                "windspeed_10m_max":   [12.5],
            }
        }
        result = _parse_daily(response)
        r = result[0]
        assert r["temp_max"]       == 10.0
        assert r["temp_min"]       == 0.0
        assert r["temp_mean"]      == 5.0
        assert r["precipitation"]  == 0.0
        assert r["snowfall"]       == 0.0
        assert r["snow_depth_max"] == 0.0
        assert r["wind_max"]       == 12.5

    def test_empty_input_returns_empty_list(self):
        """An API response with no dates must produce an empty list."""
        empty_response = {
            "daily": {
                "time": [],
                "temperature_2m_max":  [],
                "temperature_2m_min":  [],
                "temperature_2m_mean": [],
                "precipitation_sum":   [],
                "snowfall_sum":        [],
                "snow_depth_max":      [],
                "windspeed_10m_max":   [],
            }
        }
        result = _parse_daily(empty_response)
        assert result == []


# ---------------------------------------------------------------------------
# fetch_historical (mocked HTTP)
# ---------------------------------------------------------------------------

class TestFetchHistorical:

    @patch("weather_alert.history.requests.get")
    def test_returns_list(self, mock_get):
        """fetch_historical must return a list."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_historical(46.5, 7.0, years=1)

        assert isinstance(result, list)

    @patch("weather_alert.history.requests.get")
    def test_result_has_correct_structure(self, mock_get):
        """Each record in the result must have the 8 expected keys."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_historical(46.5, 7.0, years=1)

        expected_keys = {
            "date", "temp_max", "temp_min", "temp_mean",
            "precipitation", "snowfall", "snow_depth_max", "wind_max",
        }
        assert len(result) > 0
        for record in result:
            assert set(record.keys()) == expected_keys

    @patch("weather_alert.history.requests.get")
    def test_api_called_with_correct_lat_lon(self, mock_get):
        """requests.get must receive the latitude and longitude in params."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        lat, lon = 51.5074, -0.1278
        fetch_historical(lat, lon, years=1)

        assert mock_get.called, "requests.get was never called"
        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        assert params.get("latitude") == lat
        assert params.get("longitude") == lon

    @patch("weather_alert.history.requests.get")
    def test_api_called_with_date_range_params(self, mock_get):
        """requests.get params must include start_date and end_date."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        fetch_historical(48.8, 2.35, years=2)

        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        assert "start_date" in params
        assert "end_date" in params
        # end_date must be yesterday in ISO format
        expected_end = (date.today() - timedelta(days=1)).isoformat()
        assert params["end_date"] == expected_end

    @patch("weather_alert.history.requests.get")
    def test_date_fields_are_date_objects(self, mock_get):
        """Parsed records returned by fetch_historical must have date objects."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_historical(40.7, -74.0, years=1)

        for record in result:
            assert isinstance(record["date"], date)

    @patch("weather_alert.history.requests.get")
    def test_result_length_matches_api_response(self, mock_get):
        """Number of records returned must equal number of dates in API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_historical(35.7, 139.7, years=1)

        # MOCK_API_RESPONSE has 2 dates
        assert len(result) == 2
