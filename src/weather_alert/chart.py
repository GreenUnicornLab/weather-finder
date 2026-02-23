# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
chart.py — ASCII chart and table rendering for forecast output.

Uses only the Python standard library (os, math).
All rendering functions return strings ready to print.
"""

import os

from weather_alert.utils import fmt_day, fmt_hour

FALLBACK_TERMINAL_WIDTH: int = 80
BAR_LABEL_RESERVE: int = 30  # characters reserved for label + value outside the bar

# Aliases kept for any callers that import these names from chart
_fmt_day = fmt_day
_fmt_hour = fmt_hour


def render_daily_table(days: list[dict], location_line: str) -> str:
    """Render a multi-day forecast as a fixed-width ASCII table.

    Args:
        days: List of daily forecast dicts from fetch_daily_forecast.
        location_line: Display name for the location header.

    Returns:
        Multi-line string containing the formatted table.
    """
    has_snow = any(d["snowfall_cm"] > 0 or d["snow_depth_cm"] > 0 for d in days)

    header_label = f"📍 {location_line} — {len(days)}-day forecast"
    col_widths = {
        "day":   10,
        "max":    6,
        "min":    6,
        "rain":   6,
        "snow":   9 if has_snow else 0,
        "depth":  12 if has_snow else 0,
        "wind":   10,
    }

    sep_width = sum(w for w in col_widths.values() if w) + len(col_widths) - 1
    sep = "─" * sep_width

    # Header row
    headers = ["Day       ", " Max°C", " Min°C", " Rain%"]
    if has_snow:
        headers += [" Snow(cm)", " Depth(cm)"]
    headers += [" Wind km/h"]

    header_row = "  ".join(headers)

    lines = [header_label, sep, header_row, sep]

    for d in days:
        row_parts = [
            f"{_fmt_day(d['date']):<10}",
            f"{d['temp_max']:>5.1f}°",
            f"{d['temp_min']:>5.1f}°",
            f"{d['rain_probability']:>5}%",
        ]
        if has_snow:
            row_parts.append(f"{d['snowfall_cm']:>7.1f} cm")
            row_parts.append(f"{d['snow_depth_cm']:>8.1f} cm")
        row_parts.append(f"{d['wind_max']:>8.0f} {d['wind_direction']}")
        lines.append("  ".join(row_parts))

    lines.append(sep)
    return "\n".join(lines)


def render_hourly_table(hours: list[dict], location_line: str) -> str:
    """Render a multi-hour forecast as a fixed-width ASCII table.

    Args:
        hours: List of hourly forecast dicts from fetch_forecast.
        location_line: Display name for the location header.

    Returns:
        Multi-line string containing the formatted table.
    """
    has_snow = any(h.get("snowfall", 0) > 0 or h.get("snow_depth", 0) > 0 for h in hours)

    header_label = f"📍 {location_line} — {len(hours)}-hour forecast"
    sep = "─" * 65

    headers = ["Time   ", " Temp°C", " Feels°C", " Rain%", " Humid%"]
    if has_snow:
        headers += [" Snow(cm)"]
    headers += [" Wind km/h"]

    header_row = "  ".join(headers)
    lines = [header_label, sep, header_row, sep]

    for h in hours:
        row_parts = [
            f"{_fmt_hour(h['time']):<7}",
            f"{h['temperature']:>6.1f}°",
            f"{h['feels_like']:>7.1f}°",
            f"{h.get('precipitation_probability', 0):>5}%",
            f"{h.get('humidity', 0):>5}%",
        ]
        if has_snow:
            row_parts.append(f"{h.get('snowfall', 0):>7.1f} cm")
        row_parts.append(
            f"{h['wind_speed']:>7.0f} {h.get('wind_direction', '')}"
        )
        lines.append("  ".join(row_parts))

    lines.append(sep)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Bar chart helpers
# ─────────────────────────────────────────────────────────────

def _bar(value: float, max_value: float, bar_width: int) -> str:
    """Render a single filled/empty bar scaled to bar_width.

    Args:
        value: The data value to represent.
        max_value: The maximum value (maps to full bar width).
        bar_width: Total character width of the bar.

    Returns:
        String of '█' and '░' characters of length bar_width.
    """
    if max_value == 0:
        filled = 0
    else:
        filled = round((value / max_value) * bar_width)
    filled = max(0, min(filled, bar_width))
    return "█" * filled + "░" * (bar_width - filled)


def render_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    unit: str = "",
    bar_width: int | None = None,
) -> str:
    """Render a labelled horizontal bar chart.

    Args:
        labels: List of row label strings.
        values: List of numeric values corresponding to each label.
        title: Chart title printed above the bars.
        unit: Optional unit suffix appended to each value (e.g. '°C', ' cm').
        bar_width: Width of the bar in characters. Auto-detected from terminal if None.

    Returns:
        Multi-line string containing the chart.
    """
    if bar_width is None:
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = FALLBACK_TERMINAL_WIDTH
        # Reserve space for: label(10) + " │" + bar + "│ " + value(8)
        bar_width = max(10, terminal_width - BAR_LABEL_RESERVE)

    max_val = max(values) if values else 1
    if max_val == 0:
        max_val = 1  # avoid division by zero

    label_w = max(len(lbl) for lbl in labels) if labels else 3
    lines = [title]
    for label, value in zip(labels, values):
        bar = _bar(value, max_val, bar_width)
        val_str = f"{value:.0f}{unit}"
        lines.append(f"  {label:<{label_w}} │{bar}│ {val_str:>6}")

    return "\n".join(lines)


def render_daily_charts(days: list[dict]) -> str:
    """Render temperature and (if relevant) snow depth bar charts for daily data.

    Args:
        days: List of daily forecast dicts from fetch_daily_forecast.

    Returns:
        Multi-line string containing one or two bar charts.
    """
    labels = [_fmt_day(d["date"]) for d in days]
    temp_values = [d["temp_max"] for d in days]

    # Shift values so the minimum maps to 0 for bar scaling
    temp_min = min(temp_values)
    temp_offset = -temp_min if temp_min < 0 else 0
    temp_shifted = [v + temp_offset for v in temp_values]

    # Build custom bar chart with real temp labels (not shifted values)
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = FALLBACK_TERMINAL_WIDTH
    bar_width = max(10, terminal_width - BAR_LABEL_RESERVE)
    label_w = max(len(l) for l in labels)
    max_shifted = max(temp_shifted) if temp_shifted else 1
    if max_shifted == 0:
        max_shifted = 1

    parts = ["Temperature (max°C)"]
    for label, shifted, real in zip(labels, temp_shifted, temp_values):
        bar = _bar(shifted, max_shifted, bar_width)
        parts.append(f"  {label:<{label_w}} │{bar}│ {real:>4.0f}°C")

    charts = "\n".join(parts)

    has_snow = any(d["snow_depth_cm"] > 0 for d in days)
    if has_snow:
        snow_values = [d["snow_depth_cm"] for d in days]
        charts += "\n\n" + render_bar_chart(
            labels, snow_values, "Snow depth (cm)", unit=" cm"
        )

    return charts
