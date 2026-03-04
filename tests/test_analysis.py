# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""Tests for analysis.py — yearly_summary, monthly_climatology,
temperature_trend, find_extremes, terminal_summary, seasonal_breakdown,
yearly_humidity."""

import datetime
import pytest
from datetime import date

from weather_alert.analysis import (
    yearly_summary,
    monthly_climatology,
    temperature_trend,
    find_extremes,
    terminal_summary,
    seasonal_breakdown,
    yearly_humidity,
)


# ---------------------------------------------------------------------------
# Shared sample data (no API calls)
# ---------------------------------------------------------------------------

SAMPLE_RECORDS = [
    {"date": date(2020, 1, 15), "temp_max": 20.0, "temp_min": -5.0,  "temp_mean": 7.5,
     "precipitation": 5.0, "snowfall": 2.0, "snow_depth_max": 10.0, "wind_max": 30.0},
    {"date": date(2020, 7, 15), "temp_max": 25.0, "temp_min":  0.0,  "temp_mean": 12.5,
     "precipitation": 2.0, "snowfall": 0.0, "snow_depth_max":  5.0, "wind_max": 20.0},
    {"date": date(2021, 1, 15), "temp_max": 15.0, "temp_min": -15.0, "temp_mean": 0.0,
     "precipitation": 0.5, "snowfall": 5.0, "snow_depth_max": 20.0, "wind_max": 40.0},
    {"date": date(2021, 7, 15), "temp_max": 18.0, "temp_min":  -2.0, "temp_mean": 8.0,
     "precipitation": 0.3, "snowfall": 0.0, "snow_depth_max":  0.0, "wind_max": 15.0},
    {"date": date(2022, 8, 15), "temp_max": 35.0, "temp_min":   5.0, "temp_mean": 20.0,
     "precipitation": 10.0, "snowfall": 0.0, "snow_depth_max":  0.0, "wind_max": 25.0},
    {"date": date(2022, 12, 15), "temp_max": 10.0, "temp_min":  -3.0, "temp_mean": 3.5,
     "precipitation": 8.0, "snowfall": 1.0, "snow_depth_max":  3.0, "wind_max": 20.0},
]


# ---------------------------------------------------------------------------
# yearly_summary
# ---------------------------------------------------------------------------

class TestYearlySummary:

    def setup_method(self):
        self.summaries = yearly_summary(SAMPLE_RECORDS)
        self.by_year = {s["year"]: s for s in self.summaries}

    def test_groups_into_three_years(self):
        """SAMPLE_RECORDS spans 2020, 2021, 2022 — must produce exactly 3 dicts."""
        assert len(self.summaries) == 3

    def test_year_values_are_correct(self):
        """Output years must be 2020, 2021, 2022 in sorted order."""
        years = [s["year"] for s in self.summaries]
        assert years == [2020, 2021, 2022]

    def test_hottest_year_max_temp(self):
        """2022 has the record high of 35.0°C."""
        assert self.by_year[2022]["max_temp"] == 35.0

    def test_coldest_year_min_temp(self):
        """2021 has the record low of -15.0°C."""
        assert self.by_year[2021]["min_temp"] == -15.0

    def test_snow_days_count_2020(self):
        """2020: snowfall values are [2.0, 0.0] — only one day > 0."""
        assert self.by_year[2020]["snow_days"] == 1

    def test_rain_days_count_2020(self):
        """2020: precipitation values are [5.0, 2.0] — both > 1mm threshold."""
        assert self.by_year[2020]["rain_days"] == 2

    def test_rain_days_threshold_exclusive(self):
        """rain_days uses > 1.0 mm, not >= 1.0; 0.5mm and 0.3mm must not count."""
        # 2021 has precipitation [0.5, 0.3] — neither exceeds 1.0
        assert self.by_year[2021]["rain_days"] == 0

    def test_total_precipitation_2022(self):
        """2022: precipitation [10.0, 8.0] sums to 18.0mm."""
        assert self.by_year[2022]["total_precipitation"] == pytest.approx(18.0, abs=0.1)

    def test_total_precipitation_2021(self):
        """2021: precipitation [0.5, 0.3] sums to 0.8mm."""
        assert self.by_year[2021]["total_precipitation"] == pytest.approx(0.8, abs=0.1)

    def test_hottest_date_is_date_object(self):
        """hottest_date must be a datetime.date instance."""
        for s in self.summaries:
            assert isinstance(s["hottest_date"], date)

    def test_coldest_date_is_date_object(self):
        """coldest_date must be a datetime.date instance."""
        for s in self.summaries:
            assert isinstance(s["coldest_date"], date)

    def test_required_keys_present(self):
        """Each yearly summary must contain all expected keys."""
        expected_keys = {
            "year", "avg_temp_max", "avg_temp_min", "avg_temp_mean",
            "total_precipitation", "total_snowfall", "max_snow_depth",
            "snow_days", "rain_days", "max_temp", "min_temp",
            "hottest_date", "coldest_date",
        }
        for s in self.summaries:
            assert set(s.keys()) == expected_keys

    def test_empty_input_returns_empty_list(self):
        """An empty records list must return an empty list."""
        assert yearly_summary([]) == []

    def test_avg_temp_max_2020(self):
        """2020: temp_max values [20.0, 25.0] → avg = 22.5."""
        assert self.by_year[2020]["avg_temp_max"] == pytest.approx(22.5, abs=0.01)

    def test_max_snow_depth_2021(self):
        """2021: snow_depth_max values [20.0, 0.0] → max = 20.0."""
        assert self.by_year[2021]["max_snow_depth"] == 20.0


# ---------------------------------------------------------------------------
# monthly_climatology
# ---------------------------------------------------------------------------

class TestMonthlyClimatology:

    def setup_method(self):
        self.climatology = monthly_climatology(SAMPLE_RECORDS)
        self.by_month = {c["month"]: c for c in self.climatology}

    def test_returns_exactly_12_dicts(self):
        """Must always return exactly 12 entries, one per calendar month."""
        assert len(self.climatology) == 12

    def test_month_numbers_are_1_to_12(self):
        """Month values must be integers 1 through 12."""
        months = [c["month"] for c in self.climatology]
        assert months == list(range(1, 13))

    def test_required_keys_present(self):
        """Each monthly dict must have month, avg_temp_mean, avg_precipitation, avg_snowfall."""
        expected_keys = {"month", "avg_temp_mean", "avg_precipitation", "avg_snowfall"}
        for c in self.climatology:
            assert set(c.keys()) == expected_keys

    def test_months_with_no_records_have_zero_values(self):
        """Months absent from the data must have 0.0 for all numeric fields."""
        # SAMPLE_RECORDS has entries only in months 1, 7, 8, 12
        months_with_data = {1, 7, 8, 12}
        for month in range(1, 13):
            if month not in months_with_data:
                c = self.by_month[month]
                assert c["avg_temp_mean"]     == 0.0, f"Month {month} avg_temp_mean should be 0.0"
                assert c["avg_precipitation"] == 0.0, f"Month {month} avg_precipitation should be 0.0"
                assert c["avg_snowfall"]      == 0.0, f"Month {month} avg_snowfall should be 0.0"

    def test_july_avg_temp_mean(self):
        """July records: temp_mean [12.5 (2020), 8.0 (2021)] → avg = 10.25."""
        assert self.by_month[7]["avg_temp_mean"] == pytest.approx(10.25, abs=0.01)

    def test_january_avg_temp_mean(self):
        """January records: temp_mean [7.5 (2020), 0.0 (2021)] → avg = 3.75."""
        assert self.by_month[1]["avg_temp_mean"] == pytest.approx(3.75, abs=0.01)

    def test_january_avg_snowfall(self):
        """January snowfall [2.0, 5.0] → avg = 3.5."""
        assert self.by_month[1]["avg_snowfall"] == pytest.approx(3.5, abs=0.01)

    def test_august_avg_precipitation(self):
        """August has one record (2022): precipitation = 10.0 → avg = 10.0."""
        assert self.by_month[8]["avg_precipitation"] == pytest.approx(10.0, abs=0.01)


# ---------------------------------------------------------------------------
# temperature_trend
# ---------------------------------------------------------------------------

class TestTemperatureTrend:

    def _make_yearly(self, year_temp_pairs):
        """Helper: build minimal yearly-summary list from [(year, avg_temp_mean), ...]."""
        return [{"year": yr, "avg_temp_mean": t} for yr, t in year_temp_pairs]

    def test_required_keys_present(self):
        """Return dict must always contain slope, slope_per_decade, r_squared, label."""
        yearly = yearly_summary(SAMPLE_RECORDS)
        result = temperature_trend(yearly)
        assert set(result.keys()) == {"slope", "slope_per_decade", "r_squared", "label"}

    def test_steadily_increasing_is_warming(self):
        """Monotonically rising temperatures must produce label='warming' and slope>0."""
        data = self._make_yearly([(2000, 10.0), (2001, 11.0), (2002, 12.0), (2003, 13.0)])
        result = temperature_trend(data)
        assert result["label"] == "warming"
        assert result["slope"] > 0

    def test_steadily_decreasing_is_cooling(self):
        """Monotonically falling temperatures must produce label='cooling' and slope<0."""
        data = self._make_yearly([(2000, 13.0), (2001, 12.0), (2002, 11.0), (2003, 10.0)])
        result = temperature_trend(data)
        assert result["label"] == "cooling"
        assert result["slope"] < 0

    def test_flat_data_is_stable(self):
        """Constant temperatures must produce label='stable'."""
        data = self._make_yearly([(2000, 5.0), (2001, 5.0), (2002, 5.0), (2003, 5.0)])
        result = temperature_trend(data)
        assert result["label"] == "stable"

    def test_slope_per_decade_is_slope_times_ten(self):
        """slope_per_decade must equal round(slope * 10, 2)."""
        data = self._make_yearly([(2000, 10.0), (2001, 11.0), (2002, 12.0), (2003, 13.0)])
        result = temperature_trend(data)
        assert result["slope_per_decade"] == pytest.approx(result["slope"] * 10, abs=0.01)

    def test_perfect_linear_data_r_squared_near_one(self):
        """Perfectly linear data must produce r_squared approximately 1.0."""
        data = self._make_yearly(
            [(2000 + i, 10.0 + i * 0.5) for i in range(10)]
        )
        result = temperature_trend(data)
        assert result["r_squared"] == pytest.approx(1.0, abs=0.001)

    def test_single_record_returns_stable(self):
        """Fewer than 2 yearly records must return label='stable' with zero slope."""
        data = self._make_yearly([(2020, 8.0)])
        result = temperature_trend(data)
        assert result["label"] == "stable"
        assert result["slope"] == 0.0
        assert result["slope_per_decade"] == 0.0
        assert result["r_squared"] == 0.0

    def test_empty_input_returns_stable(self):
        """Empty list must return stable with all zeros."""
        result = temperature_trend([])
        assert result["label"] == "stable"
        assert result["slope"] == 0.0

    def test_warming_slope_positive_value(self):
        """Confirm numeric slope value is positive for warming scenario."""
        data = self._make_yearly([(2000, 10.0), (2001, 10.5), (2002, 11.0)])
        result = temperature_trend(data)
        assert result["slope"] > 0.005  # above the warming threshold

    def test_cooling_slope_negative_value(self):
        """Confirm numeric slope value is negative for cooling scenario."""
        data = self._make_yearly([(2000, 11.0), (2001, 10.5), (2002, 10.0)])
        result = temperature_trend(data)
        assert result["slope"] < -0.005  # below the cooling threshold


# ---------------------------------------------------------------------------
# find_extremes
# ---------------------------------------------------------------------------

class TestFindExtremes:

    def setup_method(self):
        self.yearly = yearly_summary(SAMPLE_RECORDS)
        self.extremes = find_extremes(self.yearly)

    def test_hottest_year_is_2022(self):
        """2022 has the highest single-day max_temp (35.0°C)."""
        assert self.extremes["hottest_year"] == 2022

    def test_hottest_year_max_temp_value(self):
        """Hottest year's max_temp must be 35.0."""
        assert self.extremes["hottest_year_max_temp"] == 35.0

    def test_coldest_year_is_2021(self):
        """2021 has the lowest single-day min_temp (-15.0°C)."""
        assert self.extremes["coldest_year"] == 2021

    def test_coldest_year_min_temp_value(self):
        """Coldest year's min_temp must be -15.0."""
        assert self.extremes["coldest_year_min_temp"] == -15.0

    def test_wettest_year_is_2022(self):
        """2022 total precipitation is 18.0mm — highest among the three years."""
        assert self.extremes["wettest_year"] == 2022

    def test_driest_year_is_2021(self):
        """2021 total precipitation is 0.8mm — lowest among the three years."""
        assert self.extremes["driest_year"] == 2021

    def test_wettest_year_precip_value(self):
        """Wettest year precip must be approximately 18.0mm."""
        assert self.extremes["wettest_year_precip"] == pytest.approx(18.0, abs=0.1)

    def test_driest_year_precip_value(self):
        """Driest year precip must be approximately 0.8mm."""
        assert self.extremes["driest_year_precip"] == pytest.approx(0.8, abs=0.1)

    def test_hottest_date_is_date_object(self):
        """hottest_date must be a datetime.date instance."""
        assert isinstance(self.extremes["hottest_date"], date)

    def test_coldest_date_is_date_object(self):
        """coldest_date must be a datetime.date instance."""
        assert isinstance(self.extremes["coldest_date"], date)

    def test_empty_input_returns_empty_dict(self):
        """find_extremes([]) must return an empty dict."""
        assert find_extremes([]) == {}

    def test_all_expected_keys_present(self):
        """Return dict must contain the full set of extreme keys."""
        expected_keys = {
            "hottest_year", "hottest_year_max_temp", "hottest_date",
            "coldest_year", "coldest_year_min_temp", "coldest_date",
            "wettest_year", "wettest_year_precip",
            "driest_year",  "driest_year_precip",
            "snowiest_year", "snowiest_year_snowfall", "snowiest_year_snow_days",
            "least_snow_year", "least_snow_year_snowfall", "least_snow_year_snow_days",
            "most_snow_days_year", "most_snow_days_count",
        }
        assert set(self.extremes.keys()) == expected_keys


