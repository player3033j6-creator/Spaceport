import streamlit as st
import requests
from datetime import date, timedelta, datetime
import pandas as pd
import plotly.graph_objects as go
import random as rnd
import time

st.set_page_config(
    page_title="Spaceport | APOD",
    page_icon="🔭",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;600;900&display=swap');

html, body, [class*="css"]          { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"]           { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] *         { color:#e2e8f0 !important; }
[data-testid="stTabs"] button       { color:#64748b !important; font-family:'Space Mono',monospace !important; font-size:12px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#a78bfa !important; border-bottom-color:#a78bfa !important; }
[data-testid="metric-container"]    { background:#0f1626; border:1px solid #1a2340; border-radius:14px; padding:16px 20px !important; }
[data-testid="metric-container"] label { color:#64748b !important; font-size:11px !important; text-transform:uppercase; letter-spacing:1px; }
h1,h2,h3                            { color:#e2e8f0 !important; }
.stTextInput input                  { background:#0f1626 !important; border:1px solid #1a2340 !important; color:#e2e8f0 !important; }
.stSelectbox div[data-baseweb]      { background:#0f1626 !important; border:1px solid #1a2340 !important; }
/* Starfield shimmer */
@keyframes twinkle { 0%,100%{opacity:.2} 50%{opacity:.9} }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔑  Constants
# ══════════════════════════════════════════════════════════════════════════════
API_KEY   = "jbXRe21bgt9N6e0zReYeS7KvLg51BFZCenOafBol"
APOD_BASE = "https://api.nasa.gov/planetary/apod"
APOD_FIRST = date(1995, 6, 16)   # 📅 APOD launched June 16 1995

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Fetching helpers
# ══════════════════════════════════════════════════════════════════════════════
def _get(params: dict, retries: int = 3) -> dict | list:
    params["api_key"] = API_KEY
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(APOD_BASE, params=params, timeout=18)
            if r.status_code == 200:
                return r.json()
            last = Exception(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            last = e
        time.sleep(1.5 ** attempt)
    raise last

@st.cache_data(ttl=3600)
def fetch_apod(apod_date: str) -> dict:
    """🌌 Single APOD entry."""
    return _get({"date": apod_date, "thumbs": True})

@st.cache_data(ttl=3600)
def fetch_apod_range(start: str, end: str) -> list[dict]:
    """📅 Range of APOD entries."""
    return _get({"start_date": start, "end_date": end, "thumbs": True})

@st.cache_data(ttl=86400)
def fetch_apod_random(count: int = 12) -> list[dict]:
    """🎲 Random APOD entries."""
    return _get({"count": count, "thumbs": True})

# ══════════════════════════════════════════════════════════════════════════════
# 🎨  UI helpers
# ══════════════════════════════════════════════════════════════════════════════
def stat_card(col, emoji, label, value, color, sub=""):
    col.markdown(f"""
    <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
    border-radius:12px;padding:16px 18px;text-align:center">
      <div style="font-size:22px">{emoji}</div>
      <div style="font-family:'Space Mono',monospace;font-size:22px;color:{color};
      font-weight:700;margin:4px 0;word-break:break-all">{value}</div>
      <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
      {f'<div style="color:#475569;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

def section_hdr(emoji, title, cap=""):
    st.markdown(
        f"<div style='font-size:12px;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:1.5px;color:#64748b;margin:28px 0 4px'>{emoji} {title}</div>",
        unsafe_allow_html=True)
    if cap:
        st.caption(cap)

import re
import streamlit.components.v1 as components

def _get_embed_url(url: str) -> str:
    """
    Convert any video URL to an embeddable URL.
    - YouTube watch/short/embed  →  youtube-nocookie embed
    - Vimeo                      →  player.vimeo.com
    - Already an embed URL       →  return as-is
    """
    # Already an embed URL (NASA APOD often returns these directly)
    if "youtube.com/embed/" in url or "youtube-nocookie.com/embed/" in url:
        # Ensure it's nocookie
        vid = re.search(r"/embed/([\w-]+)", url)
        if vid:
            return f"https://www.youtube-nocookie.com/embed/{vid.group(1)}?rel=0"
        return url

    # youtube.com/watch?v=ID  or  youtu.be/ID
    yt = re.search(r"(?:youtube\.com/watch\?(?:.*&)?v=|youtu\.be/)([\w-]{11})", url)
    if yt:
        return f"https://www.youtube-nocookie.com/embed/{yt.group(1)}?rel=0"

    # Vimeo
    vi = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
    if vi:
        return f"https://player.vimeo.com/video/{vi.group(1)}"

    # Return original (best effort)
    return url


def apod_card(item: dict, show_explanation: bool = True, compact: bool = False):
    """🖼️ Render a single APOD card — images + all video types."""
    media  = item.get("media_type", "image")
    title  = item.get("title", "Untitled")
    expl   = item.get("explanation", "")
    d      = item.get("date", "")
    copy   = item.get("copyright", "")
    url    = item.get("url", "")
    hdurl  = item.get("hdurl", "")
    thumb  = item.get("thumbnail_url", "")
    height = 320 if compact else 500

    # ── Media block ───────────────────────────────────────────────────────────
    if media == "image":
        display_url = hdurl or url
        st.markdown(f"""
        <div style="border-radius:14px;overflow:hidden;border:1px solid #1a2340;
        box-shadow:0 0 40px rgba(167,139,250,.08);margin-bottom:12px;background:#04060f">
          <img src="{display_url}"
               style="width:100%;display:block;max-height:{height}px;
               object-fit:contain;background:#04060f" loading="lazy" />
        </div>""", unsafe_allow_html=True)
        if hdurl and not compact:
            st.markdown(
                f'<a href="{hdurl}" target="_blank" style="font-size:11px;color:#a78bfa;'
                f'text-decoration:none;font-family:\'Space Mono\',monospace">'
                f'🔎 Open HD image ↗</a>', unsafe_allow_html=True)

    elif media == "video":
        embed_url = _get_embed_url(url)
        embed_h   = int(height * 0.5625) if compact else 480   # 16:9

        # Use st.components.v1.iframe — this is the ONLY way iframes reliably
        # render inside Streamlit's security sandbox
        components.iframe(embed_url, height=embed_h)

        # Always show a direct link below the embed as backup
        st.markdown(
            f'<a href="{url}" target="_blank" style="font-size:11px;color:#a78bfa;'
            f'text-decoration:none;font-family:\'Space Mono\',monospace;display:inline-block;margin-top:6px">'
            f'▶️ Open video in new tab ↗</a>', unsafe_allow_html=True)

    # ── Meta row ──────────────────────────────────────────────────────────────
    video_badge = ('<span style="background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);'
                   'border-radius:20px;padding:2px 9px;font-size:10px;color:#ef4444">🎬 Video</span>'
                   if media == "video" else "")
    st.markdown(f"""
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;margin:10px 0 5px">
      <span style="font-family:'Orbitron',monospace;font-size:{'13px' if compact else '17px'};
      font-weight:700;color:#e2e8f0">{title}</span>
      {video_badge}
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:#64748b;
    font-family:'Space Mono',monospace;margin-bottom:8px">
      <span>📅 {d}</span>
      {f'<span>©️ {copy}</span>' if copy else ''}
    </div>""", unsafe_allow_html=True)

    if show_explanation and expl and not compact:
        with st.expander("📖 Read explanation", expanded=False):
            st.markdown(
                f'<div style="font-size:13px;color:#94a3b8;line-height:1.8">{expl}</div>',
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🗂️  HEADER
# ══════════════════════════════════════════════════════════════════════════════
cl, ct, cb = st.columns([0.06, 0.70, 0.24])
with cl:
    st.markdown("""
    <div style="width:52px;height:52px;background:radial-gradient(circle,#2e1065,#0f172a);
    border:2px solid #a78bfa;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-family:'Space Mono',monospace;font-size:9px;
    font-weight:700;color:#a78bfa;letter-spacing:1px;
box-shadow:0 0 20px rgba(167,139,250,.35);margin-top:6px">Spaceport</div>
    """, unsafe_allow_html=True)
with ct:
    st.markdown("## 🔭 Astronomy Picture of the Day (APOD)")
    st.caption("Each day a different image or photograph of our universe — with a brief explanation by a professional astronomer · Since June 16 1995")
with cb:
    st.markdown("""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.3);
      border-radius:20px;padding:4px 12px;font-size:12px;color:#a78bfa;font-weight:500">
      ✨ Daily Update</span>
    </div>""", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2340;margin:8px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🎛️  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔭 APOD Controls")

    mode = st.radio("🗂️ Mode", [
        "📅 Today's APOD",
        "🗓️ Pick a date",
        "📆 Date range",
        "🎲 Random APODs",
    ], index=0)

    st.markdown("---")

    if mode == "🗓️ Pick a date":
        pick = st.date_input(
            "📅 Select date",
            value=date.today(),
            min_value=APOD_FIRST,
            max_value=date.today(),
            help="APOD has been published every day since June 16, 1995"
        )

    elif mode == "📆 Date range":
        r_end   = date.today()
        r_start = r_end - timedelta(days=29)
        rng_start = st.date_input("🗓️ Start date", value=r_start,
                                   min_value=APOD_FIRST, max_value=date.today())
        rng_end   = st.date_input("🗓️ End date",   value=r_end,
                                   min_value=APOD_FIRST, max_value=date.today())
        if rng_end < rng_start:
            st.error("⚠️ End date must be after start date.")

    elif mode == "🎲 Random APODs":
        rand_count = st.slider("🎲 Number of random APODs", 4, 24, 12)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#475569;line-height:1.9">
    <b style="color:#64748b">🌌 About APOD</b><br>
    🔭 Started: June 16, 1995<br>
    📸 Images + videos<br>
    👨‍🚀 Written by astronomers<br>
    🌐 Most visited NASA site<br>
    📚 10,000+ entries archived
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Data from [NASA APOD API](https://api.nasa.gov/)")

# ══════════════════════════════════════════════════════════════════════════════
# 📡  Fetch data based on mode
# ══════════════════════════════════════════════════════════════════════════════
today_str = str(date.today())
apod_single   = None
apod_list     = []
fetch_error   = None

with st.spinner("🌌 Fetching from the cosmos…"):
    try:
        if mode == "📅 Today's APOD":
            apod_single = fetch_apod(today_str)
            apod_list   = [apod_single]

        elif mode == "🗓️ Pick a date":
            apod_single = fetch_apod(str(pick))
            apod_list   = [apod_single]

        elif mode == "📆 Date range":
            if rng_end >= rng_start:
                apod_list = fetch_apod_range(str(rng_start), str(rng_end))
            else:
                apod_list = []

        elif mode == "🎲 Random APODs":
            apod_list = fetch_apod_random(rand_count)

    except Exception as e:
        fetch_error = e

if fetch_error:
    st.markdown(f"""
    <div style="background:#1a0a0a;border:1px solid #7f1d1d;border-left:4px solid #ef4444;
    border-radius:10px;padding:18px 20px;margin-bottom:12px">
      <div style="font-size:14px;font-weight:600;color:#ef4444;margin-bottom:6px">
        🔭 Could not reach the APOD API
      </div>
      <div style="font-size:12px;color:#94a3b8;line-height:1.8">
        NASA's APOD endpoint returned an error. This is usually temporary.
      </div>
      <details style="margin-top:8px">
        <summary style="color:#64748b;font-size:11px;cursor:pointer">🔍 Details</summary>
        <pre style="color:#475569;font-size:10px;margin-top:6px;white-space:pre-wrap">{fetch_error}</pre>
      </details>
    </div>""", unsafe_allow_html=True)
    if st.button("🔄 Retry", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

if not apod_list:
    st.warning("⚠️ No APOD data returned.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 📊  Stat strip (always shown)
# ══════════════════════════════════════════════════════════════════════════════
days_since = (date.today() - APOD_FIRST).days
images_count = sum(1 for a in apod_list if a.get("media_type")=="image")
videos_count = sum(1 for a in apod_list if a.get("media_type")=="video")
has_hd       = sum(1 for a in apod_list if a.get("hdurl"))
authors      = list({a.get("copyright","Unknown NASA").strip() for a in apod_list if a.get("copyright")})

sc1,sc2,sc3,sc4,sc5 = st.columns(5)
stat_card(sc1,"🌌","Days of APOD",   f"{days_since:,}",   "#a78bfa", f"since {APOD_FIRST}")
stat_card(sc2,"📸","Images loaded",  images_count,         "#4f8ef7", f"of {len(apod_list)} total")
stat_card(sc3,"🎬","Videos loaded",  videos_count,         "#f59e0b", "embedded")
stat_card(sc4,"🖼️","HD available",   has_hd,               "#22c55e", "high-resolution")
stat_card(sc5,"📅","Date range",
          apod_list[0].get("date","—") if len(apod_list)==1
          else f"{apod_list[0].get('date','—')} → {apod_list[-1].get('date','—')}",
          "#ef4444")
st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📑  TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_viewer, tab_gallery, tab_archive, tab_stats = st.tabs([
    "🔭  APOD Viewer",
    "🖼️  Gallery",
    "📚  Archive Browser",
    "📊  Insights",
])

# ══════════════════════════════════════════════════════════════════════════════
# 🔭  TAB 1 — APOD VIEWER
# ══════════════════════════════════════════════════════════════════════════════
with tab_viewer:

    if mode in ("📅 Today's APOD", "🗓️ Pick a date") and apod_single:
        item  = apod_single
        media = item.get("media_type","image")
        url   = item.get("url","")
        hdurl = item.get("hdurl","")
        expl  = item.get("explanation","")
        copy  = item.get("copyright","NASA / Public Domain")
        d     = item.get("date","")

        st.markdown(f"### 🔭 {item.get('title','')}")
        st.caption(f"📅 {d} &nbsp;·&nbsp; 🌌 NASA Astronomy Picture of the Day")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Layout: video = full-width embed THEN explanation below
        #            image = side-by-side (image left, explanation right)
        if media == "video":
            # Render video full width for best embed experience
            apod_card(item, show_explanation=False, compact=False)

            # Explanation below
            st.markdown(f"""
            <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #a78bfa;
            border-radius:12px;padding:20px 22px;margin-top:14px">
              <div style="font-size:10px;color:#64748b;text-transform:uppercase;
              letter-spacing:1px;margin-bottom:8px">📖 Explanation</div>
              <div style="font-size:13px;color:#94a3b8;line-height:1.85">{expl}</div>
            </div>""", unsafe_allow_html=True)

        else:
            # Image — side by side
            vcol, tcol = st.columns([3, 2])
            with vcol:
                apod_card(item, show_explanation=False, compact=False)

            with tcol:
                st.markdown(f"""
                <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #a78bfa;
                border-radius:12px;padding:20px 22px;margin-bottom:14px">
                  <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:1px;margin-bottom:6px">📖 Explanation</div>
                  <div style="font-size:13px;color:#94a3b8;line-height:1.85;
                  max-height:380px;overflow-y:auto">{expl}</div>
                </div>""", unsafe_allow_html=True)

                # Meta badges
                badges  = f'<span style="background:rgba(167,139,250,.15);border:1px solid rgba(167,139,250,.4);border-radius:20px;padding:3px 10px;font-size:10px;color:#a78bfa;margin-right:6px">📅 {d}</span>'
                badges += f'<span style="background:rgba(79,142,247,.12);border:1px solid rgba(79,142,247,.4);border-radius:20px;padding:3px 10px;font-size:10px;color:#4f8ef7;margin-right:6px">📸 Image</span>'
                if copy:
                    badges += f'<span style="background:rgba(100,116,139,.12);border:1px solid rgba(100,116,139,.4);border-radius:20px;padding:3px 10px;font-size:10px;color:#64748b">©️ {copy}</span>'
                st.markdown(f'<div style="margin-bottom:14px;line-height:2.4">{badges}</div>', unsafe_allow_html=True)

                link_cols = st.columns(2)
                if hdurl:
                    link_cols[0].markdown(
                        f'<a href="{hdurl}" target="_blank" style="display:block;background:#0f1626;'
                        f'border:1px solid #a78bfa55;border-radius:8px;padding:8px 12px;'
                        f'font-size:11px;color:#a78bfa;text-decoration:none;text-align:center;'
                        f'font-family:\'Space Mono\',monospace">🖼️ HD Image</a>',
                        unsafe_allow_html=True)
                link_cols[1].markdown(
                    f'<a href="{url}" target="_blank" style="display:block;background:#0f1626;'
                    f'border:1px solid #4f8ef755;border-radius:8px;padding:8px 12px;'
                    f'font-size:11px;color:#4f8ef7;text-decoration:none;text-align:center;'
                    f'font-family:\'Space Mono\',monospace">🔗 Original URL</a>',
                    unsafe_allow_html=True)

        # ── Date navigator ────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        section_hdr("🗓️","DATE NAVIGATOR","Jump to adjacent days")
        nd1, nd2, nd3, nd4, nd5 = st.columns(5)
        nav_base = date.fromisoformat(item.get("date", today_str))

        for col, delta, label, clr in [
            (nd1, -7,  "⏮️ -7 days",   "#475569"),
            (nd2, -1,  "◀️ Yesterday", "#64748b"),
            (nd3,  0,  "📅 Today",     "#a78bfa"),
            (nd4, +1,  "▶️ Tomorrow",  "#64748b"),
            (nd5, +7,  "⏭️ +7 days",   "#475569"),
        ]:
            target = nav_base + timedelta(days=delta)
            if APOD_FIRST <= target <= date.today():
                col.markdown(f"""
                <a href="?nav_date={target}" style="display:block;background:#0f1626;
                border:1px solid {clr}55;border-radius:8px;padding:9px;text-align:center;
                font-size:11px;color:{clr};text-decoration:none;
                font-family:'Space Mono',monospace">{label}<br>
                <span style="font-size:9px;color:#475569">{target}</span></a>""",
                unsafe_allow_html=True)
            else:
                col.markdown(f"""
                <div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:8px;
                padding:9px;text-align:center;font-size:11px;color:#334155;
                font-family:'Space Mono',monospace">{label}<br>
                <span style="font-size:9px">out of range</span></div>""",
                unsafe_allow_html=True)

    else:
        # ── Multi-item mode: show first item as hero ─────────────────────────
        if apod_list:
            hero = apod_list[0]
            st.markdown(f"### 🌌 {hero.get('title','')}  <span style='font-size:14px;color:#64748b'>— {hero.get('date','')}</span>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            hc1, hc2 = st.columns([3,2])
            with hc1:
                apod_card(hero, show_explanation=False)
            with hc2:
                expl = hero.get("explanation","")
                st.markdown(f"""
                <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid #a78bfa;
                border-radius:12px;padding:20px 22px">
                  <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:1px;margin-bottom:8px">📖 Explanation</div>
                  <div style="font-size:13px;color:#94a3b8;line-height:1.85;
                  max-height:380px;overflow-y:auto">{expl}</div>
                </div>""", unsafe_allow_html=True)
            st.info(f"ℹ️ {len(apod_list)} APODs loaded. Switch to **🖼️ Gallery** to see all of them.")

# ══════════════════════════════════════════════════════════════════════════════
# 🖼️  TAB 2 — GALLERY
# ══════════════════════════════════════════════════════════════════════════════
with tab_gallery:
    st.markdown("### 🖼️ APOD Gallery")
    st.caption(f"📸 {len(apod_list)} entries loaded — click any image to open full resolution")

    if len(apod_list) == 0:
        st.info("No APODs to show.")
    else:
        # Controls
        gc1, gc2, gc3 = st.columns(3)
        grid_cols   = gc1.slider("🗂️ Columns", 2, 5, 3)
        show_caps   = gc2.toggle("💬 Show titles", True)
        media_filt  = gc3.selectbox("🎭 Media type", ["All 🌌", "Images only 📸", "Videos only 🎬"])

        filtered = apod_list
        if media_filt == "Images only 📸":
            filtered = [a for a in apod_list if a.get("media_type")=="image"]
        elif media_filt == "Videos only 🎬":
            filtered = [a for a in apod_list if a.get("media_type")=="video"]

        st.markdown(f"<div style='font-size:11px;color:#64748b;margin-bottom:12px'>"
                    f"Showing {len(filtered)} of {len(apod_list)} entries</div>",
                    unsafe_allow_html=True)

        rows = [filtered[i:i+grid_cols] for i in range(0, len(filtered), grid_cols)]
        for row in rows:
            cols = st.columns(grid_cols)
            for col, item in zip(cols, row):
                media  = item.get("media_type","image")
                title  = item.get("title","")
                d      = item.get("date","")
                url    = item.get("hdurl") or item.get("url","")
                thumb  = item.get("thumbnail_url", url)
                img_url = thumb if media=="video" else url

                with col:
                    st.markdown(f"""
                    <a href="{item.get('hdurl') or item.get('url','')}" target="_blank"
                    style="text-decoration:none;display:block">
                    <div style="background:#0f1626;border:1px solid #1a2340;border-radius:10px;
                    overflow:hidden;margin-bottom:10px;transition:border-color .2s">
                      <div style="position:relative">
                        <img src="{img_url}"
                             style="width:100%;height:180px;object-fit:cover;display:block"
                             loading="lazy" onerror="this.parentElement.style.display='none'" />
                        {"<div style='position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.4)'><span style='font-size:28px'>▶️</span></div>" if media=='video' else ''}
                      </div>
                      {"f'<div style=\"padding:8px 10px\"><div style=\"font-size:11px;font-weight:600;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\">{title}</div><div style=\"font-size:9px;color:#64748b;margin-top:2px;font-family:Space Mono,monospace\">{d}</div></div>'" if show_caps else ''}
                    </div></a>""".replace(
                        "f'<div style=\"padding:8px 10px\"><div style=\"font-size:11px;font-weight:600;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\">{title}</div><div style=\"font-size:9px;color:#64748b;margin-top:2px;font-family:Space Mono,monospace\">{d}</div></div>'",
                        f'<div style="padding:8px 10px"><div style="font-size:11px;font-weight:600;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{title}</div><div style="font-size:9px;color:#64748b;margin-top:2px;font-family:\'Space Mono\',monospace">{d}</div></div>'
                        if show_caps else ""
                    ), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📚  TAB 3 — ARCHIVE BROWSER
# ══════════════════════════════════════════════════════════════════════════════
with tab_archive:
    st.markdown("### 📚 APOD Archive Browser")
    st.caption("Browse any date range from the full APOD archive (June 1995 → today)")

    # Independent date range selector for this tab
    ac1, ac2, ac3 = st.columns([2,2,1])
    arc_end   = ac1.date_input("📅 End date",   value=date.today(),
                                min_value=APOD_FIRST, max_value=date.today(), key="arc_end")
    arc_start = ac2.date_input("📅 Start date", value=date.today()-timedelta(days=13),
                                min_value=APOD_FIRST, max_value=date.today(), key="arc_start")
    load_arc  = ac3.button("🔭 Load", type="primary", use_container_width=True)

    if "arc_data" not in st.session_state:
        st.session_state.arc_data = []

    if load_arc:
        if arc_start > arc_end:
            st.error("⚠️ Start date must be before end date.")
        elif (arc_end - arc_start).days > 100:
            st.warning("⚠️ Please select a range of 100 days or fewer.")
        else:
            with st.spinner("📡 Loading archive…"):
                try:
                    st.session_state.arc_data = fetch_apod_range(str(arc_start), str(arc_end))
                except Exception as e:
                    st.error(f"⚠️ {e}")

    arc_data = st.session_state.arc_data
    if arc_data:
        st.markdown(f"<div style='font-size:12px;color:#64748b;margin:10px 0'>"
                    f"✅ {len(arc_data)} APODs loaded · "
                    f"{sum(1 for a in arc_data if a.get('media_type')=='image')} images · "
                    f"{sum(1 for a in arc_data if a.get('media_type')=='video')} videos</div>",
                    unsafe_allow_html=True)

        # Search in archive
        search = st.text_input("🔍 Search titles & explanations", placeholder="e.g. nebula, galaxy, eclipse…")
        if search:
            arc_data = [a for a in arc_data
                        if search.lower() in a.get("title","").lower()
                        or search.lower() in a.get("explanation","").lower()]
            st.caption(f"🔍 {len(arc_data)} results for '{search}'")

        # Sort
        sort_dir = st.radio("🔃 Sort", ["📅 Newest first","📅 Oldest first"], horizontal=True)
        if sort_dir == "📅 Newest first":
            arc_data = sorted(arc_data, key=lambda x: x.get("date",""), reverse=True)
        else:
            arc_data = sorted(arc_data, key=lambda x: x.get("date",""))

        # Paginate — 6 per page
        PAGE = 6
        total_pages = max(1, (len(arc_data)-1)//PAGE+1)
        arc_page = st.number_input("📄 Page", min_value=1, max_value=total_pages, value=1, step=1)
        page_items = arc_data[(arc_page-1)*PAGE : arc_page*PAGE]

        for item in page_items:
            media   = item.get("media_type","image")
            title   = item.get("title","")
            d       = item.get("date","")
            expl    = item.get("explanation","")[:300]
            url     = item.get("hdurl") or item.get("url","")
            thumb   = item.get("thumbnail_url", url)
            img_src = thumb if media=="video" else (item.get("url",""))
            copy    = item.get("copyright","")

            arc_img_col, arc_txt_col = st.columns([1,3])
            with arc_img_col:
                if media == "image":
                    st.markdown(f"""
                    <a href="{url}" target="_blank">
                    <img src="{img_src}"
                         style="width:100%;height:130px;object-fit:cover;border-radius:10px;
                         border:1px solid #1a2340;display:block"
                         loading="lazy" onerror="this.style.display='none'"/>
                    </a>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="position:relative;width:100%;height:130px;border-radius:10px;
                    overflow:hidden;border:1px solid #1a2340">
                      <img src="{thumb or img_src}" style="width:100%;height:100%;object-fit:cover"/>
                      <div style="position:absolute;inset:0;background:rgba(0,0,0,.5);
                      display:flex;align-items:center;justify-content:center;font-size:24px">▶️</div>
                    </div>""", unsafe_allow_html=True)
            with arc_txt_col:
                st.markdown(f"""
                <div style="background:#0f1626;border:1px solid #1a2340;border-left:3px solid #a78bfa;
                border-radius:10px;padding:14px 16px">
                  <div style="font-family:'Orbitron',monospace;font-size:13px;font-weight:600;
                  color:#e2e8f0;margin-bottom:4px">{title}</div>
                  <div style="font-size:10px;color:#64748b;font-family:'Space Mono',monospace;
                  margin-bottom:8px">
                    📅 {d} &nbsp;·&nbsp;
                    {"📸 Image" if media=="image" else "🎬 Video"}
                    {f"&nbsp;·&nbsp; ©️ {copy}" if copy else ""}
                  </div>
                  <div style="font-size:12px;color:#94a3b8;line-height:1.7">{expl}…</div>
                  <div style="margin-top:8px">
                    <a href="{url}" target="_blank"
                    style="font-size:10px;color:#a78bfa;text-decoration:none;
                    font-family:'Space Mono',monospace">🔎 View full image ↗</a>
                  </div>
                </div>""", unsafe_allow_html=True)
            st.markdown("<br style='margin:2px'>", unsafe_allow_html=True)

        if total_pages > 1:
            st.caption(f"Page {arc_page} of {total_pages}")
    else:
        st.markdown("""
        <div style="background:#0f1626;border:1px solid #1a2340;border-radius:12px;
        padding:40px;text-align:center;color:#475569;font-family:'Space Mono',monospace">
          📚 Select a date range and click <b style="color:#a78bfa">🔭 Load</b> to browse the archive
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📊  TAB 4 — INSIGHTS / STATS
# ══════════════════════════════════════════════════════════════════════════════
with tab_stats:
    st.markdown("### 📊 APOD Insights")

    # Need some data for stats — use loaded apod_list
    if len(apod_list) < 2:
        st.info("ℹ️ Load a **date range** or **random APODs** (sidebar) to see insights across multiple entries.")

    # ── Days since APOD began ─────────────────────────────────────────────────
    section_hdr("🌌","APOD MISSION STATS","Since the very first APOD on June 16 1995")
    mission_days = (date.today() - APOD_FIRST).days
    mission_years = mission_days / 365.25

    ms1,ms2,ms3,ms4 = st.columns(4)
    stat_card(ms1,"📅","Days of APOD",    f"{mission_days:,}",            "#a78bfa")
    stat_card(ms2,"🎂","Years running",   f"{mission_years:.1f}",          "#4f8ef7", "and counting")
    stat_card(ms3,"🌠","Est. total APODs",f"{mission_days:,}",             "#22c55e", "≈1 per day")
    stat_card(ms4,"👁️","Days until 10k",
              max(0, 10000 - mission_days) if mission_days < 10000 else "✅ Reached!",
              "#f59e0b")
    st.markdown("<br>", unsafe_allow_html=True)

    if len(apod_list) >= 2:
        # ── Media type donut ─────────────────────────────────────────────────
        section_hdr("🎭","MEDIA TYPE BREAKDOWN","")
        ic1, ic2 = st.columns(2)

        with ic1:
            media_counts = {"📸 Image": images_count, "🎬 Video": videos_count}
            media_counts = {k:v for k,v in media_counts.items() if v > 0}
            fig_donut = go.Figure(go.Pie(
                labels=list(media_counts.keys()),
                values=list(media_counts.values()),
                hole=0.55,
                marker=dict(colors=["#4f8ef7","#f59e0b"],
                            line=dict(color="#04060f", width=3)),
                textinfo="percent+label",
                textfont=dict(size=12, family="Space Mono", color="#e2e8f0"),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
            ))
            fig_donut.update_layout(
                paper_bgcolor="#04060f", height=300,
                margin=dict(l=10,r=10,t=20,b=10),
                font=dict(family="Space Mono", color="#94a3b8"),
                showlegend=True,
                legend=dict(bgcolor="rgba(15,22,38,0.85)", bordercolor="#1a2340", borderwidth=1,
                            font=dict(color="#94a3b8", size=11, family="Space Mono")),
                hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                                font=dict(color="#e2e8f0", size=12, family="Space Mono")),
                annotations=[dict(text=f"<b>{len(apod_list)}</b><br>APODs",
                                  x=0.5,y=0.5,showarrow=False,
                                  font=dict(size=14,color="#e2e8f0",family="Space Mono"))]
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with ic2:
            # HD availability
            hd_counts = {"🖼️ HD Available": has_hd, "📷 Standard only": len(apod_list)-has_hd}
            hd_counts = {k:v for k,v in hd_counts.items() if v > 0}
            fig_hd = go.Figure(go.Pie(
                labels=list(hd_counts.keys()),
                values=list(hd_counts.values()),
                hole=0.55,
                marker=dict(colors=["#22c55e","#475569"],
                            line=dict(color="#04060f", width=3)),
                textinfo="percent+label",
                textfont=dict(size=12, family="Space Mono", color="#e2e8f0"),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
            ))
            fig_hd.update_layout(
                paper_bgcolor="#04060f", height=300,
                margin=dict(l=10,r=10,t=20,b=10),
                font=dict(family="Space Mono", color="#94a3b8"),
                showlegend=True,
                legend=dict(bgcolor="rgba(15,22,38,0.85)", bordercolor="#1a2340", borderwidth=1,
                            font=dict(color="#94a3b8", size=11, family="Space Mono")),
                hoverlabel=dict(bgcolor="#0f1626", bordercolor="#1a2340",
                                font=dict(color="#e2e8f0", size=12, family="Space Mono")),
                annotations=[dict(text="<b>HD</b><br>ratio",
                                  x=0.5,y=0.5,showarrow=False,
                                  font=dict(size=14,color="#e2e8f0",family="Space Mono"))]
            )
            st.plotly_chart(fig_hd, use_container_width=True)

        # ── Copyright / photographer leaderboard ─────────────────────────────
        section_hdr("📸","TOP CONTRIBUTORS","Most frequently credited photographers/agencies")
        copy_counts = {}
        for a in apod_list:
            c = (a.get("copyright","") or "NASA / Public Domain").strip()
            copy_counts[c] = copy_counts.get(c, 0) + 1
        top_copies = sorted(copy_counts.items(), key=lambda x: x[1], reverse=True)[:12]

        if top_copies:
            fig_bar = go.Figure(go.Bar(
                x=[c[1] for c in top_copies],
                y=[c[0][:35]+"…" if len(c[0])>35 else c[0] for c in top_copies],
                orientation="h",
                marker=dict(color="#a78bfa", opacity=0.85),
                hovertemplate="<b>%{y}</b><br>APODs: %{x}<extra></extra>",
            ))
            fig_bar.update_layout(
                paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
                height=max(200, len(top_copies)*38),
                margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=True, gridcolor="#1a2340", color="#64748b",
                           tickfont=dict(family="Space Mono",size=10)),
                yaxis=dict(showgrid=False, color="#94a3b8",
                           tickfont=dict(family="Space Mono",size=10),
                           autorange="reversed"),
                hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                                font=dict(color="#e2e8f0",size=12,family="Space Mono")),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ── Timeline of images per day ────────────────────────────────────────
        section_hdr("📅","APOD TIMELINE","Media type per date in the loaded range")
        dated = [a for a in apod_list if a.get("date")]
        if dated:
            dated_sorted = sorted(dated, key=lambda x: x["date"])
            dates_   = [a["date"] for a in dated_sorted]
            is_img   = [1 if a.get("media_type")=="image"  else 0 for a in dated_sorted]
            is_vid   = [1 if a.get("media_type")=="video"  else 0 for a in dated_sorted]

            fig_tl = go.Figure()
            fig_tl.add_trace(go.Bar(x=dates_, y=is_img, name="📸 Image",
                                    marker_color="#4f8ef7", opacity=0.9,
                                    hovertemplate="%{x}<br>📸 Image<extra></extra>"))
            fig_tl.add_trace(go.Bar(x=dates_, y=is_vid, name="🎬 Video",
                                    marker_color="#f59e0b", opacity=0.9,
                                    hovertemplate="%{x}<br>🎬 Video<extra></extra>"))
            fig_tl.update_layout(
                barmode="stack", paper_bgcolor="#04060f", plot_bgcolor="#0f1626",
                height=160, margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=False,color="#64748b",
                           tickfont=dict(family="Space Mono",size=9)),
                yaxis=dict(visible=False),
                legend=dict(bgcolor="rgba(15,22,38,0.85)",bordercolor="#1a2340",borderwidth=1,
                            orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,
                            font=dict(color="#94a3b8",size=10,family="Space Mono")),
                hoverlabel=dict(bgcolor="#0f1626",bordercolor="#1a2340",
                                font=dict(color="#e2e8f0",size=12,family="Space Mono")),
            )
            st.plotly_chart(fig_tl, use_container_width=True)

        # ── Full data table ───────────────────────────────────────────────────
        section_hdr("🔢","RAW DATA TABLE","")
        tbl_rows = []
        for a in sorted(apod_list, key=lambda x: x.get("date",""), reverse=True):
            tbl_rows.append({
                "📅 Date":      a.get("date",""),
                "🌌 Title":     a.get("title",""),
                "🎭 Type":      "📸 Image" if a.get("media_type")=="image" else "🎬 Video",
                "🖼️ HD":        "✅" if a.get("hdurl") else "—",
                "©️ Copyright": a.get("copyright","NASA")[:40] if a.get("copyright") else "NASA",
            })
        if tbl_rows:
            df_tbl = pd.DataFrame(tbl_rows)
            st.dataframe(df_tbl, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Download CSV", df_tbl.to_csv(index=False),
                               "apod_data.csv", "text/csv")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#0b0f1e;border:1px solid #1a2340;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#64748b;line-height:1.9">
    <b style="color:#94a3b8">🔭 About APOD</b> — The Astronomy Picture of the Day is one of the
    most popular websites in NASA's history. Each day a different image or photograph of our
    fascinating universe is featured, along with a brief explanation written by a professional
    astronomer. APOD was created in 1995 by Robert Nemiroff and Jerry Bonnell. It has been
    published continuously every single day since June 16, 1995 — over 10,000 entries.
    &nbsp;·&nbsp;
    API: <span style="font-family:'Space Mono',monospace;color:#a78bfa">https://api.nasa.gov/planetary/apod</span>
    &nbsp;·&nbsp;
    <a href="https://apod.nasa.gov" target="_blank"
    style="color:#a78bfa;text-decoration:none">🌐 apod.nasa.gov ↗</a>
  </div>
</div>""", unsafe_allow_html=True)
