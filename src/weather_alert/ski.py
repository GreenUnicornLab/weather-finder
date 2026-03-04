# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
ski.py — Ski Season Intelligence: historical pattern matching and season prediction.

Defines "ski season" as November 1 to April 30.
Defines "winter months" as December, January, February.
Powder day threshold: snowfall > 20 cm.
Season start/end: first/last day with snow_depth_max > 10 cm.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from weather_alert.history import fetch_historical

# ── Constants ─────────────────────────────────────────────────────────────────

POWDER_THRESHOLD_CM: float = 20.0
DEPTH_THRESHOLD_CM: float = 10.0
PEAK_WINDOW_DAYS: int = 21
WINTER_MONTHS: frozenset[int] = frozenset({12, 1, 2})

RATING_STARS: dict[str, str] = {
    "EXCEPTIONAL": "⭐⭐⭐⭐⭐",
    "EXCELLENT": "⭐⭐⭐⭐",
    "GOOD": "⭐⭐⭐",
    "AVERAGE": "⭐⭐",
    "POOR": "⭐",
    "UNKNOWN": "❓",
}

RATING_PRIORITY = ["EXCEPTIONAL", "EXCELLENT", "GOOD", "AVERAGE", "POOR"]


# ── Data Fetching ─────────────────────────────────────────────────────────────


def fetch_ski_data(latitude: float, longitude: float, years: int = 51) -> list[dict]:
    """Fetch historical weather data; 51 years ensures current season is included."""
    return fetch_historical(latitude, longitude, years=years)


# ── Season Helpers ────────────────────────────────────────────────────────────


def _season_year(d: date) -> int:
    """Return the 'season year' (the Nov/Dec year) for a date.

    Season 2018-19: Nov/Dec 2018 + Jan-Apr 2019 → season_year = 2018.
    Returns -1 for May-Oct (off-season).
    """
    if d.month >= 11:
        return d.year
    if 1 <= d.month <= 4:
        return d.year - 1
    return -1  # off-season


def _season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


# ── Season Grouping ───────────────────────────────────────────────────────────


def historical_seasons(records: list[dict]) -> list[dict]:
    """Group daily records into ski seasons (Nov 1 – Apr 30).

    Only returns past, completed seasons. The current running season is
    excluded so it is never used as a historical comparator.
    Results sorted by season_label ascending.
    """
    today = date.today()
    current_season_year = today.year if today.month >= 10 else today.year - 1

    by_season: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        sy = _season_year(r["date"])
        if sy >= 0:
            by_season[sy].append(r)

    seasons = []
    for sy, recs in sorted(by_season.items()):
        # Exclude the current running season
        if sy >= current_season_year:
            continue
        months_present = {r["date"].month for r in recs}
        # Must have November (start) and January (past mid-season) to be valid
        if 11 not in months_present or 1 not in months_present:
            continue

        recs_sorted = sorted(recs, key=lambda r: r["date"])

        total_snowfall = sum(r["snowfall"] for r in recs_sorted)
        peak_snow_depth = max(
            (r["snow_depth_max"] for r in recs_sorted), default=0.0
        )
        snow_days = sum(1 for r in recs_sorted if r["snowfall"] > 0)
        powder_days = sum(
            1 for r in recs_sorted if r["snowfall"] > POWDER_THRESHOLD_CM
        )

        winter_recs = [
            r for r in recs_sorted if r["date"].month in WINTER_MONTHS
        ]
        avg_winter_temp = (
            sum(r["temp_mean"] for r in winter_recs) / len(winter_recs)
            if winter_recs
            else 0.0
        )

        deep = [r for r in recs_sorted if r["snow_depth_max"] > DEPTH_THRESHOLD_CM]
        season_start: date | None = deep[0]["date"] if deep else None
        season_end: date | None = deep[-1]["date"] if deep else None

        # 21-day peak window
        peak_window_start: date | None = None
        peak_window_end: date | None = None
        if len(recs_sorted) >= PEAK_WINDOW_DAYS:
            best_sum = -1.0
            for i in range(len(recs_sorted) - PEAK_WINDOW_DAYS + 1):
                window = recs_sorted[i : i + PEAK_WINDOW_DAYS]
                s = sum(r["snow_depth_max"] for r in window)
                if s > best_sum:
                    best_sum = s
                    peak_window_start = window[0]["date"]
                    peak_window_end = window[-1]["date"]

        seasons.append(
            {
                "season_label": _season_label(sy),
                "season_year": sy,
                "total_snowfall": total_snowfall,
                "peak_snow_depth": peak_snow_depth,
                "snow_days": snow_days,
                "powder_days": powder_days,
                "avg_winter_temp": avg_winter_temp,
                "season_start": season_start,
                "season_end": season_end,
                "peak_window_start": peak_window_start,
                "peak_window_end": peak_window_end,
                "records": recs_sorted,
            }
        )

    return seasons


