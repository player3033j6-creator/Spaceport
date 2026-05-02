import streamlit as st
import requests
from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import math, random

st.set_page_config(page_title="Spaceport | DONKI", page_icon="🌩️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="metric-container"] { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
[data-testid="stSidebar"] { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stTabs"] button { color:#64748b !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#f59e0b !important; border-bottom-color:#f59e0b !important; }
h1,h2,h3 { color:#e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

API_KEY    = "C0dXt7TGMVzs70jSstfEMjO6TQC90XU4dNsnP9Uf"
DONKI_BASE = "https://api.nasa.gov/DONKI"
FLARE_COLORS = {"X":"#ef4444","M":"#f59e0b","C":"#4f8ef7","B":"#22c55e","A":"#64748b"}

# ── Shared layout defaults ────────────────────────────────────────────────────
MAP_LAYOUT = dict(
    paper_bgcolor="#04060f", plot_bgcolor="#04060f",
    margin=dict(l=10,r=10,t=48,b=10),
    font=dict(family="Space Mono", color="#94a3b8"),
    hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                    font=dict(color="#e2e8f0", size=12, family="Space Mono")),
    legend=dict(bgcolor="rgba(15,22,38,0.85)", bordercolor="#1a2340", borderwidth=1,
                font=dict(color="#94a3b8", size=11, family="Space Mono")),
)

# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_donki(endpoint, start, end):
    resp = requests.get(f"{DONKI_BASE}/{endpoint}",
                        params={"startDate":start,"endDate":end,"api_key":API_KEY})
    resp.raise_for_status()
    return resp.json() or []

# ── Helper functions ──────────────────────────────────────────────────────────
def flare_color(cls_str):
    if not cls_str: return "#64748b"
    return FLARE_COLORS.get(cls_str[0].upper(),"#64748b")

def gst_color(kp):
    try:
        kp = float(kp)
        if kp >= 8: return "#ef4444"
        if kp >= 6: return "#f59e0b"
        if kp >= 4: return "#a855f7"
        return "#22c55e"
    except: return "#64748b"

def gst_label(kp):
    try:
        kp = float(kp)
        if kp >= 8: return "Severe (G4–G5)"
        if kp >= 6: return "Strong (G3)"
        if kp >= 5: return "Moderate (G2)"
        return "Minor (G1)"
    except: return "Unknown"

def stat_card(col, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
    border-radius:12px;padding:18px 20px;text-align:center">
      <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      <div style="font-family:'Space Mono',monospace;font-size:30px;color:{color};margin-top:6px;font-weight:700">{value}</div>
      {f'<div style="color:#64748b;font-size:11px;margin-top:4px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def event_card(title, subtitle, body_html, badge_label, badge_color, border_color="#1a2340"):
    return f"""
    <div style="background:#0f1626;border:1px solid {border_color};border-left:3px solid {badge_color};
    border-radius:12px;padding:16px 18px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
        <div style="flex:1;min-width:0">
          <div style="font-size:14px;font-weight:600;color:#e2e8f0">{title}</div>
          <div style="font-size:11px;color:#64748b;font-family:'Space Mono',monospace;margin-top:2px">{subtitle}</div>
          <div style="margin-top:10px;font-size:12px;color:#94a3b8;line-height:1.7">{body_html}</div>
        </div>
        <span style="background:{badge_color}22;border:1px solid {badge_color}66;
        border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;color:{badge_color};
        white-space:nowrap;flex-shrink:0">{badge_label}</span>
      </div>
    </div>"""

def section_header(title, caption):
    st.markdown(f"<div style='font-size:13px;font-weight:600;text-transform:uppercase;"
                f"letter-spacing:1.5px;color:#64748b;margin:28px 0 4px'>{title}</div>",
                unsafe_allow_html=True)
    st.caption(caption)

# ══════════════════════════════════════════════════════════════════════════════
# MAP BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def circle_xy(r, n=200):
    a = [2*math.pi*i/n for i in range(n+1)]
    return [r*math.cos(t) for t in a], [r*math.sin(t) for t in a]

def sun_glows(fig):
    """Add layered sun glow traces."""
    for sz, al in [(90,0.04),(70,0.07),(50,0.11),(34,0.18)]:
        fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",
            marker=dict(size=sz, color=f"rgba(253,230,138,{al})"),
            hoverinfo="skip", showlegend=False, name="_glow"))
    fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",
        marker=dict(size=22,color="#fde68a",line=dict(color="#fbbf24",width=2)),
        hovertemplate="<b>☀️ Sun</b><extra></extra>",showlegend=False,name="Sun"))

def starfield(fig, n=250, xlim=2.1, ylim=2.1):
    rng = random.Random(99)
    fig.add_trace(go.Scatter(
        x=[rng.uniform(-xlim,xlim) for _ in range(n)],
        y=[rng.uniform(-ylim,ylim) for _ in range(n)],
        mode="markers",
        marker=dict(size=[rng.uniform(0.5,2.0) for _ in range(n)],
                    color="rgba(255,255,255,0.18)"),
        hoverinfo="skip", showlegend=False, name="_stars"))

