import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
import random
import math
import urllib.parse

st.set_page_config(
    page_title="Spaceport | OuterSpace",
    page_icon="🌠",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;600;900&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"]           { background-color: #050709 !important; color: #e8eaf0 !important; }
[data-testid="stSidebar"]            { background:#07090e !important; border-right:1px solid #141926; }
[data-testid="stSidebar"] *          { color:#e8eaf0 !important; }
[data-testid="stTabs"] button        { color:#3d4460 !important; font-family:'Space Mono',monospace !important; font-size:11px !important; letter-spacing:.5px; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#e8b84b !important; border-bottom-color:#e8b84b !important; }
[data-testid="metric-container"]     { background:#0b0e17; border:1px solid #141926; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#3d4460 !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
h1,h2,h3                             { color:#e8eaf0 !important; }
div[data-baseweb="select"] > div     { background:#0b0e17 !important; border-color:#141926 !important; }
.stTextInput input, .stNumberInput input { background:#0b0e17 !important; border:1px solid #141926 !important; color:#e8eaf0 !important; }
.stMultiSelect div[data-baseweb]     { background:#0b0e17 !important; }
/* Shimmer animation for loading cards */
@keyframes shimmer { 0%{opacity:.4} 50%{opacity:.9} 100%{opacity:.4} }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑  Constants
# ══════════════════════════════════════════════════════════════════════════════
API_KEY  = "QQThI6OsOqvcIQXhuHlSGpYamccaAcWIz9PyyhPj"
BASE_URL = "https://images-api.nasa.gov"

# Design tokens — golden editorial palette
GOLD   = "#e8b84b"
SILVER = "#94a3c0"
BLUE   = "#4b8ee8"
TEAL   = "#4be8d4"
RED    = "#e84b6a"
PURPLE = "#9b4be8"
GREEN  = "#4be876"
MUTED  = "#3d4460"

# ── Curated topic collections ─────────────────────────────────────────────────
COLLECTIONS = {
    "🌌 Deep Space":        {"q": "galaxy nebula deep space universe",    "color": PURPLE},
    "🚀 Space Launches":    {"q": "rocket launch NASA astronaut",         "color": BLUE},
    "🌍 Earth from Space":  {"q": "Earth orbit ISS blue marble",          "color": TEAL},
    "🌕 Moon Missions":     {"q": "Apollo lunar moon landing",            "color": SILVER},
    "🔭 Telescopes":        {"q": "Hubble Webb telescope observation",    "color": GOLD},
    "🔴 Mars Exploration":  {"q": "Mars rover surface exploration",       "color": RED},
    "☀️ The Sun":           {"q": "solar flare corona sun",               "color": "#f97316"},
    "🧑‍🚀 Astronauts":       {"q": "astronaut spacewalk EVA spacesuit",    "color": GREEN},
    "✨ Nebulae":           {"q": "nebula stellar nursery star formation", "color": PURPLE},
    "🪐 Planets":           {"q": "planet Saturn Jupiter outer solar system","color": GOLD},
    "🌠 Historic Missions": {"q": "Apollo Gemini Mercury historic NASA",  "color": SILVER},
    "🛸 Space Stations":    {"q": "ISS Mir space station orbital",        "color": TEAL},
}

NASA_CENTERS = [
    "All Centers","JSC","MSFC","KSC","JPL","GSFC","ARC","LaRC","GRC","HQ","SSC","AFRC","WFF"
]

# ══════════════════════════════════════════════════════════════════════════════
# 📡  API helpers
# ══════════════════════════════════════════════════════════════════════════════
def _get(endpoint: str, params: dict = None, retries: int = 3) -> dict:
    params = params or {}
    last   = None
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            last = Exception(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            last = e
        time.sleep(1.2 ** attempt)
    raise last

@st.cache_data(ttl=1800)
def search(query: str, media_type: str = "", center: str = "",
           year_start: str = "", year_end: str = "",
           page: int = 1, page_size: int = 40) -> dict:
    """Full search with all filter options."""
    params = {"q": query, "page": page, "page_size": page_size}
    if media_type and media_type != "all":
        params["media_type"] = media_type
    if center and center != "All Centers":
        params["center"] = center
    if year_start:
        params["year_start"] = year_start
    if year_end:
        params["year_end"]   = year_end
    data = _get("/search", params)
    col  = data.get("collection", {})
    items= col.get("items", [])
    total= col.get("metadata", {}).get("total_hits", len(items))
    return {"items": _parse_items(items), "total": total}

@st.cache_data(ttl=3600)
def get_asset(nasa_id: str) -> list[str]:
    """Get all asset URLs for a specific NASA ID."""
    data = _get(f"/asset/{nasa_id}")
    return [item.get("href","") for item in data.get("collection",{}).get("items",[])]

@st.cache_data(ttl=7200)
def get_metadata(nasa_id: str) -> dict:
    """Get full metadata for an item."""
    data = _get(f"/metadata/{nasa_id}")
    return data.get("collection",{}).get("items",[{}])[0] if data else {}

@st.cache_data(ttl=3600)
def get_captions(nasa_id: str) -> str:
    """Get captions URL for a video."""
    data = _get(f"/captions/{nasa_id}")
    items = data.get("collection",{}).get("items",[])
    if items:
        return items[0].get("href","")
    return ""

def _parse_items(raw_items: list) -> list[dict]:
    """Normalise raw API items into clean dicts."""
    results = []
    for item in raw_items:
        links    = item.get("links", [])
        data_arr = item.get("data", [{}])
        meta     = data_arr[0] if data_arr else {}
        href_arr = item.get("href","")

        # Best preview image
        thumb = next((l["href"] for l in links if l.get("rel") == "preview"), "")
        if not thumb:
            thumb = next((l.get("href","") for l in links), "")

        media_type = meta.get("media_type", "image")

        results.append({
            "nasa_id":     meta.get("nasa_id",""),
            "title":       meta.get("title","Untitled"),
            "description": meta.get("description",""),
            "date":        (meta.get("date_created","") or "")[:10],
            "center":      meta.get("center",""),
            "photographer":meta.get("photographer",""),
            "keywords":    meta.get("keywords",[]),
            "media_type":  media_type,
            "thumb":       thumb,
            "detail_url":  f"https://images.nasa.gov/details/{meta.get('nasa_id','')}",
            "href":        href_arr,
        })
    return results

# ══════════════════════════════════════════════════════════════════════════════
# 🎨  UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0b0e17;border:1px solid #141926;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:22px">{emoji}</div>
      <div style="font-family:'Orbitron',monospace;font-size:20px;color:{color};
      font-weight:700;margin:6px 0;word-break:break-all">{value}</div>
      <div style="color:{MUTED};font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#252b3d;font-size:10px;margin-top:3px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def section_hdr(emoji, title, cap=""):
    st.markdown(
        f"<div style='font-family:Syne,sans-serif;font-size:11px;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:2px;color:{MUTED};margin:28px 0 6px'>"
        f"{emoji} {title}</div>", unsafe_allow_html=True)
    if cap:
        st.caption(cap)

MEDIA_BADGES = {
    "image": (f"background:{BLUE}22;border:1px solid {BLUE}44;color:{BLUE}", "📷 Image"),
    "video": (f"background:{RED}22;border:1px solid {RED}44;color:{RED}",    "🎬 Video"),
    "audio": (f"background:{GREEN}22;border:1px solid {GREEN}44;color:{GREEN}","🎵 Audio"),
}

def media_card(item: dict, compact: bool = False, show_meta: bool = True):
    """Render a single media card."""
    thumb  = item.get("thumb","")
    title  = item.get("title","Untitled")
    date   = item.get("date","")
    center = item.get("center","")
    mtype  = item.get("media_type","image")
    url    = item.get("detail_url","")
    h      = "140px" if compact else "195px"
    badge_style, badge_label = MEDIA_BADGES.get(mtype, MEDIA_BADGES["image"])

    # Overlay for video
    overlay = ""
    if mtype == "video":
        overlay = (f'<div style="position:absolute;inset:0;display:flex;align-items:center;'
                   f'justify-content:center;background:rgba(5,7,9,.4)">'
                   f'<div style="width:44px;height:44px;border-radius:50%;'
                   f'background:rgba(232,72,106,.85);display:flex;align-items:center;'
                   f'justify-content:center;font-size:18px">▶</div></div>')
    elif mtype == "audio":
        overlay = (f'<div style="position:absolute;inset:0;display:flex;align-items:center;'
                   f'justify-content:center;background:rgba(5,7,9,.6)">'
                   f'<div style="font-size:32px">🎵</div></div>')

    img_block = f"""
    <a href="{url}" target="_blank" style="text-decoration:none;display:block">
      <div style="position:relative;background:#07090e">
        {'<img src="' + thumb + '" style="width:100%;height:' + h + ';object-fit:cover;display:block" loading="lazy" onerror="this.style.display=\'none\'" />' if thumb else '<div style="height:' + h + ';background:#07090e;display:flex;align-items:center;justify-content:center;color:#252b3d;font-size:11px">No preview</div>'}
        {overlay}
        <div style="position:absolute;top:7px;right:7px;border-radius:6px;padding:2px 7px;
        font-size:9px;font-family:Space Mono,monospace;{badge_style}">{badge_label}</div>
      </div>
    </a>"""

    meta_block = "" if (not show_meta or compact) else f"""
    <div style="padding:9px 11px">
      <div style="font-family:'Syne',sans-serif;font-size:12px;font-weight:700;
      color:#e8eaf0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
      margin-bottom:3px" title="{title}">{title}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
        <span style="font-size:9px;color:{GOLD};font-family:'Space Mono',monospace">📅 {date}</span>
        {f'<span style="font-size:9px;color:{MUTED};font-family:Space Mono,monospace">🏛️ {center}</span>' if center else ''}
      </div>
    </div>"""

    st.markdown(f"""
    <div style="background:#0b0e17;border:1px solid #141926;border-radius:12px;
    overflow:hidden;margin-bottom:10px">
      {img_block}
      {meta_block}
    </div>""", unsafe_allow_html=True)

def render_grid(items: list, cols: int = 4, compact: bool = False, show_meta: bool = True):
    if not items:
        st.markdown(f"""
        <div style="background:#0b0e17;border:1px solid #141926;border-radius:12px;
        padding:50px;text-align:center;color:{MUTED};font-family:'Space Mono',monospace">
          🌠 No results found.<br>
          <span style="font-size:10px;margin-top:6px;display:block">
          Try a different keyword, date range, or media type.</span>
        </div>""", unsafe_allow_html=True)
        return
    rows = [items[i:i+cols] for i in range(0, len(items), cols)]
    for row in rows:
        row_cols = st.columns(cols)
        for col, item in zip(row_cols, row):
            with col:
                media_card(item, compact=compact, show_meta=show_meta)

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  HEADER
# ══════════════════════════════════════════════════════════════════════════════
hl, hc, hr = st.columns([0.06, 0.68, 0.26])
with hl:
    st.markdown(f"""
    <div style="width:52px;height:52px;background:radial-gradient(135deg,#1a1206,#050709);
    border:2px solid {GOLD};border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-family:'Orbitron',monospace;font-size:9px;font-weight:700;
    color:{GOLD};letter-spacing:1px;box-shadow:0 0 24px rgba(232,184,75,.35);margin-top:6px">
Spaceport</div>""", unsafe_allow_html=True)
with hc:
    st.markdown("## 🌠 Spaceport | Image & Video Library")
    st.caption("140,000+ images · videos · audio files · spanning every NASA mission · aeronautics · Earth science · astrophysics · human spaceflight")
with hr:
    st.markdown(f"""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(232,184,75,.1);border:1px solid rgba(232,184,75,.3);
      border-radius:20px;padding:4px 14px;font-size:12px;color:{GOLD};font-weight:600;
      font-family:'Space Mono',monospace">🌌 images.nasa.gov</span>
    </div>""", unsafe_allow_html=True)
st.markdown(f"<hr style='border-color:#141926;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"### 🌠 Library Controls")

    # Main search
    st.markdown(f"#### 🔍 Search")
    search_query = st.text_input("Keywords", value="",
                                  placeholder="e.g. Apollo Moon Saturn nebula")

    # Media type
    media_type = st.radio("🎭 Media type",
                           ["all", "image", "video", "audio"],
                           format_func=lambda x: {"all":"🌌 All media","image":"📷 Images only",
                                                   "video":"🎬 Videos only","audio":"🎵 Audio only"}[x],
                           index=0, horizontal=False)

    st.markdown("---")
    st.markdown("#### 🗓️ Date Range")
    dc1, dc2 = st.columns(2)
    year_start = dc1.text_input("From", value="", placeholder="1960")
    year_end   = dc2.text_input("To",   value="", placeholder="2024")

    st.markdown("---")
    st.markdown("#### 🏛️ NASA Center")
    center_sel = st.selectbox("Center", NASA_CENTERS, index=0)

    st.markdown("---")
    st.markdown("#### 🖼️ Display")
    cols_per_row = st.slider("Columns", 2, 6, 4)
    compact_mode = st.toggle("⚡ Compact view", False)
    show_meta    = st.toggle("💬 Show metadata", True)
    page_num     = st.number_input("📄 Page", min_value=1, max_value=100, value=1, step=1)

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:11px;color:#252b3d;line-height:2">
    <b style="color:{MUTED}">🌠 About</b><br>
    🏛️ NASA Official Archive<br>
    📸 140,000+ media assets<br>
    🎬 Images · Video · Audio<br>
    🏢 11 NASA Centers<br>
    📅 Archive from 1958<br>
    🔓 Public domain
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data: [images.nasa.gov](https://images.nasa.gov)")

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Main search fetch
# ══════════════════════════════════════════════════════════════════════════════
active_query = search_query.strip() if search_query.strip() else "space NASA"
results      = {}
fetch_error  = None

with st.spinner("🌠 Loading from NASA Image & Video Library…"):
    try:
        results = search(
            query      = active_query,
            media_type = media_type if media_type != "all" else "",
            center     = center_sel,
            year_start = year_start.strip(),
            year_end   = year_end.strip(),
            page       = int(page_num),
            page_size  = 40,
        )
    except Exception as e:
        fetch_error = str(e)

if fetch_error:
    is_dns = "resolve" in fetch_error.lower() or "getaddrinfo" in fetch_error.lower()
    st.error("🌠 Could not reach the NASA Images API", icon="🚨")
    if is_dns:
        st.warning(
            "🔌 **Network error** — check your internet connection.\n\n"
            "Make sure `images-api.nasa.gov` is reachable in your browser:\n"
            "https://images-api.nasa.gov/search?q=apollo"
        )
    else:
        st.warning(f"⚠️ {fetch_error[:300]}")
    with st.expander("🔍 Details"):
        st.code(fetch_error, language=None)
    if st.button("🔄 Retry", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

items = results.get("items", [])
total = results.get("total", 0)

# ══════════════════════════════════════════════════════════════════════════════
# 📊  Stat strip
# ══════════════════════════════════════════════════════════════════════════════
images_n = sum(1 for i in items if i.get("media_type")=="image")
videos_n = sum(1 for i in items if i.get("media_type")=="video")
audio_n  = sum(1 for i in items if i.get("media_type")=="audio")

sc1,sc2,sc3,sc4,sc5 = st.columns(5)
stat_card(sc1,"🌠","Total Hits",    f"{total:,}"    if total else str(len(items)), GOLD,   f"query: {active_query[:20]}")
stat_card(sc2,"📷","Images",         f"{images_n}",  BLUE,   f"page {page_num}")
stat_card(sc3,"🎬","Videos",         f"{videos_n}",  RED,    "playable")
stat_card(sc4,"🎵","Audio",          f"{audio_n}",   GREEN,  "recordings")
stat_card(sc5,"📚","Archive Size",   "140,000+",     PURPLE, "media assets")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_gallery, tab_featured, tab_collections, tab_video, tab_audio, tab_explore = st.tabs([
    "🖼️  Gallery",
    "⭐  Featured",
    "🗂️  Collections",
    "🎬  Video Player",
    "🎵  Audio",
    "🔭  Explore & Stats",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🖼️  TAB 1 — GALLERY
# ══════════════════════════════════════════════════════════════════════════════
with tab_gallery:
    st.markdown(f"### 🖼️ Search Results — *{active_query}*")
    st.caption(
        f"📊 {total:,} total results · Showing page {page_num} ({len(items)} items) · "
        f"Media: {media_type} · Center: {center_sel}"
    )

    if items:
        # Quick filter chips
        types_found = sorted({i["media_type"] for i in items})
        if len(types_found) > 1:
            sel_types = st.multiselect(
                "🎭 Filter by type", types_found, default=types_found, key="gal_type")
            filtered = [i for i in items if i["media_type"] in sel_types]
        else:
            filtered = items

        # Sort
        sort_by = st.selectbox("🔃 Sort by",
                                ["📅 Newest first","📅 Oldest first","🔤 Title A→Z"],
                                label_visibility="collapsed")
        if sort_by == "📅 Newest first":
            filtered = sorted(filtered, key=lambda x: x["date"], reverse=True)
        elif sort_by == "📅 Oldest first":
            filtered = sorted(filtered, key=lambda x: x["date"])
        elif sort_by == "🔤 Title A→Z":
            filtered = sorted(filtered, key=lambda x: x["title"])

        st.markdown(f"<div style='font-size:11px;color:{MUTED};margin-bottom:10px'>"
                    f"Showing {len(filtered)} items</div>", unsafe_allow_html=True)

        render_grid(filtered, cols_per_row, compact=compact_mode, show_meta=show_meta)

        # Pagination row
        if total > 40:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"📄 Page {page_num} of ~{math.ceil(total/40):,} — change page in the sidebar")
    else:
        st.info("🌠 No results found. Try a different search term.")

# ══════════════════════════════════════════════════════════════════════════════
# ⭐  TAB 2 — FEATURED
# ══════════════════════════════════════════════════════════════════════════════
with tab_featured:
    st.markdown("### ⭐ Featured Media")

    if items:
        if st.button("🎲 Random pick", type="primary"):
            st.session_state.outer_idx = random.randint(0, len(items)-1)
        if "outer_idx" not in st.session_state:
            st.session_state.outer_idx = 0

        idx  = min(st.session_state.outer_idx, len(items)-1)
        feat = items[idx]

        # Nav
        n1, n2, n3 = st.columns([1,1,4])
        if n1.button("⬅️ Prev", use_container_width=True):
            st.session_state.outer_idx = max(0, idx-1); st.rerun()
        if n2.button("➡️ Next", use_container_width=True):
            st.session_state.outer_idx = min(len(items)-1, idx+1); st.rerun()
        n3.caption(f"Item {idx+1} of {len(items)}")

        st.markdown("<br>", unsafe_allow_html=True)

        mtype  = feat.get("media_type","image")
        thumb  = feat.get("thumb","")
        title  = feat.get("title","")
        date   = feat.get("date","")
        center = feat.get("center","")
        photo  = feat.get("photographer","")
        desc   = feat.get("description","")
        kw     = feat.get("keywords",[])
        url    = feat.get("detail_url","")
        nasa_id= feat.get("nasa_id","")

        fc1, fc2 = st.columns([3, 2])

        with fc1:
            if mtype == "image" and thumb:
                st.markdown(f"""
                <div style="border-radius:16px;overflow:hidden;
                border:2px solid {GOLD};box-shadow:0 0 50px rgba(232,184,75,.12)">
                  <img src="{thumb}" style="width:100%;display:block;max-height:65vh;
                  object-fit:contain;background:#050709" loading="lazy"/>
                </div>""", unsafe_allow_html=True)
            elif mtype == "video":
                # Try to get actual mp4 via asset endpoint
                with st.spinner("Loading video assets…"):
                    try:
                        assets = get_asset(nasa_id) if nasa_id else []
                        mp4s = [a for a in assets if a.endswith(".mp4")]
                        if mp4s:
                            st.video(mp4s[-1])   # use highest quality (last usually biggest)
                        elif thumb:
                            st.markdown(f"""
                            <div style="border-radius:16px;overflow:hidden;border:2px solid {RED};
                            position:relative">
                              <img src="{thumb}" style="width:100%;display:block;
                              max-height:50vh;object-fit:cover;filter:brightness(.7)"/>
                              <div style="position:absolute;inset:0;display:flex;align-items:center;
                              justify-content:center">
                                <div style="width:72px;height:72px;border-radius:50%;
                                background:rgba(232,72,106,.9);display:flex;align-items:center;
                                justify-content:center;font-size:30px">▶</div>
                              </div>
                            </div>""", unsafe_allow_html=True)
                    except Exception:
                        if thumb:
                            st.image(thumb)
                        st.info("Video preview not available — open in NASA Library.")
            elif mtype == "audio":
                with st.spinner("Loading audio…"):
                    try:
                        assets = get_asset(nasa_id) if nasa_id else []
                        mp3s = [a for a in assets if ".mp3" in a or ".wav" in a or ".m4a" in a]
                        if mp3s:
                            st.audio(mp3s[0])
                        else:
                            st.info("Audio stream not directly available.")
                    except Exception:
                        st.info("Audio preview not available.")

            col_link1, col_link2 = st.columns(2)
            col_link1.markdown(
                f'<a href="{url}" target="_blank" style="display:block;background:#0b0e17;'
                f'border:1px solid {GOLD}44;border-radius:8px;padding:9px;text-align:center;'
                f'font-size:11px;color:{GOLD};text-decoration:none;font-family:Space Mono,monospace">'
                f'🔎 Open in NASA Library ↗</a>', unsafe_allow_html=True)
            if nasa_id:
                col_link2.markdown(
                    f'<a href="https://images-api.nasa.gov/asset/{nasa_id}" target="_blank" '
                    f'style="display:block;background:#0b0e17;border:1px solid {BLUE}44;'
                    f'border-radius:8px;padding:9px;text-align:center;font-size:11px;'
                    f'color:{BLUE};text-decoration:none;font-family:Space Mono,monospace">'
                    f'⬇️ Asset Downloads ↗</a>', unsafe_allow_html=True)

        with fc2:
            badge_style, badge_label = MEDIA_BADGES.get(mtype, MEDIA_BADGES["image"])
            st.markdown(f"""
            <div style="background:#0b0e17;border:1px solid #141926;
            border-top:4px solid {GOLD};border-radius:14px;padding:20px 18px;
            margin-bottom:14px">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;
              margin-bottom:12px">
                <div style="font-family:'Syne',sans-serif;font-size:15px;font-weight:800;
                color:#e8eaf0;line-height:1.3;flex:1">{title}</div>
                <span style="border-radius:6px;padding:2px 8px;font-size:9px;
                font-family:Space Mono,monospace;margin-left:8px;{badge_style}">{badge_label}</span>
              </div>
              <div style="font-size:12px;font-family:'Space Mono',monospace;
              color:#94a3c0;line-height:2.4">
                <span style="color:{MUTED}">📅 Date:</span>
                <span style="color:{GOLD}"> {date}</span><br>
                {f'<span style="color:{MUTED}">🏛️ Center:</span> <span style="color:#e8eaf0">{center}</span><br>' if center else ''}
                {f'<span style="color:{MUTED}">📸 Photographer:</span> <span style="color:#94a3c0">{photo}</span><br>' if photo else ''}
                <span style="color:{MUTED}">🆔 ID:</span>
                <span style="color:#3d4460;font-size:10px"> {nasa_id[:35]}{'…' if len(nasa_id)>35 else ''}</span>
              </div>
            </div>""", unsafe_allow_html=True)

            if desc:
                st.markdown(f"""
                <div style="background:#07090e;border:1px solid #141926;
                border-left:3px solid {GOLD};border-radius:8px;padding:14px 16px;
                font-size:11px;color:#475569;line-height:1.8;
                max-height:260px;overflow-y:auto;margin-bottom:12px">
                  📖 {desc[:800]}{'…' if len(desc)>800 else ''}
                </div>""", unsafe_allow_html=True)

            if kw:
                tags_html = "".join(
                    f'<span style="background:{GOLD}15;border:1px solid {GOLD}30;'
                    f'border-radius:20px;padding:2px 9px;font-size:9px;color:{GOLD};'
                    f'margin:2px;display:inline-block">{k}</span>'
                    for k in kw[:12]
                )
                st.markdown(f'<div style="line-height:2.2">{tags_html}</div>',
                            unsafe_allow_html=True)
    else:
        st.info("No items loaded. Try searching above.")

# ══════════════════════════════════════════════════════════════════════════════
# 🗂️  TAB 3 — COLLECTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_collections:
    st.markdown("### 🗂️ Curated Space Collections")
    st.caption("Pre-built topic collections — click any card to browse")

    col_rows = [list(COLLECTIONS.items())[i:i+3] for i in range(0, len(COLLECTIONS), 3)]
    for row in col_rows:
        cc = st.columns(3)
        for col, (cname, cinfo) in zip(cc, row):
            color = cinfo["color"]
            col.markdown(f"""
            <div style="background:#0b0e17;border:1px solid #141926;
            border-top:3px solid {color};border-radius:12px;
            padding:16px 18px;margin-bottom:8px;min-height:80px">
              <div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
              color:{color};margin-bottom:4px">{cname}</div>
              <div style="font-size:10px;color:{MUTED};font-family:'Space Mono',monospace;
              line-height:1.5">🔍 "{cinfo['q'][:40]}"</div>
            </div>""", unsafe_allow_html=True)
            if col.button("📂 Browse", key=f"col_{cname[:8]}", use_container_width=True):
                with st.spinner(f"Loading {cname}…"):
                    try:
                        col_results = search(cinfo["q"], page_size=12)
                        col_items   = col_results.get("items",[])
                        total_col   = col_results.get("total",0)
                        if col_items:
                            st.markdown(f"**{cname}** — {total_col:,} total results (showing 12)")
                            render_grid(col_items[:12], 4, compact=True)
                        else:
                            st.info("No results found for this collection.")
                    except Exception as e:
                        st.warning(f"⚠️ {e}")

# ══════════════════════════════════════════════════════════════════════════════
# 🎬  TAB 4 — VIDEO PLAYER
# ══════════════════════════════════════════════════════════════════════════════
with tab_video:
    st.markdown("### 🎬 NASA Video Player")
    st.caption("Search for NASA videos and play them directly")

    vc1, vc2 = st.columns([3,1])
    vid_query = vc1.text_input("🎬 Search videos", value="",
                                placeholder="e.g. Apollo launch, ISS spacewalk, Saturn rocket")
    load_vids = vc2.button("🔍 Search", type="primary", use_container_width=True)

    if "vid_results" not in st.session_state:
        st.session_state.vid_results = []
    if "vid_playing" not in st.session_state:
        st.session_state.vid_playing = None

    if load_vids and vid_query.strip():
        with st.spinner("🎬 Searching NASA videos…"):
            try:
                vr = search(vid_query.strip(), media_type="video", page_size=20)
                st.session_state.vid_results = vr.get("items",[])
                st.session_state.vid_playing = None
            except Exception as e:
                st.warning(f"⚠️ {e}")
                st.session_state.vid_results = []

    vid_items = st.session_state.vid_results

    # Load some default videos on first load
    if not vid_items and not load_vids:
        with st.spinner("Loading featured NASA videos…"):
            try:
                vr = search("NASA space launch historic", media_type="video", page_size=12)
                vid_items = vr.get("items",[])
            except Exception:
                vid_items = []

    if vid_items:
        st.markdown(f"<div style='font-size:11px;color:{MUTED};margin-bottom:12px'>"
                    f"🎬 {len(vid_items)} videos</div>", unsafe_allow_html=True)

        # Video selector grid
        vc_cols = st.columns(4)
        for vi, vitem in enumerate(vid_items[:8]):
            col = vc_cols[vi % 4]
            thumb = vitem.get("thumb","")
            title = vitem.get("title","")[:35]
            date  = vitem.get("date","")
            nid   = vitem.get("nasa_id","")
            is_playing = st.session_state.vid_playing == nid
            border = f"2px solid {GOLD}" if is_playing else "1px solid #141926"
            col.markdown(f"""
            <div style="background:#0b0e17;border:{border};border-radius:10px;
            overflow:hidden;margin-bottom:8px">
              <div style="position:relative">
                {'<img src="' + thumb + '" style="width:100%;height:100px;object-fit:cover;display:block;filter:' + ('none' if is_playing else 'brightness(.75)') + '" loading="lazy"/>' if thumb else '<div style="height:100px;background:#07090e"></div>'}
                <div style="position:absolute;inset:0;display:flex;align-items:center;
                justify-content:center">
                  <div style="width:36px;height:36px;border-radius:50%;
                  background:{'rgba(232,184,75,.9)' if is_playing else 'rgba(232,72,106,.8)'};
                  display:flex;align-items:center;justify-content:center;font-size:14px">▶</div>
                </div>
              </div>
              <div style="padding:6px 8px;font-size:9px;color:#94a3c0;
              font-family:Space Mono,monospace;white-space:nowrap;overflow:hidden;
              text-overflow:ellipsis" title="{title}">{title}</div>
            </div>""", unsafe_allow_html=True)
            if col.button("▶ Play", key=f"vplay_{nid}", use_container_width=True):
                st.session_state.vid_playing = nid
                st.rerun()

        # Video player
        playing_id = st.session_state.vid_playing
        if playing_id:
            section_hdr("▶️","NOW PLAYING","")
            playing_item = next((v for v in vid_items if v.get("nasa_id")==playing_id), None)
            if playing_item:
                with st.spinner("Loading video…"):
                    try:
                        assets = get_asset(playing_id)
                        mp4s = sorted([a for a in assets if a.endswith(".mp4")])
                        if mp4s:
                            st.video(mp4s[-1])   # highest quality
                        else:
                            st.info("No MP4 available — open in NASA Library.")
                            st.markdown(
                                f'<a href="{playing_item.get("detail_url","")}" target="_blank" '
                                f'style="color:{GOLD}">🔗 Open on images.nasa.gov ↗</a>',
                                unsafe_allow_html=True)
                    except Exception as e:
                        st.warning(f"Could not load video: {e}")

                # Metadata below player
                st.markdown(f"""
                <div style="background:#0b0e17;border:1px solid #141926;border-top:3px solid {GOLD};
                border-radius:10px;padding:14px 16px;margin-top:10px">
                  <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:700;
                  color:#e8eaf0;margin-bottom:8px">{playing_item.get('title','')}</div>
                  <div style="font-size:11px;color:{MUTED};font-family:'Space Mono',monospace;
                  margin-bottom:8px">📅 {playing_item.get('date','')} &nbsp;·&nbsp;
                  🏛️ {playing_item.get('center','NASA')}</div>
                  <div style="font-size:11px;color:#475569;line-height:1.7">
                  {playing_item.get('description','')[:400]}{'…' if len(playing_item.get('description',''))>400 else ''}
                  </div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("🎬 Search for a video above to get started.")

# ══════════════════════════════════════════════════════════════════════════════
# 🎵  TAB 5 — AUDIO
# ══════════════════════════════════════════════════════════════════════════════
with tab_audio:
    st.markdown("### 🎵 NASA Audio Archive")
    st.caption("Historic mission audio, rocket sounds, space ambient recordings")

    ac1, ac2 = st.columns([3,1])
    aud_query = ac1.text_input("🎵 Search audio", value="",
                                placeholder="e.g. Apollo mission control, Saturn V rocket")
    load_aud  = ac2.button("🔍 Search", type="primary", use_container_width=True, key="aud_srch")

    if "aud_results" not in st.session_state:
        st.session_state.aud_results = []

    # Default audio on first load
    if not st.session_state.aud_results and not load_aud:
        with st.spinner("Loading NASA audio archive…"):
            try:
                ar = search("Apollo mission control astronaut", media_type="audio", page_size=16)
                st.session_state.aud_results = ar.get("items",[])
            except Exception:
                st.session_state.aud_results = []

    if load_aud and aud_query.strip():
        with st.spinner("🎵 Searching audio…"):
            try:
                ar = search(aud_query.strip(), media_type="audio", page_size=16)
                st.session_state.aud_results = ar.get("items",[])
            except Exception as e:
                st.warning(f"⚠️ {e}")

    aud_items = st.session_state.aud_results

    if aud_items:
        st.markdown(f"<div style='font-size:11px;color:{MUTED};margin-bottom:12px'>"
                    f"🎵 {len(aud_items)} audio files</div>", unsafe_allow_html=True)

        for ai, aitem in enumerate(aud_items):
            nid   = aitem.get("nasa_id","")
            title = aitem.get("title","Untitled")
            date  = aitem.get("date","")
            center= aitem.get("center","")
            desc  = aitem.get("description","")[:200]

            with st.expander(f"🎵 {title[:70]}{'…' if len(title)>70 else ''}  —  {date}"):
                st.markdown(f"""
                <div style="font-size:11px;color:{MUTED};font-family:'Space Mono',monospace;
                margin-bottom:8px">
                  🏛️ {center} &nbsp;·&nbsp; 🆔 {nid}
                </div>
                {f'<div style="font-size:11px;color:#475569;margin-bottom:10px">{desc}…</div>' if desc else ''}
                """, unsafe_allow_html=True)
                with st.spinner("Loading audio…"):
                    try:
                        assets = get_asset(nid) if nid else []
                        audio_files = [a for a in assets
                                       if any(a.lower().endswith(ext)
                                              for ext in [".mp3",".wav",".m4a",".ogg",".aac"])]
                        if audio_files:
                            st.audio(audio_files[0])
                            st.markdown(
                                f'<a href="{aitem.get("detail_url","")}" target="_blank" '
                                f'style="font-size:10px;color:{GOLD};font-family:Space Mono,monospace">'
                                f'🔎 Full details on NASA Library ↗</a>',
                                unsafe_allow_html=True)
                        else:
                            st.info("Audio file not directly streamable.")
                            st.markdown(
                                f'<a href="{aitem.get("detail_url","")}" target="_blank" '
                                f'style="font-size:10px;color:{GOLD}">🔎 Open on NASA Library ↗</a>',
                                unsafe_allow_html=True)
                    except Exception as e:
                        st.warning(f"Could not load audio: {e}")
    else:
        st.info("🎵 No audio files loaded yet. Try searching above.")

# ══════════════════════════════════════════════════════════════════════════════
# 🔭  TAB 6 — EXPLORE & STATS
# ══════════════════════════════════════════════════════════════════════════════
with tab_explore:
    st.markdown("### 🔭 Explore & Insights")

    if items:
        # Media type breakdown
        section_hdr("📊","MEDIA TYPE BREAKDOWN","")
        type_counts = {}
        for i in items:
            t = i.get("media_type","unknown")
            type_counts[t] = type_counts.get(t,0) + 1

        tc1, tc2 = st.columns(2)
        with tc1:
            type_colors = {"image":BLUE,"video":RED,"audio":GREEN,"unknown":MUTED}
            fig_types = go.Figure(go.Pie(
                labels=list(type_counts.keys()),
                values=list(type_counts.values()),
                hole=0.55,
                marker=dict(
                    colors=[type_colors.get(k,MUTED) for k in type_counts],
                    line=dict(color="#050709",width=2)
                ),
                textinfo="percent+label",
                textfont=dict(size=11,family="Space Mono",color="#e8eaf0"),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
            ))
            fig_types.update_layout(
                paper_bgcolor="#050709", height=280,
                margin=dict(l=10,r=10,t=10,b=10),
                font=dict(family="Space Mono",color="#94a3c0"),
                showlegend=False,
                hoverlabel=dict(bgcolor="#0b0e17",bordercolor="#141926",
                                font=dict(color="#e8eaf0",size=12,family="Space Mono")),
                annotations=[dict(text=f"<b>{len(items)}</b><br>items",
                                  x=0.5,y=0.5,showarrow=False,
                                  font=dict(size=13,color="#e8eaf0",family="Space Mono"))]
            )
            st.plotly_chart(fig_types, use_container_width=True)

        with tc2:
            # NASA Center breakdown
            center_counts = {}
            for i in items:
                c = i.get("center","Unknown") or "Unknown"
                center_counts[c] = center_counts.get(c,0)+1
            top_centers = sorted(center_counts.items(), key=lambda x: x[1], reverse=True)[:8]

            fig_centers = go.Figure(go.Bar(
                x=[c[1] for c in top_centers],
                y=[c[0] for c in top_centers],
                orientation="h",
                marker=dict(
                    color=[c[1] for c in top_centers],
                    colorscale=[[0,"#141926"],[0.5,GOLD],[1,"#fff4cc"]],
                    showscale=False,
                ),
                hovertemplate="<b>%{y}</b><br>Items: %{x}<extra></extra>",
            ))
            fig_centers.update_layout(
                paper_bgcolor="#050709", plot_bgcolor="#0b0e17",
                height=280, margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=True,gridcolor="#141926",color=MUTED,
                           tickfont=dict(family="Space Mono",size=9)),
                yaxis=dict(showgrid=False,color="#94a3c0",
                           tickfont=dict(family="Space Mono",size=9),autorange="reversed"),
                hoverlabel=dict(bgcolor="#0b0e17",bordercolor="#141926",
                                font=dict(color="#e8eaf0",size=12,family="Space Mono")),
            )
            st.plotly_chart(fig_centers, use_container_width=True)

        # Timeline: items by year
        section_hdr("📅","ITEMS BY YEAR","")
        year_counts = {}
        for i in items:
            y = i.get("date","")[:4]
            if y and y.isdigit():
                year_counts[y] = year_counts.get(y,0)+1
        if year_counts:
            ys = sorted(year_counts.keys())
            fig_yr = go.Figure(go.Bar(
                x=ys, y=[year_counts[y] for y in ys],
                marker=dict(
                    color=[year_counts[y] for y in ys],
                    colorscale=[[0,"#141926"],[0.5,GOLD],[1,"#fff4cc"]],
                ),
                hovertemplate="<b>%{x}</b><br>Items: %{y}<extra></extra>",
            ))
            fig_yr.update_layout(
                paper_bgcolor="#050709", plot_bgcolor="#0b0e17",
                height=220, margin=dict(l=10,r=10,t=10,b=40),
                xaxis=dict(showgrid=False,color=MUTED,tickfont=dict(family="Space Mono",size=9)),
                yaxis=dict(showgrid=True,gridcolor="#141926",color=MUTED,
                           tickfont=dict(family="Space Mono",size=9)),
                hoverlabel=dict(bgcolor="#0b0e17",bordercolor="#141926",
                                font=dict(color="#e8eaf0",size=12,family="Space Mono")),
            )
            st.plotly_chart(fig_yr, use_container_width=True)

        # Top keywords wordcloud (text badges)
        all_kw = {}
        for i in items:
            for k in (i.get("keywords",[]) or []):
                k = k.strip().lower()
                if k and len(k) > 2:
                    all_kw[k] = all_kw.get(k,0)+1
        top_kw = sorted(all_kw.items(), key=lambda x:x[1], reverse=True)[:30]
        if top_kw:
            section_hdr("🔤","TOP KEYWORDS","")
            import random as rnd2
            max_ct = top_kw[0][1] if top_kw else 1
            kw_html = ""
            keyword_colors = [GOLD, BLUE, TEAL, RED, PURPLE, GREEN, SILVER]
            for ki, (kw, ct) in enumerate(top_kw):
                size = 9 + int((ct/max_ct)*8)
                clr  = keyword_colors[ki % len(keyword_colors)]
                kw_html += (f'<span style="background:{clr}15;border:1px solid {clr}33;'
                            f'border-radius:20px;padding:3px 10px;font-size:{size}px;'
                            f'color:{clr};margin:3px;display:inline-block;'
                            f'font-family:Space Mono,monospace">'
                            f'{kw} <sup style="font-size:8px;color:{clr}88">{ct}</sup></span>')
            st.markdown(f'<div style="line-height:2.2;margin-top:8px">{kw_html}</div>',
                        unsafe_allow_html=True)

        # Full data table
        section_hdr("📋","DATA TABLE","")
        tbl = [{
            "🖼️ Type":       i.get("media_type","—"),
            "📝 Title":      i.get("title","")[:60],
            "📅 Date":       i.get("date",""),
            "🏛️ Center":     i.get("center",""),
            "📸 Photographer":i.get("photographer",""),
            "🆔 NASA ID":    i.get("nasa_id",""),
        } for i in items]
        df = pd.DataFrame(tbl)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download CSV", df.to_csv(index=False),
                           "nasa_library.csv","text/csv")
    else:
        st.info("Search for something to see stats and insights here.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:#07090e;border:1px solid #141926;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:{MUTED};line-height:1.9">
    <b style="color:#3d4460">🌠 NASA Image & Video Library</b> — Official NASA media archive
    with 140,000+ images, videos, and audio files covering every NASA mission since 1958.
    Content spans aeronautics, astrophysics, Earth science, and human spaceflight from
    11 NASA centers. All content is in the public domain unless otherwise noted.
    &nbsp;·&nbsp;
    <a href="https://images.nasa.gov" target="_blank"
    style="color:{GOLD};text-decoration:none">images.nasa.gov ↗</a>
    &nbsp;·&nbsp;
    <a href="https://images-api.nasa.gov" target="_blank"
    style="color:{BLUE};text-decoration:none">API docs ↗</a>
  </div>
</div>""", unsafe_allow_html=True)