# ── Rating ────────────────────────────────────────────────────────────────────


def rate_season(season: dict, all_seasons: list[dict]) -> str:
    """Rate a season by total_snowfall percentile relative to all_seasons.

    EXCEPTIONAL ≥ 90th percentile
    EXCELLENT   ≥ 75th
    GOOD        ≥ 50th
    AVERAGE     ≥ 25th
    POOR        < 25th
    """
    n = len(all_seasons)
    if n == 0:
        return "AVERAGE"
    sf = season["total_snowfall"]
    rank = sum(1 for s in all_seasons if s["total_snowfall"] < sf)
    pct = rank / n * 100
    if pct >= 90:
        return "EXCEPTIONAL"
    if pct >= 75:
        return "EXCELLENT"
    if pct >= 50:
        return "GOOD"
    if pct >= 25:
        return "AVERAGE"
    return "POOR"


# ── Current Season ────────────────────────────────────────────────────────────


def get_current_season_data(records: list[dict]) -> list[dict]:
    """Return records from Oct 1 of the current ski-season year to today.

    The 'current season year' is the Nov/Dec year of the running season.
    e.g. in March 2026 the current season is 2025-26, so Oct 1 2025 is the start.
    """
    today = date.today()
    # Determine which season we are in: months Oct-Dec belong to this calendar year,
    # months Jan-Sep belong to the season that started the previous calendar year.
    season_year = today.year if today.month >= 10 else today.year - 1
    oct_1 = date(season_year, 10, 1)
    return sorted(
        [r for r in records if oct_1 <= r["date"] <= today],
        key=lambda r: r["date"],
    )


# ── Prediction ────────────────────────────────────────────────────────────────


def _day_offset(d: date, season_year: int) -> int:
    """Days since Oct 1 of season_year (Oct 1 = offset 0)."""
    return (d - date(season_year, 10, 1)).days


