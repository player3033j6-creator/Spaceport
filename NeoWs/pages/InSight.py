import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import math
import time
from datetime import datetime

st.set_page_config(
    page_title="Spaceport | InSight",
    page_icon="🔴",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');

html, body, [class*="css"]          { background-color: #0d0500 !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"]           { background:#120800 !important; border-right:1px solid #2d1a0a; }
[data-testid="stSidebar"] *         { color:#e2e8f0 !important; }
[data-testid="stTabs"] button       { color:#64748b !important; font-family:'Space Mono',monospace !important; font-size:11px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#f97316 !important; border-bottom-color:#f97316 !important; }
[data-testid="metric-container"]    { background:#1a0c04; border:1px solid #2d1a0a; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#78350f !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
h1,h2,h3                            { color:#e2e8f0 !important; }
div[data-baseweb="select"] > div    { background:#1a0c04 !important; border-color:#2d1a0a !important; }
.stTextInput input                  { background:#1a0c04 !important; border:1px solid #2d1a0a !important; color:#e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑  Constants
# ══════════════════════════════════════════════════════════════════════════════
API_KEY      = "Dgv4uu9ydStNaBYdobvRbec55i03X4i8hMwd1U8A"
INSIGHT_URL  = "https://api.nasa.gov/insight_weather/"
ACCENT       = "#f97316"   # Mars orange
COL2         = "#ef4444"   # red
COL3         = "#fbbf24"   # amber
COL4         = "#60a5fa"   # blue (pressure)
COL5         = "#34d399"   # green (wind)

# Mars facts
MARS_DAY_HRS  = 24.6597   # hours in a Sol
MARS_YEAR_SOL = 668.6     # Sols in a Mars year
ELYSIUM_LAT   = 4.5       # InSight landing latitude
ELYSIUM_LON   = 135.9     # InSight landing longitude

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Data fetching
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=1800)
def fetch_insight() -> dict:
    """Fetch InSight Mars weather data from NASA API."""
    r = requests.get(
        INSIGHT_URL,
        params={"api_key": API_KEY, "feedtype": "json", "ver": "1.0"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def parse_sols(raw: dict) -> list[dict]:
    """Parse raw API response into a list of Sol dicts, newest first."""
    sol_keys = raw.get("sol_keys", [])
    sols = []
    for sk in sol_keys:
        sol_data = raw.get(sk, {})
        if not sol_data:
            continue

        at  = sol_data.get("AT",  {})   # Atmospheric Temperature (°C)
        hws = sol_data.get("HWS", {})   # Horizontal Wind Speed (m/s)
        pre = sol_data.get("PRE", {})   # Pressure (Pa)
        wd  = sol_data.get("WD",  {})   # Wind Direction

        # Wind direction most common
        wd_most = wd.get("most_common") if isinstance(wd, dict) else None
        wind_dir  = wd_most.get("compass_point", "—") if wd_most else "—"
        wind_deg  = wd_most.get("compass_degrees", None) if wd_most else None

        # First/last UTC
        first_utc = sol_data.get("First_UTC", "")
        last_utc  = sol_data.get("Last_UTC",  "")

        # Convert UTC to readable
        def fmt_utc(s):
            try:
                return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").strftime("%b %d %Y  %H:%M")
            except Exception:
                return s[:19] if s else "—"

        # Wind direction histogram (all 16 compass points)
        wd_hist = {}
        if isinstance(wd, dict):
            for k, v in wd.items():
                if k != "most_common" and isinstance(v, dict) and "compass_point" in v:
                    wd_hist[v["compass_point"]] = v.get("ct", 0)

        sols.append({
            "sol":          sk,
            "sol_int":      int(sk),
            # Temp
            "at_av":        at.get("av"),
            "at_mn":        at.get("mn"),
            "at_mx":        at.get("mx"),
            "at_ct":        at.get("ct"),
            # Wind speed
            "hws_av":       hws.get("av"),
            "hws_mn":       hws.get("mn"),
            "hws_mx":       hws.get("mx"),
            "hws_ct":       hws.get("ct"),
            # Pressure
            "pre_av":       pre.get("av"),
            "pre_mn":       pre.get("mn"),
            "pre_mx":       pre.get("mx"),
            "pre_ct":       pre.get("ct"),
            # Wind direction
            "wind_dir":     wind_dir,
            "wind_deg":     wind_deg,
            "wd_hist":      wd_hist,
            # Times
            "first_utc":    fmt_utc(first_utc),
            "last_utc":     fmt_utc(last_utc),
            "first_utc_raw":first_utc,
        })
    return sorted(sols, key=lambda x: x["sol_int"], reverse=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎨  UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#1a0c04;border:1px solid #2d1a0a;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:20px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:20px;color:{color};
      font-weight:700;margin:4px 0">{value}</div>
      <div style="color:#78350f;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#57280a;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def section_hdr(emoji, title, cap=""):
    st.markdown(
        f"<div style='font-size:12px;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:1.5px;color:#78350f;margin:28px 0 6px'>{emoji} {title}</div>",
        unsafe_allow_html=True)
    if cap:
        st.caption(cap)

def fmt(val, decimals=1, unit=""):
    """Format a numeric value safely."""
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}{unit}"
    except Exception:
        return "—"

def temp_bar(mn, av, mx, color=ACCENT):
    """Inline min/avg/max temperature bar."""
    if mn is None or av is None or mx is None:
        return ""
    rng = (mx - mn) or 1
    pct = ((av - mn) / rng) * 100
    return f"""
    <div style="margin-top:6px">
      <div style="display:flex;justify-content:space-between;font-size:9px;
      color:#78350f;font-family:'Space Mono',monospace;margin-bottom:3px">
        <span>{mn:.1f}°</span><span style="color:{color}">{av:.1f}°</span><span>{mx:.1f}°</span>
      </div>
      <div style="background:#2d1a0a;border-radius:4px;height:6px;position:relative">
        <div style="position:absolute;left:{pct-2}%;width:6px;height:6px;
        background:{color};border-radius:50%;top:0"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:8px;
      color:#57280a;margin-top:2px"><span>min</span><span>avg</span><span>max</span></div>
    </div>"""

def compass_arrow(deg, color=COL5):
    """SVG compass arrow."""
    if deg is None:
        return ""
    rad = math.radians(deg)
    cx, cy, r = 24, 24, 18
    tip_x = cx + r * math.sin(rad)
    tip_y = cy - r * math.cos(rad)
    tail_x = cx - (r*0.6) * math.sin(rad)
    tail_y = cy + (r*0.6) * math.cos(rad)
    return f"""
    <svg width="48" height="48" style="display:inline-block;vertical-align:middle">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="#2d1a0a" stroke="#57280a" stroke-width="1"/>
      <line x1="{tail_x:.1f}" y1="{tail_y:.1f}" x2="{tip_x:.1f}" y2="{tip_y:.1f}"
            stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="3" fill="{color}"/>
      <text x="{cx}" y="6" text-anchor="middle" font-size="7"
            fill="#78350f" font-family="Space Mono">N</text>
    </svg>"""

def chart_layout(title="", height=280):
    return dict(
        paper_bgcolor="#0d0500", plot_bgcolor="#1a0c04",
        height=height,
        margin=dict(l=10,r=10,t=30 if title else 10,b=40),
        title=dict(text=title, font=dict(color="#78350f",size=11,family="Space Mono"), x=0.5) if title else {},
        font=dict(family="Space Mono", color="#a16207"),
        xaxis=dict(showgrid=False, color="#78350f",
                   tickfont=dict(family="Space Mono",size=9), zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#2d1a0a", color="#78350f",
                   tickfont=dict(family="Space Mono",size=9), zeroline=False),
        legend=dict(bgcolor="rgba(26,12,4,0.9)",bordercolor="#2d1a0a",borderwidth=1,
                    font=dict(color="#a16207",size=10,family="Space Mono")),
        hoverlabel=dict(bgcolor="#1a0c04",bordercolor="#2d1a0a",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")),
    )

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  HEADER
# ══════════════════════════════════════════════════════════════════════════════
hl, hc, hr = st.columns([0.06, 0.70, 0.24])
with hl:
    st.markdown("""
    <div style="width:52px;height:52px;
    background:radial-gradient(circle,#7c2d12,#1c0a02);
    border:2px solid #f97316;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-family:'Space Mono',monospace;font-size:9px;
    font-weight:700;color:#f97316;letter-spacing:1px;
box-shadow:0 0 20px rgba(249,115,22,.4);margin-top:6px">Spaceport</div>
    """, unsafe_allow_html=True)
with hc:
    st.markdown("## 🔴 InSight: Mars Weather Service")
    st.caption("Daily weather measurements from NASA's InSight lander at Elysium Planitia, Mars · Temperature · Wind · Pressure · Mission: May 2018 – Dec 2022")
with hr:
    st.markdown("""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.3);
      border-radius:20px;padding:4px 12px;font-size:12px;color:#f97316;font-weight:500">
      🔴 Mars Archive</span></div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#2d1a0a;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Fetch data
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner("🔴 Fetching Mars weather data from NASA…"):
    try:
        raw_data = fetch_insight()
        sols     = parse_sols(raw_data)
    except Exception as e:
        err = str(e)
        st.error("🔴 Could not fetch InSight Mars weather data", icon="🚨")
        is_dns  = "resolve" in err.lower() or "name resolution" in err.lower()
        is_http = "http" in err.lower()
        if is_dns:
            st.warning("🔌 Network error — check your internet connection.")
        elif is_http:
            st.warning(f"⚠️ API error — the NASA InSight endpoint returned an error.")
        else:
            st.warning("⚠️ Unknown error — see details below.")
        with st.expander("🔍 Technical details"):
            st.code(err, language=None)
        if st.button("🔄 Retry", type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

if not sols:
    st.warning("⚠️ No Sol data available. The InSight mission ended in December 2022 — the API returns the last archived Sols.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔴 InSight Controls")

    # Sol selector
    sol_labels  = [f"Sol {s['sol']}  ({s['first_utc'][:12]})" for s in sols]
    sel_sol_idx = st.selectbox("🪐 Select Sol", range(len(sols)),
                                format_func=lambda i: sol_labels[i], index=0)
    sel_sol = sols[sel_sol_idx]

    st.markdown("---")

    # Temperature unit
    temp_unit = st.radio("🌡️ Temperature unit", ["°C Celsius", "°F Fahrenheit", "K Kelvin"],
                          index=0)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#57280a;line-height:2">
    <b style="color:#78350f">🔴 About InSight</b><br>
    🚀 Launch: May 5, 2018<br>
    🛬 Landing: Nov 26, 2018<br>
    📍 Elysium Planitia<br>
    🌡️ Temp · 💨 Wind · 🌀 Pressure<br>
    📡 Mission end: Dec 21, 2022<br>
    🏛️ NASA JPL + Cornell Univ
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data: [NASA InSight API](https://api.nasa.gov/)")

# ── Temperature converter ──────────────────────────────────────────────────────
def convert_temp(c):
    if c is None:
        return None
    if "°F" in temp_unit:
        return c * 9/5 + 32
    elif "K" in temp_unit:
        return c + 273.15
    return c

t_unit = temp_unit.split()[0]   # "°C", "°F", or "K"

# ══════════════════════════════════════════════════════════════════════════════
# 📊  Stat strip (latest Sol)
# ══════════════════════════════════════════════════════════════════════════════
latest = sols[0]
sc1,sc2,sc3,sc4,sc5 = st.columns(5)
stat_card(sc1,"🪐","Latest Sol",        latest["sol"],                              ACCENT)
stat_card(sc2,"🌡️","Avg Temperature",
          fmt(convert_temp(latest["at_av"]),1,t_unit),                              COL2,
          f"{fmt(convert_temp(latest['at_mn']),1)} to {fmt(convert_temp(latest['at_mx']),1)}")
stat_card(sc3,"💨","Avg Wind Speed",    fmt(latest["hws_av"],2," m/s"),             COL5,
          f"max {fmt(latest['hws_mx'],2,' m/s')}")
stat_card(sc4,"🌀","Avg Pressure",      fmt(latest["pre_av"],1," Pa"),              COL4,
          f"{fmt(latest['pre_mn'],1)} – {fmt(latest['pre_mx'],1)} Pa")
stat_card(sc5,"🧭","Wind Direction",    latest["wind_dir"],                         COL3,
          f"{fmt(latest['wind_deg'],1)}°" if latest["wind_deg"] else "")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_dash, tab_temp, tab_wind, tab_pressure, tab_sols, tab_about = st.tabs([
    "🔴  Dashboard",
    "🌡️  Temperature",
    "💨  Wind",
    "🌀  Pressure",
    "📋  All Sols",
    "🚀  Mission Info",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🔴  TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown(f"### 🔴 Sol {sel_sol['sol']} — Mars Weather Report")
    st.caption(f"📅 Earth date: **{sel_sol['first_utc']}** → **{sel_sol['last_utc']}**")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Big weather card ──────────────────────────────────────────────────────
    dc1, dc2, dc3 = st.columns(3)

    # Temperature card
    at_av = convert_temp(sel_sol["at_av"])
    at_mn = convert_temp(sel_sol["at_mn"])
    at_mx = convert_temp(sel_sol["at_mx"])
    bar_html = temp_bar(at_mn, at_av, at_mx, COL2) if all(v is not None for v in [at_mn, at_av, at_mx]) else ""

    dc1.markdown(f"""
    <div style="background:#1a0c04;border:1px solid #2d1a0a;border-top:4px solid {COL2};
    border-radius:14px;padding:22px 20px;text-align:center;min-height:180px">
      <div style="font-size:32px;margin-bottom:6px">🌡️</div>
      <div style="font-size:11px;color:#78350f;text-transform:uppercase;
      letter-spacing:1px;margin-bottom:4px">Atmospheric Temperature</div>
      <div style="font-family:'Orbitron',monospace;font-size:36px;
      color:{COL2};font-weight:900;margin:6px 0">{fmt(at_av,1)}</div>
      <div style="font-size:12px;color:#a16207;font-family:'Space Mono',monospace">{t_unit}</div>
      {bar_html}
    </div>""", unsafe_allow_html=True)

    # Wind card
    compass_svg = compass_arrow(sel_sol["wind_deg"])
    dc2.markdown(f"""
    <div style="background:#1a0c04;border:1px solid #2d1a0a;border-top:4px solid {COL5};
    border-radius:14px;padding:22px 20px;text-align:center;min-height:180px">
      <div style="font-size:32px;margin-bottom:6px">💨</div>
      <div style="font-size:11px;color:#78350f;text-transform:uppercase;
      letter-spacing:1px;margin-bottom:4px">Horizontal Wind Speed</div>
      <div style="font-family:'Orbitron',monospace;font-size:36px;
      color:{COL5};font-weight:900;margin:6px 0">{fmt(sel_sol['hws_av'],2)}</div>
      <div style="font-size:12px;color:#a16207;font-family:'Space Mono',monospace">m/s avg</div>
      <div style="margin-top:10px;display:flex;align-items:center;justify-content:center;gap:10px">
        {compass_svg}
        <div style="text-align:left">
          <div style="font-size:18px;color:{COL3};font-weight:700;
          font-family:'Space Mono',monospace">{sel_sol['wind_dir']}</div>
          <div style="font-size:9px;color:#78350f">most common</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Pressure card
    dc3.markdown(f"""
    <div style="background:#1a0c04;border:1px solid #2d1a0a;border-top:4px solid {COL4};
    border-radius:14px;padding:22px 20px;text-align:center;min-height:180px">
      <div style="font-size:32px;margin-bottom:6px">🌀</div>
      <div style="font-size:11px;color:#78350f;text-transform:uppercase;
      letter-spacing:1px;margin-bottom:4px">Atmospheric Pressure</div>
      <div style="font-family:'Orbitron',monospace;font-size:36px;
      color:{COL4};font-weight:900;margin:6px 0">{fmt(sel_sol['pre_av'],0)}</div>
      <div style="font-size:12px;color:#a16207;font-family:'Space Mono',monospace">Pascal</div>
      <div style="margin-top:10px;font-size:11px;color:#78350f;
      font-family:'Space Mono',monospace;line-height:1.8">
        ↓ Min: {fmt(sel_sol['pre_mn'],1)} Pa<br>↑ Max: {fmt(sel_sol['pre_mx'],1)} Pa
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── All-sols mini sparklines ──────────────────────────────────────────────
    section_hdr("📈","WEEK AT A GLANCE","All available Sols — hover for details")

    sol_nums   = [s["sol_int"] for s in reversed(sols)]
    sol_labels_x = [f"Sol {s['sol']}" for s in reversed(sols)]

    spark1, spark2, spark3 = st.columns(3)

    # Temp sparkline
    at_avgs = [convert_temp(s["at_av"]) for s in reversed(sols)]
    at_mins = [convert_temp(s["at_mn"]) for s in reversed(sols)]
    at_maxs = [convert_temp(s["at_mx"]) for s in reversed(sols)]
    fig_s1 = go.Figure()
    fig_s1.add_trace(go.Scatter(x=sol_labels_x, y=at_maxs, mode="lines", fill=None,
        line=dict(color="rgba(239,68,68,0.3)", width=1), showlegend=False, name="Max"))
    fig_s1.add_trace(go.Scatter(x=sol_labels_x, y=at_mins, mode="lines",
        fill="tonexty", fillcolor="rgba(239,68,68,0.06)",
        line=dict(color="rgba(239,68,68,0.3)", width=1), showlegend=False, name="Min"))
    fig_s1.add_trace(go.Scatter(x=sol_labels_x, y=at_avgs, mode="lines+markers",
        line=dict(color=COL2, width=2.5), marker=dict(size=6, color=COL2),
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.1f}" + t_unit + "<extra></extra>",
        name="Avg Temp"))
    fig_s1.update_layout(**chart_layout(f"🌡️ Temperature ({t_unit})", 220))
    spark1.plotly_chart(fig_s1, use_container_width=True)

    # Wind sparkline
    hws_avgs = [s["hws_av"] for s in reversed(sols)]
    hws_maxs = [s["hws_mx"] for s in reversed(sols)]
    fig_s2 = go.Figure()
    fig_s2.add_trace(go.Bar(x=sol_labels_x, y=hws_maxs,
        marker_color="rgba(52,211,153,0.15)", name="Max", showlegend=False))
    fig_s2.add_trace(go.Scatter(x=sol_labels_x, y=hws_avgs, mode="lines+markers",
        line=dict(color=COL5, width=2.5), marker=dict(size=6, color=COL5),
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.2f} m/s<extra></extra>",
        name="Avg Wind"))
    fig_s2.update_layout(**chart_layout("💨 Wind Speed (m/s)", 220))
    spark2.plotly_chart(fig_s2, use_container_width=True)

    # Pressure sparkline
    pre_avgs = [s["pre_av"] for s in reversed(sols)]
    fig_s3 = go.Figure()
    fig_s3.add_trace(go.Scatter(x=sol_labels_x, y=pre_avgs,
        mode="lines+markers", fill="tozeroy",
        fillcolor="rgba(96,165,250,0.06)",
        line=dict(color=COL4, width=2.5), marker=dict(size=6, color=COL4),
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.1f} Pa<extra></extra>",
        name="Avg Pressure"))
    fig_s3.update_layout(**chart_layout("🌀 Pressure (Pa)", 220))
    spark3.plotly_chart(fig_s3, use_container_width=True)

    # ── Wind rose for selected Sol ────────────────────────────────────────────
    if sel_sol["wd_hist"]:
        section_hdr("🧭","WIND ROSE",f"Wind direction frequency — Sol {sel_sol['sol']}")
        wd_hist = sel_sol["wd_hist"]
        compass_order = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                         "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        r_vals = [wd_hist.get(c, 0) for c in compass_order]
        theta  = [c for c in compass_order]

        fig_rose = go.Figure(go.Barpolar(
            r=r_vals, theta=theta,
            marker=dict(
                color=r_vals,
                colorscale=[[0,"#2d1a0a"],[0.5,"#f97316"],[1,"#fbbf24"]],
                showscale=True,
                colorbar=dict(title="Count", tickfont=dict(family="Space Mono",size=9,color="#a16207"),
                              titlefont=dict(family="Space Mono",size=10,color="#a16207")),
            ),
            hovertemplate="<b>%{theta}</b><br>Count: %{r:,}<extra></extra>",
        ))
        fig_rose.update_layout(
            paper_bgcolor="#0d0500",
            polar=dict(
                bgcolor="#1a0c04",
                radialaxis=dict(showticklabels=True, tickfont=dict(size=8,color="#78350f",family="Space Mono"),
                                gridcolor="#2d1a0a", linecolor="#2d1a0a"),
                angularaxis=dict(tickfont=dict(size=10,color="#a16207",family="Space Mono"),
                                 gridcolor="#2d1a0a", linecolor="#2d1a0a",
                                 direction="clockwise", rotation=90),
            ),
            height=400,
            margin=dict(l=40,r=40,t=20,b=20),
            showlegend=False,
            hoverlabel=dict(bgcolor="#1a0c04",bordercolor="#2d1a0a",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")),
        )
        st.plotly_chart(fig_rose, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🌡️  TAB 2 — TEMPERATURE
# ══════════════════════════════════════════════════════════════════════════════
with tab_temp:
    st.markdown(f"### 🌡️ Temperature Analysis ({t_unit})")
    st.caption("Atmospheric temperature measured ~1m above the Martian surface by the TWINS sensor")

    t1c1, t1c2, t1c3 = st.columns(3)
    # Stats from all sols
    all_at_av = [convert_temp(s["at_av"]) for s in sols if s["at_av"] is not None]
    all_at_mn = [convert_temp(s["at_mn"]) for s in sols if s["at_mn"] is not None]
    all_at_mx = [convert_temp(s["at_mx"]) for s in sols if s["at_mx"] is not None]

    stat_card(t1c1,"❄️","Coldest Min",    fmt(min(all_at_mn),1,t_unit) if all_at_mn else "—", COL4)
    stat_card(t1c2,"🌡️","Mean Average",   fmt(sum(all_at_av)/len(all_at_av),1,t_unit) if all_at_av else "—", COL2)
    stat_card(t1c3,"🔥","Hottest Max",    fmt(max(all_at_mx),1,t_unit) if all_at_mx else "—", ACCENT)
    st.markdown("<br>", unsafe_allow_html=True)

    # Full temperature chart
    section_hdr("📈","TEMPERATURE RANGE PER SOL","")
    sol_x = [f"Sol {s['sol']}" for s in reversed(sols)]
    t_mn  = [convert_temp(s["at_mn"]) for s in reversed(sols)]
    t_av  = [convert_temp(s["at_av"]) for s in reversed(sols)]
    t_mx  = [convert_temp(s["at_mx"]) for s in reversed(sols)]

    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=sol_x, y=t_mx, mode="lines+markers",
        line=dict(color="rgba(239,68,68,0.5)", width=1.5, dash="dot"),
        marker=dict(size=5), name="🔥 Max",
        hovertemplate="<b>%{x}</b><br>Max: %{y:.1f}" + t_unit + "<extra></extra>"))
    fig_temp.add_trace(go.Scatter(
        x=sol_x, y=t_mn, mode="lines+markers",
        fill="tonexty", fillcolor="rgba(239,68,68,0.07)",
        line=dict(color="rgba(96,165,250,0.5)", width=1.5, dash="dot"),
        marker=dict(size=5), name="❄️ Min",
        hovertemplate="<b>%{x}</b><br>Min: %{y:.1f}" + t_unit + "<extra></extra>"))
    fig_temp.add_trace(go.Scatter(
        x=sol_x, y=t_av, mode="lines+markers",
        line=dict(color=COL2, width=3),
        marker=dict(size=8, color=COL2, line=dict(color="#0d0500",width=1.5)),
        name="🌡️ Avg",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.1f}" + t_unit + "<extra></extra>"))
    fig_temp.update_layout(**chart_layout("", 360))
    fig_temp.update_yaxes(title=f"Temperature ({t_unit})")
    st.plotly_chart(fig_temp, use_container_width=True)

    # Diurnal range bar
    section_hdr("📊","DAILY TEMPERATURE RANGE","Max minus Min per Sol")
    ranges = [(convert_temp(s["at_mx"]) or 0) - (convert_temp(s["at_mn"]) or 0)
              for s in reversed(sols)
              if s["at_mx"] is not None and s["at_mn"] is not None]
    fig_rng = go.Figure(go.Bar(
        x=sol_x[:len(ranges)], y=ranges,
        marker=dict(color=ranges,
                    colorscale=[[0,"#2d1a0a"],[0.5,ACCENT],[1,COL2]],
                    showscale=False),
        hovertemplate="<b>%{x}</b><br>Range: %{y:.1f}" + t_unit + "<extra></extra>",
    ))
    fig_rng.update_layout(**chart_layout("", 240))
    fig_rng.update_yaxes(title=f"Range ({t_unit})")
    st.plotly_chart(fig_rng, use_container_width=True)

    # Sensor count
    section_hdr("🔢","SENSOR SAMPLE COUNT","Number of temperature readings per Sol")
    t_cts = [s["at_ct"] for s in reversed(sols) if s["at_ct"] is not None]
    if t_cts:
        fig_ct = go.Figure(go.Bar(
            x=sol_x[:len(t_cts)], y=t_cts,
            marker=dict(color=ACCENT, opacity=0.7),
            hovertemplate="<b>%{x}</b><br>Samples: %{y:,}<extra></extra>",
        ))
        fig_ct.update_layout(**chart_layout("", 200))
        fig_ct.update_yaxes(title="Sample count")
        st.plotly_chart(fig_ct, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 💨  TAB 3 — WIND
# ══════════════════════════════════════════════════════════════════════════════
with tab_wind:
    st.markdown("### 💨 Wind Analysis")
    st.caption("Horizontal wind speed and direction measured by the TWINS anemometer")

    wc1, wc2, wc3 = st.columns(3)
    all_hws_av = [s["hws_av"] for s in sols if s["hws_av"] is not None]
    all_hws_mx = [s["hws_mx"] for s in sols if s["hws_mx"] is not None]
    stat_card(wc1,"🌬️","Lowest Avg",    fmt(min(all_hws_av),2," m/s") if all_hws_av else "—",  COL4)
    stat_card(wc2,"💨","Overall Avg",   fmt(sum(all_hws_av)/len(all_hws_av),2," m/s") if all_hws_av else "—", COL5)
    stat_card(wc3,"🌪️","Peak Gust",    fmt(max(all_hws_mx),2," m/s") if all_hws_mx else "—",  ACCENT)
    st.markdown("<br>", unsafe_allow_html=True)

    section_hdr("📈","WIND SPEED PER SOL","")
    sol_x   = [f"Sol {s['sol']}" for s in reversed(sols)]
    hws_mn_ = [s["hws_mn"] for s in reversed(sols)]
    hws_av_ = [s["hws_av"] for s in reversed(sols)]
    hws_mx_ = [s["hws_mx"] for s in reversed(sols)]

    fig_wind = go.Figure()
    fig_wind.add_trace(go.Scatter(
        x=sol_x, y=hws_mx_, mode="lines",
        fill=None, line=dict(color="rgba(52,211,153,0.3)",width=1),
        name="Max", hovertemplate="Max: %{y:.2f} m/s<extra></extra>"))
    fig_wind.add_trace(go.Scatter(
        x=sol_x, y=hws_mn_, mode="lines",
        fill="tonexty", fillcolor="rgba(52,211,153,0.06)",
        line=dict(color="rgba(52,211,153,0.3)",width=1),
        name="Min", hovertemplate="Min: %{y:.2f} m/s<extra></extra>"))
    fig_wind.add_trace(go.Scatter(
        x=sol_x, y=hws_av_, mode="lines+markers",
        line=dict(color=COL5, width=3),
        marker=dict(size=8, color=COL5, line=dict(color="#0d0500",width=1.5)),
        name="Avg", hovertemplate="<b>%{x}</b><br>Avg: %{y:.2f} m/s<extra></extra>"))
    fig_wind.update_layout(**chart_layout("", 340))
    fig_wind.update_yaxes(title="Wind Speed (m/s)")
    st.plotly_chart(fig_wind, use_container_width=True)

    # Wind direction table
    section_hdr("🧭","WIND DIRECTION PER SOL","")
    dir_rows = []
    for s in sols:
        dir_rows.append({
            "🪐 Sol":           s["sol"],
            "🧭 Direction":      s["wind_dir"],
            "📐 Degrees":        fmt(s["wind_deg"],1,"°"),
            "💨 Avg Speed (m/s)":fmt(s["hws_av"],2),
            "🌪️ Max Speed (m/s)":fmt(s["hws_mx"],2),
            "📅 Earth Date":     s["first_utc"][:12],
        })
    st.dataframe(pd.DataFrame(dir_rows), use_container_width=True, hide_index=True)

    # All wind roses
    section_hdr("🌹","WIND ROSE — ALL SOLS","")
    compass_order = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                     "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    rose_cols = st.columns(min(len(sols), 4))
    for ci, (sol_d, rcol) in enumerate(zip(sols, rose_cols)):
        if not sol_d["wd_hist"]:
            continue
        r_vals = [sol_d["wd_hist"].get(c,0) for c in compass_order]
        fig_r  = go.Figure(go.Barpolar(
            r=r_vals, theta=compass_order,
            marker=dict(color=r_vals,
                        colorscale=[[0,"#2d1a0a"],[1,"#f97316"]]),
            hovertemplate="%{theta}: %{r:,}<extra></extra>",
        ))
        fig_r.update_layout(
            paper_bgcolor="#0d0500",
            polar=dict(bgcolor="#1a0c04",
                       radialaxis=dict(showticklabels=False, gridcolor="#2d1a0a"),
                       angularaxis=dict(tickfont=dict(size=8,color="#a16207",family="Space Mono"),
                                        gridcolor="#2d1a0a", direction="clockwise", rotation=90)),
            height=220, margin=dict(l=10,r=10,t=30,b=10),
            title=dict(text=f"Sol {sol_d['sol']}",
                       font=dict(color="#78350f",size=10,family="Space Mono"),x=0.5),
            showlegend=False,
        )
        rcol.plotly_chart(fig_r, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🌀  TAB 4 — PRESSURE
# ══════════════════════════════════════════════════════════════════════════════
with tab_pressure:
    st.markdown("### 🌀 Atmospheric Pressure")
    st.caption("Pressure measured by the APSS/TWINS sensor — Mars atmosphere is ~160× thinner than Earth's")

    pc1, pc2, pc3 = st.columns(3)
    all_pre_av = [s["pre_av"] for s in sols if s["pre_av"] is not None]
    all_pre_mn = [s["pre_mn"] for s in sols if s["pre_mn"] is not None]
    all_pre_mx = [s["pre_mx"] for s in sols if s["pre_mx"] is not None]

    stat_card(pc1,"⬇️","Lowest Min",     fmt(min(all_pre_mn),1," Pa") if all_pre_mn else "—",  COL4)
    stat_card(pc2,"🌀","Overall Avg",    fmt(sum(all_pre_av)/len(all_pre_av),1," Pa") if all_pre_av else "—", COL4)
    stat_card(pc3,"⬆️","Highest Max",    fmt(max(all_pre_mx),1," Pa") if all_pre_mx else "—",  ACCENT)
    st.markdown("<br>", unsafe_allow_html=True)

    section_hdr("📈","PRESSURE OVER TIME","")
    pre_mn_ = [s["pre_mn"] for s in reversed(sols)]
    pre_av_ = [s["pre_av"] for s in reversed(sols)]
    pre_mx_ = [s["pre_mx"] for s in reversed(sols)]

    fig_pre = go.Figure()
    fig_pre.add_trace(go.Scatter(
        x=sol_x, y=pre_mx_, mode="lines", fill=None,
        line=dict(color="rgba(96,165,250,0.3)",width=1), name="Max",
        hovertemplate="Max: %{y:.1f} Pa<extra></extra>"))
    fig_pre.add_trace(go.Scatter(
        x=sol_x, y=pre_mn_, mode="lines",
        fill="tonexty", fillcolor="rgba(96,165,250,0.06)",
        line=dict(color="rgba(96,165,250,0.3)",width=1), name="Min",
        hovertemplate="Min: %{y:.1f} Pa<extra></extra>"))
    fig_pre.add_trace(go.Scatter(
        x=sol_x, y=pre_av_, mode="lines+markers",
        line=dict(color=COL4, width=3),
        marker=dict(size=8, color=COL4, line=dict(color="#0d0500",width=1.5)),
        name="Avg",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.1f} Pa<extra></extra>"))
    fig_pre.update_layout(**chart_layout("", 360))
    fig_pre.update_yaxes(title="Pressure (Pa)")
    st.plotly_chart(fig_pre, use_container_width=True)

    # Context comparison
    section_hdr("🌍","PRESSURE CONTEXT","How Mars compares to Earth")
    earth_sea_level = 101325
    mars_avg_pre = sum(all_pre_av)/len(all_pre_av) if all_pre_av else 700

    fig_ctx = go.Figure(go.Bar(
        x=["🌍 Earth\n(sea level)", "🔴 Mars\n(InSight)"],
        y=[earth_sea_level, mars_avg_pre],
        marker=dict(color=[COL4, ACCENT], opacity=0.85),
        text=[f"{earth_sea_level:,} Pa", f"{mars_avg_pre:.0f} Pa"],
        textposition="outside",
        textfont=dict(family="Space Mono", size=11, color="#e2e8f0"),
        hovertemplate="%{x}: %{y:,.0f} Pa<extra></extra>",
    ))
    fig_ctx.update_layout(**chart_layout("", 320))
    fig_ctx.update_yaxes(title="Pressure (Pa)", type="log")
    st.plotly_chart(fig_ctx, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📋  TAB 5 — ALL SOLS TABLE
# ══════════════════════════════════════════════════════════════════════════════
with tab_sols:
    st.markdown("### 📋 All Available Sols")
    st.caption(f"Complete data for all {len(sols)} Sols returned by the InSight API")

    rows = []
    for s in sols:
        rows.append({
            "🪐 Sol":           s["sol"],
            "📅 Earth Date":    s["first_utc"][:12],
            "🌡️ T Avg":         fmt(convert_temp(s["at_av"]),1,t_unit),
            "🌡️ T Min":         fmt(convert_temp(s["at_mn"]),1,t_unit),
            "🌡️ T Max":         fmt(convert_temp(s["at_mx"]),1,t_unit),
            "💨 W Avg (m/s)":   fmt(s["hws_av"],2),
            "💨 W Max (m/s)":   fmt(s["hws_mx"],2),
            "🧭 Wind Dir":      s["wind_dir"],
            "🌀 P Avg (Pa)":    fmt(s["pre_av"],1),
            "🌀 P Min (Pa)":    fmt(s["pre_mn"],1),
            "🌀 P Max (Pa)":    fmt(s["pre_mx"],1),
            "🕐 First UTC":     s["first_utc"],
            "🕔 Last UTC":      s["last_utc"],
        })
    df_sols = pd.DataFrame(rows)
    st.dataframe(df_sols, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV",
                       df_sols.to_csv(index=False), "insight_sols.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# 🚀  TAB 6 — MISSION INFO
# ══════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown("### 🚀 InSight Mission Overview")

    mi1, mi2 = st.columns(2)

    with mi1:
        section_hdr("📡","MISSION TIMELINE","")
        timeline = [
            ("🚀", "Launch",          "May 5, 2018",      "Atlas V-401 from Vandenberg AFB"),
            ("🛬", "Mars Landing",    "Nov 26, 2018",     "Elysium Planitia, Mars"),
            ("🔬", "Science Start",   "Feb 22, 2019",     "Instruments deployed"),
            ("⚡", "Low Power Mode",  "May 2022",         "Dust on solar panels"),
            ("📡", "Last Contact",    "Dec 21, 2022",     "Mission declared complete"),
        ]
        for emoji, event, date_str, detail in timeline:
            st.markdown(f"""
            <div style="display:flex;gap:12px;align-items:flex-start;
            margin-bottom:10px;padding:10px 12px;background:#1a0c04;
            border:1px solid #2d1a0a;border-left:3px solid {ACCENT};border-radius:8px">
              <div style="font-size:18px;margin-top:2px">{emoji}</div>
              <div>
                <div style="font-family:'Orbitron',monospace;font-size:12px;
                font-weight:700;color:#e2e8f0">{event}</div>
                <div style="font-size:11px;color:{ACCENT};font-family:'Space Mono',monospace">{date_str}</div>
                <div style="font-size:10px;color:#78350f;margin-top:2px">{detail}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    with mi2:
        section_hdr("🔬","SCIENCE INSTRUMENTS","")
        instruments = [
            ("🌡️", "TWINS",      "Temperature and Wind for InSight",    "Temp + wind sensors", "#ef4444"),
            ("🌀", "APSS",      "Atmospheric Pressure Sensor Suite",    "Pressure sensor",     "#60a5fa"),
            ("📳", "SEIS",      "Seismic Experiment for Interior Str.", "Marsquake detector",  "#34d399"),
            ("🌡️", "HP³",       "Heat Flow and Physical Properties",    "Underground heat",    "#f59e0b"),
            ("📡", "RISE",      "Rotation and Interior Structure Exp.", "Radio science",       "#a78bfa"),
        ]
        for emoji, name, full, desc, color in instruments:
            st.markdown(f"""
            <div style="background:#1a0c04;border:1px solid #2d1a0a;
            border-top:3px solid {color};border-radius:10px;
            padding:12px 14px;margin-bottom:8px">
              <div style="font-size:11px;font-weight:700;color:{color};
              font-family:'Space Mono',monospace">{emoji} {name}</div>
              <div style="font-size:10px;color:#a16207;margin-top:2px">{full}</div>
              <div style="font-size:10px;color:#57280a;margin-top:2px">{desc}</div>
            </div>""", unsafe_allow_html=True)

    section_hdr("📍","LANDING SITE — ELYSIUM PLANITIA","")
    st.markdown(f"""
    <div style="background:#1a0c04;border:1px solid #2d1a0a;
    border-radius:12px;padding:18px 20px;line-height:2">
      <div style="display:flex;flex-wrap:wrap;gap:20px;font-size:12px;
      font-family:'Space Mono',monospace">
        <span style="color:{ACCENT}">📍 Lat: {ELYSIUM_LAT}°N</span>
        <span style="color:{ACCENT}">📍 Lon: {ELYSIUM_LON}°E</span>
        <span style="color:#a16207">🌋 Region: Elysium Planitia</span>
        <span style="color:#a16207">⛰️ Elevation: −2.7 km (MOLA)</span>
        <span style="color:#78350f">🌡️ Avg surface temp: −60°C</span>
        <span style="color:#78350f">🌀 Avg pressure: ~700–800 Pa</span>
      </div>
    </div>""", unsafe_allow_html=True)

    section_hdr("🌍","MARS vs EARTH — QUICK FACTS","")
    facts = [
        ("Property",           "🔴 Mars",          "🌍 Earth"),
        ("Day length",         "24 hr 37 min",      "24 hr 00 min"),
        ("Year length",        "687 Earth days",    "365.25 days"),
        ("Avg temp (surface)", "−60°C",             "+15°C"),
        ("Atm. pressure",      "~700 Pa",           "101,325 Pa"),
        ("Atm. composition",   "95% CO₂",           "78% N₂, 21% O₂"),
        ("Gravity",            "3.72 m/s²",         "9.81 m/s²"),
        ("Distance from Sun",  "1.52 AU avg",       "1.0 AU"),
    ]
    hdr, *body = facts
    rows_html = ""
    for i, (prop, mars, earth) in enumerate(body):
        bg = "#1a0c04" if i % 2 == 0 else "#150900"
        rows_html += f"""
        <tr style="background:{bg}">
          <td style="padding:8px 12px;color:#a16207;font-size:11px">{prop}</td>
          <td style="padding:8px 12px;color:{ACCENT};font-size:11px;font-family:'Space Mono',monospace">{mars}</td>
          <td style="padding:8px 12px;color:#60a5fa;font-size:11px;font-family:'Space Mono',monospace">{earth}</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;border:1px solid #2d1a0a;border-radius:10px;overflow:hidden">
      <thead>
        <tr style="background:#2d1a0a">
          <th style="padding:10px 12px;text-align:left;color:#78350f;font-size:10px;
          text-transform:uppercase;letter-spacing:1px;font-family:'Space Mono',monospace">{hdr[0]}</th>
          <th style="padding:10px 12px;text-align:left;color:{ACCENT};font-size:10px;
          text-transform:uppercase;letter-spacing:1px;font-family:'Space Mono',monospace">{hdr[1]}</th>
          <th style="padding:10px 12px;text-align:left;color:#60a5fa;font-size:10px;
          text-transform:uppercase;letter-spacing:1px;font-family:'Space Mono',monospace">{hdr[2]}</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:#120800;border:1px solid #2d1a0a;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#78350f;line-height:1.9">
    <b style="color:#a16207">🔴 About InSight Mars Weather Service</b> — NASA's InSight
    (Interior Exploration using Seismic Investigations, Geodesy and Heat Transport) lander
    operated on the surface of Mars from November 26 2018 to December 21 2022 at Elysium Planitia.
    It carried the TWINS meteorological sensors measuring atmospheric temperature, wind speed &amp;
    direction, and pressure. This API returns per-Sol (Martian day) summary data from the
    mission archive, maintained by NASA JPL and Cornell University.
    &nbsp;·&nbsp;
    <a href="https://mars.nasa.gov/insight/weather/" target="_blank"
    style="color:{ACCENT};text-decoration:none">🌐 mars.nasa.gov/insight/weather ↗</a>
    &nbsp;·&nbsp;
    <a href="https://api.nasa.gov/" target="_blank"
    style="color:#a16207;text-decoration:none">api.nasa.gov ↗</a>
  </div>
</div>""", unsafe_allow_html=True)
