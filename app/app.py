# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
app.py — Streamlit weather dashboard with Apple-inspired dark UI.

Run with: streamlit run app/app.py
Requires: pip install -e ".[ui]"
"""

import sys
from pathlib import Path

# Ensure the src/ package is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

from weather_alert.geocode import geocode
from weather_alert.weather import fetch_forecast, fetch_daily_forecast
from weather_alert.rules import evaluate_rules


# ─────────────────────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Weather",
    page_icon="🌤",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────
# CSS injection
# ─────────────────────────────────────────────────────────────

CUSTOM_CSS = """
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

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

WEATHERCODE_LABELS: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Rain showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
              color="#8e8e93", size=12),
    margin=dict(l=8, r=8, t=32, b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8e8e93")),
    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#636366")),
    yaxis=dict(gridcolor="#2c2c2e", zeroline=False, tickfont=dict(color="#636366")),
)


def weathercode_label(code: int | None) -> str:
    """Return a human-readable label for an Open-Meteo weather code."""
    if code is None:
        return "Unknown"
    return WEATHERCODE_LABELS.get(int(code), f"Code {code}")


def fmt_day(date_str: str, today_str: str) -> tuple[str, bool]:
    """Format a date string as 'Mon 24 Feb'; also return True if it's today."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    is_today = date_str == today_str
    label = "Today" if is_today else dt.strftime("%a %d %b")
    return label, is_today


def stat_html(label: str, value: str, unit: str = "") -> str:
    """Render a stat pill as HTML."""
    return f"""
    <div class="stat-pill">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}<span class="stat-unit"> {unit}</span></div>
    </div>
    """


# ─────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────

if "location" not in st.session_state:
    st.session_state.location = None   # resolved {latitude, longitude, name}
if "hourly" not in st.session_state:
    st.session_state.hourly = None     # current-hour forecast list
if "daily" not in st.session_state:
    st.session_state.daily = None      # daily forecast list
if "error" not in st.session_state:
    st.session_state.error = None
if "forecast_days" not in st.session_state:
    st.session_state.forecast_days = 7


def fetch_all(place: str, days: int) -> None:
    """Geocode the place and fetch both hourly and daily forecasts."""
    st.session_state.error = None
    try:
        loc = geocode(place)
    except SystemExit:
        st.session_state.error = f'Location "{place}" not found. Try a more specific name.'
        st.session_state.location = None
        return
    except RuntimeError as e:
        st.session_state.error = f"Network error: {e}"
        return

    st.session_state.location = loc

    try:
        st.session_state.hourly = fetch_forecast(
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            forecast_hours=4,
        )
        st.session_state.daily = fetch_daily_forecast(
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            forecast_days=days,
        )
    except RuntimeError as e:
        st.session_state.error = f"Weather API error: {e}"
        st.session_state.hourly = None
        st.session_state.daily = None


# ─────────────────────────────────────────────────────────────
# SECTION 1: Search
# ─────────────────────────────────────────────────────────────

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    location_input = st.text_input(
        label="location",
        placeholder="Enter a location",
        label_visibility="collapsed",
        key="location_input",
    )
    btn_col, _ = st.columns([1, 2])
    with btn_col:
        get_weather = st.button("Get Weather", use_container_width=True)

    if get_weather and location_input.strip():
        fetch_all(location_input.strip(), st.session_state.forecast_days)

    if st.session_state.location:
        loc = st.session_state.location
        st.markdown(
            f'<div class="location-resolved">'
            f'📍 {loc["name"]} &nbsp;·&nbsp; '
            f'{loc["latitude"]:.4f}°, {loc["longitude"]:.4f}°'
            f'</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.error:
        st.markdown(
            f'<div class="error-card">⚠️ {st.session_state.error}</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# SECTION 2: Current conditions hero
# ─────────────────────────────────────────────────────────────

if st.session_state.hourly and not st.session_state.error:
    current = st.session_state.hourly[0]
    loc = st.session_state.location

    # Evaluate alerts against a minimal config
    mock_config = {
        "alerts": {
            "rain_probability_threshold": 50,
            "wind_speed_threshold": 30,
            "feels_like_min": 2,
            "lookahead_hours": 3,
        }
    }
    # Try to load real config; fall back to mock
    try:
        from weather_alert.config import load_config
        config = load_config()
    except Exception:
        config = mock_config

    alerts = evaluate_rules(st.session_state.hourly, config)

    temp = current.get("temperature", "—")
    feels = current.get("feels_like", "—")
    humidity = current.get("humidity", "—")
    wind_speed = current.get("wind_speed", "—")
    wind_dir = current.get("wind_direction", "")
    precip = current.get("precipitation_probability", 0) or 0
    snow_depth = current.get("snow_depth", 0) or 0
    code = current.get("weathercode")

    try:
        dt = datetime.strptime(current["time"], "%Y-%m-%dT%H:%M")
        time_str = dt.strftime("%A, %d %B · %H:%M")
    except (ValueError, KeyError):
        time_str = current.get("time", "")

    st.markdown('<div class="wa-card">', unsafe_allow_html=True)

    hero_left, hero_right = st.columns([1, 1])

    with hero_left:
        st.markdown(
            f'<div class="hero-temp">{temp}°</div>'
            f'<div class="hero-feels">Feels like {feels}°C</div>',
            unsafe_allow_html=True,
        )

    with hero_right:
        pill_cols = st.columns(2)
        stats = [
            ("Humidity", f"{humidity}", "%"),
            ("Rain chance", f"{precip}", "%"),
            (f"Wind · {wind_dir}", f"{wind_speed}", "km/h"),
        ]
        if snow_depth > 0:
            stats.append(("Snow depth", f"{snow_depth}", "cm"))
        else:
            stats.append(("Condition", weathercode_label(code), ""))

        for i, (label, val, unit) in enumerate(stats):
            with pill_cols[i % 2]:
                st.markdown(stat_html(label, val, unit), unsafe_allow_html=True)

    st.markdown(
        f'<div class="condition-line">'
        f'{weathercode_label(code)} &nbsp;·&nbsp; {loc["name"]} &nbsp;·&nbsp; {time_str}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if alerts:
        alerts_text = " &nbsp;·&nbsp; ".join(
            a.split(":")[0] if ":" in a else a for a in alerts
        )
        st.markdown(
            f'<div class="alert-pill">⚠️ {alerts_text}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SECTION 3 + 4 + 5: Forecast
# ─────────────────────────────────────────────────────────────

if st.session_state.daily and not st.session_state.error:
    daily = st.session_state.daily

    # ── Forecast window selector
    st.markdown('<div class="section-label">Forecast</div>', unsafe_allow_html=True)

    window_options = {"1 day": 1, "3 days": 3, "7 days": 7, "16 days": 16}
    selected_label = st.radio(
        label="Forecast window",
        options=list(window_options.keys()),
        index=2,
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_days = window_options[selected_label]

    # Re-fetch if window changed
    if selected_days != st.session_state.forecast_days and st.session_state.location:
        st.session_state.forecast_days = selected_days
        loc = st.session_state.location
        try:
            st.session_state.daily = fetch_daily_forecast(
                latitude=loc["latitude"],
                longitude=loc["longitude"],
                forecast_days=selected_days,
            )
            daily = st.session_state.daily
        except RuntimeError:
            pass

    display_days = daily[:selected_days]
    today_str = datetime.now().strftime("%Y-%m-%d")
    has_snow = any(d["snowfall_cm"] > 0 or d["snow_depth_cm"] > 0 for d in display_days)

    # ── Forecast table
    st.markdown('<div class="wa-card">', unsafe_allow_html=True)

    snow_cols = '<th>Snow (cm)</th><th>Depth (cm)</th>' if has_snow else ""
    table_html = f"""
    <table class="wa-table">
      <thead>
        <tr>
          <th>Day</th>
          <th>Max °C</th>
          <th>Min °C</th>
          <th>Rain %</th>
          {snow_cols}
          <th>Wind km/h</th>
        </tr>
      </thead>
      <tbody>
    """
    for d in display_days:
        label, is_today = fmt_day(d["date"], today_str)
        row_class = "today" if is_today else ""
        snow_cells = ""
        if has_snow:
            snow_cells = f'<td>{d["snowfall_cm"]:.1f}</td><td>{d["snow_depth_cm"]:.1f}</td>'
        table_html += f"""
        <tr class="{row_class}">
          <td>{label}</td>
          <td>{d["temp_max"]:.1f}°</td>
          <td>{d["temp_min"]:.1f}°</td>
          <td>{d["rain_probability"]}%</td>
          {snow_cells}
          <td>{d["wind_max"]:.0f} {d["wind_direction"]}</td>
        </tr>
        """
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Charts (only if > 1 day)
    if selected_days > 1:
        dates = [d["date"] for d in display_days]
        date_labels = [fmt_day(d, today_str)[0] for d in dates]
        temp_max = [d["temp_max"] for d in display_days]
        temp_min = [d["temp_min"] for d in display_days]
        rain_pct = [d["rain_probability"] for d in display_days]
        snowfall  = [d["snowfall_cm"] for d in display_days]

        # Layout: side by side if > 3 days, stacked otherwise
        if selected_days > 3:
            chart_cols = st.columns(2)
        else:
            chart_cols = [st.container(), st.container()]

        # Chart 1: Temperature range
        with chart_cols[0]:
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=date_labels, y=temp_max,
                name="Max",
                mode="lines",
                line=dict(color="#0a84ff", width=2),
                fill="tonexty",
                fillcolor="rgba(10,132,255,0.08)",
            ))
            fig_temp.add_trace(go.Scatter(
                x=date_labels, y=temp_min,
                name="Min",
                mode="lines",
                line=dict(color="#0a84ff", width=1, dash="dot"),
                fill="tozeroy",
                fillcolor="rgba(10,132,255,0.04)",
            ))
            fig_temp.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Temperature Range (°C)", font=dict(color="#8e8e93", size=13)),
                yaxis=dict(**PLOTLY_LAYOUT["yaxis"], ticksuffix="°"),
                height=280,
            )
            st.plotly_chart(fig_temp, use_container_width=True, config={"displayModeBar": False})

        # Chart 2: Precipitation + Snow
        with chart_cols[1]:
            fig_precip = go.Figure()
            fig_precip.add_trace(go.Bar(
                x=date_labels, y=rain_pct,
                name="Rain %",
                marker_color="rgba(10,132,255,0.6)",
                marker_line_width=0,
            ))
            if any(s > 0 for s in snowfall):
                fig_precip.add_trace(go.Scatter(
                    x=date_labels, y=snowfall,
                    name="Snow cm",
                    mode="lines+markers",
                    line=dict(color="#ffffff", width=2),
                    marker=dict(color="#ffffff", size=5),
                    yaxis="y2",
                ))
                fig_precip.update_layout(
                    yaxis2=dict(
                        overlaying="y", side="right",
                        showgrid=False, zeroline=False,
                        tickfont=dict(color="#636366"),
                        ticksuffix=" cm",
                    )
                )
            fig_precip.update_layout(
                **PLOTLY_LAYOUT,
                title=dict(text="Precipitation & Snow", font=dict(color="#8e8e93", size=13)),
                yaxis=dict(**PLOTLY_LAYOUT["yaxis"], ticksuffix="%", range=[0, 100]),
                barmode="group",
                height=280,
            )
            st.plotly_chart(fig_precip, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────

st.markdown(
    '<div class="wa-footer">'
    'Powered by <a href="https://open-meteo.com" style="color:#0a84ff;text-decoration:none;">Open-Meteo</a>'
    ' &nbsp;·&nbsp; No API key required &nbsp;·&nbsp; Data updates every hour'
    '</div>',
    unsafe_allow_html=True,
)