def predict_current_season(
    current_data: list[dict], hist_seasons: list[dict]
) -> dict:
    """Pattern-match current snow_depth_max trajectory vs historical seasons.

    Uses sum-of-squared-differences on daily snow_depth_max aligned by day
    offset from Oct 1. Returns a prediction dict.

    hist_seasons must have a "rating" key already set on each season.
    """
    today = date.today()
    current_year = today.year if today.month >= 10 else today.year - 1

    if not current_data:
        return {
            "predicted_rating": "UNKNOWN",
            "confidence": "LOW",
            "similar_seasons": [],
            "similar_season_outcomes": [],
            "current_snowpack": 0.0,
            "historical_avg_snowpack": 0.0,
            "snowpack_vs_avg": 0.0,
        }

    # Build current depth lookup by day offset
    cur_depth: dict[int, float] = {
        _day_offset(r["date"], current_year): r["snow_depth_max"]
        for r in current_data
    }
    max_offset = max(cur_depth.keys())
    current_snowpack = cur_depth.get(max_offset, 0.0)

    # Compute SSD for each historical season
    ssds: list[tuple[float, dict]] = []
    for season in hist_seasons:
        sy = season["season_year"]
        hist_depth: dict[int, float] = {
            _day_offset(r["date"], sy): r["snow_depth_max"]
            for r in season["records"]
        }
        common = [o for o in range(max_offset + 1) if o in hist_depth]
        if len(common) < 5:
            continue
        ssd = sum(
            (cur_depth.get(o, 0.0) - hist_depth[o]) ** 2 for o in common
        )
        ssds.append((ssd, season))

    ssds.sort(key=lambda x: x[0])
    top3 = ssds[:3]

    similar_labels = [s["season_label"] for _, s in top3]
    similar_ratings = [s.get("rating", "AVERAGE") for _, s in top3]

    # Most common rating, highest wins ties
    counts: dict[str, int] = defaultdict(int)
    for r in similar_ratings:
        counts[r] += 1
    max_count = max(counts.values(), default=0)
    predicted_rating = "AVERAGE"
    for r in RATING_PRIORITY:
        if counts.get(r, 0) == max_count:
            predicted_rating = r
            break

    min_ssd = top3[0][0] if top3 else float("inf")
    if min_ssd < 500:
        confidence = "HIGH"
    elif min_ssd < 2000:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Historical average snowpack at today's position
    avg_depths = []
    for season in hist_seasons:
        sy = season["season_year"]
        for r in season["records"]:
            if _day_offset(r["date"], sy) == max_offset:
                avg_depths.append(r["snow_depth_max"])
                break
    hist_avg = sum(avg_depths) / len(avg_depths) if avg_depths else 0.0
    vs_avg = (
        (current_snowpack - hist_avg) / hist_avg * 100 if hist_avg > 0 else 0.0
    )

    return {
        "predicted_rating": predicted_rating,
        "confidence": confidence,
        "similar_seasons": similar_labels,
        "similar_season_outcomes": similar_ratings,
        "current_snowpack": current_snowpack,
        "historical_avg_snowpack": hist_avg,
        "snowpack_vs_avg": vs_avg,
    }


# ── Best Weeks ────────────────────────────────────────────────────────────────


def _ski_season_week(d: date, season_year: int) -> int | None:
    """0-indexed week within the ski season. Week 0 = Nov 1-7.
    Returns None if outside Nov 1 – Apr 30.
    """
    nov_1 = date(season_year, 11, 1)
    apr_30 = date(season_year + 1, 4, 30)
    if d < nov_1 or d > apr_30:
        return None
    return (d - nov_1).days // 7


def _week_label(week_num: int) -> str:
    """Canonical week label e.g. 'Jan 15 – Jan 21' (using 2024/25 as reference)."""
    ref_nov_1 = date(2024, 11, 1)
    start = ref_nov_1 + timedelta(days=week_num * 7)
    end = start + timedelta(days=6)

    def fmt(d: date) -> str:
        return f"{d.day} {d.strftime('%b')}"

    return f"{fmt(start)} – {fmt(end)}"


def best_weeks_to_ski(hist_seasons: list[dict]) -> list[dict]:
    """Find the top 5 historically best weeks to ski.

    For each week of the ski season across all historical seasons compute:
    avg_snow_depth, powder_day_probability (%), avg_temp.
    Returns top 5 sorted by avg_snow_depth descending with rank 1-5.
    """
    accumulator: dict[int, dict] = {}

    for season in hist_seasons:
        sy = season["season_year"]
        for r in season["records"]:
            wn = _ski_season_week(r["date"], sy)
            if wn is None or wn > 25:
                continue
            if wn not in accumulator:
                accumulator[wn] = {
                    "depths": [],
                    "snowfalls": [],
                    "powder_count": 0,
                    "day_count": 0,
                    "temps": [],
                }
            acc = accumulator[wn]
            acc["depths"].append(r["snow_depth_max"])
            acc["snowfalls"].append(r["snowfall"])
            acc["temps"].append(r["temp_mean"])
            acc["day_count"] += 1
            if r["snowfall"] > POWDER_THRESHOLD_CM:
                acc["powder_count"] += 1

    weeks = []
    for wn, acc in accumulator.items():
        if not acc["depths"]:
            continue
        avg_depth = sum(acc["depths"]) / len(acc["depths"])
        avg_snowfall = sum(acc["snowfalls"]) / len(acc["snowfalls"])
        powder_prob = (
            acc["powder_count"] / acc["day_count"] * 100 if acc["day_count"] > 0 else 0.0
        )
        avg_temp = sum(acc["temps"]) / len(acc["temps"]) if acc["temps"] else 0.0
        weeks.append(
            {
                "week_num": wn,
                "week_label": _week_label(wn),
                "avg_snow_depth": avg_depth,
                "avg_snowfall": avg_snowfall,
                "powder_day_probability": powder_prob,
                "avg_temp": avg_temp,
            }
        )

    # Rank by avg_snowfall (reliable across all elevations) rather than snow_depth
    # which can be poorly calibrated in the archive API for mountain grid points.
    weeks.sort(key=lambda w: w["avg_snowfall"], reverse=True)
    top5 = weeks[:5]
    for i, w in enumerate(top5):
        w["rank"] = i + 1
    return top5


