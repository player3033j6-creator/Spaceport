import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import time
from urllib.parse import quote

st.set_page_config(
    page_title="Spaceport | Exoplanet",
    page_icon="🪐",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');

html, body, [class*="css"]          { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"]           { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] *         { color:#e2e8f0 !important; }
[data-testid="stTabs"] button       { color:#64748b !important; font-family:'Space Mono',monospace !important; font-size:11px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#22d3ee !important; border-bottom-color:#22d3ee !important; }
[data-testid="metric-container"]    { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
h1,h2,h3                            { color:#e2e8f0 !important; }
.stTextInput input, .stNumberInput input { background:#0f1626 !important; border:1px solid #1a2340 !important; color:#e2e8f0 !important; border-radius:8px !important; }
div[data-baseweb="select"] > div    { background:#0f1626 !important; border-color:#1a2340 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑  Constants  — TAP is public; NASA key used for nexsci supplementary calls
# ══════════════════════════════════════════════════════════════════════════════
NASA_KEY   = "HqbgDRjKxx6DfcnPZhrp0GHffM5XGHBTaNKQA3IO"

# Only the working endpoint — /tap/sync (lowercase) returns 404
TAP_URLS = [
    "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
]

# Colour palette
ACCENT    = "#22d3ee"
COL2      = "#818cf8"
COL3      = "#f59e0b"
COL4      = "#22c55e"
DANGER    = "#ef4444"

DISC_COLORS = {
    "Transit":                  "#22d3ee",
    "Radial Velocity":          "#818cf8",
    "Microlensing":             "#f59e0b",
    "Imaging":                  "#22c55e",
    "Transit Timing Variations":"#f472b6",
    "Eclipse Timing Variations":"#fb923c",
    "Astrometry":               "#a78bfa",
    "Pulsar Timing":            "#34d399",
    "Other":                    "#64748b",
}

# ══════════════════════════════════════════════════════════════════════════════
# 📡  TAP query helpers
# ══════════════════════════════════════════════════════════════════════════════
def tap_query(adql: str, maxrec: int = 6000, retries: int = 2) -> pd.DataFrame:
    """Execute an ADQL query against the NASA Exoplanet Archive TAP service."""
    from io import StringIO
    import xml.etree.ElementTree as ET

    tap_url = TAP_URLS[0]
    errors  = []

    for attempt in range(retries):
        try:
            # MAXREC must be a separate top-level parameter, NOT inside the ADQL
            r = requests.get(
                tap_url,
                params={"QUERY": adql, "FORMAT": "csv", "MAXREC": str(maxrec), "REQUEST": "doQuery", "LANG": "ADQL", "VERSION": "1.0"},
                timeout=60,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            text = r.text.strip()

            if r.status_code == 400:
                # Extract VOTable error message if present
                try:
                    root = ET.fromstring(text)
                    for el in root.iter():
                        if el.tag.endswith("INFO") and el.get("value") == "ERROR":
                            msg = (el.text or "").strip() or el.get("name","")
                            errors.append(f"ADQL error (400): {msg}")
                            raise ConnectionError("\n".join(errors))
                except ET.ParseError:
                    pass
                errors.append(f"HTTP 400: {text[:300]}")
                break

            if r.status_code != 200:
                errors.append(f"HTTP {r.status_code}: {text[:200]}")
                break

            # Check for XML/VOTable error in a 200 response
            if text.startswith("<?xml") or text.startswith("<VOTABLE") or "<INFO" in text[:300]:
                try:
                    root = ET.fromstring(text)
                    for el in root.iter():
                        if el.tag.endswith("INFO") and el.get("value") == "ERROR":
                            msg = (el.text or "").strip()
                            errors.append(f"TAP error: {msg}")
                            raise ConnectionError("\n".join(errors))
                except ET.ParseError:
                    pass
                errors.append(f"Unexpected XML response: {text[:200]}")
                break

            if text.upper().startswith("ERROR"):
                errors.append(text[:200])
                break

            df = pd.read_csv(StringIO(text), comment="#")
            return df

        except ConnectionError:
            raise
        except requests.exceptions.Timeout:
            errors.append(f"Timed out after 60s (attempt {attempt+1})")
            if attempt < retries - 1:
                time.sleep(3)
        except requests.exceptions.ConnectionError as e:
            errors.append(f"Connection error: {str(e)[:120]}")
            break
        except Exception as e:
            errors.append(f"{type(e).__name__}: {str(e)[:120]}")
            if attempt < retries - 1:
                time.sleep(2)

    raise ConnectionError("\n".join(errors) if errors else "Unknown TAP error")

@st.cache_data(ttl=3600)
def load_overview() -> pd.DataFrame:
    """🌌 Load confirmed exoplanets — no ORDER BY to avoid server 400."""
    adql = (
        "SELECT pl_name, hostname, pl_letter, disc_year, discoverymethod, "
        "pl_orbper, pl_rade, pl_masse, pl_eqt, pl_dens, "
        "pl_orbsmax, pl_orbeccen, "
        "st_teff, st_rad, st_mass, st_spectype, "
        "ra, dec, sy_snum, sy_pnum, sy_dist, "
        "pl_controv_flag "
        "FROM pscomppars "
        "WHERE pl_controv_flag = 0"
    )
    return tap_query(adql, maxrec=6000)

@st.cache_data(ttl=3600)
def load_discovery_stats() -> pd.DataFrame:
    """📊 Count planets per discovery method per year."""
    adql = (
        "SELECT discoverymethod, disc_year, count(*) as count "
        "FROM pscomppars "
        "WHERE pl_controv_flag = 0 AND disc_year IS NOT NULL "
        "GROUP BY discoverymethod, disc_year"
    )
    return tap_query(adql, maxrec=2000)

@st.cache_data(ttl=3600)
def search_planet(name: str) -> pd.DataFrame:
    """🔍 Search for a specific planet or host star by name."""
    safe = name.replace("'", "''")
    adql = (
        f"SELECT pl_name, hostname, discoverymethod, disc_year, "
        f"pl_rade, pl_masse, pl_eqt, pl_orbper, pl_orbsmax, "
        f"st_teff, st_spectype, sy_dist, ra, dec "
        f"FROM pscomppars "
        f"WHERE lower(pl_name) LIKE lower('%{safe}%') "
        f"OR lower(hostname) LIKE lower('%{safe}%')"
    )
    return tap_query(adql, maxrec=50)

@st.cache_data(ttl=3600)
def load_habitable_zone_candidates() -> pd.DataFrame:
    """🌱 Planets in/near the habitable zone."""
    adql = (
        "SELECT pl_name, hostname, pl_rade, pl_masse, pl_eqt, pl_orbper, "
        "pl_orbsmax, st_teff, discoverymethod, disc_year, "
        "st_spectype, sy_dist "
        "FROM pscomppars "
        "WHERE pl_eqt BETWEEN 200 AND 400 "
        "AND pl_rade < 2.5 "
        "AND pl_controv_flag = 0"
    )
    return tap_query(adql, maxrec=500)

# ══════════════════════════════════════════════════════════════════════════════
# 🎨  UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:20px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:22px;color:{color};
      font-weight:700;margin:4px 0">{value}</div>
      <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#475569;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def section_hdr(emoji, title, cap=""):
    st.markdown(
        f"<div style='font-size:12px;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:1.5px;color:#64748b;margin:28px 0 6px'>{emoji} {title}</div>",
        unsafe_allow_html=True)
    if cap:
        st.caption(cap)

def planet_card(row: pd.Series, color: str = ACCENT):
    """🪐 Render a planet info card."""
    name   = row.get("pl_name", "Unknown")
    host   = row.get("hostname", "—")
    method = row.get("discoverymethod", "—")
    year   = int(row["disc_year"]) if pd.notna(row.get("disc_year")) else "—"
    rade   = f"{row['pl_rade']:.2f} R⊕" if pd.notna(row.get("pl_rade")) else "—"
    masse  = f"{row['pl_masse']:.2f} M⊕" if pd.notna(row.get("pl_masse")) else "—"
    period = f"{row['pl_orbper']:.2f} days" if pd.notna(row.get("pl_orbper")) else "—"
    eqt    = f"{int(row['pl_eqt'])} K" if pd.notna(row.get("pl_eqt")) else "—"
    dist   = f"{row['sy_dist']:.1f} pc" if pd.notna(row.get("sy_dist")) else "—"
    spec   = str(row.get("st_spectype") or "").strip()

    method_color = DISC_COLORS.get(method, "#64748b")

    st.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-left:4px solid {color};
    border-radius:12px;padding:16px 18px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;
      flex-wrap:wrap;gap:6px;margin-bottom:10px">
        <div>
          <div style="font-family:'Orbitron',monospace;font-size:15px;font-weight:700;
          color:#e2e8f0">🪐 {name}</div>
          <div style="font-size:11px;color:#64748b;margin-top:2px;
          font-family:'Space Mono',monospace">⭐ {host} {f'· {spec[:4]}' if spec else ''}</div>
        </div>
        <div style="text-align:right">
          <span style="background:{method_color}18;border:1px solid {method_color}44;
          border-radius:20px;padding:3px 10px;font-size:10px;color:{method_color}">
            {method}</span>
          <div style="font-size:10px;color:#475569;margin-top:3px;
          font-family:'Space Mono',monospace">📅 {year}</div>
        </div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;
      font-family:'Space Mono',monospace">
        <span style="color:#22d3ee">📏 {rade}</span>
        <span style="color:#818cf8">⚖️ {masse}</span>
        <span style="color:#f59e0b">🔄 {period}</span>
        <span style="color:#f472b6">🌡️ {eqt}</span>
        <span style="color:#94a3b8">📡 {dist}</span>
      </div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  HEADER
# ══════════════════════════════════════════════════════════════════════════════
hl, hc, hr = st.columns([0.06, 0.70, 0.24])
with hl:
    st.markdown("""
    <div style="width:52px;height:52px;background:radial-gradient(circle,#0c4a6e,#0f172a);
    border:2px solid #22d3ee;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-family:'Space Mono',monospace;font-size:9px;font-weight:700;
    color:#22d3ee;letter-spacing:1px;box-shadow:0 0 20px rgba(34,211,238,.35);margin-top:6px">
Spaceport</div>""", unsafe_allow_html=True)
with hc:
    st.markdown("## 🪐 Spaceport | Exoplanet Archive")
    st.caption("Confirmed exoplanets beyond our solar system · NASA Exoplanet Archive TAP Service · California Institute of Technology")
with hr:
    st.markdown("""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(34,211,238,.1);border:1px solid rgba(34,211,238,.3);
      border-radius:20px;padding:4px 12px;font-size:12px;color:#22d3ee;font-weight:500">
      🌌 Live Archive</span></div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🪐 Exoplanet Controls")

    section = st.radio("🗂️ View", [
        "🌌 Overview & Stats",
        "🔭 Explorer",
        "🌱 Habitable Zone",
        "🔍 Planet Search",
        "📊 Custom Query",
    ], index=0)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#475569;line-height:2">
    <b style="color:#64748b">🌌 About the Archive</b><br>
    🏛️ NASA / Caltech IPAC<br>
    🪐 5,800+ confirmed planets<br>
    🔭 Kepler · TESS · Hubble<br>
    📅 Updated weekly<br>
    🌐 TAP / ADQL service
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data: [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/)")

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Load main dataset
# ══════════════════════════════════════════════════════════════════════════════
# Clear cache once on first run to bust any stale queries from previous versions
if "cache_cleared_v3" not in st.session_state:
    st.cache_data.clear()
    st.session_state["cache_cleared_v3"] = True

with st.spinner("🌌 Querying NASA Exoplanet Archive…"):
    try:
        df = load_overview()
    except Exception as e:
        err_str = str(e)
        is_timeout = "timeout" in err_str.lower()
        is_dns     = "name resolution" in err_str.lower() or "resolve" in err_str.lower()
        is_conn    = "connection error" in err_str.lower() or "refused" in err_str.lower()
        is_tap_err = "tap error" in err_str.lower() or "votable" in err_str.lower()

        st.error("🪐 Could not reach the NASA Exoplanet Archive", icon="🚨")

        if is_dns or is_conn:
            st.warning("🔌 **Network error** — your machine cannot reach `exoplanetarchive.ipac.caltech.edu`. Check your internet connection or VPN.")
        elif is_timeout:
            st.warning("⏱️ **Request timed out** — the archive is taking too long. It may be under heavy load. Try again in a minute.")
        elif is_tap_err:
            st.warning("⚙️ **TAP service error** — the archive returned an invalid response. This is usually temporary.")
        else:
            st.warning("⚠️ **Unknown error** — see details below.")

        st.info(
            "**Troubleshooting:**\n\n"
            "1. Open [exoplanetarchive.ipac.caltech.edu](https://exoplanetarchive.ipac.caltech.edu) in your browser to check if the site is up\n"
            "2. Test the TAP endpoint: [click here to test](https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT+pl_name+FROM+pscomppars&MAXREC=3&format=csv)\n"
            "3. If on a VPN, try disabling it — some VPNs block Caltech servers\n"
            "4. Check the [IPAC status page](https://status.ipac.caltech.edu)"
        )

        with st.expander("🔍 Technical error details"):
            st.code(err_str, language=None)

        if st.button("🔄 Retry", type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

if df.empty:
    st.warning("⚠️ No data returned from the Exoplanet Archive.")
    st.stop()

# ── Quick computed fields ──────────────────────────────────────────────────────
df["disc_year"] = pd.to_numeric(df["disc_year"], errors="coerce")
df["pl_rade"]   = pd.to_numeric(df["pl_rade"], errors="coerce")
df["pl_masse"]  = pd.to_numeric(df["pl_masse"], errors="coerce")
df["pl_eqt"]    = pd.to_numeric(df["pl_eqt"], errors="coerce")
df["sy_dist"]   = pd.to_numeric(df["sy_dist"], errors="coerce")
df["pl_orbper"] = pd.to_numeric(df["pl_orbper"], errors="coerce")
df["st_teff"]   = pd.to_numeric(df["st_teff"], errors="coerce")

# Planet size categories
def size_cat(r):
    if pd.isna(r):      return "Unknown"
    if r < 0.5:         return "Sub-Earth"
    if r < 1.25:        return "Earth-like"
    if r < 2.0:         return "Super-Earth"
    if r < 4.0:         return "Mini-Neptune"
    if r < 10.0:        return "Neptune-like"
    return "Jupiter+"

df["size_cat"] = df["pl_rade"].apply(size_cat)

# Stat totals
total_planets = len(df)
total_systems = df["hostname"].nunique()
total_methods = df["discoverymethod"].nunique()
latest_year   = int(df["disc_year"].max()) if df["disc_year"].notna().any() else "—"
total_hz      = ((df["pl_eqt"].between(200, 400)) & (df["pl_rade"] < 2.5)).sum()

# ── Stat strip ─────────────────────────────────────────────────────────────────
sc1,sc2,sc3,sc4,sc5 = st.columns(5)
stat_card(sc1,"🪐","Confirmed Planets", f"{total_planets:,}",   ACCENT)
stat_card(sc2,"⭐","Star Systems",      f"{total_systems:,}",   COL2)
stat_card(sc3,"🔭","Discovery Methods", total_methods,           COL3)
stat_card(sc4,"📅","Latest Discovery",  latest_year,             COL4)
stat_card(sc5,"🌱","HZ Candidates",     f"{total_hz:,}",        "#f472b6",
          "T_eq 200–400K, R<2.5R⊕")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_overview, tab_explorer, tab_hz, tab_search, tab_query = st.tabs([
    "🌌  Overview & Stats",
    "🔭  Explorer",
    "🌱  Habitable Zone",
    "🔍  Planet Search",
    "📊  Custom Query",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🌌  TAB 1 — OVERVIEW & STATS
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.markdown("### 🌌 Exoplanet Discovery Overview")
    st.caption(f"Showing {total_planets:,} confirmed exoplanets from the NASA Exoplanet Archive PSCompPars table")

    # ── Discovery methods donut ───────────────────────────────────────────────
    section_hdr("🔭","DISCOVERY METHOD BREAKDOWN","")
    dc1, dc2 = st.columns(2)

    with dc1:
        method_counts = df["discoverymethod"].value_counts().reset_index()
        method_counts.columns = ["method","count"]
        colors_list = [DISC_COLORS.get(m, "#64748b") for m in method_counts["method"]]

        fig_pie = go.Figure(go.Pie(
            labels=method_counts["method"],
            values=method_counts["count"],
            hole=0.52,
            marker=dict(colors=colors_list, line=dict(color="#04060f", width=2)),
            textinfo="percent+label",
            textfont=dict(size=11, family="Space Mono", color="#e2e8f0"),
            hovertemplate="<b>%{label}</b><br>Planets: %{value:,}<br>%{percent}<extra></extra>",
        ))
        fig_pie.update_layout(
            paper_bgcolor="#04060f", height=360,
            margin=dict(l=10,r=10,t=20,b=10),
            font=dict(family="Space Mono", color="#94a3b8"),
            showlegend=False,
            hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                            font=dict(color="#e2e8f0", size=12, family="Space Mono")),
            annotations=[dict(text=f"<b>{total_planets:,}</b><br>planets",
                              x=0.5,y=0.5,showarrow=False,
                              font=dict(size=14,color="#e2e8f0",family="Space Mono"))]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with dc2:
        # Size category donut
        size_counts = df["size_cat"].value_counts().reset_index()
        size_counts.columns = ["cat","count"]
        size_colors = {
            "Sub-Earth":"#94a3b8","Earth-like":"#22d3ee","Super-Earth":"#22c55e",
            "Mini-Neptune":"#818cf8","Neptune-like":"#f59e0b","Jupiter+":"#ef4444","Unknown":"#334155"
        }
        sc_colors = [size_colors.get(c,"#64748b") for c in size_counts["cat"]]
        fig_size = go.Figure(go.Pie(
            labels=size_counts["cat"], values=size_counts["count"],
            hole=0.52,
            marker=dict(colors=sc_colors, line=dict(color="#04060f", width=2)),
            textinfo="percent+label",
            textfont=dict(size=11, family="Space Mono", color="#e2e8f0"),
            hovertemplate="<b>%{label}</b><br>Planets: %{value:,}<extra></extra>",
        ))
        fig_size.update_layout(
            paper_bgcolor="#04060f", height=360,
            margin=dict(l=10,r=10,t=20,b=10),
            font=dict(family="Space Mono", color="#94a3b8"), showlegend=False,
            hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                            font=dict(color="#e2e8f0", size=12, family="Space Mono")),
            annotations=[dict(text="<b>By</b><br>size",
                              x=0.5,y=0.5,showarrow=False,
                              font=dict(size=14,color="#e2e8f0",family="Space Mono"))]
        )
        st.plotly_chart(fig_size, use_container_width=True)

    # ── Discovery timeline ────────────────────────────────────────────────────
    section_hdr("📅","DISCOVERY TIMELINE","Cumulative and annual planet discoveries by method")

    try:
        disc_stats = load_discovery_stats()
        disc_stats["disc_year"] = pd.to_numeric(disc_stats["disc_year"], errors="coerce")
        disc_stats = disc_stats.dropna(subset=["disc_year"])
        disc_stats["disc_year"] = disc_stats["disc_year"].astype(int)

        # Annual bar chart
        fig_tl = go.Figure()
        methods_sorted = disc_stats.groupby("discoverymethod")["count"].sum().sort_values(ascending=False).index

        for method in methods_sorted:
            mdf = disc_stats[disc_stats["discoverymethod"]==method].sort_values("disc_year")
            color = DISC_COLORS.get(method, "#64748b")
            fig_tl.add_trace(go.Bar(
                x=mdf["disc_year"], y=mdf["count"],
                name=method, marker_color=color, opacity=0.88,
                hovertemplate=f"<b>{method}</b><br>Year: %{{x}}<br>Planets: %{{y}}<extra></extra>",
            ))

        fig_tl.update_layout(
            barmode="stack",
            paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
            height=320, margin=dict(l=10,r=10,t=10,b=40),
            xaxis=dict(showgrid=False, color="#64748b",
                       tickfont=dict(family="Space Mono",size=10), dtick=5),
            yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10), title="Planets discovered"),
            legend=dict(bgcolor="rgba(15,22,38,0.9)", bordercolor="#1a2340", borderwidth=1,
                        font=dict(color="#94a3b8",size=10,family="Space Mono"),
                        orientation="v"),
            hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")),
        )
        st.plotly_chart(fig_tl, use_container_width=True)

        # Cumulative line
        annual = disc_stats.groupby("disc_year")["count"].sum().sort_index().reset_index()
        annual["cumulative"] = annual["count"].cumsum()
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=annual["disc_year"], y=annual["cumulative"],
            mode="lines", fill="tozeroy",
            line=dict(color=ACCENT, width=2.5),
            fillcolor="rgba(34,211,238,0.07)",
            hovertemplate="Year: %{x}<br>Total confirmed: %{y:,}<extra></extra>",
            name="Cumulative",
        ))
        fig_cum.update_layout(
            paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
            height=200, margin=dict(l=10,r=10,t=10,b=40),
            xaxis=dict(showgrid=False, color="#64748b",
                       tickfont=dict(family="Space Mono",size=10), dtick=5),
            yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10),
                       title="Cumulative count"),
            showlegend=False,
            hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")),
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ Could not load timeline data: {e}")

    # ── Top multi-planet systems ──────────────────────────────────────────────
    section_hdr("🌍","TOP MULTI-PLANET SYSTEMS","Host stars with the most confirmed planets")
    top_systems = (df.groupby("hostname")["pl_name"].count()
                     .sort_values(ascending=False).head(15).reset_index())
    top_systems.columns = ["⭐ Star", "🪐 Planet count"]

    fig_sys = go.Figure(go.Bar(
        x=top_systems["🪐 Planet count"],
        y=top_systems["⭐ Star"],
        orientation="h",
        marker=dict(
            color=top_systems["🪐 Planet count"],
            colorscale=[[0,"#0c4a6e"],[0.5,"#22d3ee"],[1,"#a5f3fc"]],
            showscale=False,
        ),
        hovertemplate="<b>%{y}</b><br>Planets: %{x}<extra></extra>",
    ))
    fig_sys.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=380, margin=dict(l=10,r=10,t=10,b=10),
        xaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                   tickfont=dict(family="Space Mono",size=10), title="Number of planets"),
        yaxis=dict(showgrid=False, color="#94a3b8",
                   tickfont=dict(family="Space Mono",size=10), autorange="reversed"),
        hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")),
    )
    st.plotly_chart(fig_sys, use_container_width=True)

    # ── Distance histogram ────────────────────────────────────────────────────
    section_hdr("📡","DISTANCE DISTRIBUTION","How far away are known exoplanets? (parsecs)")
    dist_data = df["sy_dist"].dropna()
    dist_data = dist_data[dist_data < 5000]   # clip extreme outliers
    fig_dist = go.Figure(go.Histogram(
        x=dist_data, nbinsx=80,
        marker=dict(color=COL2, opacity=0.85, line=dict(color="#04060f",width=0.5)),
        hovertemplate="Distance: %{x:.0f} pc<br>Planets: %{y}<extra></extra>",
    ))
    fig_dist.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=240, margin=dict(l=10,r=10,t=10,b=40),
        xaxis=dict(showgrid=False, color="#64748b",
                   tickfont=dict(family="Space Mono",size=10), title="Distance (parsecs)"),
        yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                   tickfont=dict(family="Space Mono",size=10), title="Count"),
        showlegend=False,
        hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")),
    )
    st.plotly_chart(fig_dist, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔭  TAB 2 — EXPLORER (interactive scatter diagrams)
# ══════════════════════════════════════════════════════════════════════════════
with tab_explorer:
    st.markdown("### 🔭 Exoplanet Explorer")
    st.caption("Interactive scatter diagrams — hover any dot for planet details")

    # Controls
    ec1, ec2, ec3 = st.columns(3)
    x_axis  = ec1.selectbox("📐 X axis", [
        "pl_orbper","pl_rade","pl_masse","pl_eqt","st_teff","sy_dist","pl_orbsmax"
    ], format_func=lambda c: {
        "pl_orbper":"Orbital Period (days)","pl_rade":"Planet Radius (R⊕)",
        "pl_masse":"Planet Mass (M⊕)","pl_eqt":"Equilibrium Temp (K)",
        "st_teff":"Star Temperature (K)","sy_dist":"System Distance (pc)",
        "pl_orbsmax":"Semi-major Axis (AU)",
    }.get(c, c))
    y_axis  = ec2.selectbox("📐 Y axis", [
        "pl_rade","pl_masse","pl_eqt","pl_orbper","st_teff","sy_dist","pl_orbsmax"
    ], format_func=lambda c: {
        "pl_rade":"Planet Radius (R⊕)","pl_masse":"Planet Mass (M⊕)",
        "pl_eqt":"Equilibrium Temp (K)","pl_orbper":"Orbital Period (days)",
        "st_teff":"Star Temperature (K)","sy_dist":"System Distance (pc)",
        "pl_orbsmax":"Semi-major Axis (AU)",
    }.get(c, c))
    color_by = ec3.selectbox("🎨 Color by", ["discoverymethod","size_cat","disc_year"])

    # Filter
    fc1, fc2, fc3 = st.columns(3)
    methods_avail = sorted(df["discoverymethod"].dropna().unique())
    sel_methods = fc1.multiselect("🔭 Methods", methods_avail, default=methods_avail[:6])
    year_range = fc2.slider("📅 Discovery year", int(df["disc_year"].min() or 1990),
                             int(df["disc_year"].max() or 2025), (2000, int(df["disc_year"].max() or 2025)))
    max_dist = fc3.slider("📡 Max distance (pc)", 10, 5000, 2000, step=50)

    # Filter dataframe
    plot_df = df.copy()
    plot_df = plot_df[plot_df["discoverymethod"].isin(sel_methods)]
    plot_df = plot_df[plot_df["disc_year"].between(year_range[0], year_range[1])]
    plot_df = plot_df[plot_df["sy_dist"].fillna(0) <= max_dist]
    plot_df = plot_df.dropna(subset=[x_axis, y_axis])

    st.markdown(f"<div style='font-size:11px;color:#64748b;margin-bottom:8px'>"
                f"📊 Showing {len(plot_df):,} of {total_planets:,} planets</div>",
                unsafe_allow_html=True)

    if not plot_df.empty:
        if color_by == "disc_year":
            color_vals = plot_df["disc_year"]
            color_scale = [[0,"#0c4a6e"],[0.5,"#22d3ee"],[1,"#a5f3fc"]]
            color_arg = dict(color=color_vals, colorscale=color_scale,
                             colorbar=dict(title="Year",
                                           tickfont=dict(family="Space Mono",size=9,color="#94a3b8"),
                                           titlefont=dict(family="Space Mono",size=10,color="#94a3b8")))
        elif color_by == "size_cat":
            size_colors_list = [size_colors.get(c,"#64748b") for c in plot_df["size_cat"]]
            color_arg = dict(color=size_colors_list)
        else:
            method_colors_list = [DISC_COLORS.get(m,"#64748b") for m in plot_df["discoverymethod"]]
            color_arg = dict(color=method_colors_list)

        hover_text = (
            "<b>" + plot_df["pl_name"].fillna("?") + "</b><br>"
            + "⭐ " + plot_df["hostname"].fillna("?") + "<br>"
            + "🔭 " + plot_df["discoverymethod"].fillna("?") + "<br>"
            + "📅 " + plot_df["disc_year"].fillna(0).astype(int).astype(str) + "<br>"
            + "📏 R=" + plot_df["pl_rade"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—") + " R⊕<br>"
            + "⚖️ M=" + plot_df["pl_masse"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—") + " M⊕<br>"
            + "🌡️ T=" + plot_df["pl_eqt"].map(lambda v: f"{int(v)}" if pd.notna(v) else "—") + " K"
        )

        fig_scatter = go.Figure(go.Scatter(
            x=plot_df[x_axis], y=plot_df[y_axis],
            mode="markers",
            marker=dict(size=5, opacity=0.75, **color_arg,
                        line=dict(color="rgba(0,0,0,0.2)", width=0.5)),
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
        ))

        xtype = "log" if x_axis in ("pl_orbper","pl_masse","sy_dist","pl_orbsmax") else "linear"
        ytype = "log" if y_axis in ("pl_orbper","pl_masse","sy_dist","pl_orbsmax") else "linear"

        axis_labels = {
            "pl_orbper":"Orbital Period (days)","pl_rade":"Planet Radius (R⊕)",
            "pl_masse":"Planet Mass (M⊕)","pl_eqt":"Equilibrium Temperature (K)",
            "st_teff":"Star Temperature (K)","sy_dist":"System Distance (pc)",
            "pl_orbsmax":"Semi-major Axis (AU)",
        }
        fig_scatter.update_layout(
            paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
            height=520, margin=dict(l=10,r=10,t=20,b=40),
            xaxis=dict(type=xtype, showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10),
                       title=axis_labels.get(x_axis, x_axis)),
            yaxis=dict(type=ytype, showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10),
                       title=axis_labels.get(y_axis, y_axis)),
            hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")),
        )
        st.plotly_chart(fig_scatter, use_container_width=True,
                        config={"scrollZoom":True,"displayModeBar":True,
                                "modeBarButtonsToRemove":["select2d","lasso2d"]})

        # ── Sky position map ──────────────────────────────────────────────────
        section_hdr("🌐","SKY DISTRIBUTION","RA/Dec positions of filtered exoplanets (equatorial coordinates)")
        sky_df = plot_df.dropna(subset=["ra","dec"])
        if not sky_df.empty:
            sky_colors = [DISC_COLORS.get(m,"#64748b") for m in sky_df["discoverymethod"]]
            fig_sky = go.Figure(go.Scattergeo(
                lon=sky_df["ra"], lat=sky_df["dec"],
                mode="markers",
                marker=dict(size=3, color=sky_colors, opacity=0.7),
                text=sky_df["pl_name"],
                hovertemplate="<b>%{text}</b><br>RA: %{lon:.2f}°<br>Dec: %{lat:.2f}°<extra></extra>",
            ))
            fig_sky.update_geos(
                projection_type="mollweide",
                bgcolor="#04060f",
                showframe=False,
                showcoastlines=False,
                showland=False,
                showocean=False,
                lataxis_showgrid=True,
                lonaxis_showgrid=True,
                lataxis_gridcolor="#1a2340",
                lonaxis_gridcolor="#1a2340",
            )
            fig_sky.update_layout(
                paper_bgcolor="#04060f",
                height=380, margin=dict(l=0,r=0,t=20,b=0),
                hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                                font=dict(color="#e2e8f0",size=12,family="Space Mono")),
                geo=dict(bgcolor="#04060f",
                         lataxis=dict(showgrid=True,gridcolor="#1a2340"),
                         lonaxis=dict(showgrid=True,gridcolor="#1a2340")),
            )
            st.plotly_chart(fig_sky, use_container_width=True)
    else:
        st.info("No planets match the current filters.")

# ══════════════════════════════════════════════════════════════════════════════
# 🌱  TAB 3 — HABITABLE ZONE
# ══════════════════════════════════════════════════════════════════════════════
with tab_hz:
    st.markdown("### 🌱 Habitable Zone Candidates")
    st.caption("Planets with equilibrium temperatures 200–400 K and radii < 2.5 R⊕ — potential rocky worlds in temperate orbits")

    with st.spinner("🌱 Loading habitable zone candidates…"):
        try:
            hz_df = load_habitable_zone_candidates()
            hz_df["pl_rade"]  = pd.to_numeric(hz_df["pl_rade"], errors="coerce")
            hz_df["pl_eqt"]   = pd.to_numeric(hz_df["pl_eqt"], errors="coerce")
            hz_df["pl_masse"] = pd.to_numeric(hz_df["pl_masse"], errors="coerce")
            hz_df["sy_dist"]  = pd.to_numeric(hz_df["sy_dist"], errors="coerce")
            hz_df["st_teff"]  = pd.to_numeric(hz_df["st_teff"], errors="coerce")
        except Exception as e:
            st.warning(f"⚠️ {e}")
            hz_df = pd.DataFrame()

    if not hz_df.empty:
        hz1,hz2,hz3,hz4 = st.columns(4)
        stat_card(hz1,"🌱","HZ Candidates",     len(hz_df),                                                       "#22c55e")
        stat_card(hz2,"📏","Smallest radius",    f"{hz_df['pl_rade'].min():.2f} R⊕" if hz_df["pl_rade"].notna().any() else "—", "#22d3ee")
        stat_card(hz3,"🌡️","Coolest (T_eq)",     f"{int(hz_df['pl_eqt'].min())} K" if hz_df["pl_eqt"].notna().any() else "—",  "#818cf8")
        stat_card(hz4,"📡","Nearest system",     f"{hz_df['sy_dist'].min():.1f} pc" if hz_df["sy_dist"].notna().any() else "—", "#f59e0b")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── HZ scatter: Radius vs Equilibrium Temp ────────────────────────────
        section_hdr("🌡️","RADIUS vs EQUILIBRIUM TEMPERATURE",
                    "Shaded band shows the 'classic' habitable zone (273–373 K)")

        fig_hz = go.Figure()

        # HZ band
        fig_hz.add_shape(type="rect", x0=273, x1=373, y0=0, y1=2.5,
                         fillcolor="rgba(34,197,94,0.07)",
                         line=dict(width=0), layer="below")
        fig_hz.add_vline(x=288, line=dict(color="#22c55e", width=1, dash="dot"))
        fig_hz.add_annotation(x=288, y=2.4, text="Earth T_eq",
                               font=dict(color="#22c55e",size=9,family="Space Mono"),
                               showarrow=False)

        hz_plot = hz_df.dropna(subset=["pl_eqt","pl_rade"])
        method_colors_hz = [DISC_COLORS.get(m,"#64748b") for m in hz_plot.get("discoverymethod",["—"]*len(hz_plot))]
        hover_hz = (
            "<b>" + hz_plot["pl_name"].fillna("?") + "</b><br>"
            + "⭐ " + hz_plot["hostname"].fillna("?") + "<br>"
            + "📏 " + hz_plot["pl_rade"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—") + " R⊕<br>"
            + "🌡️ " + hz_plot["pl_eqt"].map(lambda v: f"{int(v)}" if pd.notna(v) else "—") + " K<br>"
            + "📡 " + hz_plot["sy_dist"].map(lambda v: f"{v:.1f}" if pd.notna(v) else "—") + " pc"
        )
        fig_hz.add_trace(go.Scatter(
            x=hz_plot["pl_eqt"], y=hz_plot["pl_rade"],
            mode="markers",
            marker=dict(size=10, color=method_colors_hz, opacity=0.85,
                        line=dict(color="rgba(255,255,255,0.3)",width=1)),
            text=hover_hz,
            hovertemplate="%{text}<extra></extra>",
        ))

        # Earth reference
        fig_hz.add_trace(go.Scatter(
            x=[288], y=[1.0], mode="markers+text",
            marker=dict(size=14, color="#22d3ee", symbol="star",
                        line=dict(color="#a5f3fc",width=2)),
            text=["🌍"], textposition="top right",
            hovertemplate="<b>🌍 Earth</b><br>T_eq=288K<br>R=1.0 R⊕<extra></extra>",
            name="Earth",
        ))

        fig_hz.update_layout(
            paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
            height=480, margin=dict(l=10,r=10,t=10,b=40),
            showlegend=False,
            xaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10),
                       title="Equilibrium Temperature (K)"),
            yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10),
                       title="Planet Radius (R⊕)", range=[0, 2.6]),
            hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")),
        )
        st.plotly_chart(fig_hz, use_container_width=True,
                        config={"scrollZoom":True})

        # ── HZ candidate cards ────────────────────────────────────────────────
        section_hdr("🌿","CANDIDATE PLANET CARDS",f"{len(hz_df)} planets sorted by equilibrium temperature")
        hz_sorted = hz_df.sort_values("pl_eqt")
        for i in range(0, min(len(hz_sorted), 20), 2):
            c1, c2 = st.columns(2)
            with c1:
                planet_card(hz_sorted.iloc[i], color="#22c55e")
            if i+1 < len(hz_sorted):
                with c2:
                    planet_card(hz_sorted.iloc[i+1], color="#22c55e")

        if len(hz_sorted) > 20:
            st.caption(f"ℹ️ Showing 20 of {len(hz_sorted)} candidates. Use 🔍 Planet Search or 📊 Custom Query for more.")

        # ── Full HZ table ─────────────────────────────────────────────────────
        section_hdr("📋","FULL CANDIDATE TABLE","")
        hz_tbl = hz_df[["pl_name","hostname","pl_rade","pl_masse","pl_eqt",
                         "pl_orbper","sy_dist","discoverymethod","disc_year","st_spectype"]].copy()
        hz_tbl.columns = ["🪐 Planet","⭐ Host","📏 R(R⊕)","⚖️ M(M⊕)","🌡️ T_eq(K)",
                           "🔄 Period(d)","📡 Dist(pc)","🔭 Method","📅 Year","🌟 Spec"]
        st.dataframe(hz_tbl.round(2), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download HZ candidates CSV",
                           hz_tbl.to_csv(index=False), "hz_candidates.csv","text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# 🔍  TAB 4 — PLANET SEARCH
# ══════════════════════════════════════════════════════════════════════════════
with tab_search:
    st.markdown("### 🔍 Planet & Star Search")
    st.caption("Search the NASA Exoplanet Archive by planet name or host star name")

    sc1, sc2 = st.columns([3,1])
    search_term = sc1.text_input("🔍 Enter planet or star name",
                                 placeholder="e.g. Kepler-22 b, TRAPPIST-1, HD 209458")
    do_search   = sc2.button("🚀 Search", type="primary", use_container_width=True)

    if search_term and do_search:
        with st.spinner(f"🔍 Searching for '{search_term}'…"):
            try:
                results = search_planet(search_term)
                results["pl_rade"]  = pd.to_numeric(results.get("pl_rade",  pd.Series()), errors="coerce")
                results["pl_masse"] = pd.to_numeric(results.get("pl_masse", pd.Series()), errors="coerce")
                results["pl_eqt"]   = pd.to_numeric(results.get("pl_eqt",   pd.Series()), errors="coerce")
                results["pl_orbper"]= pd.to_numeric(results.get("pl_orbper",pd.Series()), errors="coerce")
                results["sy_dist"]  = pd.to_numeric(results.get("sy_dist",  pd.Series()), errors="coerce")
            except Exception as e:
                st.error(f"⚠️ Search failed: {e}")
                results = pd.DataFrame()

        if results.empty:
            st.info(f"⚠️ No results found for '{search_term}'.")
        else:
            st.success(f"✅ Found {len(results)} result(s) for '{search_term}'")

            if len(results) == 1:
                # ── Single planet detailed view ───────────────────────────────
                row = results.iloc[0]
                st.markdown(f"### 🪐 {row.get('pl_name','')}")

                dc1, dc2, dc3, dc4 = st.columns(4)
                stat_card(dc1,"📏","Radius", f"{row['pl_rade']:.2f} R⊕" if pd.notna(row.get('pl_rade')) else "—", ACCENT)
                stat_card(dc2,"⚖️","Mass",   f"{row['pl_masse']:.2f} M⊕" if pd.notna(row.get('pl_masse')) else "—", COL2)
                stat_card(dc3,"🌡️","T_eq",   f"{int(row['pl_eqt'])} K"   if pd.notna(row.get('pl_eqt'))   else "—", COL3)
                stat_card(dc4,"🔄","Period", f"{row['pl_orbper']:.2f} d"  if pd.notna(row.get('pl_orbper')) else "—", COL4)

                st.markdown("<br>", unsafe_allow_html=True)

                # All fields table
                all_fields = {k: v for k,v in row.items() if pd.notna(v) and str(v).strip()}
                field_df = pd.DataFrame(list(all_fields.items()), columns=["Field","Value"])
                st.dataframe(field_df, use_container_width=True, hide_index=True)

            else:
                # ── Multiple results as cards ─────────────────────────────────
                for i in range(0, len(results), 2):
                    c1, c2 = st.columns(2)
                    with c1:
                        planet_card(results.iloc[i])
                    if i+1 < len(results):
                        with c2:
                            planet_card(results.iloc[i+1])

                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(results[["pl_name","hostname","discoverymethod","disc_year",
                                       "pl_rade","pl_masse","pl_eqt","pl_orbper","sy_dist"]].round(3),
                             use_container_width=True, hide_index=True)
                st.download_button("⬇️ Download search results",
                                   results.to_csv(index=False),
                                   "exoplanet_search.csv","text/csv")

    elif not search_term:
        # ── Popular planets quick links ───────────────────────────────────────
        section_hdr("⭐","POPULAR EXOPLANETS","Click a card to prefill the search")
        famous = [
            ("🪐 Kepler-22 b",   "First confirmed in the HZ of a sun-like star",  "#22d3ee"),
            ("🌍 TRAPPIST-1 e",  "Rocky HZ planet around an ultracool dwarf",      "#22c55e"),
            ("🌊 K2-18 b",       "Mini-Neptune with detected water vapour",         "#818cf8"),
            ("🔥 55 Cnc e",      "Ultra-hot super-Earth, 1 year = 18 hours",        "#f59e0b"),
            ("⭐ HD 209458 b",   "First transiting exoplanet confirmed",            "#f472b6"),
            ("🌙 Proxima Cen b", "Nearest known exoplanet, ~4.2 light-years",       "#34d399"),
        ]
        fc1, fc2, fc3 = st.columns(3)
        for idx, (name, desc, color) in enumerate(famous):
            col = [fc1, fc2, fc3][idx % 3]
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
            border-radius:10px;padding:14px;margin-bottom:10px">
              <div style="font-family:'Orbitron',monospace;font-size:12px;font-weight:700;
              color:#e2e8f0;margin-bottom:4px">{name}</div>
              <div style="font-size:11px;color:#64748b;line-height:1.5">{desc}</div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📊  TAB 5 — CUSTOM QUERY
# ══════════════════════════════════════════════════════════════════════════════
with tab_query:
    st.markdown("### 📊 Custom ADQL Query")
    st.caption("Write your own SQL/ADQL query against the NASA Exoplanet Archive TAP service")

    # Presets
    presets = {
        "🪐 All confirmed planets (100 recent)":
            "SELECT pl_name, hostname, discoverymethod, disc_year,\n"
            "       pl_rade, pl_masse, pl_eqt, pl_orbper, sy_dist\n"
            "FROM pscomppars\n"
            "WHERE pl_controv_flag = 0",
        "🌍 Earth-size planets (R < 1.5 R⊕)":
            "SELECT pl_name, hostname, pl_rade, pl_masse, pl_eqt,\n"
            "       pl_orbper, sy_dist, discoverymethod, disc_year\n"
            "FROM pscomppars\n"
            "WHERE pl_rade < 1.5 AND pl_controv_flag = 0",
        "🔭 TESS discoveries":
            "SELECT pl_name, hostname, pl_rade, pl_masse, pl_eqt,\n"
            "       disc_year, sy_dist, st_teff\n"
            "FROM pscomppars\n"
            "WHERE disc_facility LIKE '%TESS%'\n"
            "  AND pl_controv_flag = 0",
        "⭐ Multi-planet systems (≥4 planets)":
            "SELECT hostname, count(pl_name) as num_planets,\n"
            "       min(pl_rade) as min_radius, max(pl_rade) as max_radius,\n"
            "       min(pl_orbper) as inner_period, max(pl_orbper) as outer_period\n"
            "FROM pscomppars\n"
            "WHERE pl_controv_flag = 0\n"
            "GROUP BY hostname\n"
            "HAVING count(pl_name) >= 4",
        "🌡️ Hot Jupiters (P < 10 days, R > 8 R⊕)":
            "SELECT pl_name, hostname, pl_rade, pl_masse, pl_orbper,\n"
            "       pl_eqt, st_teff, sy_dist, discoverymethod\n"
            "FROM pscomppars\n"
            "WHERE pl_orbper < 10 AND pl_rade > 8\n"
            "  AND pl_controv_flag = 0",
    }

    preset_choice = st.selectbox("📋 Load a preset query", ["— write your own —"] + list(presets.keys()))
    default_query = presets.get(preset_choice, "SELECT pl_name, hostname, pl_rade, pl_masse\nFROM pscomppars\nWHERE pl_controv_flag = 0")

    adql_input = st.text_area("📝 ADQL Query", value=default_query, height=160,
                               help="Standard ADQL syntax. Do NOT use ORDER BY or TOP — use MAXREC param instead.")

    qr1, qr2, qr3 = st.columns([1, 1, 3])
    run_query = qr1.button("🚀 Run Query", type="primary", use_container_width=True)
    q_maxrec  = qr2.number_input("Max rows", min_value=10, max_value=5000, value=100, step=50)
    qr3.markdown("<div style='padding-top:8px;font-size:11px;color:#475569'>"
                 "⚠️ Avoid <code>ORDER BY</code> and <code>TOP</code> — use the Max rows control above instead</div>",
                 unsafe_allow_html=True)

    if "query_result" not in st.session_state:
        st.session_state.query_result = None

    if run_query and adql_input.strip():
        with st.spinner("🌌 Running query against NASA Exoplanet Archive…"):
            try:
                result_df = tap_query(adql_input.strip(), maxrec=int(q_maxrec), retries=2)
                st.session_state.query_result = result_df
            except Exception as e:
                st.error(f"⚠️ Query failed: {e}")
                st.session_state.query_result = None

    if st.session_state.query_result is not None:
        qdf = st.session_state.query_result
        st.success(f"✅ Query returned {len(qdf):,} rows · {len(qdf.columns)} columns")

        # Auto-visualise if numeric columns present
        num_cols = qdf.select_dtypes(include="number").columns.tolist()
        if len(num_cols) >= 2:
            vc1, vc2 = st.columns(2)
            vx = vc1.selectbox("📐 Plot X", num_cols, key="qx")
            vy = vc2.selectbox("📐 Plot Y", num_cols, index=min(1,len(num_cols)-1), key="qy")

            pdata = qdf.dropna(subset=[vx, vy])
            if not pdata.empty:
                fig_q = go.Figure(go.Scatter(
                    x=pdata[vx], y=pdata[vy],
                    mode="markers",
                    marker=dict(size=6, color=ACCENT, opacity=0.8,
                                line=dict(color="rgba(0,0,0,0.2)",width=0.5)),
                    text=pdata.iloc[:,0].astype(str) if len(pdata.columns) > 0 else None,
                    hovertemplate="%{text}<br>X: %{x}<br>Y: %{y}<extra></extra>",
                ))
                fig_q.update_layout(
                    paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
                    height=380, margin=dict(l=10,r=10,t=10,b=40),
                    xaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                               tickfont=dict(family="Space Mono",size=10), title=vx),
                    yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                               tickfont=dict(family="Space Mono",size=10), title=vy),
                    hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                                    font=dict(color="#e2e8f0",size=12,family="Space Mono")),
                )
                st.plotly_chart(fig_q, use_container_width=True)

        st.dataframe(qdf, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download results CSV",
                           qdf.to_csv(index=False), "exoplanet_query.csv","text/csv")

        # Schema reference
        with st.expander("📚 Key column reference"):
            st.markdown("""
            | Column | Description |
            |--------|-------------|
            | `pl_name` | Planet name |
            | `hostname` | Host star name |
            | `discoverymethod` | Transit, Radial Velocity, etc. |
            | `disc_year` | Year of discovery |
            | `pl_rade` | Planet radius (Earth radii) |
            | `pl_masse` | Planet mass (Earth masses) |
            | `pl_bmasse` | Planet mass or M sin i (Earth masses) |
            | `pl_eqt` | Equilibrium temperature (K) |
            | `pl_orbper` | Orbital period (days) |
            | `pl_orbsmax` | Semi-major axis (AU) |
            | `pl_orbeccen` | Orbital eccentricity |
            | `st_teff` | Stellar effective temperature (K) |
            | `st_rad` | Stellar radius (solar) |
            | `st_mass` | Stellar mass (solar) |
            | `sy_dist` | System distance (parsecs) |
            | `sy_pnum` | Number of planets in system |
            | `ra`, `dec` | Right Ascension, Declination (degrees) |
            """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#64748b;line-height:1.9">
    <b style="color:#94a3b8">🪐 About the NASA Exoplanet Archive</b> — The NASA Exoplanet Archive
    is an online astronomical exoplanet and stellar catalog operated by the California Institute
    of Technology under contract with NASA. Data are accessed via the IVOA-compliant
    Table Access Protocol (TAP) service using ADQL queries against the PSCompPars
    (Planetary Systems Composite Parameters) table — one row per confirmed planet.
    The archive is updated regularly as new discoveries are published and vetted.
    &nbsp;·&nbsp;
    <a href="https://exoplanetarchive.ipac.caltech.edu" target="_blank"
    style="color:#22d3ee;text-decoration:none">🌐 exoplanetarchive.ipac.caltech.edu ↗</a>
    &nbsp;·&nbsp;
    TAP endpoint: <span style="font-family:'Space Mono',monospace;color:#22d3ee">
    https://exoplanetarchive.ipac.caltech.edu/TAP/sync</span>
  </div>
</div>""", unsafe_allow_html=True)