# ---------------------------------------------------------------------------
# terminal_summary
# ---------------------------------------------------------------------------

class TestTerminalSummary:

    def setup_method(self):
        self.yearly   = yearly_summary(SAMPLE_RECORDS)
        self.extremes = find_extremes(self.yearly)
        self.trend    = temperature_trend(self.yearly)
        self.output   = terminal_summary(
            "Test City", self.yearly, self.extremes, self.trend
        )

    def test_contains_location_name(self):
        """The summary string must include the location name passed in."""
        assert "Test City" in self.output

    def test_contains_start_year(self):
        """The summary must reference the first year in the data (2020)."""
        assert "2020" in self.output

    def test_contains_end_year(self):
        """The summary must reference the last year in the data (2022)."""
        assert "2022" in self.output

    def test_contains_trend_label(self):
        """The trend label (warming/cooling/stable) must appear in the output."""
        assert self.trend["label"] in self.output

    def test_contains_separator_line(self):
        """The summary must contain the em-dash separator character."""
        assert "─" in self.output

    def test_empty_yearly_returns_no_data_message(self):
        """An empty yearly list must return a 'No historical data' message."""
        result = terminal_summary("Nowhere", [], {}, {})
        assert "No historical data" in result

    def test_empty_yearly_contains_location_name(self):
        """Even the 'no data' fallback must include the location name."""
        result = terminal_summary("Nowhere", [], {}, {})
        assert "Nowhere" in result

    def test_returns_string(self):
        """terminal_summary must always return a str."""
        assert isinstance(self.output, str)

    def test_is_multiline(self):
        """A non-empty summary must span multiple lines."""
        assert "\n" in self.output


