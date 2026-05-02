import streamlit as st
import requests
import streamlit.components.v1 as components
from datetime import date, timedelta
import pandas as pd
import time

st.set_page_config(
    page_title="Spaceport | GIBS",
    page_icon="🛰️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');

html, body, [class*="css"]          { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"]           { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] *         { color:#e2e8f0 !important; }
[data-testid="stTabs"] button       { color:#64748b !important; font-family:'Space Mono',monospace !important; font-size:11px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#38bdf8 !important; border-bottom-color:#38bdf8 !important; }
[data-testid="metric-container"]    { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
h1,h2,h3                            { color:#e2e8f0 !important; }
div[data-baseweb="select"] > div    { background:#0f1626 !important; border-color:#1a2340 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑  Constants
# ══════════════════════════════════════════════════════════════════════════════
NASA_KEY   = "rV6H5dIlCawxnw4zuQ8y1khmFIoxewTjNM1cvXgC"
GIBS_WMS   = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
GIBS_WMTS  = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi"
ACCENT     = "#38bdf8"

# ── Layer catalogue — hand-picked best layers per category ────────────────────
LAYERS = {
    "🌍 True Colour": [
        {"id": "MODIS_Terra_CorrectedReflectance_TrueColor",   "label": "MODIS Terra — True Colour",         "res": "250m", "start": "2002-07-04"},
        {"id": "MODIS_Aqua_CorrectedReflectance_TrueColor",    "label": "MODIS Aqua — True Colour",          "res": "250m", "start": "2002-07-04"},
        {"id": "VIIRS_SNPP_CorrectedReflectance_TrueColor",    "label": "VIIRS Suomi NPP — True Colour",     "res": "250m", "start": "2012-01-20"},
        {"id": "VIIRS_NOAA20_CorrectedReflectance_TrueColor",  "label": "VIIRS NOAA-20 — True Colour",       "res": "250m", "start": "2018-05-01"},
        {"id": "VIIRS_NOAA21_CorrectedReflectance_TrueColor",  "label": "VIIRS NOAA-21 — True Colour",       "res": "250m", "start": "2023-02-10"},
    ],
    "🔥 Fire & Thermal": [
        {"id": "MODIS_Terra_Thermal_Anomalies_Day",            "label": "MODIS Terra — Thermal Anomalies (Day)",   "res": "1km",  "start": "2002-07-04"},
        {"id": "MODIS_Aqua_Thermal_Anomalies_Day",             "label": "MODIS Aqua — Thermal Anomalies (Day)",    "res": "1km",  "start": "2002-07-04"},
        {"id": "VIIRS_SNPP_Thermal_Anomalies_375m_All",        "label": "VIIRS Suomi NPP — Thermal Anomalies 375m","res": "375m", "start": "2012-01-20"},
        {"id": "VIIRS_NOAA20_Thermal_Anomalies_375m_All",      "label": "VIIRS NOAA-20 — Thermal Anomalies 375m", "res": "375m", "start": "2018-01-01"},
    ],
    "🌊 Sea Surface": [
        {"id": "GHRSST_L4_MUR_Sea_Surface_Temperature",        "label": "GHRSST MUR — Sea Surface Temp",          "res": "1km",  "start": "2010-06-01"},
        {"id": "MODIS_Terra_L3_SST_MidIR_9km_Night_Daily",     "label": "MODIS Terra — SST Night 9km",            "res": "9km",  "start": "2003-01-01"},
        {"id": "MODIS_Aqua_L3_SST_MidIR_9km_Night_Daily",      "label": "MODIS Aqua — SST Night 9km",             "res": "9km",  "start": "2003-01-01"},
    ],
    "❄️ Ice & Snow": [
        {"id": "MODIS_Terra_Sea_Ice",                          "label": "MODIS Terra — Sea Ice",                  "res": "1km",  "start": "2002-07-04"},
        {"id": "MODIS_Aqua_Sea_Ice",                           "label": "MODIS Aqua — Sea Ice",                   "res": "1km",  "start": "2002-07-04"},
        {"id": "VIIRS_SNPP_Ice_Surface_Temp_Night",            "label": "VIIRS Suomi NPP — Ice Surface Temp Night","res": "1km",  "start": "2012-01-20"},
        {"id": "MODIS_Terra_Snow_Cover_Daily",                 "label": "MODIS Terra — Snow Cover",               "res": "500m", "start": "2002-07-04"},
    ],
    "🌫️ Atmosphere": [
        {"id": "MODIS_Terra_Aerosol",                          "label": "MODIS Terra — Aerosol Optical Depth",    "res": "10km", "start": "2002-07-04"},
        {"id": "MODIS_Aqua_Aerosol",                           "label": "MODIS Aqua — Aerosol Optical Depth",     "res": "10km", "start": "2002-07-04"},
        {"id": "MODIS_Terra_Water_Vapor_5km_Day",              "label": "MODIS Terra — Water Vapour (Day)",       "res": "5km",  "start": "2002-07-04"},
        {"id": "MODIS_Terra_Cloud_Top_Temp_Day",               "label": "MODIS Terra — Cloud Top Temperature",    "res": "5km",  "start": "2002-07-04"},
        {"id": "OMI_AI_Radiometric",                           "label": "OMI — Aerosol Index (Radiometric)",      "res": "25km", "start": "2004-10-01"},
    ],
    "🌱 Land & Vegetation": [
        {"id": "MODIS_Terra_NDVI_8Day",                        "label": "MODIS Terra — NDVI 8-Day",               "res": "250m", "start": "2002-07-04"},
        {"id": "MODIS_Aqua_NDVI_8Day",                         "label": "MODIS Aqua — NDVI 8-Day",                "res": "250m", "start": "2002-07-04"},
        {"id": "MODIS_Terra_Land_Surface_Temp_Day",            "label": "MODIS Terra — Land Surface Temp (Day)",  "res": "1km",  "start": "2002-07-04"},
        {"id": "MODIS_Aqua_Land_Surface_Temp_Day",             "label": "MODIS Aqua — Land Surface Temp (Day)",   "res": "1km",  "start": "2002-07-04"},
    ],
    "🌧️ Precipitation": [
        {"id": "IMERG_Precipitation_Rate",                     "label": "GPM IMERG — Precipitation Rate",         "res": "10km", "start": "2014-04-01"},
        {"id": "TRMM_3B42RT_Precipitation_3hr",                "label": "TRMM — Precipitation 3-Hour",            "res": "25km", "start": "2000-03-01"},
    ],
    "💧 Soil & Water": [
        {"id": "SMAP_L4_Analyzed_Surface_Soil_Moisture",       "label": "SMAP L4 — Surface Soil Moisture",        "res": "9km",  "start": "2015-04-01"},
        {"id": "SMAP_L4_Analyzed_Root_Zone_Soil_Moisture",     "label": "SMAP L4 — Root Zone Soil Moisture",      "res": "9km",  "start": "2015-04-01"},
    ],
}

# Flatten for easy lookup
ALL_LAYERS = {lyr["id"]: lyr for cat_layers in LAYERS.values() for lyr in cat_layers}

# ══════════════════════════════════════════════════════════════════════════════
# 🎨  UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:20px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:20px;color:{color};
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

def wms_image_url(layer_id: str, img_date: str,
                  bbox="-180,-90,180,90", width=1024, height=512,
                  fmt="image/jpeg") -> str:
    """Build a WMS GetMap URL for a GIBS layer."""
    params = (
        f"SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
        f"&LAYERS={layer_id}&STYLES=&CRS=EPSG:4326"
        f"&BBOX={bbox}&WIDTH={width}&HEIGHT={height}"
        f"&FORMAT={fmt}&TIME={img_date}"
    )
    return f"{GIBS_WMS}?{params}"

def layer_card(col, lyr: dict, img_date: str, selected: bool = False):
    """Render a compact layer preview card."""
    border_color = ACCENT if selected else "#1a2340"
    url = wms_image_url(lyr["id"], img_date, width=400, height=200)
    col.markdown(f"""
    <div style="background:#0f1626;border:2px solid {border_color};border-radius:10px;
    overflow:hidden;margin-bottom:10px;cursor:pointer">
      <img src="{url}" style="width:100%;height:140px;object-fit:cover;display:block"
           loading="lazy" onerror="this.style.background='#0f1626';this.style.height='60px'" />
      <div style="padding:8px 10px">
        <div style="font-size:11px;font-weight:600;color:#e2e8f0;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{lyr['label']}</div>
        <div style="font-size:9px;color:#64748b;font-family:'Space Mono',monospace;
        margin-top:2px">📏 {lyr['res']} &nbsp;·&nbsp; 📅 since {lyr['start'][:7]}</div>
      </div>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  HEADER
# ══════════════════════════════════════════════════════════════════════════════
hl, hc, hr = st.columns([0.06, 0.70, 0.24])
with hl:
    st.markdown("""
    <div style="width:52px;height:52px;background:radial-gradient(circle,#0c4a6e,#0f172a);
    border:2px solid #38bdf8;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-family:'Space Mono',monospace;font-size:9px;font-weight:700;
    color:#38bdf8;letter-spacing:1px;box-shadow:0 0 20px rgba(56,189,248,.35);margin-top:6px">
Spaceport</div>""", unsafe_allow_html=True)
with hc:
    st.markdown("## 🛰️ Global Imagery Browse Services (GIBS)")
    st.caption("NASA's full-resolution satellite imagery — 1,000+ layers from MODIS, VIIRS, SMAP, OMI & more · Updated within 3–5 hours of satellite overpass")
with hr:
    st.markdown("""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.3);
      border-radius:20px;padding:4px 12px;font-size:12px;color:#38bdf8;font-weight:500">
      🛰️ Near Real-Time</span></div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🛰️ GIBS Controls")

    # Date picker
    st.markdown("#### 📅 Image Date")
    img_date = st.date_input(
        "Select date",
        value=date.today() - timedelta(days=2),   # GIBS ~3 day lag
        min_value=date(2000, 1, 1),
        max_value=date.today(),
        help="Most layers have a 3–5 hour processing lag. Use 2+ days ago for reliable imagery."
    )
    img_date_str = str(img_date)

    st.markdown("---")

    # Category filter
    st.markdown("#### 🗂️ Layer Category")
    selected_cat = st.selectbox("Category", list(LAYERS.keys()), index=0)

    # Layer picker within category
    cat_layers = LAYERS[selected_cat]
    layer_labels = [l["label"] for l in cat_layers]
    sel_layer_idx = st.selectbox(
        "Layer", range(len(cat_layers)),
        format_func=lambda i: cat_layers[i]["label"],
        index=0
    )
    sel_layer = cat_layers[sel_layer_idx]

    st.markdown("---")

    # Region presets
    st.markdown("#### 🌐 Region")
    REGIONS = {
        "🌍 Global":          "-180,-90,180,90",
        "🌎 Americas":        "-170,-60,-30,75",
        "🌍 Europe & Africa": "-25,-40,60,75",
        "🌏 Asia & Pacific":  "60,-50,180,75",
        "🇺🇸 CONUS":          "-130,24,-65,50",
        "🧊 Arctic":          "-180,55,180,90",
        "🧊 Antarctic":       "-180,-90,180,-55",
        "🌊 Pacific Ocean":   "140,-60,-100,60",
        "🌊 Indian Ocean":    "30,-50,110,30",
    }
    sel_region_label = st.selectbox("Preset region", list(REGIONS.keys()), index=0)
    sel_bbox = REGIONS[sel_region_label]

    # Custom bbox toggle
    use_custom = st.checkbox("✏️ Custom bounding box", False)
    if use_custom:
        bb = sel_bbox.split(",")
        c1, c2 = st.columns(2)
        lon_min = float(c1.number_input("Lon min", value=float(bb[0]), min_value=-180.0, max_value=180.0))
        lat_min = float(c2.number_input("Lat min", value=float(bb[1]), min_value=-90.0, max_value=90.0))
        lon_max = float(c1.number_input("Lon max", value=float(bb[2]), min_value=-180.0, max_value=180.0))
        lat_max = float(c2.number_input("Lat max", value=float(bb[3]), min_value=-90.0, max_value=90.0))
        sel_bbox = f"{lon_min},{lat_min},{lon_max},{lat_max}"

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#475569;line-height:2">
    <b style="color:#64748b">🛰️ About GIBS</b><br>
    🌍 1,000+ imagery layers<br>
    ⚡ Updated within 3–5 hrs<br>
    📡 MODIS · VIIRS · SMAP<br>
    🗓️ Archive from 1997<br>
    🌐 WMS / WMTS / TWMS
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data: [NASA GIBS](https://earthdata.nasa.gov/gibs)")

# ══════════════════════════════════════════════════════════════════════════════
# 📊  Stat strip
# ══════════════════════════════════════════════════════════════════════════════
sc1,sc2,sc3,sc4,sc5 = st.columns(5)
stat_card(sc1,"🛰️","Total Layers",     "1,000+", ACCENT,     "across all sensors")
stat_card(sc2,"⚡","Update Latency",   "3–5 hrs", "#f59e0b",  "near real-time")
stat_card(sc3,"📅","Archive Start",    "1997",    "#22c55e",  "historical archive")
stat_card(sc4,"🌐","Projections",      "4",       "#818cf8",  "EPSG 4326·3857·3413·3031")
stat_card(sc5,"📏","Best Resolution",  "250m",    "#f472b6",  "MODIS & VIIRS")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_viewer, tab_compare, tab_browse, tab_animate, tab_layers = st.tabs([
    "🗺️  Image Viewer",
    "🔀  Compare Layers",
    "📚  Layer Browser",
    "🎞️  Time Animation",
    "📋  Layer Catalogue",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  TAB 1 — IMAGE VIEWER
# ══════════════════════════════════════════════════════════════════════════════
with tab_viewer:
    st.markdown("### 🗺️ Satellite Image Viewer")
    st.caption(f"Displaying: **{sel_layer['label']}** · Date: **{img_date_str}** · Region: **{sel_region_label}**")

    # Build WMS URL
    img_url = wms_image_url(sel_layer["id"], img_date_str, bbox=sel_bbox, width=1280, height=640)

    # Main image
    st.markdown(f"""
    <div style="border-radius:14px;overflow:hidden;border:1px solid #1a2340;
    box-shadow:0 0 40px rgba(56,189,248,.08);margin-bottom:12px;background:#04060f;
    position:relative">
      <img src="{img_url}"
           style="width:100%;display:block;min-height:300px;object-fit:cover"
           loading="lazy"
           onerror="this.parentElement.innerHTML='<div style=\'padding:60px;text-align:center;color:#475569;font-family:Space Mono,monospace;font-size:12px\'>⚠️ Image not available for this date/layer combination.<br>Try a different date or layer.</div>'" />
    </div>""", unsafe_allow_html=True)

    # Links row
    lc1, lc2, lc3 = st.columns(3)
    lc1.markdown(
        f'<a href="{img_url}" target="_blank" style="display:block;background:#0f1626;'
        f'border:1px solid #38bdf844;border-radius:8px;padding:9px 12px;text-align:center;'
        f'font-size:11px;color:{ACCENT};text-decoration:none;font-family:Space Mono,monospace">'
        f'🔎 Open full resolution ↗</a>', unsafe_allow_html=True)

    worldview_url = (
        f"https://worldview.earthdata.nasa.gov/?t={img_date_str}"
        f"&l={sel_layer['id']}"
    )
    lc2.markdown(
        f'<a href="{worldview_url}" target="_blank" style="display:block;background:#0f1626;'
        f'border:1px solid #22c55e44;border-radius:8px;padding:9px 12px;text-align:center;'
        f'font-size:11px;color:#22c55e;text-decoration:none;font-family:Space Mono,monospace">'
        f'🌍 Open in Worldview ↗</a>', unsafe_allow_html=True)

    lc3.markdown(
        f'<a href="{GIBS_WMS}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0" '
        f'target="_blank" style="display:block;background:#0f1626;'
        f'border:1px solid #818cf844;border-radius:8px;padding:9px 12px;text-align:center;'
        f'font-size:11px;color:#818cf8;text-decoration:none;font-family:Space Mono,monospace">'
        f'📋 WMS Capabilities ↗</a>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Layer metadata panel
    section_hdr("ℹ️","LAYER DETAILS","")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {ACCENT};
    border-radius:10px;padding:12px 14px">
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Layer ID</div>
      <div style="font-family:'Space Mono',monospace;font-size:11px;color:{ACCENT};
      margin-top:4px;word-break:break-all">{sel_layer['id']}</div>
    </div>""", unsafe_allow_html=True)
    mc2.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #f59e0b;
    border-radius:10px;padding:12px 14px">
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Resolution</div>
      <div style="font-family:'Space Mono',monospace;font-size:18px;color:#f59e0b;
      font-weight:700;margin-top:4px">{sel_layer['res']}</div>
    </div>""", unsafe_allow_html=True)
    mc3.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #22c55e;
    border-radius:10px;padding:12px 14px">
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Archive Start</div>
      <div style="font-family:'Space Mono',monospace;font-size:18px;color:#22c55e;
      font-weight:700;margin-top:4px">{sel_layer['start'][:7]}</div>
    </div>""", unsafe_allow_html=True)
    mc4.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #818cf8;
    border-radius:10px;padding:12px 14px">
      <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Bounding Box</div>
      <div style="font-family:'Space Mono',monospace;font-size:11px;color:#818cf8;
      margin-top:4px">{sel_bbox}</div>
    </div>""", unsafe_allow_html=True)

    # WMS URL box
    st.markdown("<br>", unsafe_allow_html=True)
    section_hdr("🔗","WMS REQUEST URL","Copy this URL to use in any WMS-compatible GIS application")
    st.code(img_url, language=None)

# ══════════════════════════════════════════════════════════════════════════════
# 🔀  TAB 2 — LAYER COMPARE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("### 🔀 Side-by-Side Layer Comparison")
    st.caption("Compare two different layers or the same layer on different dates")

    cmp_mode = st.radio("🔀 Compare mode", ["🗺️ Two layers, same date", "📅 Same layer, two dates"], horizontal=True)
    st.markdown("<br>", unsafe_allow_html=True)

    all_layer_list = [(lyr["id"], lyr["label"]) for cat_layers in LAYERS.values() for lyr in cat_layers]
    all_layer_ids   = [l[0] for l in all_layer_list]
    all_layer_labels = [l[1] for l in all_layer_list]

    if cmp_mode == "🗺️ Two layers, same date":
        cc1, cc2 = st.columns(2)
        with cc1:
            idx_a = st.selectbox("🛰️ Left layer", range(len(all_layer_list)),
                                 format_func=lambda i: all_layer_labels[i], index=0, key="cmp_a")
        with cc2:
            idx_b = st.selectbox("🛰️ Right layer", range(len(all_layer_list)),
                                 format_func=lambda i: all_layer_labels[i], index=1, key="cmp_b")
        layer_a_id = all_layer_ids[idx_a]
        layer_b_id = all_layer_ids[idx_b]
        date_a = date_b = img_date_str

    else:  # same layer, two dates
        cc1, cc2 = st.columns(2)
        with cc1:
            cmp_layer_idx = st.selectbox("🛰️ Layer", range(len(all_layer_list)),
                                          format_func=lambda i: all_layer_labels[i], index=0, key="cmp_layer")
            date_a = str(st.date_input("📅 Date A", value=img_date - timedelta(days=30),
                                        min_value=date(2000,1,1), max_value=date.today(), key="da"))
        with cc2:
            st.markdown("<div style='height:76px'></div>", unsafe_allow_html=True)
            date_b = str(st.date_input("📅 Date B", value=img_date,
                                        min_value=date(2000,1,1), max_value=date.today(), key="db"))
        layer_a_id = layer_b_id = all_layer_ids[cmp_layer_idx]

    url_a = wms_image_url(layer_a_id, date_a, bbox=sel_bbox, width=700, height=400)
    url_b = wms_image_url(layer_b_id, date_b, bbox=sel_bbox, width=700, height=400)

    img_col_a, img_col_b = st.columns(2)
    with img_col_a:
        label_a = all_layer_labels[idx_a] if cmp_mode == "🗺️ Two layers, same date" else f"Date A: {date_a}"
        st.markdown(f"<div style='font-size:11px;color:{ACCENT};font-family:Space Mono,monospace;"
                    f"margin-bottom:6px;text-align:center'>⬅️ {label_a}</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="border-radius:12px;overflow:hidden;border:2px solid {ACCENT}44">
          <img src="{url_a}" style="width:100%;display:block"
               loading="lazy"
               onerror="this.parentElement.innerHTML='<div style=\'padding:40px;text-align:center;color:#475569;font-size:11px\'>⚠️ Not available</div>'" />
        </div>""", unsafe_allow_html=True)
        st.markdown(f'<a href="{url_a}" target="_blank" style="font-size:10px;color:{ACCENT};'
                    f'font-family:Space Mono,monospace">🔎 Full res ↗</a>', unsafe_allow_html=True)

    with img_col_b:
        label_b = all_layer_labels[idx_b] if cmp_mode == "🗺️ Two layers, same date" else f"Date B: {date_b}"
        st.markdown(f"<div style='font-size:11px;color:#f59e0b;font-family:Space Mono,monospace;"
                    f"margin-bottom:6px;text-align:center'>➡️ {label_b}</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="border-radius:12px;overflow:hidden;border:2px solid #f59e0b44">
          <img src="{url_b}" style="width:100%;display:block"
               loading="lazy"
               onerror="this.parentElement.innerHTML='<div style=\'padding:40px;text-align:center;color:#475569;font-size:11px\'>⚠️ Not available</div>'" />
        </div>""", unsafe_allow_html=True)
        st.markdown(f'<a href="{url_b}" target="_blank" style="font-size:10px;color:#f59e0b;'
                    f'font-family:Space Mono,monospace">🔎 Full res ↗</a>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📚  TAB 3 — LAYER BROWSER (grid of thumbnails per category)
# ══════════════════════════════════════════════════════════════════════════════
with tab_browse:
    st.markdown("### 📚 Layer Browser")
    st.caption(f"Thumbnail previews for all {sum(len(v) for v in LAYERS.values())} curated layers · Date: {img_date_str}")

    for cat_name, cat_layers in LAYERS.items():
        section_hdr(cat_name.split()[0], cat_name[2:].upper(), f"{len(cat_layers)} layers")
        cols = st.columns(min(len(cat_layers), 4))
        for i, lyr in enumerate(cat_layers):
            col = cols[i % 4]
            is_sel = lyr["id"] == sel_layer["id"]
            layer_card(col, lyr, img_date_str, selected=is_sel)
        st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎞️  TAB 4 — TIME ANIMATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_animate:
    st.markdown("### 🎞️ Time Series Animation")
    st.caption("Generate a sequence of daily satellite images to visualise change over time")

    ac1, ac2, ac3 = st.columns(3)
    anim_layer_idx = ac1.selectbox("🛰️ Layer", range(len(all_layer_list)),
                                    format_func=lambda i: all_layer_labels[i],
                                    index=0, key="anim_layer")
    anim_layer = all_layer_list[anim_layer_idx]

    anim_start = ac2.date_input("📅 Start date",
                                 value=img_date - timedelta(days=13),
                                 min_value=date(2000,1,1), max_value=date.today(),
                                 key="anim_start")
    anim_end   = ac3.date_input("📅 End date",
                                 value=img_date,
                                 min_value=date(2000,1,1), max_value=date.today(),
                                 key="anim_end")

    anim_step = st.radio("📆 Step interval", ["Daily","Every 3 days","Weekly","Every 2 weeks"],
                          horizontal=True)
    step_map = {"Daily":1,"Every 3 days":3,"Weekly":7,"Every 2 weeks":14}
    step_days = step_map[anim_step]

    # Generate date list
    anim_dates = []
    cur = anim_start
    while cur <= anim_end:
        anim_dates.append(cur)
        cur += timedelta(days=step_days)
    anim_dates = anim_dates[:30]   # cap at 30 frames

    if len(anim_dates) < 2:
        st.warning("⚠️ Please select a wider date range to generate an animation.")
    else:
        st.markdown(f"<div style='font-size:11px;color:#64748b;margin-bottom:12px'>"
                    f"🎞️ {len(anim_dates)} frames · Layer: {anim_layer[1]}</div>",
                    unsafe_allow_html=True)

        # Build list of URLs
        frame_urls = [wms_image_url(anim_layer[0], str(d), bbox=sel_bbox, width=800, height=400)
                      for d in anim_dates]
        frame_labels = [str(d) for d in anim_dates]

        # Frame slider
        frame_idx = st.slider("🎞️ Frame", 0, len(frame_urls)-1, 0)
        st.caption(f"📅 Selected: **{frame_labels[frame_idx]}**")

        st.markdown(f"""
        <div style="border-radius:14px;overflow:hidden;border:1px solid #1a2340;
        box-shadow:0 0 30px rgba(56,189,248,.06)">
          <img src="{frame_urls[frame_idx]}"
               style="width:100%;display:block;min-height:200px;object-fit:cover"
               loading="lazy"
               onerror="this.parentElement.innerHTML='<div style=\'padding:40px;text-align:center;color:#475569;font-size:12px\'>⚠️ Image not available for {frame_labels[frame_idx]}</div>'" />
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center;font-family:'Space Mono',monospace;font-size:13px;
        color:{ACCENT};margin-top:8px;font-weight:700">📅 {frame_labels[frame_idx]}</div>""",
                    unsafe_allow_html=True)

        # Filmstrip
        section_hdr("🎞️","FILMSTRIP","All frames — scroll right")
        film_cols = st.columns(min(len(frame_urls), 8))
        for fi, (fc, fu, fl) in enumerate(zip(film_cols, frame_urls[:8], frame_labels[:8])):
            border = f"2px solid {ACCENT}" if fi == frame_idx else "1px solid #1a2340"
            fc.markdown(f"""
            <div style="border:{border};border-radius:6px;overflow:hidden;margin-bottom:4px">
              <img src="{fu}" style="width:100%;height:60px;object-fit:cover;display:block"
                   loading="lazy" onerror="this.style.display='none'" />
            </div>
            <div style="font-size:8px;color:#475569;text-align:center;
            font-family:Space Mono,monospace">{fl[5:]}</div>""", unsafe_allow_html=True)

        if len(frame_urls) > 8:
            st.caption(f"ℹ️ Showing first 8 of {len(frame_urls)} frames in filmstrip. Use the slider above to browse all.")

        # Download links
        section_hdr("⬇️","DOWNLOAD FRAME URLs","Right-click any link to save the image")
        dl_rows = [{"📅 Date": fl, "🔗 WMS URL": fu}
                   for fl, fu in zip(frame_labels, frame_urls)]
        st.dataframe(pd.DataFrame(dl_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📋  TAB 5 — LAYER CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════
with tab_layers:
    st.markdown("### 📋 Full Layer Catalogue")
    st.caption("All curated GIBS layers available in this dashboard")

    # Build catalogue table
    cat_rows = []
    for cat_name, cat_layers in LAYERS.items():
        for lyr in cat_layers:
            cat_rows.append({
                "🗂️ Category":  cat_name,
                "📡 Layer ID":  lyr["id"],
                "📝 Label":     lyr["label"],
                "📏 Resolution": lyr["res"],
                "📅 Start Date": lyr["start"],
                "🔗 WMS URL":   wms_image_url(lyr["id"], img_date_str),
            })

    cat_df = pd.DataFrame(cat_rows)

    # Search
    search = st.text_input("🔍 Search layers", placeholder="e.g. VIIRS, temperature, aerosol…")
    if search:
        mask = cat_df.apply(lambda row: search.lower() in row.astype(str).str.lower().str.cat(), axis=1)
        cat_df = cat_df[mask]
        st.caption(f"🔍 {len(cat_df)} results for '{search}'")

    # Filter by category
    cat_filter = st.multiselect("🗂️ Filter by category", list(LAYERS.keys()), default=list(LAYERS.keys()))
    cat_df = cat_df[cat_df["🗂️ Category"].isin(cat_filter)]

    st.dataframe(cat_df.drop(columns=["🔗 WMS URL"]), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download catalogue CSV",
                       cat_df.to_csv(index=False), "gibs_layers.csv", "text/csv")

    # WMS/WMTS endpoint reference
    section_hdr("🔗","SERVICE ENDPOINTS","Use these in any GIS application (QGIS, ArcGIS, etc.)")
    endpoints = [
        ("WMS EPSG:4326",  "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi",  ACCENT),
        ("WMS EPSG:3857",  "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi",  "#f59e0b"),
        ("WMTS EPSG:4326", "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi","#22c55e"),
        ("WMTS EPSG:3857", "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi","#818cf8"),
    ]
    ep_cols = st.columns(2)
    for i, (name, url, color) in enumerate(endpoints):
        ep_cols[i % 2].markdown(f"""
        <div style="background:#0f1626;border:1px solid #1a2340;border-left:4px solid {color};
        border-radius:8px;padding:12px 14px;margin-bottom:8px">
          <div style="font-size:11px;font-weight:600;color:{color};
          font-family:'Space Mono',monospace">{name}</div>
          <div style="font-size:10px;color:#475569;margin-top:4px;
          word-break:break-all;font-family:'Space Mono',monospace">{url}</div>
        </div>""", unsafe_allow_html=True)

    # Quick sample request
    section_hdr("💡","SAMPLE WMS REQUEST","")
    sample = (
        f"https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?"
        f"SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
        f"&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor"
        f"&STYLES=&CRS=EPSG:4326&BBOX=-180,-90,180,90"
        f"&WIDTH=1024&HEIGHT=512&FORMAT=image/jpeg"
        f"&TIME={img_date_str}"
    )
    st.code(sample, language=None)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#64748b;line-height:1.9">
    <b style="color:#94a3b8">🛰️ About NASA GIBS</b> — The Global Imagery Browse Services (GIBS)
    system provides visualizations of NASA Earth Science observations through standardized
    web services (WMS, WMTS, TWMS). It delivers 1,000+ global, full-resolution satellite
    imagery layers in near real-time (3–5 hours after observation) and historical archive
    dating back to 1997. Data comes from instruments including MODIS (Terra & Aqua),
    VIIRS (Suomi NPP, NOAA-20, NOAA-21), SMAP, OMI, GPM/IMERG, GHRSST and more.
    &nbsp;·&nbsp;
    <a href="https://earthdata.nasa.gov/gibs" target="_blank"
    style="color:{ACCENT};text-decoration:none">🌐 earthdata.nasa.gov/gibs ↗</a>
    &nbsp;·&nbsp;
    <a href="https://worldview.earthdata.nasa.gov" target="_blank"
    style="color:#22c55e;text-decoration:none">🌍 NASA Worldview ↗</a>
  </div>
</div>""", unsafe_allow_html=True)
