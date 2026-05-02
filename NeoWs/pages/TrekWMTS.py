import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Spaceport | Trek WMTS",
    page_icon="🗺️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');

html, body, [class*="css"] { background-color: #05070d !important; color: #e5edf7 !important; }
[data-testid="stSidebar"] { background:#0a0f18 !important; border-right:1px solid #1c2740; }
[data-testid="stSidebar"] * { color:#e5edf7 !important; }
[data-testid="stTabs"] button { color:#64748b !important; font-family:'Space Mono',monospace !important; font-size:11px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#60a5fa !important; border-bottom-color:#60a5fa !important; }
[data-testid="metric-container"] { background:#0d1422; border:1px solid #1c2740; border-radius:14px; padding:16px 20px !important; }
h1,h2,h3 { color:#f8fafc !important; }
div[data-baseweb="select"] > div { background:#0d1422 !important; border-color:#1c2740 !important; }
.trek-card {
  background:#0d1422;
  border:1px solid #1c2740;
  border-top:3px solid #60a5fa;
  border-radius:14px;
  padding:18px 20px;
}
.muted {
  color:#94a3b8;
  font-size:12px;
  line-height:1.7;
}
.tiny {
  color:#64748b;
  font-size:10px;
  font-family:'Space Mono',monospace;
}
</style>
""", unsafe_allow_html=True)

ACCENT = "#60a5fa"

TREK_BODIES = {
    "🌕 Moon Trek": {
        "short": "Moon",
        "portal": "https://trek.nasa.gov/moon/",
        "wmts_docs": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
        "about": "NASA's Moon Trek portal for lunar layers, terrain, and mission-planning visuals.",
    },
    "🔴 Mars Trek": {
        "short": "Mars",
        "portal": "https://trek.nasa.gov/mars/",
        "wmts_docs": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
        "about": "NASA's Mars Trek portal for planetary surface exploration and layered mapping products.",
    },
    "🪨 Vesta Trek": {
        "short": "Vesta",
        "portal": "https://trek.nasa.gov/vesta/index.html",
        "wmts_docs": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=vesta",
        "about": "NASA's Vesta Trek portal built from Dawn mission data for asteroid surface exploration.",
    },
}


def stat_card(col, emoji: str, label: str, value: str, color: str, sub: str = ""):
    col.markdown(
        f"""
        <div style="background:#0d1422;border:1px solid #1c2740;border-top:3px solid {color};
        border-radius:12px;padding:16px 18px;text-align:center">
          <div style="font-size:20px">{emoji}</div>
          <div style="font-family:'Space Mono',monospace;font-size:20px;color:{color};
          font-weight:700;margin:4px 0">{value}</div>
          <div style="color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px">{label}</div>
          {f'<div style="color:#94a3b8;font-size:10px;margin-top:2px">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def tile_template(body: str) -> str:
    return (
        f"https://trek.nasa.gov/tiles/{body.lower()}/{{layer_name}}/1.0.0/"
        "{style}/{tile_matrix_set}/{tile_matrix}/{tile_row}/{tile_col}.png"
    )


hl, hc, hr = st.columns([0.07, 0.68, 0.25])
with hl:
    st.markdown(
        """
        <div style="width:54px;height:54px;background:radial-gradient(circle,#1d4ed8,#08111f);
        border:2px solid #60a5fa;border-radius:50%;display:flex;align-items:center;justify-content:center;
        font-family:'Space Mono',monospace;font-size:10px;font-weight:700;color:#60a5fa;
        letter-spacing:1px;box-shadow:0 0 24px rgba(96,165,250,.35);margin-top:6px">WMTS</div>
        """,
        unsafe_allow_html=True,
    )
with hc:
    st.markdown("## 🗺️ Spaceport | Vesta / Moon / Mars Trek WMTS")
    st.caption("Spaceport brings together Solar System Treks portals with direct WMTS documentation and quick launch links.")
with hr:
    st.markdown(
        """
        <div style="margin-top:14px;text-align:right">
          <span style="background:rgba(96,165,250,.1);border:1px solid rgba(96,165,250,.35);
          border-radius:20px;padding:4px 12px;font-size:12px;color:#60a5fa;font-weight:500">
          Spaceport</span></div>
        """,
        unsafe_allow_html=True,
    )
st.markdown("<hr style='border-color:#1c2740;margin:8px 0 20px'>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🗺️ Trek Controls")
    selected_body = st.radio("Choose Trek", list(TREK_BODIES.keys()), index=0)
    embed_height = st.slider("Embed Height", 520, 900, 680, 20)
    show_portal = st.toggle("Show embedded portal", True)

selected = TREK_BODIES[selected_body]

sc1, sc2, sc3 = st.columns(3)
stat_card(sc1, "🌐", "Portal", selected["short"], ACCENT, "Solar System Treks")
stat_card(sc2, "📚", "WMTS Docs", "RESTful", "#22c55e", "official Trek API docs")
stat_card(sc3, "🛰️", "Access", "Public", "#f59e0b", "official NASA Trek links")

tab_selected, tab_moon, tab_mars, tab_vesta = st.tabs([
    f"✨ Selected: {selected['short']}",
    "🌕 Moon",
    "🔴 Mars",
    "🪨 Vesta",
])


def render_body(label: str):
    body = TREK_BODIES[label]
    lc, rc = st.columns([1.05, 1.35])
    with lc:
        st.markdown(
            f"""
            <div class="trek-card">
              <div style="font-family:'Orbitron',monospace;font-size:20px;font-weight:800;color:{ACCENT};margin-bottom:8px">
                {label}
              </div>
              <div class="muted">{body['about']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")
        st.link_button(f"Open {body['short']} Trek Portal", body["portal"], use_container_width=True)
        st.link_button(f"Open {body['short']} WMTS Docs", body["wmts_docs"], use_container_width=True)
        st.markdown("##### WMTS Template")
        st.code(tile_template(body["short"]), language="text")
        st.markdown("##### Service Links")
        st.markdown(
            f"""
            - Portal: {body['portal']}
            - WMTS docs: {body['wmts_docs']}
            """,
        )
        st.markdown(
            """
            <div class="tiny">
            Source notes: Trek WMTS documentation is published on <code>trek.nasa.gov</code>. Spaceport surfaces the docs and
            RESTful WMTS tile pattern and point to per-body service details.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with rc:
        st.markdown(f"#### {body['short']} Trek Preview")
        if show_portal:
            components.iframe(body["portal"], height=embed_height, scrolling=True)
        else:
            st.info("Enable `Show embedded portal` in the sidebar to preview the Trek site here.")


with tab_selected:
    render_body(selected_body)

with tab_moon:
    render_body("🌕 Moon Trek")

with tab_mars:
    render_body("🔴 Mars Trek")

with tab_vesta:
    render_body("🪨 Vesta Trek")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="background:#0a0f18;border:1px solid #1c2740;border-radius:12px;padding:16px 20px">
      <div style="font-size:12px;color:#94a3b8;line-height:1.8">
        <b style="color:#e2e8f0">About this page</b>:
        Spaceport groups the official Trek portals for Moon, Mars, and Vesta in one place for quick access.
        &nbsp;·&nbsp;
        <a href="https://trek.nasa.gov/" target="_blank" style="color:{ACCENT};text-decoration:none">trek.nasa.gov ↗</a>
        &nbsp;·&nbsp;
        <a href="https://trek.nasa.gov/tiles/apidoc/index.html" target="_blank" style="color:#22c55e;text-decoration:none">WMTS docs ↗</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