# ---------------------------------------------------------------------------
# seasonal_breakdown
# ---------------------------------------------------------------------------

class TestSeasonalBreakdown:

    def _make_seasonal_records(self):
        """Build records covering all 4 seasons across 2 complete years (2020 and 2021).

        Season definitions used by seasonal_breakdown:
            Winter  — Dec (shifted to next year), Jan, Feb
            Spring  — Mar, Apr, May
            Summer  — Jun, Jul, Aug
            Autumn  — Sep, Oct, Nov
        """
        current_year = datetime.date.today().year
        # Use years well in the past to avoid any overlap with current year
        base_years = [current_year - 4, current_year - 3]
        records = []
        for yr in base_years:
            # Winter: January and February (yr); December (yr-1) shifts into yr's Winter
            records.append({
                "date": date(yr, 1, 15), "temp_max": 5.0, "temp_min": -5.0,
                "temp_mean": 0.0, "precipitation": 3.0, "snowfall": 2.0,
                "snow_depth_max": 8.0, "wind_max": 20.0,
            })
            records.append({
                "date": date(yr, 2, 15), "temp_max": 6.0, "temp_min": -4.0,
                "temp_mean": 1.0, "precipitation": 2.0, "snowfall": 1.0,
                "snow_depth_max": 5.0, "wind_max": 18.0,
            })
            # Spring: March, April, May
            records.append({
                "date": date(yr, 3, 15), "temp_max": 12.0, "temp_min": 2.0,
                "temp_mean": 7.0, "precipitation": 5.0, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 15.0,
            })
            records.append({
                "date": date(yr, 5, 15), "temp_max": 18.0, "temp_min": 8.0,
                "temp_mean": 13.0, "precipitation": 4.0, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 12.0,
            })
            # Summer: June, July, August
            records.append({
                "date": date(yr, 7, 15), "temp_max": 28.0, "temp_min": 15.0,
                "temp_mean": 21.0, "precipitation": 1.0, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 10.0,
            })
            records.append({
                "date": date(yr, 8, 15), "temp_max": 30.0, "temp_min": 17.0,
                "temp_mean": 23.0, "precipitation": 0.5, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 8.0,
            })
            # Autumn: September, October, November
            records.append({
                "date": date(yr, 9, 15), "temp_max": 20.0, "temp_min": 10.0,
                "temp_mean": 15.0, "precipitation": 6.0, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 14.0,
            })
            records.append({
                "date": date(yr, 11, 15), "temp_max": 8.0, "temp_min": 0.0,
                "temp_mean": 4.0, "precipitation": 7.0, "snowfall": 0.5,
                "snow_depth_max": 1.0, "wind_max": 16.0,
            })
            # December of this year feeds into (yr+1)'s Winter bucket
            records.append({
                "date": date(yr, 12, 15), "temp_max": 4.0, "temp_min": -3.0,
                "temp_mean": 0.5, "precipitation": 4.0, "snowfall": 1.5,
                "snow_depth_max": 4.0, "wind_max": 22.0,
            })
        return records, base_years

    def test_result_contains_both_years_as_keys(self):
        """seasonal_breakdown must include both base years as top-level keys."""
        records, base_years = self._make_seasonal_records()
        result = seasonal_breakdown(records)
        for yr in base_years:
            assert yr in result, f"Expected year {yr} in result keys"

    def test_each_year_has_four_seasons(self):
        """Each year in the result must have exactly 4 season entries."""
        records, base_years = self._make_seasonal_records()
        result = seasonal_breakdown(records)
        for yr in base_years:
            seasons = set(result[yr].keys())
            assert seasons == {"Winter", "Spring", "Summer", "Autumn"}, (
                f"Year {yr} seasons are {seasons}"
            )

    def test_avg_temp_mean_is_float(self):
        """avg_temp_mean for every (year, season) bucket must be a float."""
        records, base_years = self._make_seasonal_records()
        result = seasonal_breakdown(records)
        for yr in base_years:
            for season, stats in result[yr].items():
                assert isinstance(stats["avg_temp_mean"], float), (
                    f"{yr}/{season} avg_temp_mean is not a float"
                )

    def test_total_precipitation_is_float(self):
        """total_precipitation for every (year, season) bucket must be a float."""
        records, base_years = self._make_seasonal_records()
        result = seasonal_breakdown(records)
        for yr in base_years:
            for season, stats in result[yr].items():
                assert isinstance(stats["total_precipitation"], float), (
                    f"{yr}/{season} total_precipitation is not a float"
                )

    def test_current_year_not_in_result(self):
        """The current calendar year must never appear as a key in the result."""
        current_year = datetime.date.today().year
        records, _ = self._make_seasonal_records()
        # Inject some records dated in the current year to confirm they are dropped
        records.append({
            "date": date(current_year, 6, 15), "temp_max": 30.0, "temp_min": 20.0,
            "temp_mean": 25.0, "precipitation": 2.0, "snowfall": 0.0,
            "snow_depth_max": 0.0, "wind_max": 10.0,
        })
        result = seasonal_breakdown(records)
        assert current_year not in result, (
            f"Current year {current_year} must be excluded from seasonal_breakdown result"
        )


