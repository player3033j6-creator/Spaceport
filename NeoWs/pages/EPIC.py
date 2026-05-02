import streamlit as st
import requests
from datetime import date, timedelta, datetime
import pandas as pd
import plotly.graph_objects as go
import math

st.set_page_config(page_title="Spaceport | EPIC", page_icon="🌍", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"]          { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="metric-container"]    { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
[data-testid="stSidebar"]           { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] *         { color:#e2e8f0 !important; }
[data-testid="stTabs"] button       { color:#64748b !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#4f8ef7 !important; border-bottom-color:#4f8ef7 !important; }
h1,h2,h3                            { color:#e2e8f0 !important; }
/* Image grid cards */
.epic-img-card { border-radius:12px; overflow:hidden; border:1px solid #1a2340;
                 transition:border-color .2s; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑 Constants — dual endpoints (api.nasa.gov can return 503; direct is fallback)
# ══════════════════════════════════════════════════════════════════════════════
import time

API_KEY        = "wheUPIq3Zy52ym8MZBkQZlSWvRhzeIGJU4Ir0q9P"

# Primary: api.nasa.gov proxy (sometimes 503)
EPIC_BASE_PRI  = "https://api.nasa.gov/EPIC/api"
ARCH_BASE_PRI  = "https://api.nasa.gov/EPIC/archive"

# Fallback: direct EPIC server (no API key required, very reliable)
EPIC_BASE_DIR  = "https://epic.gsfc.nasa.gov/api"
ARCH_BASE_DIR  = "https://epic.gsfc.nasa.gov/archive"

# ══════════════════════════════════════════════════════════════════════════════
# 📡 Robust fetch helpers — retry + automatic fallback
# ══════════════════════════════════════════════════════════════════════════════
def _get_json(url: str, params: dict = None, retries: int = 3, backoff: float = 1.5) -> list | dict:
    """🔁 GET with retry + exponential back-off. Raises on final failure."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=18)
            if resp.status_code in (200, 201):
                return resp.json()
            last_err = Exception(f"HTTP {resp.status_code} from {url}")
        except Exception as e:
            last_err = e
        time.sleep(backoff ** attempt)
    raise last_err

@st.cache_data(ttl=3600)
def fetch_available_dates(collection: str) -> list[str]:
    """📅 Get all available dates — tries api.nasa.gov first, falls back to direct."""
    errors = []

    # ── Try primary (api.nasa.gov) ────────────────────────────────────────────
    try:
        data = _get_json(f"{EPIC_BASE_PRI}/{collection}/all",
                         params={"api_key": API_KEY})
        return [d["date"] for d in data]
    except Exception as e:
        errors.append(f"Primary: {e}")

    # ── Fallback to direct EPIC server ────────────────────────────────────────
    try:
        data = _get_json(f"{EPIC_BASE_DIR}/{collection}/all")
        return [d["date"] for d in data]
    except Exception as e:
        errors.append(f"Fallback: {e}")

    raise ConnectionError("⚠️ Both NASA API endpoints failed:\n" + "\n".join(errors))

@st.cache_data(ttl=3600)
def fetch_images_for_date(collection: str, chosen_date: str) -> list[dict]:
    """🖼️ Get image metadata — tries api.nasa.gov first, falls back to direct."""
    errors = []

    try:
        return _get_json(f"{EPIC_BASE_PRI}/{collection}/date/{chosen_date}",
                         params={"api_key": API_KEY})
    except Exception as e:
        errors.append(f"Primary: {e}")

    try:
        return _get_json(f"{EPIC_BASE_DIR}/{collection}/date/{chosen_date}")
    except Exception as e:
        errors.append(f"Fallback: {e}")

    raise ConnectionError("⚠️ Both NASA API endpoints failed:\n" + "\n".join(errors))

def build_image_url(collection: str, img_name: str, img_date: str, fmt: str = "jpg") -> str:
    """🔗 Build archive URL — uses direct EPIC server (more reliable for images)."""
    y, m, d = img_date[:4], img_date[5:7], img_date[8:10]
    # Direct server doesn't need an API key and rarely 503s
    return f"{ARCH_BASE_DIR}/{collection}/{y}/{m}/{d}/{fmt}/{img_name}.{fmt}"

def build_image_url_pri(collection: str, img_name: str, img_date: str, fmt: str = "jpg") -> str:
    """🔗 Build primary (api.nasa.gov) archive URL as secondary option."""
    y, m, d = img_date[:4], img_date[5:7], img_date[8:10]
    return f"{ARCH_BASE_PRI}/{collection}/{y}/{m}/{d}/{fmt}/{img_name}.{fmt}?api_key={API_KEY}"

# ══════════════════════════════════════════════════════════════════════════════
# 🎨 UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji: str, label: str, value, color: str, sub: str = ""):
    col.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:22px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:26px;color:{color};
      font-weight:700;margin:4px 0">{value}</div>
      <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#475569;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def section_hdr(emoji: str, title: str, cap: str = ""):
    st.markdown(f"""<div style="font-size:12px;font-weight:600;text-transform:uppercase;
    letter-spacing:1.5px;color:#64748b;margin:28px 0 4px">{emoji} {title}</div>""",
                unsafe_allow_html=True)
    if cap:
        st.caption(cap)

def meta_pill(label: str, value: str, color: str = "#4f8ef7"):
    return (f'<span style="background:{color}18;border:1px solid {color}44;border-radius:20px;'
            f'padding:3px 10px;font-size:11px;color:{color};margin-right:6px;margin-bottom:4px;'
            f'display:inline-block"><b>{label}:</b> {value}</span>')

# ══════════════════════════════════════════════════════════════════════════════
# 🌐 Globe map builder
# ══════════════════════════════════════════════════════════════════════════════
def build_globe(images: list[dict]):
    """
    🌍 Interactive 3-D globe showing:
      • DSCOVR spacecraft position (Sun–Earth L1 point, ~1.5 million km sunward)
      • Centroid coordinates of each image (where EPIC was pointed at Earth)
      • Sub-solar and sub-spacecraft points on Earth's surface
    """
    fig = go.Figure()

    # ── Centroid markers ──────────────────────────────────────────────────────
    lats, lons, tips, times = [], [], [], []
    for i, img in enumerate(images):
        cc = img.get("centroid_coordinates", {})
        lat, lon = cc.get("lat", 0), cc.get("lon", 0)
        lats.append(lat); lons.append(lon)
        ts = img.get("date", "")[:16]
        tips.append(
            f"<b>🌍 Centroid #{i+1}</b><br>"
            f"🕐 {ts}<br>"
            f"📍 {lat:.3f}°N, {lon:.3f}°E<br>"
            f"📷 {img.get('image','')}<extra></extra>")
        times.append(ts)

    if lats:
        # Colour by time index
        n = max(len(lats)-1, 1)
        colors = [f"rgb({int(79+176*i/n)},{int(142-80*i/n)},{int(247-100*i/n)})" for i in range(len(lats))]
        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons,
            mode="markers+text",
            marker=dict(size=14, color=colors,
                        line=dict(color="rgba(255,255,255,0.5)", width=1.5),
                        symbol="circle"),
            text=[f"#{i+1}" for i in range(len(lats))],
            textfont=dict(size=8, color="white", family="Space Mono"),
            textposition="middle center",
            hovertemplate=tips,
            name="📷 Image centroids",
            showlegend=True,
        ))

        # Sub-solar point (approx from first image sun coords)
        for img in images[:1]:
            sun = img.get("sun_j2000_position", {})
            sx, sy = sun.get("x", 0), sun.get("y", 0)
            sun_lon = math.degrees(math.atan2(sy, sx)) % 360
            if sun_lon > 180: sun_lon -= 360
            fig.add_trace(go.Scattergeo(
                lat=[0], lon=[sun_lon],
                mode="markers",
                marker=dict(size=16, color="#fbbf24", symbol="star",
                            line=dict(color="#fde68a", width=2)),
                hovertemplate=f"<b>☀️ Sub-solar point</b><br>Lon: {sun_lon:.1f}°<extra></extra>",
                name="☀️ Sub-solar point",
                showlegend=True,
            ))

        # Coverage arc — connect centroids chronologically
        if len(lats) > 1:
            fig.add_trace(go.Scattergeo(
                lat=lats, lon=lons,
                mode="lines",
                line=dict(color="rgba(79,142,247,0.3)", width=1.5, dash="dot"),
                hoverinfo="skip",
                name="📐 Image sequence",
                showlegend=True,
            ))

    fig.update_geos(
        bgcolor="#04060f",
        landcolor="#0d1b2a",
        oceancolor="#04060f",
        showocean=True, showland=True,
        showcountries=True, countrycolor="#1a2340",
        showcoastlines=True, coastlinecolor="#1e3a5f",
        showrivers=False,
        showframe=False,
        showlakes=True, lakecolor="#04060f",
        projection_type="orthographic",
        # Centre on mean centroid
        projection_rotation=dict(
            lon=sum(lons)/max(len(lons),1) if lons else 0,
            lat=sum(lats)/max(len(lats),1) if lats else 0,
        ),
    )
    fig.update_layout(
        paper_bgcolor="#04060f",
        margin=dict(l=0, r=0, t=40, b=0),
        height=560,
        font=dict(family="Space Mono", color="#94a3b8"),
        title=dict(text="🌐 DSCOVR/EPIC — Centroid Positions on Earth",
                   font=dict(color="#64748b", size=12, family="Space Mono"),
                   x=0.5, xanchor="center"),
        legend=dict(bgcolor="rgba(15,22,38,0.9)", bordercolor="#1a2340", borderwidth=1,
                    font=dict(color="#94a3b8", size=11, family="Space Mono")),
        hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                        font=dict(color="#e2e8f0", size=12, family="Space Mono")),
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# ☀️ DSCOVR Spacecraft position diagram
# ══════════════════════════════════════════════════════════════════════════════
def build_spacecraft_diagram(images: list[dict]):
    """
    ☀️ 2-D diagram: Sun → L1 → Earth showing DSCOVR/EPIC position in J2000 coords.
    """
    fig = go.Figure()

    if not images:
        return fig

    img = images[0]
    dscovr = img.get("dscovr_j2000_position", {})
    sun    = img.get("sun_j2000_position", {})
    moon   = img.get("lunar_j2000_position", {})

    dx, dy = dscovr.get("x", 0) / 1e6, dscovr.get("y", 0) / 1e6   # → millions km
    sx, sy = sun.get("x", 0) / 1e6,    sun.get("y", 0) / 1e6
    mx, my = moon.get("x", 0) / 1e6,   moon.get("y", 0) / 1e6

    # Sun glow layers
    for sz, al in [(80,0.04),(60,0.07),(42,0.12),(28,0.20)]:
        fig.add_trace(go.Scatter(x=[sx], y=[sy], mode="markers",
            marker=dict(size=sz, color=f"rgba(253,230,138,{al})"),
            hoverinfo="skip", showlegend=False, name="_g"))
    fig.add_trace(go.Scatter(x=[sx], y=[sy], mode="markers",
        marker=dict(size=22, color="#fde68a", line=dict(color="#fbbf24", width=2)),
        hovertemplate=f"<b>☀️ Sun</b><br>x: {sx:.2f}M km<br>y: {sy:.2f}M km<extra></extra>",
        name="☀️ Sun", showlegend=True))

    # Earth
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers",
        marker=dict(size=18, color="#4f8ef7", line=dict(color="#93c5fd", width=2)),
        hovertemplate="<b>🌍 Earth</b><br>(0, 0) reference<extra></extra>",
        name="🌍 Earth", showlegend=True))

    # Moon
    fig.add_trace(go.Scatter(x=[mx], y=[my], mode="markers",
        marker=dict(size=9, color="#94a3b8", line=dict(color="#cbd5e1", width=1)),
        hovertemplate=f"<b>🌕 Moon</b><br>x: {mx:.3f}M km<br>y: {my:.3f}M km<extra></extra>",
        name="🌕 Moon", showlegend=True))

    # DSCOVR spacecraft
    for sz, al in [(34,0.06),(22,0.12),(14,0.22)]:
        fig.add_trace(go.Scatter(x=[dx], y=[dy], mode="markers",
            marker=dict(size=sz, color=f"rgba(245,158,11,{al})"),
            hoverinfo="skip", showlegend=False, name="_dg"))
    fig.add_trace(go.Scatter(x=[dx], y=[dy], mode="markers",
        marker=dict(size=12, color="#f59e0b", symbol="diamond",
                    line=dict(color="#fde68a", width=2)),
        hovertemplate=(f"<b>🛰️ DSCOVR</b><br>"
                       f"x: {dx:.4f}M km<br>y: {dy:.4f}M km<br>"
                       f"Distance from Earth: {math.hypot(dx,dy):.4f}M km<extra></extra>"),
        name="🛰️ DSCOVR (L1)", showlegend=True))

    # Lines: Sun→DSCOVR, DSCOVR→Earth
    fig.add_trace(go.Scatter(
        x=[sx, dx, 0], y=[sy, dy, 0],
        mode="lines",
        line=dict(color="rgba(148,163,184,0.18)", width=1, dash="dot"),
        hoverinfo="skip", showlegend=False, name="_line"))

    # L1 annotation
    fig.add_annotation(x=dx, y=dy+0.05,
        text="L1 (Lagrange point 1)",
        showarrow=False,
        font=dict(size=9, color="#64748b", family="Space Mono"),
        yshift=12)

    # Axis labels
    fig.add_annotation(x=1.0, y=-0.55, text="← Earth–Sun line →",
        showarrow=False, font=dict(size=9, color="#475569", family="Space Mono"),
        xanchor="center")

    all_x = [sx, dx, mx, 0]
    all_y = [sy, dy, my, 0]
    pad_x = (max(all_x)-min(all_x)) * 0.15 or 0.2
    pad_y = (max(all_y)-min(all_y)) * 0.15 or 0.2

    fig.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#04060f",
        height=480,
        margin=dict(l=10, r=10, t=48, b=10),
        title=dict(text="🛰️ DSCOVR Spacecraft Position (J2000 Reference Frame, millions km)",
                   font=dict(color="#64748b", size=12, family="Space Mono"),
                   x=0.5, xanchor="center"),
        xaxis=dict(visible=False, range=[min(all_x)-pad_x, max(all_x)+pad_x],
                   scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False, range=[min(all_y)-pad_y, max(all_y)+pad_y]),
        legend=dict(bgcolor="rgba(15,22,38,0.9)", bordercolor="#1a2340", borderwidth=1,
                    font=dict(color="#94a3b8", size=11, family="Space Mono")),
        hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                        font=dict(color="#e2e8f0", size=12, family="Space Mono")),
        dragmode="pan",
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# 📐 Quaternion / attitude chart
# ══════════════════════════════════════════════════════════════════════════════
def build_attitude_chart(images: list[dict]):
    """📐 Bar chart of attitude quaternion components across images."""
    records = []
    for i, img in enumerate(images):
        aq = img.get("attitude_quaternions", {})
        ts = img.get("date", "")[:16]
        records.append({"#": i+1, "Time": ts,
                        "q0": aq.get("q0", 0), "q1": aq.get("q1", 0),
                        "q2": aq.get("q2", 0), "q3": aq.get("q3", 0)})
    if not records:
        return go.Figure()
    df = pd.DataFrame(records)
    fig = go.Figure()
    colors_q = {"q0":"#4f8ef7","q1":"#22c55e","q2":"#f59e0b","q3":"#a855f7"}
    for q, col in colors_q.items():
        fig.add_trace(go.Scatter(
            x=df["Time"], y=df[q],
            mode="lines+markers",
            line=dict(color=col, width=2),
            marker=dict(size=6, color=col),
            name=q,
            hovertemplate=f"<b>{q}</b><br>%{{x}}<br>Value: %{{y:.5f}}<extra></extra>",
        ))
    fig.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=280, margin=dict(l=10,r=10,t=10,b=40),
        xaxis=dict(showgrid=False, color="#64748b",
                   tickfont=dict(family="Space Mono", size=9), tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                   tickfont=dict(family="Space Mono", size=10)),
        legend=dict(bgcolor="rgba(15,22,38,0.85)", bordercolor="#1a2340", borderwidth=1,
                    font=dict(color="#94a3b8", size=11, family="Space Mono"),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                        font=dict(color="#e2e8f0", size=12, family="Space Mono")),
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️ HEADER
# ══════════════════════════════════════════════════════════════════════════════
cl, ct, cb = st.columns([0.06, 0.70, 0.24])
with cl:
    st.markdown("""
    <div style="width:52px;height:52px;
    background:radial-gradient(circle,#1e3a8a,#0f172a);
    border:2px solid #4f8ef7;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:9px;font-weight:700;
    color:#4f8ef7;letter-spacing:1px;
box-shadow:0 0 20px rgba(79,142,247,.35);margin-top:6px">Spaceport</div>
    """, unsafe_allow_html=True)
