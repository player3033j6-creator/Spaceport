import streamlit as st
import requests
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Spaceport | EONET", page_icon="🌍", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="metric-container"] { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
[data-testid="stSidebar"] { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stTabs"] button { color:#64748b !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#22c55e !important; border-bottom-color:#22c55e !important; }
h1,h2,h3 { color:#e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
API_KEY    = "JmhRPeN6wrcctvZpQ7jVmw3A1RKwvL2SsjodCndq"
EONET_BASE = "https://eonet.gsfc.nasa.gov/api/v3"

# Category metadata: id → (emoji, display name, colour, description)
CAT_META = {
    "drought":       ("🏜️",  "Drought",              "#f59e0b", "Prolonged absence of precipitation"),
    "dustHaze":      ("🌫️",  "Dust & Haze",           "#d97706", "Dust storms and air-pollution plumes"),
    "earthquakes":   ("🌋",  "Earthquakes",           "#ef4444", "Seismic events of all magnitudes"),
    "floods":        ("🌊",  "Floods",                "#3b82f6", "River and coastal inundation"),
    "landslides":    ("⛰️",  "Landslides",            "#a16207", "Mudslides, rockfalls, avalanches"),
    "manmade":       ("🏭",  "Manmade",               "#64748b", "Human-induced extreme events"),
    "seaLakeIce":    ("🧊",  "Sea & Lake Ice",        "#67e8f9", "Arctic/Antarctic sea-ice anomalies"),
    "severeStorms":  ("⛈️",  "Severe Storms",         "#a855f7", "Cyclones, typhoons, hurricanes"),
    "snow":          ("❄️",  "Snow",                  "#93c5fd", "Extreme or anomalous snowfall"),
    "tempExtremes":  ("🌡️",  "Temp Extremes",         "#fb923c", "Heat waves and cold snaps"),
    "volcanoes":     ("🌋",  "Volcanoes",             "#dc2626", "Eruptions and ash/gas plumes"),
    "waterColor":    ("💧",  "Water Color",           "#0ea5e9", "Algal blooms and turbidity"),
    "wildfires":     ("🔥",  "Wildfires",             "#f97316", "Active wildland fires"),
}

def cat_emoji(cat_id): return CAT_META.get(cat_id,("🌐","Unknown","#64748b",""))[0]
def cat_name(cat_id):  return CAT_META.get(cat_id,("🌐",cat_id.title(),"#64748b",""))[1]
def cat_color(cat_id): return CAT_META.get(cat_id,("🌐","Unknown","#64748b",""))[2]

# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def fetch_events(status="open", days=30, limit=500, category=None):
    params = {"status": status, "limit": limit, "api_key": API_KEY}
    if status == "closed":
        end   = date.today()
        start = end - timedelta(days=days)
        params["start"] = str(start)
        params["end"]   = str(end)
    url = f"{EONET_BASE}/events"
    if category:
        url = f"{EONET_BASE}/categories/{category}"
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("events", [])

@st.cache_data(ttl=86400)
def fetch_categories():
    resp = requests.get(f"{EONET_BASE}/categories", params={"api_key": API_KEY}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("categories", [])

def parse_events(raw_events):
    rows = []
    for evt in raw_events:
        cats = evt.get("categories", [])
        cat_id    = cats[0]["id"]    if cats else "unknown"
        cat_title = cats[0]["title"] if cats else "Unknown"
        geom = evt.get("geometry", [])
        lat, lon, gdate = None, None, None
        if geom:
            g = geom[-1]  # most recent geometry
            gdate = (g.get("date","") or "")[:10]
            coords = g.get("coordinates")
            gtype  = g.get("type","Point")
            if coords:
                if gtype == "Point" and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                elif gtype in ("Polygon","LineString") and coords:
                    # take centroid of first ring
                    ring = coords[0] if gtype == "Polygon" else coords
                    try:
                        lon = sum(p[0] for p in ring) / len(ring)
                        lat = sum(p[1] for p in ring) / len(ring)
                    except: pass
        sources = evt.get("sources", [])
        src_url = sources[0].get("url","") if sources else ""
        rows.append({
            "ID":        evt.get("id",""),
            "Title":     evt.get("title",""),
            "Category":  cat_title,
            "Cat ID":    cat_id,
            "Status":    evt.get("closed") and "Closed" or "Open",
            "Date":      gdate or "",
            "Lat":       lat,
            "Lon":       lon,
            "Geometries": len(geom),
            "Source URL": src_url,
        })
    return pd.DataFrame(rows)

# ── UI helpers ────────────────────────────────────────────────────────────────
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:22px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:26px;color:{color};
      font-weight:700;margin:4px 0">{value}</div>
      <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#475569;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def event_card(row):
    color  = cat_color(row["Cat ID"])
    emoji  = cat_emoji(row["Cat ID"])
    status_badge = (
        f'<span style="background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);'
        f'border-radius:20px;padding:2px 8px;font-size:10px;color:#ef4444">● OPEN</span>'
        if row["Status"] == "Open" else
        f'<span style="background:rgba(100,116,139,.15);border:1px solid rgba(100,116,139,.4);'
        f'border-radius:20px;padding:2px 8px;font-size:10px;color:#64748b">✓ CLOSED</span>'
    )
    coords = f"{row['Lat']:.2f}°, {row['Lon']:.2f}°" if row["Lat"] is not None else "No coordinates"
    src_html = (f'<a href="{row["Source URL"]}" target="_blank" style="color:{color};font-size:10px;'
                f'text-decoration:none">🔗 Source</a>' if row["Source URL"] else "")
    return f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-left:3px solid {color};
    border-radius:12px;padding:14px 16px;margin-bottom:9px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">
        <div style="flex:1;min-width:0">
          <div style="font-size:14px;font-weight:600;color:#e2e8f0">{emoji} {row['Title']}</div>
          <div style="font-size:10px;color:#64748b;font-family:'Space Mono',monospace;margin-top:3px">
            {row['ID']} &nbsp;·&nbsp; {row['Date'] or '—'} &nbsp;·&nbsp; {coords}
          </div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;flex-shrink:0">
          <span style="background:{color}22;border:1px solid {color}55;border-radius:20px;
          padding:2px 10px;font-size:10px;font-weight:600;color:{color}">{row['Category']}</span>
          {status_badge}
          {src_html}
        </div>
      </div>
    </div>"""

def section_hdr(title, cap=""):
    st.markdown(f"<div style='font-size:12px;font-weight:600;text-transform:uppercase;"
                f"letter-spacing:1.5px;color:#64748b;margin:24px 0 4px'>{title}</div>",
                unsafe_allow_html=True)
    if cap: st.caption(cap)

# ── MAP LAYOUT defaults ───────────────────────────────────────────────────────
LEGEND_STYLE = dict(bgcolor="rgba(15,22,38,0.9)", bordercolor="#1a2340", borderwidth=1,
                    font=dict(color="#94a3b8", size=11, family="Space Mono"))

GEO_LAYOUT = dict(
    paper_bgcolor="#04060f",
    margin=dict(l=0,r=0,t=40,b=0),
    font=dict(family="Space Mono", color="#94a3b8"),
    hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                    font=dict(color="#e2e8f0", size=12, family="Space Mono")),
    geo=dict(
        bgcolor="#04060f",
        landcolor="#0d1b2a",
        oceancolor="#04060f",
        showocean=True, showland=True,
        showcountries=True, countrycolor="#1a2340",
        showcoastlines=True, coastlinecolor="#1e3a5f",
        showframe=False,
        projection_type="natural earth",
    ),
)

MAP_CFG = {"scrollZoom":True,"displayModeBar":True,
           "modeBarButtonsToRemove":["select2d","lasso2d"]}

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
cl,ct,cb = st.columns([0.06,0.70,0.24])
with cl:
    st.markdown("""<div style="width:52px;height:52px;background:radial-gradient(circle,#052e16,#0f172a);
    border:2px solid #22c55e;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:9px;font-weight:700;color:#22c55e;letter-spacing:1px;
box-shadow:0 0 20px rgba(34,197,94,.3);margin-top:6px">Spaceport</div>""", unsafe_allow_html=True)
with ct:
    st.markdown("## 🌍 Earth Observatory Natural Event Tracker (EONET)")
    st.caption("Near real-time natural event metadata — powered by NASA Earth Observatory")
with cb:
    st.markdown("""<div style="margin-top:14px;text-align:right"><span style="background:rgba(34,197,94,.1);
    border:1px solid rgba(34,197,94,.3);border-radius:20px;padding:4px 12px;font-size:12px;
    color:#22c55e;font-weight:500">● Live Data</span></div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 20px'>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌍 EONET Controls")

    event_status = st.radio("Event status", ["Open (active now)", "Closed (recent)", "Both"], index=0)
    days_back    = st.slider("Lookback window (days)", 7, 365, 60,
                             help="Used when fetching closed or both")
    event_limit  = st.slider("Max events to load", 50, 1000, 300)
    st.markdown("---")

    st.markdown("### 🎛️ Filters")
    try:
        all_cats = fetch_categories()
        cat_options = {c["title"]: c["id"] for c in all_cats}
    except:
        cat_options = {v[1]: k for k,v in CAT_META.items()}

    selected_cats = st.multiselect(
        "Filter by category",
        options=list(cat_options.keys()),
        default=[],
        placeholder="All categories"
    )
    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#475569;line-height:2">
    <b style="color:#64748b">Categories</b><br>
    """ + "".join(
        f'<span style="color:{v[2]}">■</span> {v[1]}<br>'
        for v in CAT_META.values()
    ) + "</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data from [NASA EONET API](https://eonet.gsfc.nasa.gov/)")

# ── Fetch ─────────────────────────────────────────────────────────────────────
status_map = {
    "Open (active now)":  "open",
    "Closed (recent)":    "closed",
    "Both":               "all",
}
api_status = status_map[event_status]

with st.spinner("Scanning Earth for natural events…"):
    try:
        if api_status == "all":
            open_evts   = fetch_events("open",   days_back, event_limit)
            closed_evts = fetch_events("closed", days_back, event_limit)
            raw = open_evts + closed_evts
        else:
            raw = fetch_events(api_status, days_back, event_limit)
    except Exception as e:
        st.error(f"⚠️ Failed to fetch EONET data: {e}")
        st.stop()

df = parse_events(raw)
if df.empty:
    st.warning("No events found for selected filters.")
    st.stop()

# Apply category filter
if selected_cats:
    selected_ids = [cat_options[c] for c in selected_cats]
    df = df[df["Cat ID"].isin(selected_ids)]
    if df.empty:
        st.warning("No events match the selected categories.")
        st.stop()

df_geo = df.dropna(subset=["Lat","Lon"])

# ── Summary stats ─────────────────────────────────────────────────────────────
open_cnt   = (df["Status"]=="Open").sum()
closed_cnt = (df["Status"]=="Closed").sum()
cat_cnt    = df["Cat ID"].nunique()
top_cat    = df["Category"].value_counts().idxmax() if not df.empty else "—"
top_emoji  = cat_emoji(df["Cat ID"].value_counts().idxmax()) if not df.empty else "🌐"

s1,s2,s3,s4,s5 = st.columns(5)
stat_card(s1,"🌐","Total Events",   len(df),         "#22c55e")
stat_card(s2,"🔴","Active / Open",  open_cnt,         "#ef4444", "ongoing")
stat_card(s3,"✅","Closed",         closed_cnt,        "#64748b", "resolved")
stat_card(s4,"🗂️","Categories",     cat_cnt,           "#4f8ef7", "event types")
stat_card(s5, top_emoji,"Most Common", top_cat,        "#f59e0b")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_map, tab_cats, tab_time, tab_list, tab_raw = st.tabs([
    "🗺️ Global Event Map",
    "📊 Category Breakdown",
    "📈 Timeline",
    "📋 Event List",
    "🔢 Raw Data",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – GLOBAL MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab_map:
    st.markdown("### 🗺️ Live Natural Events — Global Map")
    st.caption("Each marker is a natural event. Color = category. Size scales with number of geometry points (event duration/extent). Hover for details.")

    if df_geo.empty:
        st.info("No events with coordinates available.")
    else:
        # Map view selector
        mc1, mc2, mc3 = st.columns(3)
        map_view  = mc1.selectbox("Map style", ["Natural Earth","Orthographic","Equirectangular"], index=0)
        show_open = mc2.toggle("Show open events", True)
        show_closed = mc3.toggle("Show closed events", True)

        view_map = {"Natural Earth":"natural earth","Orthographic":"orthographic",
                    "Equirectangular":"equirectangular"}

        plot_df = df_geo.copy()
        if not show_open:    plot_df = plot_df[plot_df["Status"]!="Open"]
        if not show_closed:  plot_df = plot_df[plot_df["Status"]!="Closed"]

        fig_map = go.Figure()

        # Per-category traces for legend
        for cat_id, grp in plot_df.groupby("Cat ID"):
            color  = cat_color(cat_id)
            emoji  = cat_emoji(cat_id)
            name   = cat_name(cat_id)
            sizes  = [max(8, min(22, 8 + g*1.5)) for g in grp["Geometries"]]
            opacities = [0.9 if s=="Open" else 0.5 for s in grp["Status"]]
            symbols   = ["circle" if s=="Open" else "circle-open" for s in grp["Status"]]

            tips = [
                f"<b>{row['Title']}</b><br>"
                f"Category: {emoji} {row['Category']}<br>"
                f"Status: {row['Status']}<br>"
                f"Date: {row['Date'] or '—'}<br>"
                f"Location: {row['Lat']:.2f}°, {row['Lon']:.2f}°<br>"
                f"Track points: {row['Geometries']}<extra></extra>"
                for _, row in grp.iterrows()
            ]

            fig_map.add_trace(go.Scattergeo(
                lat=grp["Lat"].tolist(),
                lon=grp["Lon"].tolist(),
                mode="markers",
                marker=dict(
                    size=sizes,
                    color=color,
                    opacity=0.88,
                    symbol="circle",
                    line=dict(color="rgba(255,255,255,0.35)", width=1),
                ),
                hovertemplate=tips,
                name=f"{emoji} {name}",
                showlegend=True,
            ))

        proj = view_map[map_view]
        fig_map.update_geos(
            bgcolor="#04060f",
            landcolor="#0d1b2a",
            oceancolor="#060d1a",
            showocean=True, showland=True,
            showcountries=True, countrycolor="#1a2340",
            showcoastlines=True, coastlinecolor="#1e3a5f",
            showrivers=True, rivercolor="#0c2340",
            showframe=False,
            projection_type=proj,
        )
        fig_map.update_layout(
            **GEO_LAYOUT,
            height=620,
            title=dict(text=f"EONET Natural Events ({len(plot_df)} plotted)",
                       font=dict(color="#64748b",size=12,family="Space Mono"),
                       x=0.5,xanchor="center"),
            legend=dict(orientation="v", x=0.01, y=0.99,
                        bgcolor="rgba(15,22,38,0.9)", bordercolor="#1a2340", borderwidth=1,
                        font=dict(color="#94a3b8",size=10,family="Space Mono"),
                        title=None),
        )
        fig_map.update_geos(projection_type=proj)
        st.plotly_chart(fig_map, use_container_width=True, config=MAP_CFG)

        # Map legend row
        st.markdown("<br>", unsafe_allow_html=True)
        lc1,lc2,lc3 = st.columns(3)
        lc1.markdown("""<div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;
        padding:10px 14px;font-size:12px;color:#94a3b8">
        <b style="color:#e2e8f0">●</b> Filled circle = Active open event<br>
        <b style="color:#64748b">○</b> Open circle = Closed/resolved event</div>""", unsafe_allow_html=True)
        lc2.markdown("""<div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;
        padding:10px 14px;font-size:12px;color:#94a3b8">
        Marker <b style="color:#e2e8f0">size</b> scales with the number of tracked geometry points
        (more points = longer/larger event)</div>""", unsafe_allow_html=True)
        lc3.markdown("""<div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;
        padding:10px 14px;font-size:12px;color:#94a3b8">
        Scroll to zoom · drag to pan · click legend to toggle categories</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – CATEGORY BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
with tab_cats:
    st.markdown("### 📊 Event Breakdown by Category")

    cat_counts = df.groupby(["Cat ID","Category","Status"]).size().reset_index(name="Count")

    # ── Donut chart ───────────────────────────────────────────────────────────
    section_hdr("🍩 CATEGORY SHARE", "Proportion of events by type")
    donut_df = df.groupby(["Cat ID","Category"]).size().reset_index(name="Count")
    donut_df["Emoji+Name"] = donut_df.apply(
        lambda r: f"{cat_emoji(r['Cat ID'])} {r['Category']}", axis=1)
    colors_donut = [cat_color(cid) for cid in donut_df["Cat ID"]]

    fig_donut = go.Figure(go.Pie(
        labels=donut_df["Emoji+Name"],
        values=donut_df["Count"],
        hole=0.55,
        marker=dict(colors=colors_donut,
                    line=dict(color="#04060f", width=2)),
        textinfo="percent+label",
        textfont=dict(size=11, family="Space Mono", color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>Events: %{value}<br>Share: %{percent}<extra></extra>",
    ))
    fig_donut.update_layout(
        paper_bgcolor="#04060f", plot_bgcolor="#04060f",
        height=420, margin=dict(l=10,r=10,t=20,b=10),
        showlegend=True,
        legend=dict(bgcolor="rgba(15,22,38,0.85)",bordercolor="#1a2340",borderwidth=1,
                    font=dict(color="#94a3b8",size=10,family="Space Mono")),
        hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")),
        annotations=[dict(text=f"<b>{len(df)}</b><br>events",
                          x=0.5,y=0.5,font=dict(size=16,color="#e2e8f0",family="Space Mono"),
                          showarrow=False)]
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    # ── Stacked bar open vs closed ────────────────────────────────────────────
    section_hdr("📊 OPEN vs CLOSED PER CATEGORY", "")
    pivot = cat_counts.pivot_table(index="Category", columns="Status", values="Count", fill_value=0).reset_index()
    pivot = pivot.sort_values("Open" if "Open" in pivot.columns else pivot.columns[-1], ascending=False)

    fig_bar = go.Figure()
    if "Open" in pivot.columns:
        cats_list = pivot["Category"].tolist()
        cat_ids   = [df[df["Category"]==c]["Cat ID"].iloc[0] if len(df[df["Category"]==c])>0 else "" for c in cats_list]
        fig_bar.add_trace(go.Bar(
            x=pivot["Category"], y=pivot["Open"],
            name="Open",
            marker_color=[cat_color(cid) for cid in cat_ids],
            opacity=0.9,
            hovertemplate="<b>%{x}</b><br>Open: %{y}<extra></extra>"))
    if "Closed" in pivot.columns:
        fig_bar.add_trace(go.Bar(
            x=pivot["Category"], y=pivot["Closed"],
            name="Closed",
            marker_color="#1e293b",
            opacity=0.8,
            hovertemplate="<b>%{x}</b><br>Closed: %{y}<extra></extra>"))
    fig_bar.update_layout(
        barmode="stack", paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=320, margin=dict(l=10,r=10,t=10,b=80),
        xaxis=dict(showgrid=False, color="#64748b", tickfont=dict(family="Space Mono",size=10),
                   tickangle=-35),
        yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                   tickfont=dict(family="Space Mono",size=10)),
        legend=dict(bgcolor="rgba(15,22,38,0.85)",bordercolor="#1a2340",borderwidth=1,
                    font=dict(color="#94a3b8",size=11,family="Space Mono")),
        hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")))
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Category stat cards ───────────────────────────────────────────────────
    section_hdr("🗂️ CATEGORY CARDS","")
    cat_summary = df.groupby(["Cat ID","Category"]).agg(
        Count=("ID","count"), Open=("Status", lambda x: (x=="Open").sum())
    ).reset_index().sort_values("Count", ascending=False)

    cols = st.columns(4)
    for i, (_, row) in enumerate(cat_summary.iterrows()):
        col = cols[i % 4]
        clr = cat_color(row["Cat ID"])
        em  = cat_emoji(row["Cat ID"])
        col.markdown(f"""
        <div style="background:#0f1626;border:1px solid {clr}33;border-top:3px solid {clr};
        border-radius:10px;padding:14px;text-align:center;margin-bottom:12px">
          <div style="font-size:24px">{em}</div>
          <div style="font-size:13px;font-weight:600;color:#e2e8f0;margin-top:4px">{row['Category']}</div>
          <div style="font-family:'Space Mono',monospace;font-size:22px;color:{clr};
          font-weight:700;margin:6px 0">{row['Count']}</div>
          <div style="font-size:10px;color:#64748b">
            <span style="color:#ef4444">{row['Open']} open</span>
            &nbsp;·&nbsp; {row['Count']-row['Open']} closed
          </div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – TIMELINE
# ══════════════════════════════════════════════════════════════════════════════
with tab_time:
    st.markdown("### 📈 Event Timeline")
    st.caption("Daily count of events by category. Use the date column from the most recent geometry point.")

    df_dated = df[df["Date"]!=""].copy()
    if df_dated.empty:
        st.info("No dated events available.")
    else:
        # ── Daily stacked bar ─────────────────────────────────────────────────
        section_hdr("📅 DAILY EVENT COUNTS","")
        daily = df_dated.groupby(["Date","Category","Cat ID"]).size().reset_index(name="Count")
        daily_sorted = daily.sort_values("Date")
        all_dates = sorted(daily["Date"].unique())

        fig_tl = go.Figure()
        for cat_id, grp in daily_sorted.groupby("Cat ID"):
            color = cat_color(cat_id)
            name  = cat_name(cat_id)
            emoji = cat_emoji(cat_id)
            date_counts = dict(zip(grp["Date"],grp["Count"]))
            fig_tl.add_trace(go.Bar(
                x=all_dates,
                y=[date_counts.get(d,0) for d in all_dates],
                name=f"{emoji} {name}",
                marker_color=color,
                opacity=0.85,
                hovertemplate=f"<b>{emoji} {name}</b><br>%{{x}}<br>Events: %{{y}}<extra></extra>",
            ))
        fig_tl.update_layout(
            barmode="stack", paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
            height=340, margin=dict(l=10,r=10,t=10,b=10),
            xaxis=dict(showgrid=False, color="#64748b", tickfont=dict(family="Space Mono",size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10)),
            legend=dict(orientation="v", x=1.01, y=1,
                        bgcolor="rgba(15,22,38,0.85)", bordercolor="#1a2340", borderwidth=1,
                        font=dict(color="#94a3b8",size=10,family="Space Mono")),
            hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")))
        st.plotly_chart(fig_tl, use_container_width=True)

        # ── Cumulative line chart ─────────────────────────────────────────────
        section_hdr("📈 CUMULATIVE EVENTS OVER TIME","Running total of events detected")
        cumul = df_dated.groupby("Date").size().reset_index(name="Daily")
        cumul = cumul.sort_values("Date")
        cumul["Cumulative"] = cumul["Daily"].cumsum()

        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=cumul["Date"], y=cumul["Cumulative"],
            mode="lines+markers",
            line=dict(color="#22c55e", width=2),
            marker=dict(size=5, color="#22c55e"),
            fill="tozeroy", fillcolor="rgba(34,197,94,0.07)",
            hovertemplate="<b>%{x}</b><br>Total events: %{y}<extra></extra>",
            name="Cumulative",
        ))
        fig_cum.update_layout(
            paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
            height=240, margin=dict(l=10,r=10,t=10,b=10),
            xaxis=dict(showgrid=False, color="#64748b", tickfont=dict(family="Space Mono",size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                       tickfont=dict(family="Space Mono",size=10)),
            showlegend=False,
            hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")))
        st.plotly_chart(fig_cum, use_container_width=True)

        # ── Category-specific mini maps ───────────────────────────────────────
        section_hdr("🗺️ PER-CATEGORY MAPS",
                    "Individual world maps for each category. Shows geographic concentration of events.")

        cat_ids_present = df_geo["Cat ID"].unique()
        pairs = [(cat_ids_present[i], cat_ids_present[i+1] if i+1 < len(cat_ids_present) else None)
                 for i in range(0, len(cat_ids_present), 2)]

        for left_id, right_id in pairs:
            cols2 = st.columns(2)
            for col, cat_id in zip(cols2, [left_id, right_id]):
                if cat_id is None: continue
                sub = df_geo[df_geo["Cat ID"]==cat_id]
                color = cat_color(cat_id)
                emoji = cat_emoji(cat_id)
                name  = cat_name(cat_id)

                fig_mini = go.Figure()
                fig_mini.add_trace(go.Scattergeo(
                    lat=sub["Lat"].tolist(), lon=sub["Lon"].tolist(),
                    mode="markers",
                    marker=dict(size=8, color=color, opacity=0.85,
                                line=dict(color="rgba(255,255,255,0.3)",width=1)),
                    hovertemplate=[
                        f"<b>{r['Title']}</b><br>{r['Date'] or '—'}<br>"
                        f"{r['Lat']:.2f}°, {r['Lon']:.2f}°<extra></extra>"
                        for _,r in sub.iterrows()],
                    showlegend=False,
                ))
                fig_mini.update_geos(
                    bgcolor="#04060f", landcolor="#0d1b2a", oceancolor="#04060f",
                    showocean=True, showland=True,
                    showcountries=True, countrycolor="#1a2340",
                    showcoastlines=True, coastlinecolor="#1e3a5f",
                    showframe=False, projection_type="natural earth",
                )
                fig_mini.update_layout(
                    paper_bgcolor="#04060f",
                    height=280, margin=dict(l=0,r=0,t=36,b=0),
                    title=dict(
                        text=f"{emoji} {name} — {len(sub)} events",
                        font=dict(color=color,size=11,family="Space Mono"),
                        x=0.5,xanchor="center"),
                    hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                                    font=dict(color="#e2e8f0",size=11,family="Space Mono")),
                )
                col.plotly_chart(fig_mini, use_container_width=True,
                                 config={"displayModeBar":False})

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – EVENT LIST
# ══════════════════════════════════════════════════════════════════════════════
with tab_list:
    st.markdown("### 📋 Event List")

    # Filter controls
    fl1,fl2,fl3 = st.columns(3)
    status_filter = fl1.selectbox("Status", ["All","Open","Closed"], index=0)
    sort_by = fl2.selectbox("Sort by", ["Date (newest)","Date (oldest)","Category","Title"], index=0)
    search  = fl3.text_input("Search title", placeholder="Type to filter…")

    list_df = df.copy()
    if status_filter != "All":
        list_df = list_df[list_df["Status"]==status_filter]
    if search:
        list_df = list_df[list_df["Title"].str.contains(search, case=False, na=False)]
    sort_map = {
        "Date (newest)": ("Date", False),
        "Date (oldest)": ("Date", True),
        "Category":      ("Category", True),
        "Title":         ("Title", True),
    }
    sc, sa = sort_map[sort_by]
    list_df = list_df.sort_values(sc, ascending=sa)

    st.markdown(f"<div style='font-size:12px;color:#64748b;margin-bottom:12px'>"
                f"Showing <b style='color:#e2e8f0'>{len(list_df)}</b> events</div>",
                unsafe_allow_html=True)

    # Paginate
    PAGE_SIZE = 30
    total_pages = max(1, (len(list_df)-1)//PAGE_SIZE+1)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    page_df = list_df.iloc[(page-1)*PAGE_SIZE : page*PAGE_SIZE]

    for _, row in page_df.iterrows():
        st.markdown(event_card(row), unsafe_allow_html=True)

    if total_pages > 1:
        st.markdown(f"<div style='text-align:center;color:#64748b;font-size:11px;margin-top:8px'>"
                    f"Page {page} of {total_pages}</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
with tab_raw:
    st.markdown("### 🔢 Raw Event Data")

    def style_status(row):
        if row["Status"] == "Open":
            return ["background-color:rgba(239,68,68,0.07)"] * len(row)
        return [""] * len(row)

    display_df = df.drop(columns=["Cat ID"]).copy()
    styled = display_df.style.apply(style_status, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button("⬇️ Download CSV", df.to_csv(index=False),
                            "eonet_events.csv", "text/csv")
    col_dl2.download_button("⬇️ Download Open Events",
                            df[df["Status"]=="Open"].to_csv(index=False),
                            "eonet_open.csv", "text/csv")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#64748b;line-height:1.8">
    <b style="color:#94a3b8">About EONET</b> — The Earth Observatory Natural Event Tracker is a
    prototype web service from NASA Earth Observatory providing curated, continuously updated,
    near real-time natural event metadata. Events are linked to thematically-related NASA imagery
    layers via WMS/WMTS. Development began in 2015 and is supported by NASA's Earth Observatory
    and Earth Science Data and Information System (ESDIS) Project.<br>
    API: <span style="font-family:'Space Mono',monospace;color:#22c55e">
    https://eonet.gsfc.nasa.gov/api/v3</span>
  </div>
</div>""", unsafe_allow_html=True)