# ---------------------------------------------------------------------------
# yearly_humidity
# ---------------------------------------------------------------------------

class TestYearlyHumidity:

    def _make_humidity_records(self):
        """Build records with a mix of float and None humidity_mean values."""
        current_year = datetime.date.today().year
        yr_a = current_year - 3
        yr_b = current_year - 2
        yr_c = current_year - 1
        return [
            # yr_a: two records with valid humidity
            {"date": date(yr_a, 3, 1), "temp_max": 10.0, "temp_min": 2.0,
             "temp_mean": 6.0, "precipitation": 1.0, "snowfall": 0.0,
             "snow_depth_max": 0.0, "wind_max": 10.0, "humidity_mean": 70.0},
            {"date": date(yr_a, 9, 1), "temp_max": 22.0, "temp_min": 12.0,
             "temp_mean": 17.0, "precipitation": 0.5, "snowfall": 0.0,
             "snow_depth_max": 0.0, "wind_max": 8.0, "humidity_mean": 60.0},
            # yr_b: one valid, one None — year must still appear (valid record present)
            {"date": date(yr_b, 4, 1), "temp_max": 15.0, "temp_min": 5.0,
             "temp_mean": 10.0, "precipitation": 2.0, "snowfall": 0.0,
             "snow_depth_max": 0.0, "wind_max": 12.0, "humidity_mean": 80.0},
            {"date": date(yr_b, 10, 1), "temp_max": 12.0, "temp_min": 3.0,
             "temp_mean": 7.0, "precipitation": 3.0, "snowfall": 0.0,
             "snow_depth_max": 0.0, "wind_max": 11.0, "humidity_mean": None},
            # yr_c: all None — year must be absent from result
            {"date": date(yr_c, 5, 1), "temp_max": 18.0, "temp_min": 8.0,
             "temp_mean": 13.0, "precipitation": 1.5, "snowfall": 0.0,
             "snow_depth_max": 0.0, "wind_max": 9.0, "humidity_mean": None},
            # current_year: must be excluded entirely regardless of humidity value
            {"date": date(current_year, 1, 1), "temp_max": 5.0, "temp_min": -1.0,
             "temp_mean": 2.0, "precipitation": 0.5, "snowfall": 0.1,
             "snow_depth_max": 1.0, "wind_max": 7.0, "humidity_mean": 75.0},
        ], yr_a, yr_b, yr_c, current_year

    def test_result_sorted_by_year(self):
        """yearly_humidity must return results in ascending year order."""
        records, *_ = self._make_humidity_records()
        result = yearly_humidity(records)
        years = [r["year"] for r in result]
        assert years == sorted(years), "years are not in ascending order"

    def test_only_years_with_non_none_humidity_included(self):
        """Years where all humidity_mean values are None must be absent from result."""
        records, yr_a, yr_b, yr_c, current_year = self._make_humidity_records()
        result = yearly_humidity(records)
        result_years = {r["year"] for r in result}
        # yr_a and yr_b have at least one non-None value, so they must appear
        assert yr_a in result_years, f"yr_a ({yr_a}) should be in result"
        assert yr_b in result_years, f"yr_b ({yr_b}) should be in result"
        # yr_c has only None values, so it must be absent
        assert yr_c not in result_years, (
            f"yr_c ({yr_c}) has only None humidity, must not appear in result"
        )

    def test_current_year_excluded(self):
        """yearly_humidity must never return an entry for the current calendar year."""
        current_year = datetime.date.today().year
        records, *_ = self._make_humidity_records()
        result = yearly_humidity(records)
        result_years = {r["year"] for r in result}
        assert current_year not in result_years, (
            f"Current year {current_year} must be excluded from yearly_humidity result"
        )

    def test_avg_humidity_excludes_none_in_average(self):
        """None humidity values must not affect the computed average for the year."""
        records, yr_a, yr_b, yr_c, current_year = self._make_humidity_records()
        result = yearly_humidity(records)
        by_year = {r["year"]: r for r in result}
        # yr_a: (70.0 + 60.0) / 2 = 65.0
        assert by_year[yr_a]["avg_humidity"] == pytest.approx(65.0, abs=0.01)
        # yr_b: only the 80.0 record counts (None is skipped) → 80.0
        assert by_year[yr_b]["avg_humidity"] == pytest.approx(80.0, abs=0.01)