# ── CME Heliospheric Propagation Map ─────────────────────────────────────────
def build_cme_map(cme_data):
    """
    Polar-like top-down view of the inner heliosphere.
    Each CME is drawn as a filled wedge (half-angle cone) radiating from the Sun,
    with colour = speed bucket and opacity = recency.
    """
    fig = go.Figure()

    # Starfield
    starfield(fig, xlim=2.1, ylim=2.1)

    # Orbit rings: Mercury 0.39, Venus 0.72, Earth 1.0, Mars 1.52
    planet_info = [("Mercury",0.387,"#b5b5b5",45),
                   ("Venus",0.723,"#e8cda0",120),
                   ("Earth",1.000,"#4f8ef7",0),
                   ("Mars",1.524,"#c1440e",220)]
    for name,r,col,angle_deg in planet_info:
        cx,cy = circle_xy(r)
        fig.add_trace(go.Scatter(x=cx,y=cy,mode="lines",
            line=dict(color="rgba(255,255,255,0.05)",width=1,dash="dot"),
            hoverinfo="skip",showlegend=False,name=f"_o{name}"))
        a = angle_deg*math.pi/180
        fig.add_trace(go.Scatter(x=[r*math.cos(a)],y=[r*math.sin(a)],
            mode="markers+text",
            marker=dict(size=9 if name=="Earth" else 7,color=col,
                        line=dict(color="rgba(255,255,255,0.3)",width=1)),
            text=[name],textposition="top center",
            textfont=dict(color=col,size=9,family="Space Mono"),
            hovertemplate=f"<b>{name}</b><br>{r} AU<extra></extra>",
            showlegend=False,name=name))

    sun_glows(fig)

    # Parse CMEs
    rng2 = random.Random(7)
    n_total = len(cme_data)

    for idx, evt in enumerate(sorted(cme_data, key=lambda x: x.get("startTime",""))):
        analyses = evt.get("cmeAnalyses") or []
        speed, half_angle, lat, lon, etype = 500, 30, 0.0, 0.0, "U"
        if analyses:
            best = sorted(analyses, key=lambda x: x.get("isMostAccurate",False), reverse=True)[0]
            try: speed = float(best.get("speed") or 500)
            except: speed = 500
            try: half_angle = float(best.get("halfAngle") or 30)
            except: half_angle = 30
            try: lat = float(best.get("latitude") or 0)
            except: lat = 0.0
            try: lon = float(best.get("longitude") or rng2.uniform(-180,180))
            except: lon = rng2.uniform(-180,180)
            etype = (best.get("type") or "U")

        # Recency opacity
        age_frac = idx / max(n_total-1,1)
        alpha    = 0.15 + 0.55 * age_frac

        # Speed → colour
        if speed >= 1500: sc = f"rgba(239,68,68,{alpha})"
        elif speed >= 800: sc = f"rgba(245,158,11,{alpha})"
        else:              sc = f"rgba(168,85,247,{alpha})"

        # Central direction angle (lon projected into ecliptic plane)
        direction = lon * math.pi / 180
        half_rad  = min(half_angle, 90) * math.pi / 180

        # Build wedge polygon from Sun outward to 1.7 AU
        R_max = 1.7
        n_pts = 40
        wedge_angles = [direction - half_rad + 2*half_rad*i/(n_pts-1) for i in range(n_pts)]
        wx = [0] + [R_max*math.cos(a) for a in wedge_angles] + [0]
        wy = [0] + [R_max*math.sin(a) for a in wedge_angles] + [0]

        act_ts = (evt.get("startTime","") or "")[:16]
        fig.add_trace(go.Scatter(
            x=wx, y=wy,
            fill="toself", fillcolor=sc,
            line=dict(color=sc.replace(f",{alpha})",",0.8)"), width=1),
            mode="lines",
            name=etype,
            hovertemplate=(
                f"<b>{evt.get('activityID','CME')}</b><br>"
                f"Type: {etype} · Speed: {speed:.0f} km/s<br>"
                f"Half-angle: {half_angle}°<br>"
                f"Start: {act_ts}<extra></extra>"
            ),
            showlegend=False,
        ))

    # Legend proxies
    for label, clr in [("≥1500 km/s (extreme)","#ef4444"),
                        ("800–1500 km/s (fast)","#f59e0b"),
                        ("<800 km/s (moderate)","#a855f7")]:
        fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",
            marker=dict(size=10,color=clr,symbol="square"),
            name=label, showlegend=True))

    fig.update_layout(
        **MAP_LAYOUT,
        height=600,
        title=dict(text="CME Heliospheric Propagation — Top-Down View (1 AU = Earth orbit)",
                   font=dict(color="#64748b",size=12,family="Space Mono"),x=0.5,xanchor="center"),
        xaxis=dict(visible=False,range=[-2.05,2.05],scaleanchor="y",scaleratio=1),
        yaxis=dict(visible=False,range=[-2.05,2.05]),
        dragmode="pan",
    )
    return fig

# ── FLR Solar Disk Map ────────────────────────────────────────────────────────
def build_flr_map(flr_data):
    """
    Heliographic map of the solar disk (Stonyhurst coords, lon –90→+90, lat –90→+90).
    Each flare is plotted at its active region location.
    Marker size ∝ class intensity, colour = class.
    """
    fig = go.Figure()

    # Solar disk background
    theta_disk = [2*math.pi*i/200 for i in range(201)]
    fig.add_trace(go.Scatter(
        x=[math.cos(t)*90 for t in theta_disk],
        y=[math.sin(t)*90 for t in theta_disk],
        fill="toself",
        fillcolor="rgba(253,186,116,0.06)",
        line=dict(color="rgba(251,191,36,0.4)",width=1.5),
        hoverinfo="skip", showlegend=False, name="_disk"))

    # Grid lines (Carrington-like grid)
    for lon in range(-60,90,30):
        fig.add_trace(go.Scatter(
            x=[lon,lon],y=[-90,90],mode="lines",
            line=dict(color="rgba(255,255,255,0.04)",width=1),
            hoverinfo="skip",showlegend=False,name="_g"))
    for lat in range(-60,90,30):
        fig.add_trace(go.Scatter(
            x=[-90,90],y=[lat,lat],mode="lines",
            line=dict(color="rgba(255,255,255,0.04)",width=1),
            hoverinfo="skip",showlegend=False,name="_g"))

    # Grid labels
    for lon in [-60,-30,0,30,60]:
        fig.add_annotation(x=lon,y=-95,text=f"{lon}°",showarrow=False,
            font=dict(size=8,color="#475569",family="Space Mono"),xanchor="center")
    for lat in [-60,-30,0,30,60]:
        fig.add_annotation(x=-97,y=lat,text=f"{lat}°",showarrow=False,
            font=dict(size=8,color="#475569",family="Space Mono"),yanchor="middle")

    # Equator & central meridian
    fig.add_hline(y=0,line_color="rgba(255,255,255,0.12)",line_width=1)
    fig.add_vline(x=0,line_color="rgba(255,255,255,0.12)",line_width=1)

    rng3 = random.Random(13)
    CLASS_SIZE = {"X":28,"M":18,"C":12,"B":8,"A":6}

    # Group by class for legend
    by_class = {}
    for evt in flr_data:
        cls   = (evt.get("classType") or "?")[0].upper()
        loc   = evt.get("sourceLocation","") or ""
        # Parse N/S lat, E/W lon from e.g. "N14E60"
        lon_v, lat_v = rng3.uniform(-70,70), rng3.uniform(-70,70)  # fallback
        try:
            import re
            m = re.match(r"([NS])(\d+)([EW])(\d+)", loc.strip().upper())
            if m:
                lat_v = float(m.group(2)) * (1 if m.group(1)=="N" else -1)
                lon_v = float(m.group(4)) * (-1 if m.group(3)=="E" else 1)
        except: pass
        by_class.setdefault(cls,[]).append((evt,lon_v,lat_v))

    for cls in ["X","M","C","B","A"]:
        if cls not in by_class: continue
        evts = by_class[cls]
        xs,ys,tips,szs = [],[],[],[]
        fc = FLARE_COLORS.get(cls,"#64748b")
        for evt,lx,ly in evts:
            xs.append(lx); ys.append(ly)
            szs.append(CLASS_SIZE.get(cls,8))
            begin = (evt.get("beginTime","") or "")[:16]
            peak  = (evt.get("peakTime","")  or "")[:16]
            region= evt.get("activeRegionNum","—")
            tips.append(
                f"<b>{evt.get('classType','?')} Flare</b><br>"
                f"Region: AR{region}<br>"
                f"Location: {evt.get('sourceLocation','—')}<br>"
                f"Begin: {begin}<br>Peak: {peak}<extra></extra>")
        fig.add_trace(go.Scatter(
            x=xs,y=ys,mode="markers",
            marker=dict(size=szs,color=fc,opacity=0.9,
                        symbol="circle",
                        line=dict(color="rgba(255,255,255,0.4)",width=1.2)),
            hovertemplate=tips,name=f"{cls}-class",showlegend=True,
        ))

    # Sun label
    fig.add_annotation(x=0,y=92,text="Solar Disk (Heliographic Coords)",showarrow=False,
        font=dict(size=10,color="#64748b",family="Space Mono"),xanchor="center")

    fig.update_layout(
        **MAP_LAYOUT,
        height=560,
        title=dict(text="Solar Flare Locations on the Solar Disk",
                   font=dict(color="#64748b",size=12,family="Space Mono"),x=0.5,xanchor="center"),
        xaxis=dict(visible=False,range=[-105,105],scaleanchor="y",scaleratio=1),
        yaxis=dict(visible=False,range=[-105,105]),
        dragmode="pan",
    )
    return fig

