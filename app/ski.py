# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
ski.py — Streamlit Ski Season Intelligence dashboard with Apple-inspired dark UI.

Run with:
    streamlit run app/ski.py
    streamlit run app/ski.py -- --location "Soldeu, Andorra"

Requires: pip install -e ".[ui]"
Data source: ERA5 reanalysis via Open-Meteo Historical Weather API (free, no key).
"""

import sys
from pathlib import Path

# Ensure the src/ package is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from collections import defaultdict
from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

from weather_alert.geocode import LocationNotFoundError, geocode
from weather_alert.ski import (
    RATING_STARS,
    best_weeks_to_ski,
    fetch_ski_data,
    get_current_season_data,
    historical_seasons,
    predict_current_season,
    rate_season,
)


# ─────────────────────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Ski Season Intelligence",
    page_icon="🎿",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────
# CSS (Apple-inspired dark theme — same as history.py)
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
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: #f5f5f7;
    line-height: 1.3;
  }
  .stat-unit {
    font-size: 0.9rem;
    color: #8e8e93;
    font-weight: 400;
  }

  /* ── Similar season cards ── */
  .season-card {
    background: #1c1c1e;
    border: 1px solid #2c2c2e;
    border-radius: 12px;
    padding: 20px 22px;
    height: 100%;
  }
  .season-card-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #f5f5f7;
    margin-bottom: 4px;
  }
  .season-card-rating {
    font-size: 0.95rem;
    color: #8e8e93;
    margin-bottom: 12px;
  }
  .season-card-row {
    font-size: 0.88rem;
    color: #8e8e93;
    padding: 4px 0;
    border-bottom: 1px solid #2c2c2e;
  }
  .season-card-row:last-child { border-bottom: none; }
  .season-card-val { color: #f5f5f7; font-weight: 500; float: right; }

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

  /* ── Section heading ── */
  .section-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #636366;
    font-weight: 600;
    margin-bottom: 0.75rem;
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
# Plotly base layout
# ─────────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
        color="#8e8e93",
        size=12,
    ),
    margin=dict(l=8, r=8, t=40, b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8e8e93")),
    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#636366")),
    yaxis=dict(gridcolor="#2c2c2e", zeroline=False, tickfont=dict(color="#636366")),
)

RATING_COLORS = {
    "EXCEPTIONAL": "#0a84ff",
    "EXCELLENT": "#30d158",
    "GOOD": "#ffd60a",
    "AVERAGE": "#636366",
    "POOR": "#ff453a",
}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def stat_html(label: str, value: str, unit: str = "") -> str:
    return f"""
    <div class="stat-pill">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}<span class="stat-unit"> {unit}</span></div>
    </div>
    """


def _fmt_date(d: date | None) -> str:
    if d is None:
        return "—"
    return f"{d.day} {d.strftime('%b %Y')}"


# ─────────────────────────────────────────────────────────────
# CLI arg parsing (for streamlit run app/ski.py -- --location X)
# ─────────────────────────────────────────────────────────────


def _parse_cli_args() -> str | None:
    """Return --location value if passed via CLI, else None."""
    try:
        idx = sys.argv.index("--")
        raw = sys.argv[idx + 1 :]
    except ValueError:
        return None
    p = argparse.ArgumentParser()
    p.add_argument("--location", default=None)
    args, _ = p.parse_known_args(raw)
    return args.location


# ─────────────────────────────────────────────────────────────
# Data loading (cached)
# ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=86400)
def load_ski_data(location: str) -> dict:
    """Geocode, fetch data, run all ski analyses. Cached for 24 hours."""
    try:
        loc = geocode(location)
    except LocationNotFoundError as e:
        return {"error": str(e)}
    except RuntimeError as e:
        return {"error": str(e)}

    try:
        records = fetch_ski_data(loc["latitude"], loc["longitude"], years=51)
    except RuntimeError as e:
        return {"error": str(e)}

    seasons = historical_seasons(records)
    if not seasons:
        return {"error": "No complete historical ski seasons found for this location."}

    for s in seasons:
        s["rating"] = rate_season(s, seasons)

    current_data = get_current_season_data(records)
    prediction = predict_current_season(current_data, seasons)
    best_weeks = best_weeks_to_ski(seasons)

    today = date.today()
    current_year = today.year if today.month >= 10 else today.year - 1

    # Build historical avg + min/max depth by day-of-year offset (for the tracker chart)
    from weather_alert.ski import day_offset  # noqa: PLC0415
    depth_by_offset: dict[int, list[float]] = defaultdict(list)
    for season in seasons:
        sy = season["season_year"]
        for r in season["records"]:
            off = day_offset(r["date"], sy)
            depth_by_offset[off].append(r["snow_depth_max"])

    # Monthly avg snowfall (historical) for months Nov–Apr
    monthly_hist: dict[int, list[float]] = defaultdict(list)
    for season in seasons:
        monthly_snow: dict[int, float] = defaultdict(float)
        for r in season["records"]:
            if r["date"].month in (11, 12, 1, 2, 3, 4):
                monthly_snow[r["date"].month] += r["snowfall"]
        for m, sf in monthly_snow.items():
            monthly_hist[m].append(sf)

    monthly_hist_avg = {m: sum(v) / len(v) for m, v in monthly_hist.items()}

    # Monthly snowfall for current season
    monthly_current: dict[int, float] = defaultdict(float)
    for r in current_data:
        if r["date"].month in (10, 11, 12, 1, 2, 3, 4):
            monthly_current[r["date"].month] += r["snowfall"]

    # Build week × year heatmap matrix
    from weather_alert.ski import ski_season_week  # noqa: PLC0415
    week_year_matrix: dict[tuple[int, int], float] = {}
    season_years = sorted({s["season_year"] for s in seasons})
    for season in seasons:
        sy = season["season_year"]
        week_depths: dict[int, list[float]] = defaultdict(list)
        for r in season["records"]:
            wn = ski_season_week(r["date"], sy)
            if wn is not None and wn <= 25:
                week_depths[wn].append(r["snow_depth_max"])
        for wn, depths in week_depths.items():
            week_year_matrix[(sy, wn)] = sum(depths) / len(depths)

    return {
        "error": None,
        "loc": loc,
        "seasons": seasons,
        "current_data": current_data,
        "prediction": prediction,
        "best_weeks": best_weeks,
        "current_year": current_year,
        "depth_by_offset": dict(depth_by_offset),
        "monthly_hist_avg": monthly_hist_avg,
        "monthly_current": dict(monthly_current),
        "week_year_matrix": week_year_matrix,
        "season_years": season_years,
    }


# ─────────────────────────────────────────────────────────────
# Main dashboard
# ─────────────────────────────────────────────────────────────


def main() -> None:
    cli_location = _parse_cli_args()

    # ── Location Input ────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1, 3, 1])
    with col_c:
        location_input = st.text_input(
            "Mountain location",
            value=cli_location or "",
            placeholder="Soldeu, Andorra · Verbier, Switzerland · Niseko, Japan",
            label_visibility="collapsed",
        )
        analyse = st.button("🎿 Analyse Season", use_container_width=True)

    if not location_input and not cli_location:
        st.markdown(
            "<div style='text-align:center;color:#48484a;padding:4rem 0'>"
            "Enter a mountain resort to get started.</div>",
            unsafe_allow_html=True,
        )
        return

    query = location_input if location_input else cli_location

    # ── Load data ─────────────────────────────────────────────
    with st.spinner(f"Fetching 50 years of snow data for {query}…"):
        data = load_ski_data(query)

    if data.get("error"):
        st.markdown(
            f'<div class="error-card">⚠️ {data["error"]}</div>',
            unsafe_allow_html=True,
        )
        return

    loc = data["loc"]
    seasons = data["seasons"]
    prediction = data["prediction"]
    best_weeks = data["best_weeks"]
    current_data = data["current_data"]
    current_year = data["current_year"]
    season_label = f"{current_year}-{str(current_year + 1)[-2:]}"

    # ── Page Header ───────────────────────────────────────────
    st.markdown(
        f"<h1 style='text-align:center;font-size:2.4rem;font-weight:700;"
        f"letter-spacing:-0.04em;margin-bottom:0'>🎿 {loc['name']}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center;color:#8e8e93;font-size:1rem;"
        f"margin-top:4px;margin-bottom:2rem'>"
        f"Ski Season Intelligence · 50-year Analysis · {season_label}</p>",
        unsafe_allow_html=True,
    )

    # ── 4 Stat Cards ─────────────────────────────────────────
    rating = prediction["predicted_rating"]
    stars = RATING_STARS.get(rating, "")
    snowpack = round(prediction["current_snowpack"])
    hist_avg = round(prediction["historical_avg_snowpack"])
    vs_avg = round(prediction["snowpack_vs_avg"])
    arrow = "↑" if vs_avg >= 0 else "↓"

    best_week_label = best_weeks[0]["week_label"] if best_weeks else "—"
    best_s = max(seasons, key=lambda s: s["total_snowfall"])
    best_season_label = f"{best_s['season_label']}"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            stat_html("Season Outlook", f"{stars}", rating),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            stat_html(
                "Current Snowpack",
                f"{snowpack}cm",
                f"{arrow}{abs(vs_avg)}% vs avg",
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            stat_html("Best Week to Ski", best_week_label),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            stat_html("Best Season on Record", best_season_label),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 1: Current Season Tracker ────────────────────
    st.markdown(
        '<div class="section-label">Current Season Snowpack vs Historical Average</div>',
        unsafe_allow_html=True,
    )

    depth_by_offset = data["depth_by_offset"]
    if current_data:
        from weather_alert.ski import day_offset  # noqa: PLC0415
        cur_offsets = sorted(
            day_offset(r["date"], current_year) for r in current_data
        )
        cur_depths = {
            day_offset(r["date"], current_year): r["snow_depth_max"]
            for r in current_data
        }
        x_dates = [
            date(current_year, 10, 1) + timedelta(days=o) for o in cur_offsets
        ]
        y_current = [cur_depths[o] for o in cur_offsets]
        y_avg = [
            sum(depth_by_offset.get(o, [0])) / max(len(depth_by_offset.get(o, [0])), 1)
            for o in cur_offsets
        ]
        y_min = [min(depth_by_offset.get(o, [0])) for o in cur_offsets]
        y_max = [max(depth_by_offset.get(o, [0])) for o in cur_offsets]

        fig1 = go.Figure()
        fig1.add_trace(
            go.Scatter(
                x=x_dates + x_dates[::-1],
                y=y_max + y_min[::-1],
                fill="toself",
                fillcolor="rgba(255,255,255,0.04)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Hist. range",
                showlegend=True,
            )
        )
        fig1.add_trace(
            go.Scatter(
                x=x_dates,
                y=y_avg,
                line=dict(color="#ffffff", dash="dash", width=1.5),
                name="Historical avg",
            )
        )
        fig1.add_trace(
            go.Scatter(
                x=x_dates,
                y=y_current,
                line=dict(color="#0a84ff", width=2.5),
                name="This season",
            )
        )
        layout1 = {**PLOTLY_LAYOUT}
        layout1["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "title": "Snow Depth (cm)"}
        fig1.update_layout(**layout1)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Current season data will appear once the season begins (Oct 1).")

    # ── Section 2: Season Rating History ─────────────────────
    st.markdown(
        '<div class="section-label">Historical Season Ratings</div>',
        unsafe_allow_html=True,
    )

    season_labels_all = [s["season_label"] for s in seasons]
    snowfalls_all = [s["total_snowfall"] for s in seasons]
    bar_colors = [RATING_COLORS.get(s.get("rating", "AVERAGE"), "#636366") for s in seasons]

    fig2 = go.Figure(
        go.Bar(
            x=season_labels_all,
            y=snowfalls_all,
            marker_color=bar_colors,
            hovertemplate=(
                "<b>%{x}</b><br>Total snowfall: %{y:.0f}cm<extra></extra>"
            ),
        )
    )
    layout2 = {**PLOTLY_LAYOUT}
    layout2["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "title": "Total Snowfall (cm)"}
    layout2["xaxis"] = {**PLOTLY_LAYOUT["xaxis"], "tickangle": -45, "tickfont": dict(size=9, color="#636366")}
    layout2["showlegend"] = False
    fig2.update_layout(**layout2)
    st.plotly_chart(fig2, use_container_width=True)

    # ── Section 3: Best Weeks ────────────────────────────────
    st.markdown(
        '<div class="section-label">Best Weeks to Ski</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2)

    with col_left:
        # Horizontal bar chart — all weeks, top 5 highlighted
        week_year_matrix = data["week_year_matrix"]
        season_years_list = data["season_years"]

        # Build all-weeks list for horizontal bar
        from weather_alert.ski import week_label  # noqa: PLC0415
        from collections import defaultdict as _dd

        all_week_depths: dict[int, list[float]] = _dd(list)
        for season in seasons:
            from weather_alert.ski import ski_season_week  # noqa: PLC0415
            for r in season["records"]:
                wn = ski_season_week(r["date"], season["season_year"])
                if wn is not None and wn <= 25:
                    all_week_depths[wn].append(r["snow_depth_max"])

        all_weeks_sorted = sorted(
            [
                {
                    "wn": wn,
                    "label": week_label(wn),
                    "avg": sum(v) / len(v) if v else 0,
                }
                for wn, v in all_week_depths.items()
            ],
            key=lambda w: w["avg"],
        )

        top5_wns = {w["week_num"] for w in best_weeks}
        bar_x = [w["avg"] for w in all_weeks_sorted]
        bar_y = [w["label"] for w in all_weeks_sorted]
        bar_colors_h = [
            "#0a84ff" if w["wn"] in top5_wns else "#2c2c2e"
            for w in all_weeks_sorted
        ]

        fig3a = go.Figure(
            go.Bar(
                x=bar_x,
                y=bar_y,
                orientation="h",
                marker_color=bar_colors_h,
                hovertemplate="%{y}: %{x:.0f}cm avg<extra></extra>",
            )
        )
        layout3a = {**PLOTLY_LAYOUT}
        layout3a["xaxis"] = {**PLOTLY_LAYOUT["xaxis"], "title": "Avg Snow Depth (cm)"}
        layout3a["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "tickfont": dict(size=9, color="#636366")}
        layout3a["title"] = dict(text="Average Snow Depth by Week", font=dict(color="#f5f5f7", size=13))
        layout3a["showlegend"] = False
        layout3a["height"] = 500
        fig3a.update_layout(**layout3a)
        st.plotly_chart(fig3a, use_container_width=True)

    with col_right:
        # Heatmap — week × year
        all_wns = sorted(all_week_depths.keys())
        z_matrix = []
        y_labels_hm = []
        for sy in season_years_list:
            row = [week_year_matrix.get((sy, wn), 0.0) for wn in all_wns]
            z_matrix.append(row)
            y_labels_hm.append(str(sy))

        x_labels_hm = [week_label(wn) for wn in all_wns]

        fig3b = go.Figure(
            go.Heatmap(
                z=z_matrix,
                x=x_labels_hm,
                y=y_labels_hm,
                colorscale=[
                    [0, "#1c1c1e"],
                    [0.3, "#0a2a5c"],
                    [0.6, "#0a54c8"],
                    [1.0, "#0a84ff"],
                ],
                hovertemplate="%{y} · %{x}: %{z:.0f}cm<extra></extra>",
                showscale=False,
            )
        )
        layout3b = {**PLOTLY_LAYOUT}
        layout3b["title"] = dict(
            text="Snow Depth Heatmap (Week × Year)",
            font=dict(color="#f5f5f7", size=13),
        )
        layout3b["xaxis"] = {
            **PLOTLY_LAYOUT["xaxis"],
            "tickangle": -45,
            "tickfont": dict(size=8, color="#636366"),
        }
        layout3b["yaxis"] = {
            **PLOTLY_LAYOUT["yaxis"],
            "tickfont": dict(size=9, color="#636366"),
        }
        layout3b["height"] = 500
        fig3b.update_layout(**layout3b)
        st.plotly_chart(fig3b, use_container_width=True)

    # ── Section 4: Similar Past Seasons ──────────────────────
    similar_labels = prediction.get("similar_seasons", [])
    if similar_labels:
        st.markdown(
            '<div class="section-label">Similar Past Seasons</div>',
            unsafe_allow_html=True,
        )
        season_by_label = {s["season_label"]: s for s in seasons}
        cols = st.columns(min(len(similar_labels), 3))
        for i, lbl in enumerate(similar_labels[:3]):
            s = season_by_label.get(lbl)
            if not s:
                continue
            r = s.get("rating", "—")
            stars_s = RATING_STARS.get(r, "")
            peak_start = _fmt_date(s.get("peak_window_start"))
            peak_end = _fmt_date(s.get("peak_window_end"))
            peak = f"{peak_start} – {peak_end}" if s.get("peak_window_start") else "—"

            with cols[i]:
                st.markdown(
                    f"""
                    <div class="season-card">
                      <div class="season-card-title">{lbl}</div>
                      <div class="season-card-rating">{stars_s} {r}</div>
                      <div class="season-card-row">
                        Total snowfall <span class="season-card-val">{round(s['total_snowfall'])}cm</span>
                      </div>
                      <div class="season-card-row">
                        Powder days <span class="season-card-val">{s['powder_days']}</span>
                      </div>
                      <div class="season-card-row">
                        Peak depth <span class="season-card-val">{round(s['peak_snow_depth'])}cm</span>
                      </div>
                      <div class="season-card-row">
                        Peak window <span class="season-card-val" style="font-size:0.8rem">{peak}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 5: Monthly Snow Profile ──────────────────────
    st.markdown(
        '<div class="section-label">Monthly Snowfall Profile (Historical vs This Season)</div>',
        unsafe_allow_html=True,
    )

    month_order = [11, 12, 1, 2, 3, 4]
    month_names = {11: "Nov", 12: "Dec", 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr"}
    monthly_hist_avg = data["monthly_hist_avg"]
    monthly_current = data["monthly_current"]

    x_months = [month_names[m] for m in month_order]
    y_hist = [monthly_hist_avg.get(m, 0.0) for m in month_order]
    y_curr = [monthly_current.get(m, 0.0) for m in month_order]

    fig5 = go.Figure()
    fig5.add_trace(
        go.Bar(
            x=x_months,
            y=y_hist,
            name="Historical avg",
            marker_color="#2c2c2e",
            hovertemplate="%{x}: %{y:.0f}cm<extra>Historical avg</extra>",
        )
    )
    fig5.add_trace(
        go.Scatter(
            x=x_months,
            y=y_curr,
            name="This season",
            line=dict(color="#0a84ff", width=2.5),
            mode="lines+markers",
            marker=dict(size=7),
            hovertemplate="%{x}: %{y:.0f}cm<extra>This season</extra>",
        )
    )
    layout5 = {**PLOTLY_LAYOUT}
    layout5["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "title": "Snowfall (cm)"}
    layout5["legend"] = {**PLOTLY_LAYOUT["legend"], "orientation": "h", "y": 1.1}
    fig5.update_layout(**layout5)
    st.plotly_chart(fig5, use_container_width=True)

    # ── Footer ────────────────────────────────────────────────
    st.markdown(
        '<div class="wa-footer">'
        "Predictions based on pattern matching against 50 years of ERA5 reanalysis data"
        " · Open-Meteo Historical API · Not a guarantee"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
else:
    main()
