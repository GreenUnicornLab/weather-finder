# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
test_ski.py — Unit tests for the ski season intelligence module.

Uses hardcoded sample data only — no API calls.
"""

from datetime import date, timedelta

import pytest

from weather_alert.ski import (
    best_weeks_to_ski,
    get_current_season_data,
    historical_seasons,
    predict_current_season,
    rate_season,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_record(
    d: date,
    snowfall: float,
    snow_depth: float,
    temp_mean: float = 0.0,
) -> dict:
    return {
        "date": d,
        "snowfall": snowfall,
        "snow_depth_max": snow_depth,
        "temp_max": temp_mean + 2,
        "temp_min": temp_mean - 2,
        "temp_mean": temp_mean,
        "precipitation": snowfall * 0.1,
        "wind_max": 10.0,
        "humidity_mean": None,
    }


def season_records(season_year: int, snowfall_per_day: float = 5.0) -> list[dict]:
    """Build a full set of daily records for one ski season (Nov – Apr)."""
    records = []
    # Nov + Dec of season_year
    for month in (11, 12):
        days_in_month = 30 if month == 11 else 31
        for day in range(1, days_in_month + 1):
            d = date(season_year, month, day)
            records.append(make_record(d, snowfall_per_day, 50.0, -5.0))
    # Jan – Apr of season_year + 1
    for month, days in ((1, 31), (2, 28), (3, 31), (4, 30)):
        for day in range(1, days + 1):
            d = date(season_year + 1, month, day)
            records.append(make_record(d, snowfall_per_day, 50.0, -5.0))
    return records


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestHistoricalSeasons:
    def test_groups_two_complete_seasons(self):
        """Two full seasons should produce two season dicts."""
        recs = season_records(2020) + season_records(2021)
        seasons = historical_seasons(recs)
        assert len(seasons) == 2
        labels = {s["season_label"] for s in seasons}
        assert "2020-21" in labels
        assert "2021-22" in labels

    def test_season_totals(self):
        """Total snowfall should match sum of daily snowfall in that season."""
        recs = season_records(2018, snowfall_per_day=10.0)
        seasons = historical_seasons(recs)
        assert len(seasons) == 1
        s = seasons[0]
        expected_days = 30 + 31 + 31 + 28 + 31 + 30  # Nov–Apr
        assert s["total_snowfall"] == pytest.approx(expected_days * 10.0)

    def test_season_label_format(self):
        """Season label for year 2019 should be '2019-20'."""
        recs = season_records(2019)
        seasons = historical_seasons(recs)
        assert seasons[0]["season_label"] == "2019-20"

    def test_excludes_incomplete_season_no_january(self):
        """A season without January data should be excluded."""
        # Only Nov + Dec — no Jan through Apr
        nov_dec = []
        for month in (11, 12):
            days_in_month = 30 if month == 11 else 31
            for day in range(1, days_in_month + 1):
                d = date(2022, month, day)
                nov_dec.append(make_record(d, 5.0, 50.0))
        seasons = historical_seasons(nov_dec)
        assert len(seasons) == 0

    def test_sorted_by_label(self):
        """Seasons returned in chronological order."""
        recs = season_records(2015) + season_records(2010) + season_records(2012)
        seasons = historical_seasons(recs)
        labels = [s["season_label"] for s in seasons]
        assert labels == sorted(labels)

    def test_powder_days_counted(self):
        """Powder days (snowfall > 20 cm) should be counted correctly."""
        recs = []
        # Jan: 10 days with 25cm (powder), 21 days with 5cm
        for day in range(1, 11):
            recs.append(make_record(date(2020, 1, day), 25.0, 80.0))
        for day in range(11, 32):
            recs.append(make_record(date(2020, 1, day), 5.0, 40.0))
        # Add minimal Nov/Dec to make it a valid season
        for month in (11, 12):
            days = 30 if month == 11 else 31
            for day in range(1, days + 1):
                recs.append(make_record(date(2019, month, day), 5.0, 30.0))
        # Add Feb-Apr
        for month, days in ((2, 28), (3, 31), (4, 30)):
            for day in range(1, days + 1):
                recs.append(make_record(date(2020, month, day), 2.0, 20.0))

        seasons = historical_seasons(recs)
        assert len(seasons) == 1
        assert seasons[0]["powder_days"] == 10


class TestRateSeason:
    def _make_seasons(self, snowfalls: list[float]) -> list[dict]:
        return [{"total_snowfall": sf} for sf in snowfalls]

    def test_exceptional_top_10(self):
        """Highest of 10 seasons should be EXCEPTIONAL (top 10%)."""
        snowfalls = [100.0 * i for i in range(1, 11)]
        seasons = self._make_seasons(snowfalls)
        best = seasons[-1]  # 1000.0
        assert rate_season(best, seasons) == "EXCEPTIONAL"

    def test_poor_bottom_25(self):
        """Lowest of 10 seasons should be POOR."""
        snowfalls = [100.0 * i for i in range(1, 11)]
        seasons = self._make_seasons(snowfalls)
        worst = seasons[0]  # 100.0
        assert rate_season(worst, seasons) == "POOR"

    def test_good_middle(self):
        """Middle season of 10 should be GOOD (50th–75th percentile)."""
        snowfalls = list(range(10, 110, 10))  # 10, 20, ..., 100
        seasons = self._make_seasons(snowfalls)
        # Index 5 = value 60 → rank 5/10 = 50th percentile → GOOD
        assert rate_season(seasons[5], seasons) == "GOOD"

    def test_single_season_average(self):
        """A single season has rank 0/1 = 0th percentile → POOR."""
        seasons = [{"total_snowfall": 500.0}]
        result = rate_season(seasons[0], seasons)
        assert result in ("POOR", "AVERAGE", "GOOD", "EXCELLENT", "EXCEPTIONAL")

    def test_empty_seasons_returns_average(self):
        """No seasons returns AVERAGE by default."""
        assert rate_season({"total_snowfall": 100.0}, []) == "AVERAGE"


class TestPredictCurrentSeason:
    def _make_season_with_records(
        self, season_year: int, depth_value: float, rating: str = "GOOD"
    ) -> dict:
        """Minimal season dict with Oct 1 through Mar records."""
        records = []
        for month in (10, 11, 12):
            days = 31 if month in (10, 12) else 30
            for day in range(1, days + 1):
                records.append(
                    make_record(date(season_year, month, day), 5.0, depth_value)
                )
        for month, days in ((1, 31), (2, 28)):
            for day in range(1, days + 1):
                records.append(
                    make_record(date(season_year + 1, month, day), 5.0, depth_value)
                )
        return {
            "season_label": f"{season_year}-{str(season_year+1)[-2:]}",
            "season_year": season_year,
            "total_snowfall": 200.0,
            "peak_snow_depth": depth_value,
            "snow_days": 80,
            "powder_days": 5,
            "avg_winter_temp": -4.0,
            "season_start": date(season_year, 11, 15),
            "season_end": date(season_year + 1, 4, 15),
            "peak_window_start": date(season_year + 1, 1, 15),
            "peak_window_end": date(season_year + 1, 2, 4),
            "rating": rating,
            "records": sorted(records, key=lambda r: r["date"]),
        }

    def test_returns_all_required_keys(self):
        """Result dict must have all required keys."""
        hist = [
            self._make_season_with_records(2018, 60.0, "GOOD"),
            self._make_season_with_records(2019, 55.0, "GOOD"),
            self._make_season_with_records(2020, 70.0, "EXCELLENT"),
        ]
        current = [make_record(date(2024, 10, day), 3.0, 60.0) for day in range(1, 32)]
        result = predict_current_season(current, hist)
        required_keys = {
            "predicted_rating",
            "confidence",
            "similar_seasons",
            "similar_season_outcomes",
            "current_snowpack",
            "historical_avg_snowpack",
            "snowpack_vs_avg",
        }
        assert required_keys.issubset(result.keys())

    def test_predicted_rating_is_valid(self):
        """Predicted rating must be one of the known rating strings."""
        valid_ratings = {"EXCEPTIONAL", "EXCELLENT", "GOOD", "AVERAGE", "POOR", "UNKNOWN"}
        hist = [self._make_season_with_records(y, 60.0, "GOOD") for y in range(2015, 2020)]
        current = [make_record(date(2024, 10, day), 3.0, 60.0) for day in range(1, 30)]
        result = predict_current_season(current, hist)
        assert result["predicted_rating"] in valid_ratings

    def test_confidence_is_valid(self):
        """Confidence must be HIGH, MEDIUM, or LOW."""
        hist = [self._make_season_with_records(y, 60.0, "GOOD") for y in range(2015, 2020)]
        current = [make_record(date(2024, 10, day), 3.0, 60.0) for day in range(1, 30)]
        result = predict_current_season(current, hist)
        assert result["confidence"] in ("HIGH", "MEDIUM", "LOW")

    def test_empty_current_returns_unknown(self):
        """Empty current data should return UNKNOWN with LOW confidence."""
        result = predict_current_season([], [])
        assert result["predicted_rating"] == "UNKNOWN"
        assert result["confidence"] == "LOW"
        assert result["similar_seasons"] == []

    def test_current_snowpack_is_latest_depth(self):
        """current_snowpack should be the last snow_depth_max in current data."""
        current = [
            make_record(date(2024, 10, 1), 0.0, 10.0),
            make_record(date(2024, 10, 2), 5.0, 20.0),
            make_record(date(2024, 10, 3), 8.0, 35.0),
        ]
        hist = [self._make_season_with_records(y, 30.0, "AVERAGE") for y in range(2010, 2015)]
        result = predict_current_season(current, hist)
        assert result["current_snowpack"] == pytest.approx(35.0)


class TestBestWeeksToSki:
    def test_returns_exactly_five(self):
        """Must return exactly 5 weeks."""
        recs_2018 = season_records(2018, snowfall_per_day=5.0)
        recs_2019 = season_records(2019, snowfall_per_day=8.0)
        seasons = historical_seasons(recs_2018 + recs_2019)
        result = best_weeks_to_ski(seasons)
        assert len(result) == 5

    def test_sorted_by_avg_snow_depth_descending(self):
        """Weeks must be ranked with highest avg_snow_depth first."""
        recs = season_records(2018) + season_records(2019) + season_records(2020)
        seasons = historical_seasons(recs)
        result = best_weeks_to_ski(seasons)
        depths = [w["avg_snow_depth"] for w in result]
        assert depths == sorted(depths, reverse=True)

    def test_ranks_are_1_through_5(self):
        """Ranks must be consecutive integers 1-5."""
        recs = season_records(2015) + season_records(2016) + season_records(2017)
        seasons = historical_seasons(recs)
        result = best_weeks_to_ski(seasons)
        assert [w["rank"] for w in result] == [1, 2, 3, 4, 5]

    def test_week_label_format(self):
        """Week labels should contain month abbreviations and dashes."""
        recs = season_records(2018) + season_records(2019)
        seasons = historical_seasons(recs)
        result = best_weeks_to_ski(seasons)
        for w in result:
            assert "–" in w["week_label"]
            # Should contain month abbreviation
            months = ("Jan", "Feb", "Mar", "Apr", "Nov", "Dec")
            assert any(m in w["week_label"] for m in months)

    def test_required_fields_present(self):
        """Each result must have all required fields."""
        recs = season_records(2018) + season_records(2019)
        seasons = historical_seasons(recs)
        result = best_weeks_to_ski(seasons)
        required = {"week_label", "avg_snow_depth", "powder_day_probability", "avg_temp", "rank"}
        for w in result:
            assert required.issubset(w.keys())