# ── Terminal Summary ──────────────────────────────────────────────────────────


def terminal_summary(
    location: str,
    prediction: dict,
    best_weeks: list[dict],
    hist_seasons: list[dict],
    current_year: int,
) -> str:
    """Format the terminal output for the ski season forecast."""
    sep = "─" * 54
    season_label = f"{current_year}-{str(current_year + 1)[-2:]}"
    rating = prediction["predicted_rating"]
    stars = RATING_STARS.get(rating, "")
    snowpack = prediction["current_snowpack"]
    hist_avg = prediction["historical_avg_snowpack"]
    vs_avg = prediction["snowpack_vs_avg"]
    arrow = "↑" if vs_avg >= 0 else "↓"
    abs_pct = abs(round(vs_avg))
    direction = "above" if vs_avg >= 0 else "below"

    lines: list[str] = [
        f"🎿 {location} — {season_label} Season Forecast",
        sep,
        f"Season outlook:      {stars} {rating}",
        f"Confidence:          {prediction['confidence']}",
        (
            f"Current snowpack:    {round(snowpack)}cm "
            f"({arrow} {abs_pct}% {direction} historical avg of {round(hist_avg)}cm)"
        ),
        "",
    ]

    # Similar seasons
    similar = prediction.get("similar_seasons", [])
    outcomes = prediction.get("similar_season_outcomes", [])
    if similar:
        pairs = [f"{lbl} ({out})" for lbl, out in zip(similar, outcomes)]
        first = f"Similar past seasons: {pairs[0]}"
        if len(pairs) > 1:
            rest = ", ".join(pairs[1:])
            indent = " " * 22
            combined = f"{first}, {rest}"
            if len(combined) <= 60:
                lines.append(combined)
            else:
                lines.append(f"{first},")
                lines.append(f"{indent}{rest}")
        else:
            lines.append(first)
        lines.append("")

    # Best weeks table
    lines.append("🏔️  Best weeks to ski (historical):")
    for w in best_weeks:
        lbl = w["week_label"]
        sf = round(w["avg_snowfall"], 1)
        powder = round(w["powder_day_probability"])
        temp = round(w["avg_temp"])
        lines.append(
            f"  {w['rank']}. {lbl:<18} │ {sf}cm/day avg │ {powder}% powder days │ {temp}°C"
        )

    lines.append("")

    # Historical stats
    if hist_seasons:
        sorted_s = sorted(hist_seasons, key=lambda s: s["total_snowfall"])
        best = sorted_s[-1]
        worst = sorted_s[0]
        avg_sf = sum(s["total_snowfall"] for s in hist_seasons) / len(hist_seasons)
        lines.append("📊 Historical records:")
        lines.append(
            f"  Best season ever:   {best['season_label']} "
            f"({round(best['total_snowfall'])}cm total, {best['powder_days']} powder days)"
        )
        lines.append(
            f"  Worst season ever:  {worst['season_label']} "
            f"({round(worst['total_snowfall'])}cm total, {worst['powder_days']} powder days)"
        )
        lines.append(f"  Avg annual snowfall: {round(avg_sf)}cm")

    lines.append(sep)
    return "\n".join(lines)