with ct:
    st.markdown("## 🌍 Earth Polychromatic Imaging Camera (EPIC)")
    st.caption("Full-disc Earth imagery from the DSCOVR spacecraft at Sun–Earth Lagrange point L1 · ~1.5 million km from Earth")
with cb:
    st.markdown("""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(79,142,247,.1);border:1px solid rgba(79,142,247,.3);
      border-radius:20px;padding:4px 12px;font-size:12px;color:#4f8ef7;font-weight:500">
      🛰️ DSCOVR/EPIC</span>
    </div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️ SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🌍 EPIC Controls")

    collection = st.radio("🎨 Image collection",
                          ["natural", "enhanced"],
                          format_func=lambda x: "🌿 Natural colour" if x=="natural" else "✨ Enhanced colour",
                          index=0)

    st.markdown("---")
    st.markdown("### 📅 Date selection")
    date_mode = st.radio("Mode", ["📡 Latest available", "📆 Pick a date"], index=0)

    st.markdown("---")
    st.markdown("### 🖼️ Gallery settings")
    cols_per_row = st.slider("🗂️ Images per row", 2, 5, 3)
    show_captions = st.toggle("💬 Show captions", True)
    img_format = st.radio("📷 Image format", ["jpg","png"],
                          format_func=lambda x: "🖼️ JPG (faster)" if x=="jpg" else "🖼️ PNG (full res)",
                          index=0)
    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#475569;line-height:1.9">
    <b style="color:#64748b">ℹ️ About EPIC</b><br>
    🛰️ DSCOVR spacecraft<br>
    📍 Sun–Earth L1 point<br>
    📏 ~1.5M km from Earth<br>
    🌐 Full-disc Earth images<br>
    🔁 ~22 images / day<br>
    📡 Since June 2015
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data from [NASA EPIC API](https://epic.gsfc.nasa.gov/)")

# ══════════════════════════════════════════════════════════════════════════════
# 📡 Fetch available dates & select one
# ══════════════════════════════════════════════════════════════════════════════
available_dates = None

with st.spinner("📡 Connecting to NASA EPIC API… (auto-retrying up to 3×)"):
    try:
        available_dates = fetch_available_dates(collection)
    except Exception as e:
        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid #7f1d1d;border-left:4px solid #ef4444;
        border-radius:10px;padding:18px 20px;margin-bottom:12px">
          <div style="font-size:14px;font-weight:600;color:#ef4444;margin-bottom:6px">
            🛰️ NASA EPIC API Temporarily Unavailable
          </div>
          <div style="font-size:12px;color:#94a3b8;line-height:1.8">
            The NASA API server returned a <b style="color:#f59e0b">503 Service Unavailable</b> error.
            This is a temporary issue on NASA's side — the direct fallback server was also attempted automatically.<br><br>
            <b style="color:#e2e8f0">What you can do:</b><br>
            ⏳ Wait 1–2 minutes and click <b>🔄 Retry</b> below<br>
            📅 The NASA EPIC API is usually available within a few minutes of a 503<br>
            🌐 You can also browse images directly at
            <a href="https://epic.gsfc.nasa.gov" target="_blank"
               style="color:#4f8ef7">epic.gsfc.nasa.gov</a>
          </div>
          <details style="margin-top:10px">
            <summary style="color:#64748b;font-size:11px;cursor:pointer">🔍 Technical details</summary>
            <pre style="color:#475569;font-size:10px;margin-top:6px;white-space:pre-wrap">{e}</pre>
          </details>
        </div>""", unsafe_allow_html=True)

        rc1, rc2 = st.columns([1,4])
        if rc1.button("🔄 Retry now", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        rc2.markdown(
            "<div style='padding-top:8px;font-size:12px;color:#64748b'>"
            "Clears the cache and re-fetches from both NASA endpoints</div>",
            unsafe_allow_html=True)
        st.stop()

if not available_dates:
    st.warning("⚠️ No EPIC dates returned. The API may be initialising — try again in a moment.")
    if st.button("🔄 Retry", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

available_dates_sorted = sorted(available_dates, reverse=True)

# ── Endpoint status badge ──────────────────────────────────────────────────────
st.markdown("""
<div style="display:inline-block;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);
border-radius:20px;padding:3px 12px;font-size:11px;color:#22c55e;margin-bottom:12px">
  ✅ Connected to NASA EPIC — data loaded successfully
</div>""", unsafe_allow_html=True)

if date_mode == "📡 Latest available":
    chosen_date = available_dates_sorted[0]
    st.markdown(f"📡 **Latest available date:** `{chosen_date}`  ·  "
                f"🗓️ Total dates on record: `{len(available_dates)}`")
else:
    # Convert available dates to datetime.date objects for the calendar
    from datetime import date as date_type
    available_date_objs = sorted(
        [date_type.fromisoformat(d) for d in available_dates_sorted], reverse=True
    )
    min_date = available_date_objs[-1]   # oldest
    max_date = available_date_objs[0]    # most recent

    picked = st.date_input(
        "📅 Choose a date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        help="📡 Only dates with EPIC imagery are valid. If no images are found for your selection, try an adjacent date.",
    )

    # Snap to nearest available date if the picked day has no data
    picked_str = str(picked)
    if picked_str in available_dates:
        chosen_date = picked_str
    else:
        # Find closest available date
        closest = min(available_date_objs, key=lambda d: abs((d - picked).days))
        chosen_date = str(closest)
        st.caption(f"⚠️ No EPIC images on {picked_str} — showing nearest available date: `{chosen_date}`")

# ══════════════════════════════════════════════════════════════════════════════
# 🖼️ Fetch images for chosen date
# ══════════════════════════════════════════════════════════════════════════════
with st.spinner(f"🌍 Loading EPIC images for {chosen_date}…"):
    try:
        images = fetch_images_for_date(collection, chosen_date)
    except Exception as e:
        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid #7f1d1d;border-left:4px solid #ef4444;
        border-radius:10px;padding:16px 20px">
          <div style="font-size:13px;font-weight:600;color:#ef4444">
            ⚠️ Could not load images for {chosen_date}
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-top:6px">{e}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄 Retry", type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

if not images:
    st.warning(f"⚠️ No images found for {chosen_date}.")
    st.stop()

# ── Stat strip ────────────────────────────────────────────────────────────────
s1,s2,s3,s4,s5 = st.columns(5)
first_img = images[0]
last_img  = images[-1]
cc        = first_img.get("centroid_coordinates",{})
dscovr    = first_img.get("dscovr_j2000_position",{})
dist_km   = math.hypot(dscovr.get("x",0), dscovr.get("y",0), dscovr.get("z",0)) / 1000
first_ts  = first_img.get("date","")[:16]
last_ts   = last_img.get("date","")[:16]

stat_card(s1,"📷","Images today", len(images), "#4f8ef7", chosen_date)
stat_card(s2,"🕐","First capture", first_ts[11:], "#22c55e", first_ts[:10])
stat_card(s3,"🕔","Last capture",  last_ts[11:],  "#f59e0b", last_ts[:10])
stat_card(s4,"📍","Centroid lat/lon",
          f"{cc.get('lat',0):.1f}°", "#a855f7",
          f"{cc.get('lon',0):.1f}° lon")
stat_card(s5,"🛰️","DSCOVR dist",
          f"{dist_km/1e6:.3f}M", "#ef4444", "km from Earth")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑 TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_gallery, tab_globe, tab_spacecraft, tab_attitude, tab_data = st.tabs([
    "🖼️  Image Gallery",
    "🌐  Globe Map",
    "🛰️  Spacecraft Position",
    "📐  Attitude Data",
    "📋  Metadata",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🖼️ TAB 1 — IMAGE GALLERY
# ══════════════════════════════════════════════════════════════════════════════
with tab_gallery:
    coll_label = "🌿 Natural" if collection == "natural" else "✨ Enhanced"
    st.markdown(f"### 🖼️ EPIC Image Gallery — {coll_label} · {chosen_date}")
    st.caption(
        "Full-disc Earth images taken by the EPIC camera aboard DSCOVR. "
        "Each image captures the entire sunlit face of Earth from ~1.5 million km away.")

    # ── Image selector strip ──────────────────────────────────────────────────
    section_hdr("🎞️","IMAGE STRIP","Click an image number to jump to it in the grid below")

    strip_cols = st.columns(min(len(images), 12))
    for idx, (col, img) in enumerate(zip(strip_cols, images[:12])):
        ts = img.get("date","")[-8:-3]   # HH:MM
        col.markdown(f"""
        <div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;
        padding:6px;text-align:center;cursor:pointer">
          <div style="font-family:'Space Mono',monospace;font-size:11px;color:#4f8ef7;font-weight:700">
            #{idx+1}</div>
          <div style="font-size:9px;color:#64748b">{ts}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Image grid ────────────────────────────────────────────────────────────
    section_hdr("🖼️","FULL DISC EARTH IMAGES", f"{len(images)} images on {chosen_date}")

    img_rows = [images[i:i+cols_per_row] for i in range(0, len(images), cols_per_row)]

    for row_imgs in img_rows:
        row_cols = st.columns(cols_per_row)
        for col, img in zip(row_cols, row_imgs):
            img_name = img.get("image","")
            img_date = img.get("date","")
            img_url  = build_image_url(collection, img_name, img_date, img_format)
            ts       = img_date[11:16] if len(img_date) > 10 else ""
            cap_txt  = img.get("caption","")
            cc_i     = img.get("centroid_coordinates", {})

            with col:
                st.markdown(f"""
                <div style="background:#0f1626;border:1px solid #1a2340;border-radius:12px;
                overflow:hidden;margin-bottom:8px">
                  <img src="{img_url}" style="width:100%;display:block;border-radius:12px 12px 0 0"
                       loading="lazy" onerror="this.src=''" />
                  <div style="padding:10px 12px">
                    <div style="font-family:'Space Mono',monospace;font-size:12px;
                    color:#4f8ef7;font-weight:700">🕐 {ts} UTC</div>
                    <div style="font-size:10px;color:#64748b;margin-top:3px">
                      📍 {cc_i.get('lat',0):.2f}°N · {cc_i.get('lon',0):.2f}°E
                    </div>
                    {"<div style='font-size:9px;color:#475569;margin-top:4px;line-height:1.4'>" + cap_txt[:120] + "…</div>" if show_captions and cap_txt else ""}
                  </div>
                </div>""", unsafe_allow_html=True)

    # ── Quick compare: first vs last ──────────────────────────────────────────
    if len(images) >= 2:
        st.markdown("<br>", unsafe_allow_html=True)
        section_hdr("🔄","FIRST vs LAST IMAGE OF THE DAY",
                    "See how Earth rotated over the course of the day")
        fc1, fc2 = st.columns(2)
        for col, img, label, color in [
            (fc1, images[0],  "🌅 First image", "#22c55e"),
            (fc2, images[-1], "🌆 Last image",  "#f59e0b"),
        ]:
            img_url = build_image_url(collection, img["image"], img["date"], img_format)
            ts      = img["date"][11:16]
            cc_i    = img.get("centroid_coordinates", {})
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid #1a2340;
            border-top:3px solid {color};border-radius:12px;overflow:hidden">
              <img src="{img_url}" style="width:100%;display:block" loading="lazy"/>
              <div style="padding:12px 14px">
                <div style="font-size:13px;font-weight:600;color:{color}">{label}</div>
                <div style="font-family:'Space Mono',monospace;font-size:11px;
                color:#64748b;margin-top:4px">
                  🕐 {ts} UTC &nbsp;·&nbsp; 📍 {cc_i.get('lat',0):.2f}°N, {cc_i.get('lon',0):.2f}°E
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🌐 TAB 2 — GLOBE MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab_globe:
    st.markdown("### 🌐 EPIC Centroid Globe Map")
    st.caption(
        "Each numbered dot shows where EPIC's camera was pointed at Earth (centroid coordinate) "
        "for that image. The star ☀️ marks the sub-solar point. "
        "Dots are coloured by time — blue = earliest, cyan = latest.")

    section_hdr("🌐","ORTHOGRAPHIC GLOBE",
                "Drag to rotate · scroll to zoom · hover dots for details")
    st.plotly_chart(build_globe(images), use_container_width=True,
                    config={"scrollZoom":True,"displayModeBar":True,
                            "modeBarButtonsToRemove":["select2d","lasso2d"],
                            "toImageButtonOptions":{"format":"png","filename":"epic_globe"}})

    # ── Centroid path table ───────────────────────────────────────────────────
    section_hdr("📊","CENTROID TRACK TABLE","")
    rows = []
    for i,img in enumerate(images):
        cc_i = img.get("centroid_coordinates",{})
        rows.append({"#": i+1,
                     "🕐 Time (UTC)": img.get("date","")[:16],
                     "🌐 Lat (°N)": round(cc_i.get("lat",0),4),
                     "🌐 Lon (°E)": round(cc_i.get("lon",0),4),
                     "📷 Image name": img.get("image","")})
    df_cc = pd.DataFrame(rows)
    st.dataframe(df_cc, use_container_width=True, hide_index=True)

    # ── Centroid drift chart ──────────────────────────────────────────────────
    section_hdr("📈","CENTROID DRIFT OVER THE DAY",
                "How the sub-spacecraft point drifts as DSCOVR orbits L1 and Earth rotates")

    fig_drift = go.Figure()
    lats_d = [img.get("centroid_coordinates",{}).get("lat",0) for img in images]
    lons_d = [img.get("centroid_coordinates",{}).get("lon",0) for img in images]
    times_d = [img.get("date","")[:16] for img in images]

    fig_drift.add_trace(go.Scatter(
        x=times_d, y=lons_d, mode="lines+markers",
        line=dict(color="#4f8ef7", width=2),
        marker=dict(size=6, color="#4f8ef7"),
        name="🌐 Longitude", yaxis="y1",
        hovertemplate="<b>Lon</b>: %{y:.3f}°E<br>%{x}<extra></extra>"))
    fig_drift.add_trace(go.Scatter(
        x=times_d, y=lats_d, mode="lines+markers",
        line=dict(color="#22c55e", width=2, dash="dash"),
        marker=dict(size=6, color="#22c55e"),
        name="🌐 Latitude", yaxis="y2",
        hovertemplate="<b>Lat</b>: %{y:.3f}°N<br>%{x}<extra></extra>"))
    fig_drift.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=240, margin=dict(l=10,r=60,t=10,b=40),
        xaxis=dict(showgrid=False, color="#64748b",
                   tickfont=dict(family="Space Mono",size=9), tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#4f8ef7",
                   tickfont=dict(family="Space Mono",size=10), title="Lon (°E)",
                   titlefont=dict(color="#4f8ef7")),
        yaxis2=dict(overlaying="y", side="right", color="#22c55e",
                    tickfont=dict(family="Space Mono",size=10), title="Lat (°N)",
                    titlefont=dict(color="#22c55e")),
        legend=dict(bgcolor="rgba(15,22,38,0.85)",bordercolor="#1a2340",borderwidth=1,
                    font=dict(color="#94a3b8",size=11,family="Space Mono")),
        hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")))
    st.plotly_chart(fig_drift, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🛰️ TAB 3 — SPACECRAFT POSITION
# ══════════════════════════════════════════════════════════════════════════════
with tab_spacecraft:
    st.markdown("### 🛰️ DSCOVR Spacecraft Position")
    st.caption(
        "DSCOVR orbits the Sun–Earth L1 Lagrange point ~1.5 million km from Earth. "
        "Coordinates are in the J2000 inertial reference frame (km), converted to millions of km here.")

    section_hdr("🗺️","DSCOVR / SUN / MOON POSITION DIAGRAM",
                "2-D projection of the J2000 reference frame · scroll to zoom")
    st.plotly_chart(build_spacecraft_diagram(images), use_container_width=True,
                    config={"scrollZoom":True,"displayModeBar":True,
                            "modeBarButtonsToRemove":["select2d","lasso2d"]})

    # ── Numeric table ─────────────────────────────────────────────────────────
    section_hdr("📊","SPACECRAFT POSITIONS (J2000, km)","From first image of the day")
    img0 = images[0]
    pos_rows = []
    for body, key, emoji in [
        ("DSCOVR", "dscovr_j2000_position", "🛰️"),
        ("Sun",    "sun_j2000_position",    "☀️"),
        ("Moon",   "lunar_j2000_position",  "🌕"),
    ]:
        p = img0.get(key, {})
        x,y,z = p.get("x",0), p.get("y",0), p.get("z",0)
        dist = math.hypot(x,y,z)
        pos_rows.append({
            "Body": f"{emoji} {body}",
            "X (km)":     f"{x:,.1f}",
            "Y (km)":     f"{y:,.1f}",
            "Z (km)":     f"{z:,.1f}",
            "Distance from Earth (km)": f"{dist:,.1f}",
        })
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)

    # ── DSCOVR distance over the day ──────────────────────────────────────────
    section_hdr("📈","DSCOVR DISTANCE FROM EARTH OVER THE DAY","")
    dists   = []
    times_s = []
    for img in images:
        d = img.get("dscovr_j2000_position",{})
        dist_i = math.hypot(d.get("x",0), d.get("y",0), d.get("z",0)) / 1000   # → Mm
        dists.append(dist_i)
        times_s.append(img.get("date","")[:16])

    fig_dist = go.Figure()
    fig_dist.add_trace(go.Scatter(
        x=times_s, y=dists, mode="lines+markers",
        line=dict(color="#f59e0b", width=2),
        marker=dict(size=6, color="#f59e0b"),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.06)",
        hovertemplate="<b>%{x}</b><br>🛰️ Distance: %{y:.4f} Mm (×10⁶ km)<extra></extra>",
        name="🛰️ DSCOVR distance",
    ))
    fig_dist.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=220, margin=dict(l=10,r=10,t=10,b=40),
        xaxis=dict(showgrid=False, color="#64748b",
                   tickfont=dict(family="Space Mono",size=9), tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                   tickfont=dict(family="Space Mono",size=10), title="Distance (Mm)"),
        showlegend=False,
        hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")))
    st.plotly_chart(fig_dist, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📐 TAB 4 — ATTITUDE DATA
# ══════════════════════════════════════════════════════════════════════════════
with tab_attitude:
    st.markdown("### 📐 EPIC Attitude Quaternions")
    st.caption(
        "Attitude quaternions (q0–q3) describe the precise orientation of the EPIC camera. "
        "They are used to accurately geo-locate each pixel of the Earth image.")

    section_hdr("📐","QUATERNION COMPONENTS OVER TIME",
                "q0–q3 encode camera orientation in 3-D space — changes reflect orbital motion")
    st.plotly_chart(build_attitude_chart(images), use_container_width=True)

    # ── Per-image quaternion cards ────────────────────────────────────────────
    section_hdr("🗂️","PER-IMAGE ATTITUDE CARDS","")
    aq_cols = st.columns(4)
    for i, img in enumerate(images[:8]):
        aq  = img.get("attitude_quaternions", {})
        ts  = img.get("date","")[11:16]
        col = aq_cols[i % 4]
        col.markdown(f"""
        <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #4f8ef7;
        border-radius:10px;padding:12px;margin-bottom:10px">
          <div style="font-family:'Space Mono',monospace;font-size:11px;color:#4f8ef7;
          font-weight:700;margin-bottom:6px">📷 #{i+1} · 🕐 {ts}</div>
          <div style="font-size:10px;color:#64748b;line-height:1.8;font-family:'Space Mono',monospace">
            q0: <span style="color:#4f8ef7">{aq.get('q0',0):.5f}</span><br>
            q1: <span style="color:#22c55e">{aq.get('q1',0):.5f}</span><br>
            q2: <span style="color:#f59e0b">{aq.get('q2',0):.5f}</span><br>
            q3: <span style="color:#a855f7">{aq.get('q3',0):.5f}</span>
          </div>
        </div>""", unsafe_allow_html=True)

    if len(images) > 8:
        st.caption(f"ℹ️ Showing first 8 of {len(images)} images. See 📋 Metadata tab for all.")

# ══════════════════════════════════════════════════════════════════════════════
# 📋 TAB 5 — METADATA
# ══════════════════════════════════════════════════════════════════════════════
with tab_data:
    st.markdown("### 📋 Full Image Metadata")
    st.caption("All metadata fields returned by the EPIC API for each image on this date.")

    # Search
    search_meta = st.text_input("🔍 Search image name or caption", placeholder="Filter…")

    meta_rows = []
    for i, img in enumerate(images):
        cc_i   = img.get("centroid_coordinates", {})
        aq     = img.get("attitude_quaternions", {})
        dscovr = img.get("dscovr_j2000_position", {})
        sun    = img.get("sun_j2000_position", {})
        moon   = img.get("lunar_j2000_position", {})
        meta_rows.append({
            "#":               i+1,
            "🕐 Date (UTC)":   img.get("date",""),
            "📷 Image name":   img.get("image",""),
            "💬 Caption":      img.get("caption","")[:80]+"…",
            "🌐 Lat (°N)":     round(cc_i.get("lat",0),4),
            "🌐 Lon (°E)":     round(cc_i.get("lon",0),4),
            "q0":              round(aq.get("q0",0),6),
            "q1":              round(aq.get("q1",0),6),
            "q2":              round(aq.get("q2",0),6),
            "q3":              round(aq.get("q3",0),6),
            "🛰️ DSC-X (km)":   round(dscovr.get("x",0),1),
            "🛰️ DSC-Y (km)":   round(dscovr.get("y",0),1),
            "🛰️ DSC-Z (km)":   round(dscovr.get("z",0),1),
        })
    df_meta = pd.DataFrame(meta_rows)
    if search_meta:
        mask = df_meta.apply(lambda row: row.astype(str).str.contains(search_meta, case=False).any(), axis=1)
        df_meta = df_meta[mask]

    st.dataframe(df_meta, use_container_width=True, hide_index=True)

    # ── Download + image URLs ─────────────────────────────────────────────────
    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button("⬇️ Download metadata CSV", df_meta.to_csv(index=False),
                            f"epic_{chosen_date}.csv","text/csv")

    section_hdr("🔗","IMAGE URLS","Direct links to all EPIC images — using reliable direct server")
    for i, img in enumerate(images):
        url_jpg     = build_image_url(collection, img["image"], img["date"], "jpg")
        url_png     = build_image_url(collection, img["image"], img["date"], "png")
        url_jpg_pri = build_image_url_pri(collection, img["image"], img["date"], "jpg")
        ts          = img.get("date","")[11:16]
        st.markdown(f"""
        <div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;
        padding:10px 14px;margin-bottom:6px;font-size:11px;font-family:'Space Mono',monospace">
          <span style="color:#4f8ef7;font-weight:700">#{i+1}</span>
          <span style="color:#64748b"> · 🕐 {ts} UTC</span><br>
          <span style="color:#64748b;font-size:9px">Direct server:</span>
          <a href="{url_jpg}" target="_blank" style="color:#22c55e;text-decoration:none">🖼️ JPG</a>
          &nbsp;
          <a href="{url_png}" target="_blank" style="color:#22c55e;text-decoration:none">🖼️ PNG</a>
          &nbsp;&nbsp;
          <span style="color:#64748b;font-size:9px">NASA API:</span>
          <a href="{url_jpg_pri}" target="_blank" style="color:#4f8ef7;text-decoration:none">🖼️ JPG</a>
          &nbsp;&nbsp;
          <span style="color:#334155">{img.get('image','')}</span>
        </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#64748b;line-height:1.9">
    <b style="color:#94a3b8">🌍 About EPIC</b> — The Earth Polychromatic Imaging Camera (EPIC) is a
    2048×2048 pixel CCD (charge-coupled device) camera and telescope aboard NOAA's DSCOVR
    (Deep Space Climate Observatory) spacecraft, which orbits the Sun–Earth L1 Lagrange point
    approximately 1.5 million km from Earth. EPIC provides global spectral images of the entire
    sunlit face of Earth on a daily basis, producing ~22 images per day in 10 spectral bands
    (UV, visible, NIR). &nbsp;·&nbsp;
    <b style="color:#4f8ef7">🌿 Natural</b>: reconstructed true-colour (bands 3-2-1) &nbsp;·&nbsp;
    <b style="color:#a855f7">✨ Enhanced</b>: contrast-enhanced for atmospheric detail &nbsp;·&nbsp;
    API: <span style="color:#4f8ef7;font-family:'Space Mono',monospace">https://api.nasa.gov/EPIC</span>
  </div>
</div>""", unsafe_allow_html=True)
