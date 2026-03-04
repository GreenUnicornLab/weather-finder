# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
analysis.py — Statistical analysis of historical daily weather records.

All calculations use the Python standard library only (no numpy/scipy).
Linear regression uses the closed-form OLS formula.
"""

from __future__ import annotations
from collections import defaultdict
from datetime import date


def yearly_summary(records: list[dict]) -> list[dict]:
    """Aggregate daily records by year.

    Input records have keys: date (datetime.date), temp_max, temp_min,
    temp_mean, precipitation, snowfall, snow_depth_max, wind_max.

    Records from the current calendar year are excluded to avoid
    incomplete-year bias.

    Returns list of dicts sorted by year with keys:
        year, avg_temp_max, avg_temp_min, avg_temp_mean,
        total_precipitation, total_snowfall, max_snow_depth,
        snow_days, rain_days, max_temp, min_temp,
        hottest_date, coldest_date
    """
    current_year = date.today().year
    by_year: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        if r["date"].year == current_year:
            continue
        by_year[r["date"].year].append(r)

    summaries = []
    for year in sorted(by_year):
        days = by_year[year]
        n = len(days)
        if n == 0:
            continue
        hottest = max(days, key=lambda d: d["temp_max"])
        coldest = min(days, key=lambda d: d["temp_min"])
        summaries.append({
            "year":                year,
            "avg_temp_max":        round(sum(d["temp_max"]        for d in days) / n, 2),
            "avg_temp_min":        round(sum(d["temp_min"]        for d in days) / n, 2),
            "avg_temp_mean":       round(sum(d["temp_mean"]       for d in days) / n, 2),
            "total_precipitation": round(sum(d["precipitation"]   for d in days), 1),
            "total_snowfall":      round(sum(d["snowfall"]        for d in days), 1),
            "max_snow_depth":      round(max(d["snow_depth_max"]  for d in days), 1),
            "snow_days":           sum(1 for d in days if d["snowfall"]      > 0),
            "rain_days":           sum(1 for d in days if d["precipitation"] > 1.0),
            "max_temp":            hottest["temp_max"],
            "min_temp":            coldest["temp_min"],
            "hottest_date":        hottest["date"],
            "coldest_date":        coldest["date"],
        })
    return summaries


def monthly_climatology(records: list[dict]) -> list[dict]:
    """Average conditions per calendar month (1-12) across all years.

    Records from the current calendar year are excluded to avoid
    incomplete-year bias.

    Returns list of 12 dicts with keys:
        month (int 1-12), avg_temp_mean, avg_precipitation, avg_snowfall
    """
    current_year = date.today().year
    by_month: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        if r["date"].year == current_year:
            continue
        by_month[r["date"].month].append(r)

    result = []
    for month in range(1, 13):
        days = by_month.get(month, [])
        n = len(days)
        if n == 0:
            result.append({
                "month":             month,
                "avg_temp_mean":     0.0,
                "avg_precipitation": 0.0,
                "avg_snowfall":      0.0,
            })
        else:
            result.append({
                "month":             month,
                "avg_temp_mean":     round(sum(d["temp_mean"]     for d in days) / n, 2),
                "avg_precipitation": round(sum(d["precipitation"] for d in days) / n, 2),
                "avg_snowfall":      round(sum(d["snowfall"]       for d in days) / n, 2),
            })
    return result


def temperature_trend(yearly: list[dict]) -> dict:
    """Compute linear regression of avg_temp_mean over years (stdlib only).

    OLS formula: slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)

    Returns dict with keys:
        slope (float, degrees C per year),
        slope_per_decade (float, degrees C per decade),
        r_squared (float, 0-1),
        label (str: "warming" | "cooling" | "stable")
    """
    if len(yearly) < 2:
        return {"slope": 0.0, "slope_per_decade": 0.0, "r_squared": 0.0, "label": "stable"}

    xs = [float(y["year"])          for y in yearly]
    ys = [float(y["avg_temp_mean"]) for y in yearly]
    n  = len(xs)

    sum_x  = sum(xs)
    sum_y  = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return {"slope": 0.0, "slope_per_decade": 0.0, "r_squared": 0.0, "label": "stable"}

    slope     = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r_sq   = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    per_decade = round(slope * 10, 2)
    if slope > 0.005:
        label = "warming"
    elif slope < -0.005:
        label = "cooling"
    else:
        label = "stable"

    return {
        "slope":            round(slope, 4),
        "slope_per_decade": per_decade,
        "r_squared":        round(r_sq, 4),
        "label":            label,
    }


def find_extremes(yearly: list[dict]) -> dict:
    """Identify extreme years from the yearly summary list.

    Returns dict with keys for hottest/coldest/wettest/driest/snowiest years
    and their corresponding values and dates.
    """
    if not yearly:
        return {}

    hottest   = max(yearly, key=lambda y: y["max_temp"])
    coldest   = min(yearly, key=lambda y: y["min_temp"])
    wettest   = max(yearly, key=lambda y: y["total_precipitation"])
    driest    = min(yearly, key=lambda y: y["total_precipitation"])
    snowiest  = max(yearly, key=lambda y: y["total_snowfall"])
    least_sn  = min(yearly, key=lambda y: y["total_snowfall"])
    most_days = max(yearly, key=lambda y: y["snow_days"])

    return {
        "hottest_year":              hottest["year"],
        "hottest_year_max_temp":     hottest["max_temp"],
        "hottest_date":              hottest["hottest_date"],
        "coldest_year":              coldest["year"],
        "coldest_year_min_temp":     coldest["min_temp"],
        "coldest_date":              coldest["coldest_date"],
        "wettest_year":              wettest["year"],
        "wettest_year_precip":       wettest["total_precipitation"],
        "driest_year":               driest["year"],
        "driest_year_precip":        driest["total_precipitation"],
        "snowiest_year":             snowiest["year"],
        "snowiest_year_snowfall":    snowiest["total_snowfall"],
        "snowiest_year_snow_days":   snowiest["snow_days"],
        "least_snow_year":           least_sn["year"],
        "least_snow_year_snowfall":  least_sn["total_snowfall"],
        "least_snow_year_snow_days": least_sn["snow_days"],
        "most_snow_days_year":       most_days["year"],
        "most_snow_days_count":      most_days["snow_days"],
    }


def terminal_summary(
    location_name: str,
    yearly: list[dict],
    extremes: dict,
    trend: dict,
) -> str:
    """Return a formatted multi-line terminal summary string.

    Example:
        📍 Soldeu, Andorra — 50-year Historical Analysis (1974–2024)
        ──────────────────────────────────────────────────────────────
        🌡  Temperature trend:   +0.4°C per decade (warming)
        ...
    """
    if not yearly:
        return f"📍 {location_name} — No historical data available."

    n_years      = len(yearly)
    start_yr     = yearly[0]["year"]
    end_yr       = yearly[-1]["year"]
    all_means    = [y["avg_temp_mean"] for y in yearly]
    overall_mean = round(sum(all_means) / n_years, 1)
    overall_max  = max(y["max_temp"] for y in yearly)
    overall_min  = min(y["min_temp"] for y in yearly)

    sign = "+" if trend["slope_per_decade"] >= 0 else ""
    per_decade_str = f"{sign}{trend['slope_per_decade']}°C per decade ({trend['label']})"
    sep = "─" * 62

    def fmt_date(d: date | None) -> str:
        if d is None:
            return "unknown"
        return d.strftime("%-d %b %Y")

    lines = [
        f"📍 {location_name} — {n_years}-year Historical Analysis ({start_yr}–{end_yr})",
        sep,
        f"🌡  Temperature trend:   {per_decade_str}",
        f"📊  Average annual temp: {overall_mean}°C  (range: {overall_min}°C to {overall_max}°C)",
        "",
        f"🌧  Wettest year:        {extremes.get('wettest_year')} ({extremes.get('wettest_year_precip')} mm)",
        f"☀️  Driest year:         {extremes.get('driest_year')} ({extremes.get('driest_year_precip')} mm)",
        "",
        f"❄️  Snowiest year:       {extremes.get('snowiest_year')} ({extremes.get('snowiest_year_snowfall')} cm total, {extremes.get('snowiest_year_snow_days')} snow days)",
        f"🌱  Least snow:          {extremes.get('least_snow_year')} ({extremes.get('least_snow_year_snowfall')} cm total, {extremes.get('least_snow_year_snow_days')} snow days)",
        "",
        f"🔥  Hottest recorded:    {extremes.get('hottest_year_max_temp')}°C on {fmt_date(extremes.get('hottest_date'))}",
        f"🥶  Coldest recorded:    {extremes.get('coldest_year_min_temp')}°C on {fmt_date(extremes.get('coldest_date'))}",
        sep,
    ]
    return "\n".join(lines)


def seasonal_breakdown(records: list[dict]) -> dict:
    """Break daily records into meteorological seasons per year.

    Records from the current calendar year are excluded to avoid
    incomplete-year bias.

    Season definitions:
        Winter  — Dec, Jan, Feb  (December belongs to the *next* year's winter)
        Spring  — Mar, Apr, May
        Summer  — Jun, Jul, Aug
        Autumn  — Sep, Oct, Nov

    Returns a nested dict::

        {
            year: {
                season: {
                    "avg_temp_mean":       float,
                    "total_precipitation": float,
                }
            }
        }

    where ``year`` is the winter-adjusted year (so December 2010 appears
    under year 2011, season "Winter").
    """
    current_year = date.today().year

    SEASON_MAP = {
        12: ("Winter", +1),  # December → next year's winter
        1:  ("Winter",  0),
        2:  ("Winter",  0),
        3:  ("Spring",  0),
        4:  ("Spring",  0),
        5:  ("Spring",  0),
        6:  ("Summer",  0),
        7:  ("Summer",  0),
        8:  ("Summer",  0),
        9:  ("Autumn",  0),
        10: ("Autumn",  0),
        11: ("Autumn",  0),
    }

    # Accumulate totals and counts per (year, season)
    buckets: dict[int, dict[str, dict[str, float | int]]] = defaultdict(
        lambda: defaultdict(lambda: {"sum_temp": 0.0, "sum_precip": 0.0, "n": 0})
    )

    for r in records:
        rec_year = r["date"].year
        if rec_year == current_year:
            continue
        month = r["date"].month
        season, year_offset = SEASON_MAP[month]
        bucket_year = rec_year + year_offset
        # After the year shift, skip if the resulting bucket year is current year
        if bucket_year == current_year:
            continue
        b = buckets[bucket_year][season]
        b["sum_temp"]   += r["temp_mean"]
        b["sum_precip"] += r["precipitation"]
        b["n"]          += 1

    result: dict[int, dict[str, dict[str, float]]] = {}
    for year in sorted(buckets):
        result[year] = {}
        for season, b in buckets[year].items():
            n = b["n"]
            result[year][season] = {
                "avg_temp_mean":       round(b["sum_temp"] / n, 2) if n else 0.0,
                "total_precipitation": round(b["sum_precip"], 1),
            }
    return result


def yearly_humidity(records: list[dict]) -> list[dict]:
    """Average relative humidity per year.

    Records from the current calendar year are excluded to avoid
    incomplete-year bias.  Records with a ``None`` value for
    ``humidity_mean`` are also skipped.

    Returns a list of dicts sorted by year::

        [{"year": int, "avg_humidity": float}, ...]
    """
    current_year = date.today().year

    by_year: dict[int, list[float]] = defaultdict(list)
    for r in records:
        if r["date"].year == current_year:
            continue
        h = r.get("humidity_mean")
        if h is None:
            continue
        by_year[r["date"].year].append(float(h))

    return [
        {"year": year, "avg_humidity": round(sum(vals) / len(vals), 2)}
        for year in sorted(by_year)
        for vals in (by_year[year],)
        if vals
    ]