# ---------------------------------------------------------------------------
# current_year_excluded (yearly_summary)
# ---------------------------------------------------------------------------

class TestCurrentYearExcluded:

    def test_current_year_not_in_yearly_summary(self):
        """yearly_summary must exclude records dated in the current calendar year."""
        current_year = datetime.date.today().year
        past_year = current_year - 1
        records = [
            # A record from the past year — must appear in output
            {
                "date": date(past_year, 6, 15), "temp_max": 25.0, "temp_min": 15.0,
                "temp_mean": 20.0, "precipitation": 3.0, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 12.0,
            },
            # Records from the current year — must be suppressed
            {
                "date": date(current_year, 1, 10), "temp_max": 8.0, "temp_min": 1.0,
                "temp_mean": 4.5, "precipitation": 1.0, "snowfall": 0.5,
                "snow_depth_max": 2.0, "wind_max": 15.0,
            },
            {
                "date": date(current_year, 6, 20), "temp_max": 32.0, "temp_min": 22.0,
                "temp_mean": 27.0, "precipitation": 0.0, "snowfall": 0.0,
                "snow_depth_max": 0.0, "wind_max": 9.0,
            },
        ]
        result = yearly_summary(records)
        result_years = [s["year"] for s in result]
        assert current_year not in result_years, (
            f"Current year {current_year} must not appear in yearly_summary output; "
            f"got years: {result_years}"
        )
