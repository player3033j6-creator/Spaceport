import streamlit as st
import requests
from datetime import date, timedelta
import pandas as pd
import math
import plotly.graph_objects as go

st.set_page_config(page_title="Spaceport | NeoWs", page_icon="🪐", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="metric-container"] { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
[data-testid="stSidebar"] { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stTabs"] button { color:#64748b !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#4f8ef7 !important; border-bottom-color:#4f8ef7 !important; }
h1,h2,h3 { color:#e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

API_KEY  = "C0dXt7TGMVzs70jSstfEMjO6TQC90XU4dNsnP9Uf"
NASA_URL = "https://api.nasa.gov/neo/rest/v1/feed"
PLANET_ORBITS = {"Mercury":0.387,"Venus":0.723,"Earth":1.000,"Mars":1.524}
PLANET_COLORS = {"Mercury":"#b5b5b5","Venus":"#e8cda0","Earth":"#4f8ef7","Mars":"#c1440e"}
PLANET_SIZES  = {"Mercury":8,"Venus":12,"Earth":13,"Mars":9}
PLANET_ANGLES = {"Mercury":45,"Venus":120,"Earth":0,"Mars":220}

@st.cache_data(ttl=3600)
def fetch_neos(start, end):
    resp = requests.get(NASA_URL, params={"start_date":start,"end_date":end,"api_key":API_KEY})
    resp.raise_for_status()
    data = resp.json()
    rows = []
    for _, neos in data["near_earth_objects"].items():
        for neo in neos:
            ca = neo["close_approach_data"][0]
            rows.append({
                "ID": neo["id"],
                "Name": neo["name"].strip("()").strip(),
                "Approach Date": ca["close_approach_date"],
                "Hazardous": neo["is_potentially_hazardous_asteroid"],
                "Diameter Min (km)": round(neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"],4),
                "Diameter Max (km)": round(neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"],4),
                "Velocity (km/s)": round(float(ca["relative_velocity"]["kilometers_per_second"]),2),
                "Miss Distance (km)": round(float(ca["miss_distance"]["kilometers"])),
                "Miss Distance (AU)": round(float(ca["miss_distance"]["astronomical"]),5),
                "Miss Distance (LD)": round(float(ca["miss_distance"]["lunar"]),2),
                "Orbiting Body": ca["orbiting_body"],
            })
    return sorted(rows, key=lambda x: x["Approach Date"])

def ld(km):      return f"{km/384400:.2f} LD"
def fmt_big(km): return f"{km/1_000_000:.2f}M"

def orbit_xy(radius, n=360):
    a = [2*math.pi*i/n for i in range(n+1)]
    return [radius*math.cos(x) for x in a], [radius*math.sin(x) for x in a]

def neo_pos(miss_au, idx):
    spread = ((idx % 72)*5 - 180) * math.pi/180
    sign   = 1 if idx%2==0 else -1
    r      = 1.0 + sign*min(miss_au, 1.4)
    return r*math.cos(spread), r*math.sin(spread)

def build_map(df, size_scale):
    import random
    fig = go.Figure()
    rng = random.Random(42)
    sx = [rng.uniform(-2.1,2.1) for _ in range(320)]
    sy = [rng.uniform(-2.1,2.1) for _ in range(320)]
    ss = [rng.uniform(0.5,2.2)  for _ in range(320)]
    fig.add_trace(go.Scatter(x=sx,y=sy,mode="markers",
        marker=dict(size=ss,color="rgba(255,255,255,0.2)"),hoverinfo="skip",showlegend=False,name="_s"))
    for planet, radius in PLANET_ORBITS.items():
        ox,oy = orbit_xy(radius)
        fig.add_trace(go.Scatter(x=ox,y=oy,mode="lines",
            line=dict(color="rgba(255,255,255,0.055)",width=1,dash="dot"),
            hoverinfo="skip",showlegend=False,name=f"_o{planet}"))
    for planet, radius in PLANET_ORBITS.items():
        a = PLANET_ANGLES[planet]*math.pi/180
        fig.add_trace(go.Scatter(x=[radius*math.cos(a)],y=[radius*math.sin(a)],
            mode="markers+text",
            marker=dict(size=PLANET_SIZES[planet],color=PLANET_COLORS[planet],
                        line=dict(color="rgba(255,255,255,0.3)",width=1)),
            text=[planet],textposition="top center",
            textfont=dict(color="rgba(255,255,255,0.55)",size=10,family="Space Mono"),
            hovertemplate=f"<b>{planet}</b><br>{radius} AU<extra></extra>",
            showlegend=False,name=planet))
    for sz,al in [(44,0.06),(34,0.09),(26,0.14)]:
        fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",
            marker=dict(size=sz,color=f"rgba(253,230,138,{al})"),
            hoverinfo="skip",showlegend=False,name="_g"))
    fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",
        marker=dict(size=20,color="#fde68a",line=dict(color="#fbbf24",width=2)),
        hovertemplate="<b>☀️ Sun</b><extra></extra>",showlegend=False,name="Sun"))
    haz  = df[df["Hazardous"]].reset_index(drop=True)
    safe = df[~df["Hazardous"]].reset_index(drop=True)
    for i,row in haz.iterrows():
        nx,ny = neo_pos(row["Miss Distance (AU)"],i)
        fig.add_trace(go.Scatter(x=[1.0,nx],y=[0.0,ny],mode="lines",
            line=dict(color="rgba(239,68,68,0.18)",width=1,dash="dot"),
            hoverinfo="skip",showlegend=False,name="_hl"))
    def add_neos(group, color, symbol, label):
        if group.empty: return
        xs,ys,szs,tips = [],[],[],[]
        for i,row in group.iterrows():
            x,y = neo_pos(row["Miss Distance (AU)"],i)
            xs.append(x); ys.append(y)
            szs.append(max(6,min(28,int(row["Diameter Max (km)"]*55*size_scale+5))))
            tips.append(
                f"<b>{row['Name']}</b><br>"
                f"{'⚠️ HAZARDOUS' if row['Hazardous'] else '✓ Safe'}<br>"
                f"Date: {row['Approach Date']}<br>"
                f"Miss: {row['Miss Distance (LD)']} LD ({row['Miss Distance (AU)']} AU)<br>"
                f"Speed: {row['Velocity (km/s)']} km/s<br>"
                f"Ø: {row['Diameter Min (km)']}–{row['Diameter Max (km)']} km<extra></extra>")
        fig.add_trace(go.Scatter(x=xs,y=ys,mode="markers",
            marker=dict(size=szs,color=color,opacity=0.85,symbol=symbol,
                        line=dict(color="rgba(255,255,255,0.25)",width=1)),
            hovertemplate=tips,name=label,showlegend=True))
    add_neos(safe,"#4f8ef7","circle","✓ Safe NEO")
    add_neos(haz, "#ef4444","diamond","⚠️ Hazardous NEO")
    fig.update_layout(
        paper_bgcolor="#04060f",plot_bgcolor="#04060f",
        margin=dict(l=0,r=0,t=44,b=0),height=700,
        title=dict(text="Inner Solar System — NEO Close Approaches (AU scale)",
                   font=dict(color="#64748b",size=13,family="Space Mono"),x=0.5,xanchor="center"),
        legend=dict(orientation="h",yanchor="bottom",y=0.01,xanchor="center",x=0.5,
                    font=dict(color="#94a3b8",size=12,family="Space Mono"),
                    bgcolor="rgba(15,22,38,0.85)",bordercolor="#1a2340",borderwidth=1),
        xaxis=dict(visible=False,range=[-2.05,2.05],scaleanchor="y",scaleratio=1),
        yaxis=dict(visible=False,range=[-2.05,2.05]),
        dragmode="pan",
        hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")))
    return fig

# ── Header ────────────────────────────────────────────────────────────────────
cl,ct,cb = st.columns([0.06,0.70,0.24])
with cl:
    st.markdown("""<div style="width:52px;height:52px;background:radial-gradient(circle,#1e3a8a,#0f172a);
    border:2px solid #4f8ef7;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:9px;font-weight:700;color:#4f8ef7;letter-spacing:1px;
box-shadow:0 0 20px rgba(79,142,247,.3);margin-top:6px">Spaceport</div>""",unsafe_allow_html=True)
with ct:
    st.markdown("## 🪐 Near Earth Object Web Service")
    st.caption("Real-time asteroid & comet tracking — powered by NASA JPL")
with cb:
    st.markdown("""<div style="margin-top:14px;text-align:right"><span style="background:rgba(34,197,94,.1);
    border:1px solid rgba(34,197,94,.3);border-radius:20px;padding:4px 12px;font-size:12px;
    color:#22c55e;font-weight:500">● Live Data</span></div>""",unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 24px'>",unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🪐 NeoWs Controls")
    today      = date.today()
    start_date = st.date_input("Start date", today)
    end_date   = st.date_input("End date",   today + timedelta(days=6))
    haz_only   = st.toggle("⚠️ Hazardous only", False)
    max_ld     = st.slider("Max miss distance (LD)", 0, 200, 200)
    st.markdown("---")
    st.markdown("### 🗺️ Orbital Map")
    size_scale = st.slider("NEO dot size scale", 1, 5, 2)
    st.markdown("---")
    st.caption("Data from [NASA NeoWs API](https://api.nasa.gov/)")

st.markdown(f"**Date range:** `{start_date}` → `{end_date}`")

with st.spinner("Scanning near-Earth space…"):
    try:
        neos = fetch_neos(str(start_date), str(end_date))
    except Exception as e:
        st.error(f"⚠️ Failed to fetch NEO data: {e}")
        st.stop()

df = pd.DataFrame(neos)
if haz_only: df = df[df["Hazardous"]]
df = df[df["Miss Distance (LD)"] <= max_ld]
if df.empty:
    st.warning("No objects match current filters.")
    st.stop()

closest = df.loc[df["Miss Distance (km)"].idxmin()]
fastest = df.loc[df["Velocity (km/s)"].idxmax()]
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total NEOs",               len(df))
c2.metric("⚠️ Potentially Hazardous", int(df["Hazardous"].sum()))
c3.metric("Closest Approach",         ld(closest["Miss Distance (km)"]), help=closest["Name"])
c4.metric("Fastest Object",           f"{fastest['Velocity (km/s)']} km/s", help=fastest["Name"])
st.markdown("<br>",unsafe_allow_html=True)

tab1,tab2,tab3,tab_map,tab4 = st.tabs([
    "🌍 Close Approaches","⚠️ Hazardous Objects","🚀 Top Velocities","🗺️ Orbital Map","📋 Raw Data"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    tstr = str(date.today())
    tdf  = df[df["Approach Date"]==tstr]
    disp = tdf if not tdf.empty else df.head(15)
    st.markdown(f"### Today's Close Approaches &nbsp; `{len(disp)}`",unsafe_allow_html=True)
    for _,row in disp.iterrows():
        ih  = row["Hazardous"]
        rgb = "239,68,68" if ih else "34,197,94"
        hc  = "#ef4444"   if ih else "#22c55e"
        hl  = "⚠️ Hazardous" if ih else "✓ Safe"
        lb  = "border-left:3px solid #ef4444;" if ih else ""
        st.markdown(f"""
        <div style="background:#0f1626;border:1px solid #1a2340;{lb}border-radius:14px;
        padding:18px 20px;margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div style="font-size:15px;font-weight:600;color:#e2e8f0">{row['Name']}</div>
              <div style="font-size:11px;color:#64748b;font-family:'Space Mono',monospace;margin-top:2px">
                ID: {row['ID']} · {row['Orbiting Body']} flyby</div>
              <div style="display:flex;gap:24px;margin-top:12px;flex-wrap:wrap">
                <div><div style="font-size:10px;text-transform:uppercase;color:#64748b">Diameter</div>
                  <div style="font-family:'Space Mono',monospace;font-size:13px">
                    {row['Diameter Min (km)']}–{row['Diameter Max (km)']} km</div></div>
                <div><div style="font-size:10px;text-transform:uppercase;color:#64748b">Velocity</div>
                  <div style="font-family:'Space Mono',monospace;font-size:13px">{row['Velocity (km/s)']} km/s</div></div>
                <div><div style="font-size:10px;text-transform:uppercase;color:#64748b">Miss Distance</div>
                  <div style="font-family:'Space Mono',monospace;font-size:13px">{fmt_big(row['Miss Distance (km)'])} km</div></div>
                <div><div style="font-size:10px;text-transform:uppercase;color:#64748b">Approach</div>
                  <div style="font-family:'Space Mono',monospace;font-size:13px">{row['Approach Date']}</div></div>
              </div>
            </div>
            <div style="text-align:right;flex-shrink:0;padding-left:16px">
              <span style="background:rgba({rgb},.15);border:1px solid rgba({rgb},.4);
              border-radius:20px;padding:4px 10px;font-size:11px;font-weight:600;color:{hc}">{hl}</span>
              <div style="font-size:12px;color:#64748b;margin-top:8px">Lunar distance<br>
                <span style="font-family:'Space Mono',monospace;color:#e2e8f0">
                  {row['Miss Distance (LD)']} LD</span></div>
            </div>
          </div>
        </div>""",unsafe_allow_html=True)

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    hdf = df[df["Hazardous"]].sort_values("Miss Distance (km)")
    st.markdown(f"### ⚠️ Potentially Hazardous Asteroids &nbsp; `{len(hdf)}`",unsafe_allow_html=True)
    if hdf.empty:
        st.success("🎉 No hazardous objects this week!")
    else:
        for _,row in hdf.iterrows():
            st.markdown(f"""
            <div style="background:#0f1626;border:1px solid rgba(239,68,68,.3);
            border-left:3px solid #ef4444;border-radius:12px;padding:14px 18px;margin-bottom:10px">
              <div style="color:#ef4444;font-size:14px;font-weight:600">{row['Name']}</div>
              <div style="color:#64748b;font-size:12px;font-family:'Space Mono',monospace;margin-top:4px">
                {fmt_big(row['Miss Distance (km)'])}M km · {row['Approach Date']}<br>
                Ø {row['Diameter Max (km)']} km · {row['Velocity (km/s)']} km/s
              </div>
            </div>""",unsafe_allow_html=True)

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🚀 Top Velocities")
    tv = df.nlargest(10,"Velocity (km/s)").reset_index(drop=True)
    mv = tv["Velocity (km/s)"].max()
    for _,row in tv.iterrows():
        pct = row["Velocity (km/s)"]/mv*100
        bc  = "#ef4444" if row["Hazardous"] else "#4f8ef7"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
          <div style="width:140px;font-size:12px;color:#94a3b8;overflow:hidden;
          text-overflow:ellipsis;white-space:nowrap;flex-shrink:0">{row['Name']}</div>
          <div style="flex:1;height:10px;background:#1a2340;border-radius:5px;overflow:hidden">
            <div style="width:{pct:.1f}%;height:100%;
            background:linear-gradient(90deg,{bc},{bc}99);border-radius:5px"></div></div>
          <div style="width:80px;text-align:right;font-family:'Space Mono',monospace;font-size:12px;
          color:#94a3b8;flex-shrink:0">{row['Velocity (km/s)']} km/s</div>
        </div>""",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    st.bar_chart(tv.set_index("Name")["Velocity (km/s)"],color="#4f8ef7")

# ── Tab Orbital Map ───────────────────────────────────────────────────────────
with tab_map:
    st.markdown("### 🗺️ Inner Solar System — Live NEO Positions")
    ic1,ic2,ic3 = st.columns(3)
    ic1.markdown(f"""<div style="background:#0f1626;border:1px solid #1a2340;border-radius:10px;
    padding:14px;text-align:center"><div style="color:#64748b;font-size:10px;text-transform:uppercase">
    NEOs Plotted</div><div style="font-family:'Space Mono',monospace;font-size:24px;color:#4f8ef7;
    margin-top:4px">{len(df)}</div></div>""",unsafe_allow_html=True)
    ic2.markdown(f"""<div style="background:#0f1626;border:1px solid rgba(239,68,68,.3);border-radius:10px;
    padding:14px;text-align:center"><div style="color:#64748b;font-size:10px;text-transform:uppercase">
    Hazardous</div><div style="font-family:'Space Mono',monospace;font-size:24px;color:#ef4444;
    margin-top:4px">{int(df['Hazardous'].sum())}</div></div>""",unsafe_allow_html=True)
    ic3.markdown(f"""<div style="background:#0f1626;border:1px solid #1a2340;border-radius:10px;
    padding:14px;text-align:center"><div style="color:#64748b;font-size:10px;text-transform:uppercase">
    Closest (AU)</div><div style="font-family:'Space Mono',monospace;font-size:24px;color:#f59e0b;
    margin-top:4px">{df['Miss Distance (AU)'].min()}</div></div>""",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    fig = build_map(df, size_scale)
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom":True,"displayModeBar":True,
        "modeBarButtonsToRemove":["select2d","lasso2d"],
        "toImageButtonOptions":{"format":"png","filename":"nasa_neows_map"}})
    st.markdown("""<div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:8px;padding:12px 16px;
    background:#0f1626;border:1px solid #1a2340;border-radius:10px;font-size:12px;color:#94a3b8">
      <span>☀️ <b style="color:#fde68a">Sun</b></span>
      <span><b style="color:#b5b5b5">Mercury</b> 0.39 AU</span>
      <span><b style="color:#e8cda0">Venus</b> 0.72 AU</span>
      <span><b style="color:#4f8ef7">Earth</b> 1.00 AU</span>
      <span><b style="color:#c1440e">Mars</b> 1.52 AU</span>
      <span>🔷 <b style="color:#ef4444">Hazardous NEO</b></span>
      <span>● <b style="color:#4f8ef7">Safe NEO</b></span>
      <span style="color:#475569">· Size ∝ diameter · Hover for details · Scroll/drag to navigate</span>
    </div>""",unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("#### 📐 Distance Reference")
    rc = st.columns(4)
    for col,(lbl,val) in zip(rc,[("1 Lunar Distance","384,400 km"),("1 AU","149,597,871 km"),
                                  ("Earth–Moon","~1.0 LD"),("Earth–Mars min","~0.37 AU")]):
        col.markdown(f"""<div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;
        padding:10px 12px;text-align:center"><div style="font-size:10px;color:#64748b;
        text-transform:uppercase">{lbl}</div><div style="font-family:'Space Mono',monospace;
        font-size:13px;color:#e2e8f0;margin-top:4px">{val}</div></div>""",unsafe_allow_html=True)

# ── Tab Raw Data ──────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📋 All NEOs")
    def style_row(r): return (["background-color:rgba(239,68,68,0.08)"]*len(r) if r["Hazardous"] else [""]*len(r))
    styled = df.style.apply(style_row,axis=1).format({"Miss Distance (km)":"{:,.0f}","Velocity (km/s)":"{:.2f}"})
    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV", df.to_csv(index=False), "nasa_neos.csv", "text/csv")
