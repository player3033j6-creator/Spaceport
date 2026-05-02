import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import random
import time
import math

st.set_page_config(
    page_title="Spaceport | JWST",
    page_icon="🔭",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');
html, body, [class*="css"]          { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"]           { background:#060912 !important; border-right:1px solid #1a1f3a; }
[data-testid="stSidebar"] *         { color:#e2e8f0 !important; }
[data-testid="stTabs"] button       { color:#475569 !important; font-family:'Space Mono',monospace !important; font-size:11px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#818cf8 !important; border-bottom-color:#818cf8 !important; }
[data-testid="metric-container"]    { background:#0a0e1f; border:1px solid #1a1f3a; border-radius:14px; padding:16px 20px !important; }
h1,h2,h3                            { color:#e2e8f0 !important; }
div[data-baseweb="select"] > div    { background:#0a0e1f !important; border-color:#1a1f3a !important; }
.stTextInput input                  { background:#0a0e1f !important; border:1px solid #1a1f3a !important; color:#e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑  Constants — NASA Images API (free, no key, very reliable)
# ══════════════════════════════════════════════════════════════════════════════
NASA_IMAGES_API = "https://images-api.nasa.gov"
ACCENT = "#818cf8"; COL2 = "#a78bfa"; COL3 = "#38bdf8"; COL4 = "#f472b6"; COL5 = "#34d399"

# ── Curated JWST search terms that return real images ────────────────────────
TARGETS = {
    "🌌 Cosmic Cliffs — Carina Nebula":   "Webb Carina Nebula",
    "🪐 Southern Ring Nebula":            "Webb Southern Ring Nebula",
    "🌀 Stephan's Quintet":               "Webb Stephan's Quintet",
    "🔭 SMACS Deep Field":                "Webb SMACS deep field",
    "💫 Pillars of Creation":             "Webb Pillars of Creation",
    "🌠 Tarantula Nebula":                "Webb Tarantula Nebula",
    "🪐 Jupiter":                         "Webb Jupiter",
    "🌌 Cartwheel Galaxy":               "Webb Cartwheel Galaxy",
    "🔬 Phantom Galaxy M74":             "Webb Phantom Galaxy",
    "✨ Wolf-Rayet Star":                 "Webb Wolf-Rayet",
    "🌀 Whirlpool Galaxy M51":           "Webb Whirlpool Galaxy",
    "🌌 Galaxy Cluster":                 "Webb galaxy cluster",
    "💎 Cosmic Hourglass":               "Webb protostar",
    "🪐 Neptune Rings":                  "Webb Neptune rings",
    "🌟 Star Formation":                 "Webb star formation",
}

ICOLORS = {"NIRCam":"#818cf8","MIRI":"#f472b6","NIRSpec":"#38bdf8","NIRISS":"#34d399","FGS":"#a78bfa"}

# ══════════════════════════════════════════════════════════════════════════════
# 📡  NASA Images API helpers  — always works, no auth needed
# ══════════════════════════════════════════════════════════════════════════════
def safe_str(val, fallback="—"):
    if val is None: return fallback
    try:
        if isinstance(val, float) and math.isnan(val): return fallback
    except Exception: pass
    s = str(val).strip()
    return s if s and s.lower() not in ("nan","none","null","") else fallback

def _get(url, params=None, retries=3):
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            last = Exception(f"HTTP {r.status_code}: {r.text[:150]}")
        except Exception as e:
            last = e
        time.sleep(1.2 ** attempt)
    raise last

@st.cache_data(ttl=1800)
def search_images(query: str, media_type: str = "image", page: int = 1, page_size: int = 40) -> list[dict]:
    """Search NASA Images API and return normalised item list."""
    data = _get(f"{NASA_IMAGES_API}/search", {
        "q": query,
        "media_type": media_type,
        "page": page,
        "page_size": page_size,
    })
    items = data.get("collection", {}).get("items", [])
    results = []
    for item in items:
        links = item.get("links", [])
        data_arr = item.get("data", [{}])
        meta = data_arr[0] if data_arr else {}

        # Get best image URL from links
        thumb = next((l["href"] for l in links if l.get("rel") == "preview"), "")
        full  = next((l["href"] for l in links if l.get("rel") == "captions"), "")
        if not thumb:
            thumb = next((l.get("href","") for l in links), "")

        results.append({
            "title":       meta.get("title", "Untitled"),
            "description": meta.get("description", ""),
            "date":        meta.get("date_created", "")[:10],
            "center":      meta.get("center", ""),
            "keywords":    meta.get("keywords", []),
            "nasa_id":     meta.get("nasa_id", ""),
            "thumb":       thumb,
            "full_url":    f"https://images.nasa.gov/details/{meta.get('nasa_id','')}",
        })
    return results

@st.cache_data(ttl=3600)
def fetch_target(search_term: str, limit: int = 30) -> list[dict]:
    """Fetch images for a specific JWST target."""
    return search_images(search_term)[:limit]

@st.cache_data(ttl=1800)
def fetch_latest_jwst(page: int = 1) -> list[dict]:
    """Latest JWST images from NASA."""
    return search_images("James Webb Space Telescope", page=page)

# ══════════════════════════════════════════════════════════════════════════════
# 🎨  UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:20px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:18px;color:{color};
      font-weight:700;margin:4px 0;word-break:break-word">{value}</div>
      <div style="color:#334155;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#1e293b;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def section_hdr(emoji, title, cap=""):
    st.markdown(
        f"<div style='font-size:12px;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:1.5px;color:#334155;margin:28px 0 6px'>{emoji} {title}</div>",
        unsafe_allow_html=True)
    if cap: st.caption(cap)

def img_card(item: dict, compact: bool = False):
    """Render a NASA Images item card."""
    thumb = item.get("thumb", "")
    title = item.get("title", "Untitled")
    date  = item.get("date", "")
    desc  = item.get("description", "")
    url   = item.get("full_url", "")
    nasa_id = item.get("nasa_id", "")
    h = "140px" if compact else "200px"

    img_block = ""
    if thumb:
        img_block = f"""<a href="{url}" target="_blank" style="display:block">
          <img src="{thumb}" style="width:100%;height:{h};object-fit:cover;display:block"
               loading="lazy"
               onerror="this.parentElement.style.display='none'" />
        </a>"""
    else:
        img_block = f'<div style="height:{h};background:#04060f;display:flex;align-items:center;justify-content:center;color:#1e293b;font-size:10px">🔭 No preview</div>'

    meta = "" if compact else f"""
    <div style="padding:9px 11px">
      <div style="font-size:11px;font-weight:600;color:#e2e8f0;white-space:nowrap;
      overflow:hidden;text-overflow:ellipsis" title="{title}">{title}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px">
        <span style="font-size:9px;color:{ACCENT};font-family:'Space Mono',monospace">📅 {date}</span>
        {f'<span style="font-size:9px;color:#334155;font-family:Space Mono,monospace">{nasa_id[:20]}</span>' if nasa_id else ''}
      </div>
    </div>"""

    st.markdown(f"""
    <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-radius:12px;
    overflow:hidden;margin-bottom:10px">
      <div style="position:relative">{img_block}</div>
      {meta}
    </div>""", unsafe_allow_html=True)

def render_grid(items: list[dict], cols: int = 3, compact: bool = False):
    if not items:
        st.markdown("""
        <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-radius:12px;
        padding:40px;text-align:center;color:#334155;font-family:'Space Mono',monospace">
          🔭 No images found.<br>
          <span style="font-size:10px">Try a different search term or target.</span>
        </div>""", unsafe_allow_html=True)
        return
    chunks = [items[i:i+cols] for i in range(0, len(items), cols)]
    for chunk in chunks:
        row_cols = st.columns(cols)
        for col, item in zip(row_cols, chunk):
            with col:
                img_card(item, compact=compact)

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  HEADER
# ══════════════════════════════════════════════════════════════════════════════
hl, hc, hr = st.columns([0.06, 0.70, 0.24])
with hl:
    st.markdown("""
    <div style="width:52px;height:52px;background:radial-gradient(circle,#1e1b4b,#04060f);
    border:2px solid #818cf8;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:9px;font-weight:700;color:#818cf8;letter-spacing:1px;
box-shadow:0 0 24px rgba(129,140,248,.4);margin-top:6px">Spaceport</div>""", unsafe_allow_html=True)
with hc:
    st.markdown("## 🔭 James Webb Space Telescope (JWST)")
    st.caption("Infrared images from humanity's deepest eye · NIRCam · MIRI · NIRSpec · NIRISS · Launched Dec 25 2021 · Data: NASA Images Library")
with hr:
    st.markdown(f"""<div style="margin-top:14px;text-align:right">
    <span style="background:rgba(129,140,248,.1);border:1px solid rgba(129,140,248,.3);
    border-radius:20px;padding:4px 12px;font-size:12px;color:{ACCENT};font-weight:500">
✨ Spaceport</span></div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a1f3a;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔭 JWST Controls")

    view_mode = st.radio("🗂️ View mode", [
        "🌟 Latest JWST Images",
        "⭐ Famous Targets",
        "🔍 Custom Search",
    ], index=0)

    if view_mode == "🌟 Latest JWST Images":
        page_num = st.number_input("📄 Page", min_value=1, max_value=20, value=1, step=1)

    elif view_mode == "⭐ Famous Targets":
        tgt_choice = st.selectbox("🌠 Target", list(TARGETS.keys()), index=0)

    elif view_mode == "🔍 Custom Search":
        custom_q = st.text_input("🔍 Search term", value="", placeholder="e.g. Webb nebula infrared")

    st.markdown("---")
    cols_per_row = st.slider("🗂️ Columns", 2, 5, 3)
    compact_mode = st.toggle("⚡ Compact view", False)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#1e293b;line-height:2">
    <b style="color:#334155">🔭 About JWST</b><br>
    🚀 Launch: Dec 25, 2021<br>
    📍 Sun–Earth L2, 1.5M km<br>
    🪞 6.5 m gold mirror<br>
    🌡️ −233°C instruments<br>
    🌌 Sees back 13.6B years
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data: [NASA Images Library](https://images.nasa.gov) — free, no API key")

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Fetch
# ══════════════════════════════════════════════════════════════════════════════
images      = []
fetch_error = None
fetch_title = ""

with st.spinner("🔭 Loading JWST images from NASA…"):
    try:
        if view_mode == "🌟 Latest JWST Images":
            images      = fetch_latest_jwst(page=int(page_num))
            fetch_title = f"Latest JWST Images — Page {page_num}"

        elif view_mode == "⭐ Famous Targets":
            term        = TARGETS[tgt_choice]
            images      = fetch_target(term)
            fetch_title = tgt_choice

        elif view_mode == "🔍 Custom Search":
            q = custom_q.strip() if custom_q.strip() else "James Webb Space Telescope"
            images      = search_images(q)
            fetch_title = f"Search: {q}"

    except Exception as e:
        fetch_error = str(e)

if fetch_error:
    is_dns = "resolve" in fetch_error.lower() or "getaddrinfo" in fetch_error.lower()
    st.error("🔭 Could not reach the NASA Images API", icon="🚨")
    if is_dns:
        st.warning(
            "🔌 **DNS / Network error** — your machine cannot resolve `images-api.nasa.gov`.\n\n"
            "**Try these steps:**\n"
            "1. Check your internet connection is active\n"
            "2. Try opening https://images-api.nasa.gov/search?q=webb in your browser\n"
            "3. If on a VPN or proxy, try disabling it\n"
            "4. Restart Streamlit and try again"
        )
    else:
        st.warning(f"⚠️ {fetch_error[:200]}")
    with st.expander("🔍 Technical details"):
        st.code(fetch_error, language=None)
    if st.button("🔄 Retry", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 📊  Stat strip
# ══════════════════════════════════════════════════════════════════════════════
sc1,sc2,sc3,sc4,sc5 = st.columns(5)
stat_card(sc1,"🔭","Images Loaded",  f"{len(images):,}",  ACCENT, "this page")
stat_card(sc2,"🪞","Mirror Size",    "6.5 m",             COL2,   "18 gold segments")
stat_card(sc3,"🌡️","Instrument Temp","−233°C",            COL3,   "40 Kelvin")
stat_card(sc4,"🌌","Lookback Time",  "13.6 Gyr",          COL4,   "near the Big Bang")
stat_card(sc5,"📡","Instruments",    "4",                  COL5,   "NIRCam·MIRI·NIRSpec·NIRISS")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_gallery, tab_featured, tab_targets, tab_instruments, tab_about = st.tabs([
    "🌌  Gallery",
    "⭐  Featured",
    "🌠  Famous Targets",
    "📡  Instruments",
    "🚀  About Webb",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🌌  TAB 1 — GALLERY
# ══════════════════════════════════════════════════════════════════════════════
with tab_gallery:
    st.markdown(f"### 🌌 {fetch_title}")
    st.caption(f"📸 {len(images)} images · NASA Images Library · Click any image to open full details")

    if images:
        render_grid(images, cols_per_row, compact=compact_mode)
        if len(images) >= 40:
            st.info("📄 Showing up to 40 results — change the page number in the sidebar for more.")
    else:
        st.info("🔭 No images found. Try a different search or target.")

# ══════════════════════════════════════════════════════════════════════════════
# ⭐  TAB 2 — FEATURED
# ══════════════════════════════════════════════════════════════════════════════
with tab_featured:
    st.markdown("### ⭐ Featured JWST Image")

    if images:
        if st.button("🎲 Random pick", type="primary"):
            st.session_state.jwst_idx = random.randint(0, len(images)-1)
        if "jwst_idx" not in st.session_state:
            st.session_state.jwst_idx = 0
        idx  = min(st.session_state.jwst_idx, len(images)-1)
        feat = images[idx]

        n1, n2, n3 = st.columns([1,1,4])
        if n1.button("⬅️ Prev", use_container_width=True):
            st.session_state.jwst_idx = max(0, idx-1); st.rerun()
        if n2.button("➡️ Next", use_container_width=True):
            st.session_state.jwst_idx = min(len(images)-1, idx+1); st.rerun()
        n3.caption(f"Image {idx+1} of {len(images)}")

        st.markdown("<br>", unsafe_allow_html=True)
        fc1, fc2 = st.columns([3, 2])

        with fc1:
            thumb = feat.get("thumb","")
            url   = feat.get("full_url","")
            if thumb:
                st.markdown(f"""
                <div style="border-radius:16px;overflow:hidden;border:2px solid {ACCENT};
                box-shadow:0 0 60px rgba(129,140,248,.15)">
                  <img src="{thumb}" style="width:100%;display:block;max-height:65vh;
                  object-fit:contain;background:#04060f" loading="lazy"/>
                </div>""", unsafe_allow_html=True)
                st.markdown(f'<a href="{url}" target="_blank" style="font-size:11px;color:{ACCENT};'
                            f'text-decoration:none;font-family:Space Mono,monospace">'
                            f'🔎 Open full details on NASA Images ↗</a>', unsafe_allow_html=True)
            else:
                st.info("No preview available for this image.")

        with fc2:
            title   = feat.get("title","Untitled")
            date    = feat.get("date","")
            desc    = feat.get("description","")
            nasa_id = feat.get("nasa_id","")
            kw      = feat.get("keywords",[])
            center  = feat.get("center","")

            st.markdown(f"""
            <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-top:4px solid {ACCENT};
            border-radius:14px;padding:20px 18px;margin-bottom:14px">
              <div style="font-family:'Orbitron',monospace;font-size:15px;font-weight:700;
              color:{ACCENT};margin-bottom:14px">🔭 {title[:60]}{'…' if len(title)>60 else ''}</div>
              <div style="font-size:12px;font-family:'Space Mono',monospace;
              color:#94a3b8;line-height:2.4">
                <span style="color:#334155">📅 Date:</span>
                <span style="color:#e2e8f0"> {date}</span><br>
                <span style="color:#334155">🆔 NASA ID:</span>
                <span style="color:{ACCENT}"> {nasa_id}</span><br>
                {f'<span style="color:#334155">🏛️ Center:</span> <span style="color:#64748b">{center}</span><br>' if center else ''}
              </div>
            </div>""", unsafe_allow_html=True)

            if desc:
                st.markdown(f"""
                <div style="background:#060912;border:1px solid #1a1f3a;border-left:3px solid {ACCENT};
                border-radius:8px;padding:12px 14px;font-size:11px;color:#475569;
                line-height:1.8;max-height:280px;overflow-y:auto">
                  📖 {desc[:600]}{'…' if len(desc)>600 else ''}
                </div>""", unsafe_allow_html=True)

            if kw:
                tags = "".join(
                    f'<span style="background:{ACCENT}18;border:1px solid {ACCENT}33;'
                    f'border-radius:20px;padding:2px 8px;font-size:9px;color:{ACCENT};'
                    f'margin:2px;display:inline-block">{k}</span>'
                    for k in kw[:10]
                )
                st.markdown(f'<div style="margin-top:10px;line-height:2">{tags}</div>',
                            unsafe_allow_html=True)
    else:
        st.info("No images loaded. Adjust the view mode in the sidebar.")

# ══════════════════════════════════════════════════════════════════════════════
# 🌠  TAB 3 — FAMOUS TARGETS
# ══════════════════════════════════════════════════════════════════════════════
with tab_targets:
    st.markdown("### 🌠 Iconic JWST Targets")
    st.caption("Click any target to load its images directly from the NASA Images Library")

    colors = [ACCENT, COL2, COL3, COL4, COL5]
    for row_start in range(0, len(TARGETS), 3):
        items = list(TARGETS.items())[row_start:row_start+3]
        tc_cols = st.columns(3)
        for col, (tname, tsearch) in zip(tc_cols, items):
            color = colors[row_start % len(colors)]
            col.markdown(f"""
            <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-top:3px solid {color};
            border-radius:12px;padding:14px 16px;margin-bottom:6px">
              <div style="font-family:'Orbitron',monospace;font-size:11px;
              font-weight:700;color:{color}">{tname}</div>
              <div style="font-size:9px;color:#334155;font-family:'Space Mono',monospace;
              margin-top:4px">🔍 "{tsearch}"</div>
            </div>""", unsafe_allow_html=True)
            if col.button("📷 Load", key=f"tgt_{row_start}_{tname[:10]}", use_container_width=True):
                with st.spinner(f"Loading {tname}…"):
                    try:
                        imgs = fetch_target(tsearch)
                        if imgs:
                            st.markdown(f"**{tname}** — {len(imgs)} images")
                            render_grid(imgs[:6], 3, compact=True)
                        else:
                            st.info("No images found for this target yet.")
                    except Exception as e:
                        st.warning(f"⚠️ {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 📡  TAB 4 — INSTRUMENTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_instruments:
    st.markdown("### 📡 JWST Science Instruments")

    INSTR_INFO = [
        ("NIRCam",  "Near Infrared Camera",                          "0.6–5 μm",   ACCENT,
         "Primary wide-field imager. Responsible for most iconic JWST images including the Carina Nebula, "
         "Pillars of Creation, and deep fields. Operates simultaneously in short & long wavelength channels."),
        ("MIRI",    "Mid-Infrared Instrument",                       "5–28 μm",    COL4,
         "Camera and spectrograph for thermal infrared. Sees through dust to reveal star-forming regions, "
         "exoplanet atmospheres, and the warmth of brown dwarfs."),
        ("NIRSpec", "Near Infrared Spectrograph",                    "0.6–5.3 μm", COL3,
         "Can observe 100+ objects simultaneously using micro-shutter arrays. Maps chemical compositions "
         "and redshifts of early galaxies, enabling large-scale surveys of the distant universe."),
        ("NIRISS",  "Near Infrared Imager & Slitless Spectrograph",  "0.8–5 μm",   COL5,
         "Specialised for exoplanet transit spectroscopy and high-contrast imaging. Detects water, "
         "methane, CO₂ in exoplanet atmospheres."),
        ("FGS",     "Fine Guidance Sensor",                          "0.6–5 μm",   COL2,
         "Provides ultra-precise pointing — keeps Webb locked on target. Also serves as a science "
         "instrument capable of time-series photometry of bright stars."),
    ]

    for nm, full, wave, clr, desc in INSTR_INFO:
        ic1, ic2 = st.columns([1, 4])
        ic1.markdown(f"""
        <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-top:4px solid {clr};
        border-radius:12px;padding:18px;text-align:center;margin-bottom:12px">
          <div style="font-family:'Orbitron',monospace;font-size:18px;font-weight:900;color:{clr}">{nm}</div>
          <div style="font-size:9px;color:#334155;margin-top:6px;letter-spacing:1px">{wave}</div>
        </div>""", unsafe_allow_html=True)
        ic2.markdown(f"""
        <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-left:4px solid {clr};
        border-radius:12px;padding:18px 20px;margin-bottom:12px">
          <div style="font-size:13px;font-weight:600;color:#e2e8f0;margin-bottom:6px">{full}</div>
          <div style="font-size:12px;color:#475569;line-height:1.7">{desc}</div>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🚀  TAB 5 — ABOUT WEBB
# ══════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown("### 🚀 About the James Webb Space Telescope")
    col_a, col_b = st.columns(2)

    with col_a:
        section_hdr("📅","MISSION TIMELINE","")
        timeline = [
            ("💡","Concept",        "1996",         "Originally Next Generation Space Telescope"),
            ("🔨","Construction",   "2004–2016",    "Built by Northrop Grumman, NASA, ESA, CSA"),
            ("🚀","Launch",         "Dec 25 2021",  "Ariane 5 rocket, Kourou, French Guiana"),
            ("📡","L2 Arrival",     "Jan 24 2022",  "Sun–Earth L2 point — 1.5M km from Earth"),
            ("🪞","Mirror Align",   "Mar 2022",     "18 segments aligned to nanometre precision"),
            ("🌌","First Images",   "Jul 12 2022",  "5 iconic deep-universe images released worldwide"),
            ("🔭","Science Ops",    "Jul 2022 →",   "Full operations ongoing · 20+ years of fuel"),
        ]
        for em, ev, dt, de in timeline:
            st.markdown(f"""
            <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:8px;
            padding:10px 12px;background:#0a0e1f;border:1px solid #1a1f3a;
            border-left:3px solid {ACCENT};border-radius:8px">
              <div style="font-size:16px;margin-top:2px">{em}</div>
              <div>
                <div style="font-family:'Orbitron',monospace;font-size:11px;font-weight:700;color:#e2e8f0">{ev}</div>
                <div style="font-size:11px;color:{ACCENT};font-family:'Space Mono',monospace">{dt}</div>
                <div style="font-size:10px;color:#334155;margin-top:2px">{de}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    with col_b:
        section_hdr("🔬","TECHNICAL SPECS","")
        specs = [
            ("🪞","Mirror diameter",   "6.5 m — 18 gold beryllium hexagons"),
            ("🌡️","Operating temp",    "−233°C (40 Kelvin)"),
            ("📡","Wavelength range",  "0.6 – 28.3 micrometres"),
            ("📍","Orbit",             "Sun–Earth L2, 1.5M km from Earth"),
            ("⚖️","Total mass",        "6,200 kg"),
            ("🌞","Sunshield",         "21 × 14 m, 5 kapton layers"),
            ("📅","Design lifetime",   "10 yr / fuel for 20+ yr"),
            ("💰","Total cost",        "~$10 billion USD"),
            ("🤝","Partners",          "NASA + ESA + Canadian Space Agency"),
        ]
        for em, lb, vl in specs:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:7px 12px;
            background:#0a0e1f;border:1px solid #1a1f3a;border-radius:7px;margin-bottom:5px">
              <span style="font-size:11px;color:#334155">{em} {lb}</span>
              <span style="font-size:11px;color:{ACCENT};font-weight:600;
              font-family:'Space Mono',monospace;text-align:right;max-width:55%">{vl}</span>
            </div>""", unsafe_allow_html=True)

        section_hdr("🌌","WEBB'S SCIENCE THEMES","")
        for em, th, ds, cl in [
            ("🌅","Early Universe",  "First galaxies after the Big Bang",      ACCENT),
            ("🌀","Galaxy Assembly", "How galaxies form and evolve",            COL2),
            ("⭐","Stellar Life",    "Star birth, death & planet formation",    COL3),
            ("🪐","Other Worlds",   "Exoplanet atmospheres & habitability",     COL4),
        ]:
            st.markdown(f"""
            <div style="background:#0a0e1f;border:1px solid #1a1f3a;border-top:3px solid {cl};
            border-radius:10px;padding:10px 14px;margin-bottom:7px">
              <span style="font-size:12px;font-weight:700;color:{cl}">{em} {th}</span>
              <div style="font-size:10px;color:#334155;margin-top:2px">{ds}</div>
            </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:#060912;border:1px solid #1a1f3a;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#334155;line-height:1.9">
    <b style="color:#475569">🔭 Data</b> — Images served by the
    <a href="https://images.nasa.gov" target="_blank" style="color:{ACCENT};text-decoration:none">
    NASA Images & Video Library</a> — a free, public API with no authentication required.
    Images are official NASA releases. For raw science data (FITS files), visit
    <a href="https://mast.stsci.edu" target="_blank" style="color:{COL2};text-decoration:none">
    STScI MAST ↗</a>.
    &nbsp;·&nbsp;
    <a href="https://www.jwst.nasa.gov" target="_blank" style="color:{COL3};text-decoration:none">
    jwst.nasa.gov ↗</a>
  </div>
</div>""", unsafe_allow_html=True)