# ── GST Global Impact Map ─────────────────────────────────────────────────────
def build_gst_map(gst_data):
    """
    Choropleth-style world map showing geomagnetic storm impact zones.
    Higher Kp storms affect lower latitudes (auroral oval expands).
    Aurora visibility zones are drawn as latitude bands.
    Each storm is plotted as a timeline bubble.
    """
    fig = go.Figure()

    # World map basemap via choropleth with uniform colouring
    fig.add_trace(go.Choropleth(
        locations=["AFG","ALB","DZA","AND","AGO","ARG","ARM","AUS","AUT","AZE",
                   "BHS","BHR","BGD","BRB","BLR","BEL","BLZ","BEN","BTN","BOL",
                   "BIH","BWA","BRA","BRN","BGR","BFA","BDI","CPV","KHM","CMR",
                   "CAN","CAF","TCD","CHL","CHN","COL","COM","COD","COG","CRI",
                   "CIV","HRV","CUB","CYP","CZE","DNK","DJI","DOM","ECU","EGY",
                   "SLV","GNQ","ERI","EST","SWZ","ETH","FJI","FIN","FRA","GAB",
                   "GMB","GEO","DEU","GHA","GRC","GTM","GIN","GNB","GUY","HTI",
                   "HND","HUN","ISL","IND","IDN","IRN","IRQ","IRL","ISR","ITA",
                   "JAM","JPN","JOR","KAZ","KEN","PRK","KOR","XKX","KWT","KGZ",
                   "LAO","LVA","LBN","LSO","LBR","LBY","LIE","LTU","LUX","MDG",
                   "MWI","MYS","MDV","MLI","MLT","MRT","MUS","MEX","MDA","MNG",
                   "MNE","MAR","MOZ","MMR","NAM","NPL","NLD","NZL","NIC","NER",
                   "NGA","MKD","NOR","OMN","PAK","PAN","PNG","PRY","PER","PHL",
                   "POL","PRT","QAT","ROU","RUS","RWA","SAU","SEN","SRB","SLE",
                   "SVK","SVN","SOM","ZAF","SSD","ESP","LKA","SDN","SUR","SWE",
                   "CHE","SYR","TWN","TJK","TZA","THA","TLS","TGO","TTO","TUN",
                   "TUR","TKM","UGA","UKR","ARE","GBR","USA","URY","UZB","VEN",
                   "VNM","YEM","ZMB","ZWE"],
        z=[1]*200,
        colorscale=[[0,"#0b0f1e"],[1,"#0f1626"]],
        showscale=False,
        marker_line_color="#1a2340",
        marker_line_width=0.4,
        hoverinfo="skip",
        showlegend=False,
        name="_world",
    ))

    # Aurora visibility zones for each Kp level
    # Kp 4→65°, Kp 5→60°, Kp 6→55°, Kp 7→50°, Kp 8→45°, Kp 9→40°
    aurora_zones = [(4,65,"#22c55e",0.08),(5,60,"#a855f7",0.10),
                    (6,55,"#f59e0b",0.12),(7,50,"#ef4444",0.14),(8,45,"#ef4444",0.18)]
    lons = list(range(-180,181,2))
    for kp_thresh, lat_bound, col, al in aurora_zones:
        # North band
        fig.add_trace(go.Scattergeo(
            lon=lons+lons[::-1],
            lat=[lat_bound]*len(lons)+[90]*len(lons),
            fill="toself", fillcolor=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},{al})",
            line=dict(width=0), mode="lines",
            hoverinfo="skip", showlegend=False, name=f"_az{kp_thresh}N"))
        # South band
        fig.add_trace(go.Scattergeo(
            lon=lons+lons[::-1],
            lat=[-lat_bound]*len(lons)+[-90]*len(lons),
            fill="toself", fillcolor=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},{al})",
            line=dict(width=0), mode="lines",
            hoverinfo="skip", showlegend=False, name=f"_az{kp_thresh}S"))

    # Storm events as geo bubbles – placed at a random lon on the auroral latitude
    if gst_data:
        rng4 = random.Random(55)
        evts = sorted(gst_data, key=lambda x: x.get("startTime",""))
        for i,evt in enumerate(evts):
            kp_obs  = evt.get("allKpIndex") or []
            max_kp  = max((float(k["kpIndex"]) for k in kp_obs if k.get("kpIndex")), default=3)
            lat_pos = 90 - max_kp * 5.5
            lon_pos = rng4.uniform(-160,160)
            start_t = (evt.get("startTime","") or "")[:10]
            gc      = gst_color(max_kp)
            sz      = max(8, min(30, int(max_kp * 3.5)))
            fig.add_trace(go.Scattergeo(
                lon=[lon_pos], lat=[lat_pos],
                mode="markers",
                marker=dict(size=sz, color=gc, opacity=0.85,
                            line=dict(color="rgba(255,255,255,0.5)",width=1.2)),
                hovertemplate=(
                    f"<b>Geomagnetic Storm</b><br>"
                    f"Date: {start_t}<br>"
                    f"Max Kp: {max_kp}<br>"
                    f"Level: {gst_label(max_kp)}<extra></extra>"
                ),
                showlegend=False, name=f"GST Kp{max_kp}"))

    # Legend proxies for aurora zones
    for lbl,clr in [("Kp≥4 aurora zone (65°+)","#22c55e"),
                     ("Kp≥5 (60°+)","#a855f7"),
                     ("Kp≥6 (55°+)","#f59e0b"),
                     ("Kp≥7 severe (50°+)","#ef4444")]:
        fig.add_trace(go.Scattergeo(lat=[None],lon=[None],mode="markers",
            marker=dict(size=10,color=clr,symbol="square"),
            name=lbl,showlegend=True))

    fig.update_geos(
        bgcolor="#04060f",
        landcolor="#0f1626",
        oceancolor="#04060f",
        showocean=True,
        showland=True,
        showcountries=True, countrycolor="#1a2340",
        showcoastlines=True, coastlinecolor="#1a2340",
        showframe=False,
        projection_type="natural earth",
        lataxis_range=[-90,90],
        lonaxis_range=[-180,180],
    )
    fig.update_layout(
        **MAP_LAYOUT,
        height=560,
        geo=dict(bgcolor="#04060f"),
        title=dict(text="Geomagnetic Storm Impact — Global Aurora Visibility Zones",
                   font=dict(color="#64748b",size=12,family="Space Mono"),x=0.5,xanchor="center"),
    )
    return fig

