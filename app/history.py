# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
history.py — Streamlit historical weather dashboard with Apple-inspired dark UI.

Run with:
    streamlit run app/history.py
    streamlit run app/history.py -- --location "Soldeu, Andorra" --years 30

Requires: pip install -e ".[ui]"
Data source: ERA5 reanalysis via Open-Meteo Historical Weather API (free, no key).
"""

import sys
from pathlib import Path

# Ensure the src/ package is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from datetime import date

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from weather_alert.analysis import (
    find_extremes,
    monthly_climatology,
    temperature_trend,
    yearly_summary,
)
from weather_alert.geocode import LocationNotFoundError, geocode
from weather_alert.history import fetch_historical


# ─────────────────────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Historical Weather",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────
# CSS injection (Apple-inspired dark theme — copied from app.py)
# ─────────────────────────────────────────────────────────────

APPLE_CSS = """
<style>
  /* ── Reset Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 960px; }

  /* ── Typography & base ── */
  html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                 "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    background-color: #0a0a0a;
    color: #f5f5f7;
  }

  /* ── Search input ── */
  .stTextInput > div > div > input {
    background: #1c1c1e !important;
    border: 1px solid #3a3a3c !important;
    border-radius: 980px !important;
    color: #f5f5f7 !important;
    font-size: 1.1rem !important;
    padding: 0.75rem 1.25rem !important;
    text-align: center;
  }
  .stTextInput > div > div > input::placeholder { color: #636366 !important; }
  .stTextInput > div > div > input:focus {
    border-color: #0a84ff !important;
    box-shadow: 0 0 0 3px rgba(10,132,255,0.2) !important;
  }

  /* ── Primary button ── */
  .stButton > button {
    background: #0a84ff !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 980px !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 2rem !important;
    letter-spacing: -0.01em;
    transition: opacity 0.15s ease;
  }
  .stButton > button:hover { opacity: 0.85; }
  .stButton > button:active { opacity: 0.7; }

  /* ── Cards ── */
  .wa-card {
    background: #1c1c1e;
    border: 1px solid #2c2c2e;
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 1.5rem;
  }

  /* ── Hero temperature ── */
  .hero-temp {
    font-size: 7rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1;
    background: linear-gradient(180deg, #ffffff 60%, #8e8e93 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .hero-feels {
    font-size: 1rem;
    color: #8e8e93;
    font-weight: 400;
    margin-top: 0.25rem;
    letter-spacing: -0.01em;
  }

  /* ── Stat pills ── */
  .stat-pill {
    background: #2c2c2e;
    border-radius: 12px;
    padding: 14px 18px;
    display: inline-block;
    width: 100%;
  }
  .stat-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8e8e93;
    font-weight: 500;
  }
  .stat-value {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: #f5f5f7;
    line-height: 1.2;
  }
  .stat-unit {
    font-size: 0.9rem;
    color: #8e8e93;
    font-weight: 400;
  }

  /* ── Alert pill ── */
  .alert-pill {
    background: rgba(255, 69, 58, 0.15);
    border: 1px solid rgba(255, 69, 58, 0.4);
    border-radius: 8px;
    color: #ff453a;
    font-size: 0.9rem;
    font-weight: 500;
    padding: 8px 16px;
    margin-top: 12px;
    display: inline-block;
  }

  /* ── Error card ── */
  .error-card {
    background: rgba(255, 69, 58, 0.1);
    border: 1px solid rgba(255, 69, 58, 0.3);
    border-radius: 12px;
    color: #ff453a;
    font-size: 1rem;
    padding: 20px 24px;
    text-align: center;
    margin: 1rem 0;
  }

  /* ── Condition line ── */
  .condition-line {
    color: #8e8e93;
    font-size: 0.95rem;
    letter-spacing: -0.01em;
    margin-top: 1rem;
    text-align: center;
  }

  /* ── Section heading ── */
  .section-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #636366;
    font-weight: 600;
    margin-bottom: 0.75rem;
  }

  /* ── Forecast table ── */
  .wa-table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
  .wa-table th {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #636366;
    font-weight: 600;
    padding: 8px 12px;
    text-align: right;
    border-bottom: 1px solid #2c2c2e;
  }
  .wa-table th:first-child { text-align: left; }
  .wa-table td {
    padding: 12px 12px;
    color: #f5f5f7;
    text-align: right;
    border-bottom: 1px solid #1c1c1e;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }
  .wa-table td:first-child { text-align: left; color: #f5f5f7; }
  .wa-table tr:hover td { background: #2c2c2e; }
  .wa-table tr.today td { background: rgba(10,132,255,0.08); }
  .wa-table tr.today td:first-child { color: #0a84ff; font-weight: 600; }

  /* ── Segmented control (radio) ── */
  .stRadio > div { gap: 0 !important; }
  .stRadio > div > label {
    background: #1c1c1e;
    border: 1px solid #3a3a3c;
    color: #8e8e93 !important;
    border-radius: 0;
    padding: 0.45rem 1.2rem;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    margin: 0 !important;
    transition: all 0.15s;
  }
  .stRadio > div > label:first-child { border-radius: 8px 0 0 8px; }
  .stRadio > div > label:last-child  { border-radius: 0 8px 8px 0; border-left: none; }
  .stRadio > div > label[data-checked="true"] {
    background: #0a84ff !important;
    border-color: #0a84ff !important;
    color: #ffffff !important;
  }

  /* ── Location resolved text ── */
  .location-resolved {
    color: #8e8e93;
    font-size: 0.85rem;
    text-align: center;
    margin-top: 0.5rem;
  }

  /* ── Footer ── */
  .wa-footer {
    text-align: center;
    color: #48484a;
    font-size: 0.8rem;
    padding: 3rem 0 1rem;
    letter-spacing: -0.005em;
  }
</style>
"""

st.markdown(APPLE_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Plotly base layout (dark, no background)
# ─────────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
        color="#8e8e93",
        size=12,
    ),
    margin=dict(l=8, r=8, t=32, b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8e8e93")),
    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#636366")),
    yaxis=dict(gridcolor="#2c2c2e", zeroline=False, tickfont=dict(color="#636366")),
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def stat_html(label: str, value: str, unit: str = "") -> str:
    """Render a stat pill as HTML."""
    return f"""
    <div class="stat-pill">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}<span class="stat-unit"> {unit}</span></div>
    </div>
    """


def _fmt_date(d: date | None) -> str:
    """Format a date as '%-d %b %Y', returning '—' for None."""
    if d is None:
        return "—"
    try:
        return d.strftime("%-d %b %Y")
    except Exception:
        return str(d)


# ─────────────────────────────────────────────────────────────
# CLI arg parsing (supports: streamlit run app/history.py -- --location X --years N)
# ─────────────────────────────────────────────────────────────


def _parse_cli_args() -> tuple[str | None, int]:
    """Parse --location and --years from sys.argv after the '--' separator.

    Streamlit passes everything after '--' as script arguments.
    Returns (location_str | None, years_int).
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--location", type=str, default=None)
    parser.add_argument("--years", type=int, default=30)

    # Streamlit forwards argv after '--'; gracefully ignore unknown flags
    try:
        sep = sys.argv.index("--")
        script_args = sys.argv[sep + 1:]
    except ValueError:
        script_args = []

    args, _ = parser.parse_known_args(script_args)
    return args.location, args.years


CLI_LOCATION, CLI_YEARS = _parse_cli_args()


# ─────────────────────────────────────────────────────────────
# Cached data loader
# ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=86400)
def load_data(location: str, years: int) -> dict:
    """Geocode *location*, fetch historical data, run all analysis passes.

    Returns a dict with keys:
        location (dict), records (list[dict]), yearly (list[dict]),
        monthly (list[dict]), trend (dict), extremes (dict)

    On any error returns {"error": str}.
    """
    try:
        loc = geocode(location)
    except LocationNotFoundError:
        return {"error": f'Location "{location}" not found. Try a more specific name.'}
    except RuntimeError as exc:
        return {"error": f"Geocoding error: {exc}"}

    try:
        records = fetch_historical(
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            years=years,
        )
    except RuntimeError as exc:
        return {"error": f"Historical data fetch failed: {exc}"}

    if not records:
        return {"error": "No historical records returned for this location."}

    yearly = yearly_summary(records)
    monthly = monthly_climatology(records)
    trend = temperature_trend(yearly)
    extremes = find_extremes(yearly)

    return {
        "location": loc,
        "records": records,
        "yearly": yearly,
        "monthly": monthly,
        "trend": trend,
        "extremes": extremes,
    }


# ─────────────────────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────────────────────

_MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def main() -> None:
    """Render the full historical weather dashboard."""

    # ── SECTION 1: Input row ─────────────────────────────────

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        location_input = st.text_input(
            label="location",
            value=CLI_LOCATION or "",
            placeholder="Enter a location (e.g. Soldeu, Andorra)",
            label_visibility="collapsed",
            key="hist_location_input",
        )
        years_col, btn_col = st.columns([1, 2])
        with years_col:
            years_input = st.number_input(
                label="Years of history",
                min_value=1,
                max_value=75,
                value=CLI_YEARS,
                step=5,
                label_visibility="collapsed",
                key="hist_years_input",
                help="Years of history to analyse (max ~75 for ERA5)",
            )
        with btn_col:
            analyse_clicked = st.button(
                "Analyse History", use_container_width=True, key="hist_analyse_btn"
            )

    # Determine the active query: button press overrides CLI default
    query_location: str | None = None
    if analyse_clicked and location_input.strip():
        query_location = location_input.strip()
    elif CLI_LOCATION and not analyse_clicked:
        # Auto-load when launched with --location flag
        query_location = CLI_LOCATION

    if query_location is None:
        st.markdown(
            '<div class="condition-line" style="margin-top:3rem;">'
            "Enter a location above and click Analyse History"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="wa-footer">'
            'Powered by <a href="https://open-meteo.com" style="color:#0a84ff;'
            'text-decoration:none;">Open-Meteo</a> Historical Weather API'
            " &nbsp;·&nbsp; ERA5 reanalysis &nbsp;·&nbsp; No API key required"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # ── SECTION 2: Spinner while loading ────────────────────

    with st.spinner(f"Loading {int(years_input)}-year history for {query_location}…"):
        data = load_data(query_location, int(years_input))

    if "error" in data:
        st.markdown(
            f'<div class="error-card">⚠️ {data["error"]}</div>',
            unsafe_allow_html=True,
        )
        return

    loc: dict = data["location"]
    yearly: list[dict] = data["yearly"]
    monthly: list[dict] = data["monthly"]
    trend: dict = data["trend"]
    extremes: dict = data["extremes"]

    if not yearly:
        st.markdown(
            '<div class="error-card">⚠️ No yearly data available.</div>',
            unsafe_allow_html=True,
        )
        return

    n_years = len(yearly)
    start_yr = yearly[0]["year"]
    end_yr = yearly[-1]["year"]
    all_means = [y["avg_temp_mean"] for y in yearly]
    overall_mean = round(sum(all_means) / n_years, 1)

    # ── SECTION 3: Page header + 4 stat pills ────────────────

    trend_sign = "+" if trend["slope_per_decade"] >= 0 else ""
    trend_color = (
        "#ff453a" if trend["label"] == "warming"
        else "#30d158" if trend["label"] == "cooling"
        else "#8e8e93"
    )

    st.markdown(
        f'<h2 style="font-size:1.6rem;font-weight:700;letter-spacing:-0.03em;'
        f'margin-bottom:0.25rem;">📅 {loc["name"]}</h2>'
        f'<div class="condition-line" style="margin-top:0;margin-bottom:1.5rem;">'
        f"{n_years}-year historical analysis &nbsp;·&nbsp; {start_yr}–{end_yr}"
        f"</div>",
        unsafe_allow_html=True,
    )

    stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
    with stat_c1:
        st.markdown(
            stat_html("Avg Annual Temp", f"{overall_mean}", "°C"),
            unsafe_allow_html=True,
        )
    with stat_c2:
        st.markdown(
            stat_html(
                "Temp Trend",
                f'<span style="color:{trend_color}">'
                f"{trend_sign}{trend['slope_per_decade']}</span>",
                "°C/dec",
            ),
            unsafe_allow_html=True,
        )
    with stat_c3:
        hottest_temp = extremes.get("hottest_year_max_temp", "—")
        st.markdown(
            stat_html("Record High", f"{hottest_temp}", "°C"),
            unsafe_allow_html=True,
        )
    with stat_c4:
        coldest_temp = extremes.get("coldest_year_min_temp", "—")
        st.markdown(
            stat_html("Record Low", f"{coldest_temp}", "°C"),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── SECTION 4: Temperature trend chart ───────────────────

    st.markdown(
        '<div class="section-label">Annual Temperature Trend</div>',
        unsafe_allow_html=True,
    )

    years_x = [float(y["year"]) for y in yearly]
    means_y = [y["avg_temp_mean"] for y in yearly]

    # Compute OLS trend line inline for the overlay
    n = len(years_x)
    sum_x = sum(years_x)
    sum_y = sum(means_y)
    sum_xy = sum(x * y for x, y in zip(years_x, means_y))
    sum_x2 = sum(x * x for x in years_x)
    denom = n * sum_x2 - sum_x ** 2
    if denom != 0:
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        trend_line_y = [slope * x + intercept for x in years_x]
    else:
        trend_line_y = means_y[:]

    year_labels = [str(y["year"]) for y in yearly]
    trend_label_str = (
        f"{trend_sign}{trend['slope_per_decade']}°C / decade ({trend['label']})"
    )

    fig_trend = go.Figure()
    fig_trend.add_trace(
        go.Scatter(
            x=year_labels,
            y=means_y,
            name="Avg Temp",
            mode="lines+markers",
            line=dict(color="#0a84ff", width=2),
            marker=dict(color="#0a84ff", size=4),
            fill="tozeroy",
            fillcolor="rgba(10,132,255,0.06)",
        )
    )
    fig_trend.add_trace(
        go.Scatter(
            x=year_labels,
            y=trend_line_y,
            name=trend_label_str,
            mode="lines",
            line=dict(color=trend_color, width=1.5, dash="dot"),
        )
    )
    fig_trend.update_layout(**{
        **PLOTLY_LAYOUT,
        "title": dict(text="Mean Annual Temperature (°C)", font=dict(color="#8e8e93", size=13)),
        "yaxis": dict(**PLOTLY_LAYOUT["yaxis"], ticksuffix="°C"),
        "height": 300,
        "hovermode": "x unified",
    })
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    # ── SECTION 5: Precipitation + Snow (side-by-side) ───────

    st.markdown(
        '<div class="section-label">Precipitation &amp; Snow</div>',
        unsafe_allow_html=True,
    )

    precip_col, snow_col = st.columns(2)

    # Annual precipitation bar chart
    with precip_col:
        total_precips = [y["total_precipitation"] for y in yearly]
        fig_precip = go.Figure(
            go.Bar(
                x=year_labels,
                y=total_precips,
                name="Total Precipitation",
                marker_color="rgba(10,132,255,0.7)",
                marker_line_width=0,
            )
        )
        fig_precip.update_layout(**{
            **PLOTLY_LAYOUT,
            "title": dict(text="Annual Precipitation (mm)", font=dict(color="#8e8e93", size=13)),
            "yaxis": dict(**PLOTLY_LAYOUT["yaxis"], ticksuffix=" mm"),
            "height": 280,
        })
        st.plotly_chart(
            fig_precip, use_container_width=True, config={"displayModeBar": False}
        )

    # Annual snowfall + snow days (dual-axis)
    with snow_col:
        total_snowfalls = [y["total_snowfall"] for y in yearly]
        snow_days_list = [y["snow_days"] for y in yearly]

        fig_snow = make_subplots(specs=[[{"secondary_y": True}]])
        fig_snow.add_trace(
            go.Bar(
                x=year_labels,
                y=total_snowfalls,
                name="Snowfall (cm)",
                marker_color="rgba(255,255,255,0.25)",
                marker_line_width=0,
            ),
            secondary_y=False,
        )
        fig_snow.add_trace(
            go.Scatter(
                x=year_labels,
                y=snow_days_list,
                name="Snow Days",
                mode="lines+markers",
                line=dict(color="#ffffff", width=1.5),
                marker=dict(color="#ffffff", size=3),
            ),
            secondary_y=True,
        )
        fig_snow.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(
                text="Annual Snowfall & Snow Days",
                font=dict(color="#8e8e93", size=13),
            ),
            height=280,
            barmode="overlay",
        )
        fig_snow.update_yaxes(
            ticksuffix=" cm",
            gridcolor="#2c2c2e",
            zeroline=False,
            tickfont=dict(color="#636366"),
            secondary_y=False,
        )
        fig_snow.update_yaxes(
            ticksuffix=" d",
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#636366"),
            secondary_y=True,
        )
        st.plotly_chart(
            fig_snow, use_container_width=True, config={"displayModeBar": False}
        )

    # ── SECTION 6: Monthly climatology ───────────────────────

    st.markdown(
        '<div class="section-label">Monthly Climatology</div>',
        unsafe_allow_html=True,
    )

    month_names = [_MONTH_ABBR[m["month"] - 1] for m in monthly]
    clim_temps = [m["avg_temp_mean"] for m in monthly]
    clim_precips = [m["avg_precipitation"] for m in monthly]
    clim_snowfalls = [m["avg_snowfall"] for m in monthly]

    fig_clim = make_subplots(specs=[[{"secondary_y": True}]])
    fig_clim.add_trace(
        go.Bar(
            x=month_names,
            y=clim_precips,
            name="Avg Precip (mm)",
            marker_color="rgba(10,132,255,0.55)",
            marker_line_width=0,
        ),
        secondary_y=False,
    )
    if any(s > 0 for s in clim_snowfalls):
        fig_clim.add_trace(
            go.Bar(
                x=month_names,
                y=clim_snowfalls,
                name="Avg Snowfall (cm)",
                marker_color="rgba(255,255,255,0.3)",
                marker_line_width=0,
            ),
            secondary_y=False,
        )
    fig_clim.add_trace(
        go.Scatter(
            x=month_names,
            y=clim_temps,
            name="Avg Temp (°C)",
            mode="lines+markers",
            line=dict(color="#ff9f0a", width=2),
            marker=dict(color="#ff9f0a", size=5),
        ),
        secondary_y=True,
    )
    fig_clim.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(
            text="Average Monthly Conditions (all years)",
            font=dict(color="#8e8e93", size=13),
        ),
        barmode="group",
        height=300,
    )
    fig_clim.update_yaxes(
        ticksuffix=" mm",
        gridcolor="#2c2c2e",
        zeroline=False,
        tickfont=dict(color="#636366"),
        secondary_y=False,
    )
    fig_clim.update_yaxes(
        ticksuffix="°C",
        showgrid=False,
        zeroline=False,
        tickfont=dict(color="#636366"),
        secondary_y=True,
    )
    st.plotly_chart(fig_clim, use_container_width=True, config={"displayModeBar": False})

    # ── SECTION 7: Extreme events table ──────────────────────

    st.markdown(
        '<div class="section-label">Extreme Years</div>',
        unsafe_allow_html=True,
    )

    import pandas as pd  # local import — pandas is optional/heavy

    extremes_rows = [
        {
            "Category": "Hottest year",
            "Year": extremes.get("hottest_year", "—"),
            "Value": f"{extremes.get('hottest_year_max_temp', '—')} °C",
            "Notable date": _fmt_date(extremes.get("hottest_date")),
        },
        {
            "Category": "Coldest year",
            "Year": extremes.get("coldest_year", "—"),
            "Value": f"{extremes.get('coldest_year_min_temp', '—')} °C",
            "Notable date": _fmt_date(extremes.get("coldest_date")),
        },
        {
            "Category": "Wettest year",
            "Year": extremes.get("wettest_year", "—"),
            "Value": f"{extremes.get('wettest_year_precip', '—')} mm",
            "Notable date": "—",
        },
        {
            "Category": "Driest year",
            "Year": extremes.get("driest_year", "—"),
            "Value": f"{extremes.get('driest_year_precip', '—')} mm",
            "Notable date": "—",
        },
        {
            "Category": "Snowiest year",
            "Year": extremes.get("snowiest_year", "—"),
            "Value": f"{extremes.get('snowiest_year_snowfall', '—')} cm",
            "Notable date": f"{extremes.get('snowiest_year_snow_days', '—')} snow days",
        },
        {
            "Category": "Least snow",
            "Year": extremes.get("least_snow_year", "—"),
            "Value": f"{extremes.get('least_snow_year_snowfall', '—')} cm",
            "Notable date": f"{extremes.get('least_snow_year_snow_days', '—')} snow days",
        },
        {
            "Category": "Most snow days",
            "Year": extremes.get("most_snow_days_year", "—"),
            "Value": f"{extremes.get('most_snow_days_count', '—')} days",
            "Notable date": "—",
        },
    ]

    df_extremes = pd.DataFrame(extremes_rows)
    st.dataframe(
        df_extremes,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Category": st.column_config.TextColumn("Category", width="medium"),
            "Year": st.column_config.NumberColumn("Year", format="%d"),
            "Value": st.column_config.TextColumn("Value"),
            "Notable date": st.column_config.TextColumn("Notable date"),
        },
    )

    # ── SECTION 8: Footer ─────────────────────────────────────

    st.markdown(
        '<div class="wa-footer">'
        'Powered by <a href="https://open-meteo.com" style="color:#0a84ff;'
        'text-decoration:none;">Open-Meteo</a> Historical Weather API'
        " &nbsp;·&nbsp; ERA5 reanalysis &nbsp;·&nbsp; No API key required"
        f" &nbsp;·&nbsp; {n_years} years of data ({start_yr}–{end_yr})"
        "</div>",
        unsafe_allow_html=True,
    )


main()