# ── HSS Solar Wind Stream Map ─────────────────────────────────────────────────
def build_hss_map(hss_data):
    """
    Polar heliospheric map showing solar wind streams as sector arcs.
    The Sun sits at center; Earth at 1 AU.
    HSS events drawn as fast-wind arcs from coronal holes.
    Background slow/fast wind sector pattern.
    """
    fig = go.Figure()
    starfield(fig, xlim=1.7, ylim=1.7)

    # Background slow-wind sectors (alternating)
    rng5 = random.Random(21)
    n_sectors = 8
    for s in range(n_sectors):
        a_start = 2*math.pi*s/n_sectors
        a_end   = 2*math.pi*(s+1)/n_sectors
        pts = 30
        angles = [a_start + (a_end-a_start)*i/(pts-1) for i in range(pts)]
        sx = [0]+[1.6*math.cos(a) for a in angles]+[0]
        sy = [0]+[1.6*math.sin(a) for a in angles]+[0]
        col = "rgba(30,58,138,0.10)" if s%2==0 else "rgba(15,22,38,0.10)"
        fig.add_trace(go.Scatter(x=sx,y=sy,fill="toself",fillcolor=col,
            line=dict(width=0),hoverinfo="skip",showlegend=False,name="_sec"))

    # Orbit rings
    for r,name,col,angle_deg in [(0.387,"Mercury","#b5b5b5",45),(0.723,"Venus","#e8cda0",120),
                                   (1.000,"Earth","#4f8ef7",0),(1.524,"Mars","#c1440e",220)]:
        cx,cy = circle_xy(r)
        fig.add_trace(go.Scatter(x=cx,y=cy,mode="lines",
            line=dict(color="rgba(255,255,255,0.07)",width=1,dash="dot"),
            hoverinfo="skip",showlegend=False,name=f"_o{name}"))
        a = angle_deg*math.pi/180
        fig.add_trace(go.Scatter(x=[r*math.cos(a)],y=[r*math.sin(a)],
            mode="markers+text",
            marker=dict(size=9 if name=="Earth" else 6,color=col,
                        line=dict(color="rgba(255,255,255,0.3)",width=1)),
            text=[name],textposition="top center",
            textfont=dict(color=col,size=9,family="Space Mono"),
            hovertemplate=f"<b>{name}</b><br>{r} AU<extra></extra>",
            showlegend=False,name=name))

    sun_glows(fig)

    # Parker spiral reference lines (slow wind ~400 km/s)
    def parker_spiral(omega_deg=360/25.4, v_sw=400):
        """Generate Parker spiral (r AU vs angle)."""
        pts = []
        r_au_AU_per_day = v_sw * 86400 / 149597870
        for angle_deg in range(0, 720, 4):
            a_rad = math.radians(angle_deg)
            r = r_au_AU_per_day * angle_deg / omega_deg
            if r > 1.6: break
            pts.append((r*math.cos(a_rad), r*math.sin(a_rad)))
        return pts

    for offset in [0,90,180,270]:
        pts = parker_spiral()
        if pts:
            px = [p[0]*math.cos(math.radians(offset)) - p[1]*math.sin(math.radians(offset)) for p in pts]
            py = [p[0]*math.sin(math.radians(offset)) + p[1]*math.cos(math.radians(offset)) for p in pts]
            fig.add_trace(go.Scatter(x=px,y=py,mode="lines",
                line=dict(color="rgba(148,163,184,0.12)",width=1,dash="dot"),
                hoverinfo="skip",showlegend=False,name="_parker"))

    # HSS events as fast-wind arcs
    n_hss = len(hss_data)
    for i,evt in enumerate(sorted(hss_data, key=lambda x: x.get("eventTime",""))):
        evt_t   = (evt.get("eventTime","") or "")[:16]
        hss_id  = evt.get("hssID","?")
        insts   = evt.get("instruments") or []
        inst_str= ", ".join(ii.get("displayName","") for ii in insts) or "—"

        # Spread evenly around the solar disk
        base_angle  = 2*math.pi*i/max(n_hss,1)
        jitter      = rng5.uniform(-0.2,0.2)
        direction   = base_angle + jitter
        half_w      = math.radians(rng5.uniform(18,35))
        R_inner, R_outer = 0.08, 1.55

        angles = [direction-half_w + 2*half_w*j/30 for j in range(31)]
        # outer arc → back to center
        wx = [R_inner*math.cos(direction)] + \
             [R_outer*math.cos(a) for a in angles] + \
             [R_inner*math.cos(direction)]
        wy = [R_inner*math.sin(direction)] + \
             [R_outer*math.sin(a) for a in angles] + \
             [R_inner*math.sin(direction)]

        recency = 0.15 + 0.6*(i/max(n_hss-1,1))
        fig.add_trace(go.Scatter(
            x=wx, y=wy,
            fill="toself",
            fillcolor=f"rgba(34,197,94,{recency*0.35})",
            line=dict(color=f"rgba(34,197,94,{recency*0.8})",width=1.2),
            mode="lines",
            hovertemplate=(
                f"<b>HSS · {hss_id}</b><br>"
                f"Event time: {evt_t}<br>"
                f"Instruments: {inst_str}<extra></extra>"
            ),
            showlegend=False, name=hss_id))

    # Legend
    for lbl,clr,sym in [("Parker spiral (slow wind)","#94a3b8","line"),
                          ("HSS fast-wind stream","#22c55e","square"),
                          ("Background sector","#1e3a8a","square")]:
        if sym == "line":
            fig.add_trace(go.Scatter(x=[None],y=[None],mode="lines",
                line=dict(color=clr,dash="dot"),name=lbl,showlegend=True))
        else:
            fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",
                marker=dict(size=10,color=clr,symbol="square"),name=lbl,showlegend=True))

    fig.update_layout(
        **MAP_LAYOUT,
        height=600,
        title=dict(text="Solar Wind High-Speed Streams — Heliospheric Sector Map",
                   font=dict(color="#64748b",size=12,family="Space Mono"),x=0.5,xanchor="center"),
        xaxis=dict(visible=False,range=[-1.75,1.75],scaleanchor="y",scaleratio=1),
        yaxis=dict(visible=False,range=[-1.75,1.75]),
        dragmode="pan",
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
cl,ct,cb = st.columns([0.06,0.70,0.24])
with cl:
    st.markdown("""<div style="width:52px;height:52px;background:radial-gradient(circle,#451a03,#0f172a);
    border:2px solid #f59e0b;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:9px;font-weight:700;color:#f59e0b;letter-spacing:1px;
box-shadow:0 0 20px rgba(245,158,11,.3);margin-top:6px">Spaceport</div>""",unsafe_allow_html=True)
with ct:
    st.markdown("## 🌩️ Space Weather Database (DONKI)")
    st.caption("Notifications, Knowledge, Information — powered by NASA CCMC")
with cb:
    st.markdown("""<div style="margin-top:14px;text-align:right"><span style="background:rgba(245,158,11,.1);
    border:1px solid rgba(245,158,11,.3);border-radius:20px;padding:4px 12px;font-size:12px;
    color:#f59e0b;font-weight:500">● Live Data</span></div>""",unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 24px'>",unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌩️ DONKI Controls")
    donki_days  = st.slider("Lookback window (days)", 7, 90, 30)
    donki_end   = str(date.today())
    donki_start = str(date.today() - timedelta(days=donki_days))
    st.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-radius:8px;padding:10px 12px;
    font-family:'Space Mono',monospace;font-size:11px;color:#64748b;margin-top:4px">
    {donki_start}<br>→ {donki_end}
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#475569;line-height:1.8">
    <b style="color:#64748b">Event types</b><br>
    <span style="color:#f59e0b">■</span> CME — Coronal Mass Ejection<br>
    <span style="color:#ef4444">■</span> FLR — Solar Flare<br>
    <span style="color:#a855f7">■</span> GST — Geomagnetic Storm<br>
    <span style="color:#22c55e">■</span> HSS — High-Speed Stream
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data from [NASA DONKI API](https://api.nasa.gov/)")

st.markdown(f"**Showing events from** `{donki_start}` → `{donki_end}` ({donki_days} days)")

# ── Fetch ─────────────────────────────────────────────────────────────────────
with st.spinner("Fetching space weather data from DONKI…"):
    try:
        cme_data = fetch_donki("CME", donki_start, donki_end)
        flr_data = fetch_donki("FLR", donki_start, donki_end)
        gst_data = fetch_donki("GST", donki_start, donki_end)
        hss_data = fetch_donki("HSS", donki_start, donki_end)
    except Exception as e:
        st.error(f"⚠️ Failed to fetch DONKI data: {e}")
        st.stop()

# ── Summary stats ─────────────────────────────────────────────────────────────
dc1,dc2,dc3,dc4 = st.columns(4)
stat_card(dc1,"☀️ CME Events",         len(cme_data),"#f59e0b","Coronal Mass Ejections")
stat_card(dc2,"🔥 Solar Flares",       len(flr_data),"#ef4444","All classes")
stat_card(dc3,"🌍 Geomagnetic Storms", len(gst_data),"#a855f7","Kp-based")
stat_card(dc4,"💨 Solar Wind Streams", len(hss_data),"#22c55e","High-speed streams")
st.markdown("<br>",unsafe_allow_html=True)

# ── Activity timeline ─────────────────────────────────────────────────────────
st.markdown("### 📈 Event Activity Timeline")

def events_to_daily(data, time_key):
    counts = {}
    for evt in data:
        ts = (evt.get(time_key,"") or "")[:10]
        if ts: counts[ts] = counts.get(ts,0)+1
    return counts

cme_daily = events_to_daily(cme_data,"startTime")
flr_daily = events_to_daily(flr_data,"beginTime")
gst_daily = events_to_daily(gst_data,"startTime")
hss_daily = events_to_daily(hss_data,"eventTime")
all_dates = sorted(set(list(cme_daily)+list(flr_daily)+list(gst_daily)+list(hss_daily)))

if all_dates:
    fig_tl = go.Figure()
    for daily,label,color in [
        (cme_daily,"CME","#f59e0b"),(flr_daily,"Solar Flare","#ef4444"),
        (gst_daily,"Geomag Storm","#a855f7"),(hss_daily,"Solar Wind","#22c55e"),
    ]:
        fig_tl.add_trace(go.Bar(
            x=all_dates, y=[daily.get(d,0) for d in all_dates],
            name=label, marker_color=color, opacity=0.85,
            hovertemplate=f"<b>{label}</b><br>%{{x}}<br>Events: %{{y}}<extra></extra>"))
    fig_tl.update_layout(
        barmode="stack", paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
        height=240, margin=dict(l=10,r=10,t=10,b=10),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,
                    font=dict(color="#94a3b8",size=11,family="Space Mono"),bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False,color="#64748b",tickfont=dict(family="Space Mono",size=10)),
        yaxis=dict(showgrid=True,gridcolor="#1a2340",color="#64748b",
                   tickfont=dict(family="Space Mono",size=10)),
        hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                        font=dict(color="#e2e8f0",size=12,family="Space Mono")))
    st.plotly_chart(fig_tl, use_container_width=True)
else:
    st.info("No timeline data available.")

st.markdown("<br>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════
d1,d2,d3,d4 = st.tabs([
    "☀️ Coronal Mass Ejections",
    "🔥 Solar Flares",
    "🌍 Geomagnetic Storms",
    "💨 Solar Wind Streams",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – CME
# ══════════════════════════════════════════════════════════════════════════════
with d1:
    st.markdown(f"#### Coronal Mass Ejections &nbsp; `{len(cme_data)}`",unsafe_allow_html=True)
    st.caption("Large expulsions of plasma and magnetic field from the Sun's corona. Earth-directed CMEs can cause radio blackouts and geomagnetic storms.")

    # ── CME MAP ───────────────────────────────────────────────────────────────
    section_header("☀️ CME PROPAGATION MAP",
        "Top-down view of the inner heliosphere. Each wedge shows a CME's angular extent and direction. "
        "Colour = speed: red ≥1500 km/s · amber 800–1500 · purple <800. Newer events are brighter.")
    if cme_data:
        st.plotly_chart(build_cme_map(cme_data), use_container_width=True,
            config={"scrollZoom":True,"displayModeBar":True,
                    "modeBarButtonsToRemove":["select2d","lasso2d"],
                    "toImageButtonOptions":{"format":"png","filename":"cme_map"}})
        # Map legend row
        lc1,lc2,lc3,lc4 = st.columns(4)
        for col,(lbl,clr,desc) in zip([lc1,lc2,lc3,lc4],[
            ("Extreme","#ef4444","≥ 1500 km/s"),
            ("Fast","#f59e0b","800–1500 km/s"),
            ("Moderate","#a855f7","< 800 km/s"),
            ("Older → Newer","#64748b","opacity ramp"),
        ]):
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid {clr}33;border-left:3px solid {clr};
            border-radius:8px;padding:10px 12px">
              <div style="font-size:11px;font-weight:600;color:{clr}">{lbl}</div>
              <div style="font-size:10px;color:#64748b;margin-top:2px">{desc}</div>
            </div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
    else:
        st.info("No CME data to map.")

    # ── Speed histogram ───────────────────────────────────────────────────────
    section_header("📊 CME SPEED DISTRIBUTION","")
    speeds = []
    for evt in cme_data:
        for a in (evt.get("cmeAnalyses") or []):
            try: speeds.append(float(a["speed"]))
            except: pass
    if speeds:
        fig_spd = go.Figure(go.Histogram(
            x=speeds, nbinsx=15, marker_color="#f59e0b", opacity=0.8,
            hovertemplate="Speed: %{x} km/s<br>Count: %{y}<extra></extra>"))
        fig_spd.update_layout(paper_bgcolor="#04060f",plot_bgcolor="#0f1626",height=180,
            margin=dict(l=10,r=10,t=10,b=10),
            xaxis=dict(showgrid=False,color="#64748b",tickfont=dict(family="Space Mono",size=10),title="km/s"),
            yaxis=dict(showgrid=True,gridcolor="#1a2340",color="#64748b",
                       tickfont=dict(family="Space Mono",size=10)),
            hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                            font=dict(color="#e2e8f0",size=12,family="Space Mono")))
        st.plotly_chart(fig_spd, use_container_width=True)

    # ── Event cards ───────────────────────────────────────────────────────────
    section_header("📋 CME EVENT LOG","")
    if not cme_data:
        st.info("No CME events in the selected period.")
    else:
        for evt in sorted(cme_data, key=lambda x: x.get("startTime",""), reverse=True):
            act_ts   = (evt.get("startTime","") or "")[:16]
            note     = evt.get("note","") or "No additional notes."
            analyses = evt.get("cmeAnalyses") or []
            speed, hangle, etype = "—","—","—"
            if analyses:
                best   = sorted(analyses,key=lambda x: x.get("isMostAccurate",False),reverse=True)[0]
                speed  = best.get("speed","—"); hangle = best.get("halfAngle","—")
                etype  = (best.get("type","—") or "—")
            linked     = evt.get("linkedEvents") or []
            linked_str = ", ".join(l.get("activityID","") for l in linked) if linked else "None"
            body = (f"<b>Speed:</b> {speed} km/s &nbsp;·&nbsp; <b>Half-angle:</b> {hangle}° "
                    f"&nbsp;·&nbsp; <b>Type:</b> {etype}<br>"
                    f"<b>Linked:</b> {linked_str}<br>"
                    f"<span style='color:#64748b'>{str(note)[:200]}{'…' if len(str(note))>200 else ''}</span>")
            bc = "#ef4444" if etype in ("S","R","O") else "#f59e0b"
            st.markdown(event_card(
                title=evt.get("activityID","CME Event"), subtitle=f"Start: {act_ts}",
                body_html=body, badge_label=f"CME · {etype}",
                badge_color=bc, border_color="rgba(245,158,11,0.3)"),unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – SOLAR FLARES
# ══════════════════════════════════════════════════════════════════════════════
with d2:
    st.markdown(f"#### Solar Flares &nbsp; `{len(flr_data)}`",unsafe_allow_html=True)
    st.caption("Intense bursts of radiation from the Sun. Classified X→A by decreasing intensity.")

    # ── FLR MAP ───────────────────────────────────────────────────────────────
    section_header("☀️ SOLAR DISK FLARE MAP",
        "Heliographic projection of the solar disk. Each dot = one flare plotted at its source "
        "location. Size ∝ class intensity. Hover for details.")
    if flr_data:
        st.plotly_chart(build_flr_map(flr_data), use_container_width=True,
            config={"scrollZoom":True,"displayModeBar":True,
                    "modeBarButtonsToRemove":["select2d","lasso2d"],
                    "toImageButtonOptions":{"format":"png","filename":"flr_map"}})
        fl1,fl2,fl3,fl4,fl5 = st.columns(5)
        for col,(cls,desc) in zip([fl1,fl2,fl3,fl4,fl5],[
            ("X","Extreme — major blackouts"),("M","Strong — wide blackouts"),
            ("C","Moderate — minor blackouts"),("B","Minor — no blackouts"),("A","Micro-flare"),
        ]):
            clr = FLARE_COLORS.get(cls,"#64748b")
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid {clr}33;border-top:3px solid {clr};
            border-radius:8px;padding:10px;text-align:center">
              <div style="font-size:16px;font-weight:700;color:{clr}">{cls}</div>
              <div style="font-size:9px;color:#64748b;margin-top:4px">{desc}</div>
            </div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
    else:
        st.info("No flare data to map.")

    # ── Class breakdown ───────────────────────────────────────────────────────
    section_header("📊 FLARE CLASS BREAKDOWN","")
    if flr_data:
        class_counts = {}
        for f in flr_data:
            cls = (f.get("classType") or "U")[0].upper()
            class_counts[cls] = class_counts.get(cls,0)+1
        order = ["X","M","C","B","A","U"]
        sorted_cls = sorted(class_counts.items(), key=lambda x: order.index(x[0]) if x[0] in order else 99)
        bar_cols = st.columns(max(len(sorted_cls),1))
        for col,(cls,cnt) in zip(bar_cols,sorted_cls):
            clr = FLARE_COLORS.get(cls,"#64748b")
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid {clr}44;border-top:3px solid {clr};
            border-radius:10px;padding:12px;text-align:center">
              <div style="font-family:'Space Mono',monospace;font-size:28px;color:{clr};font-weight:700">{cnt}</div>
              <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-top:2px">{cls}-class</div>
            </div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)

    # ── Event cards ───────────────────────────────────────────────────────────
    section_header("📋 FLARE EVENT LOG","")
    if not flr_data:
        st.info("No solar flare events in the selected period.")
    else:
        for evt in sorted(flr_data, key=lambda x: x.get("beginTime",""), reverse=True):
            cls    = evt.get("classType","?")
            begin  = (evt.get("beginTime","")  or "")[:16]
            peak   = (evt.get("peakTime","")   or "")[:16]
            end_t  = (evt.get("endTime","")    or "")[:16]
            region = evt.get("activeRegionNum","—")
            loc    = evt.get("sourceLocation","—") or "—"
            linked = evt.get("linkedEvents") or []
            linked_str = ", ".join(l.get("activityID","") for l in linked) if linked else "None"
            body = (f"<b>Class:</b> {cls} &nbsp;·&nbsp; <b>Region:</b> AR{region} &nbsp;·&nbsp; "
                    f"<b>Location:</b> {loc}<br>"
                    f"<b>Begin:</b> {begin} &nbsp;·&nbsp; <b>Peak:</b> {peak} &nbsp;·&nbsp; <b>End:</b> {end_t}<br>"
                    f"<b>Linked:</b> {linked_str}")
            fc = flare_color(cls)
            st.markdown(event_card(
                title=f"Solar Flare · {cls}", subtitle=f"AR{region} · {begin}",
                body_html=body, badge_label=cls, badge_color=fc, border_color=fc+"44"),
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – GEOMAGNETIC STORMS
# ══════════════════════════════════════════════════════════════════════════════
with d3:
    st.markdown(f"#### Geomagnetic Storms &nbsp; `{len(gst_data)}`",unsafe_allow_html=True)
    st.caption("Disturbances in Earth's magnetosphere. Kp index 0–9. Kp ≥ 5 = storm; Kp ≥ 7 = severe.")

    # ── GST MAP ───────────────────────────────────────────────────────────────
    section_header("🌍 GLOBAL AURORA VISIBILITY MAP",
        "Coloured bands show how far equatorward auroras can be seen for each Kp level. "
        "Storm event bubbles are plotted at their approximate auroral latitude. Bubble size = Kp intensity.")
    if gst_data:
        st.plotly_chart(build_gst_map(gst_data), use_container_width=True,
            config={"scrollZoom":True,"displayModeBar":True,
                    "modeBarButtonsToRemove":["select2d","lasso2d"],
                    "toImageButtonOptions":{"format":"png","filename":"gst_map"}})
        gk1,gk2,gk3,gk4 = st.columns(4)
        for col,(lbl,val,clr) in zip([gk1,gk2,gk3,gk4],[
            ("Minor G1","Kp 4–4.9","#22c55e"),("Moderate G2","Kp 5–5.9","#a855f7"),
            ("Strong G3","Kp 6–6.9","#f59e0b"),("Severe G4+","Kp ≥ 7","#ef4444")]):
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid {clr}44;border-radius:8px;
            padding:8px 10px;text-align:center">
              <div style="font-size:11px;font-weight:600;color:{clr}">{lbl}</div>
              <div style="font-size:10px;color:#64748b;margin-top:2px;font-family:'Space Mono',monospace">{val}</div>
            </div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
    else:
        st.info("No geomagnetic storm data to map.")

    # ── Kp timeline chart ─────────────────────────────────────────────────────
    section_header("📊 DAILY MAX KP INDEX","")
    if gst_data:
        kp_rows = []
        for evt in gst_data:
            for obs in (evt.get("allKpIndex") or []):
                try: kp_rows.append({"time":obs["observedTime"][:10],"kp":float(obs["kpIndex"])})
                except: pass
        if kp_rows:
            kp_df = pd.DataFrame(kp_rows).groupby("time")["kp"].max().reset_index()
            kp_df.columns = ["Date","Max Kp"]
            fig_kp = go.Figure()
            fig_kp.add_trace(go.Bar(
                x=kp_df["Date"], y=kp_df["Max Kp"],
                marker_color=["#ef4444" if v>=7 else "#f59e0b" if v>=5 else "#a855f7" if v>=4 else "#22c55e"
                              for v in kp_df["Max Kp"]],
                hovertemplate="<b>%{x}</b><br>Max Kp: %{y}<extra></extra>"))
            for kp_val,lbl,clr in [(5,"G2 Storm","#f59e0b"),(7,"G3 Severe","#ef4444")]:
                fig_kp.add_hline(y=kp_val,line_dash="dot",line_color=clr,opacity=0.5,
                    annotation_text=lbl,annotation_font=dict(color=clr,size=10,family="Space Mono"))
            fig_kp.update_layout(paper_bgcolor="#04060f",plot_bgcolor="#0f1626",
                height=220,margin=dict(l=10,r=10,t=20,b=10),
                xaxis=dict(showgrid=False,color="#64748b",tickfont=dict(family="Space Mono",size=10)),
                yaxis=dict(showgrid=True,gridcolor="#1a2340",color="#64748b",
                           tickfont=dict(family="Space Mono",size=10),range=[0,9]),
                hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                                font=dict(color="#e2e8f0",size=12,family="Space Mono")))
            st.plotly_chart(fig_kp, use_container_width=True)

    # ── Event cards ───────────────────────────────────────────────────────────
    section_header("📋 STORM EVENT LOG","")
    if not gst_data:
        st.info("No geomagnetic storms in the selected period.")
    else:
        for evt in sorted(gst_data, key=lambda x: x.get("startTime",""), reverse=True):
            start_t  = (evt.get("startTime","") or "")[:16]
            gst_id   = evt.get("gstID","?")
            kp_obs   = evt.get("allKpIndex") or []
            max_kp   = max((float(k["kpIndex"]) for k in kp_obs if k.get("kpIndex")),default=0)
            linked   = evt.get("linkedEvents") or []
            linked_str = ", ".join(l.get("activityID","") for l in linked) if linked else "None"
            body = (f"<b>Max Kp:</b> {max_kp} &nbsp;·&nbsp; <b>Level:</b> {gst_label(max_kp)}<br>"
                    f"<b>Kp readings:</b> {len(kp_obs)}<br><b>Linked:</b> {linked_str}")
            gc = gst_color(max_kp)
            st.markdown(event_card(
                title=f"Geomagnetic Storm · Kp {max_kp}", subtitle=f"ID: {gst_id} · Start: {start_t}",
                body_html=body, badge_label=gst_label(max_kp), badge_color=gc, border_color=gc+"44"),
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – SOLAR WIND / HSS
# ══════════════════════════════════════════════════════════════════════════════
with d4:
    st.markdown(f"#### High-Speed Streams (Solar Wind) &nbsp; `{len(hss_data)}`",unsafe_allow_html=True)
    st.caption("Fast solar wind flows from coronal holes. Can trigger auroras at mid-latitudes.")

    # ── HSS MAP ───────────────────────────────────────────────────────────────
    section_header("💨 HELIOSPHERIC SECTOR MAP",
        "Top-down view of the heliosphere. Green wedges show high-speed stream sectors radiating from the Sun. "
        "Dashed lines = Parker spiral (slow wind). Newer streams are brighter.")
    if hss_data:
        st.plotly_chart(build_hss_map(hss_data), use_container_width=True,
            config={"scrollZoom":True,"displayModeBar":True,
                    "modeBarButtonsToRemove":["select2d","lasso2d"],
                    "toImageButtonOptions":{"format":"png","filename":"hss_map"}})
        hc1,hc2,hc3 = st.columns(3)
        for col,(lbl,clr,desc) in zip([hc1,hc2,hc3],[
            ("Fast Wind Stream","#22c55e","700–900 km/s from coronal holes"),
            ("Parker Spiral","#94a3b8","Slow wind structure ~400 km/s"),
            ("Background Sector","#1e3a8a","HCS sector boundaries"),
        ]):
            col.markdown(f"""
            <div style="background:#0f1626;border:1px solid {clr}44;border-left:3px solid {clr};
            border-radius:8px;padding:10px 12px">
              <div style="font-size:11px;font-weight:600;color:{clr}">{lbl}</div>
              <div style="font-size:10px;color:#64748b;margin-top:3px">{desc}</div>
            </div>""",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
    else:
        st.info("No HSS data to map.")

    # ── Event cards ───────────────────────────────────────────────────────────
    section_header("📋 HSS EVENT LOG","")
    if not hss_data:
        st.info("No High-Speed Stream events in the selected period.")
    else:
        for evt in sorted(hss_data, key=lambda x: x.get("eventTime",""), reverse=True):
            evt_t  = (evt.get("eventTime","") or "")[:16]
            hss_id = evt.get("hssID","?")
            instruments = evt.get("instruments") or []
            inst_str = ", ".join(i.get("displayName","") for i in instruments) or "—"
            linked   = evt.get("linkedEvents") or []
            linked_str = ", ".join(l.get("activityID","") for l in linked) if linked else "None"
            body = (f"<b>Instruments:</b> {inst_str}<br><b>Linked:</b> {linked_str}")
            st.markdown(event_card(
                title=f"High-Speed Stream · {hss_id}", subtitle=f"Event time: {evt_t}",
                body_html=body, badge_label="HSS", badge_color="#22c55e",
                border_color="rgba(34,197,94,0.3)"),unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>",unsafe_allow_html=True)
st.markdown("""
<div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#64748b;line-height:1.8">
    <b style="color:#94a3b8">About DONKI</b> — The Space Weather Database Of Notifications,
    Knowledge, Information is maintained by NASA's Community Coordinated Modeling Center (CCMC).
    It chronicles daily interpretations of space weather observations by the Moon-to-Mars Space
    Weather Analysis Office (M2M-SWAO). &nbsp;·&nbsp;
    <b style="color:#f59e0b">CME</b>: Coronal Mass Ejection &nbsp;·&nbsp;
    <b style="color:#ef4444">FLR</b>: Solar Flare &nbsp;·&nbsp;
    <b style="color:#a855f7">GST</b>: Geomagnetic Storm &nbsp;·&nbsp;
    <b style="color:#22c55e">HSS</b>: High-Speed Stream
  </div>
</div>""",unsafe_allow_html=True)
