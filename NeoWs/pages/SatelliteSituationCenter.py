import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Spaceport | Satellite Situation Center",
    page_icon="🛰️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');

html, body, [class*="css"] { background-color: #04070e !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"] { background:#0a0f1a !important; border-right:1px solid #1a2842; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stTabs"] button { color:#64748b !important; font-family:'Space Mono',monospace !important; font-size:11px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#22c55e !important; border-bottom-color:#22c55e !important; }
h1,h2,h3 { color:#f8fafc !important; }
div[data-baseweb="select"] > div { background:#0f1728 !important; border-color:#1a2842 !important; }
.ssc-card {
  background:#0f1728;
  border:1px solid #1a2842;
  border-top:3px solid #22c55e;
  border-radius:14px;
  padding:18px 20px;
}
.muted {
  color:#94a3b8;
  font-size:12px;
  line-height:1.75;
}
.tiny {
  color:#64748b;
  font-size:10px;
  font-family:'Space Mono',monospace;
}
</style>
""", unsafe_allow_html=True)

NASA_KEY = "iIzMAqX15jOxMU064ePgWHbg0yDqQLLJKFEAKzBv"
ACCENT = "#22c55e"

SSC_LINKS = {
    "home": "https://sscweb.gsfc.nasa.gov/",
    "sscweb": "https://sscweb.gsfc.nasa.gov/ssc.html",
    "rest": "https://sscweb.gsfc.nasa.gov/WebServices/REST/",
    "services": "https://sscweb.gsfc.nasa.gov/WebServices/",
    "availability": "https://sscweb.gsfc.nasa.gov/scansat/",
    "guide": "https://sscweb.gsfc.nasa.gov/users_guide/Users_Guide_pt1.shtml",
}


def stat_card(col, emoji: str, label: str, value: str, color: str, sub: str = ""):
    col.markdown(
        f"""
        <div style="background:#0f1728;border:1px solid #1a2842;border-top:3px solid {color};
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


def render_portal(title: str, description: str, url: str, height: int):
    left, right = st.columns([1.05, 1.35])
    with left:
        st.markdown(
            f"""
            <div class="ssc-card">
              <div style="font-family:'Orbitron',monospace;font-size:20px;font-weight:800;color:{ACCENT};margin-bottom:8px">
                {title}
              </div>
              <div class="muted">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")
        st.link_button(f"Open {title}", url, use_container_width=True)
    with right:
        st.markdown(f"#### {title} Preview")
        components.iframe(url, height=height, scrolling=True)


hl, hc, hr = st.columns([0.07, 0.68, 0.25])
with hl:
    st.markdown("""
    <div style="width:54px;height:54px;background:radial-gradient(circle,#14532d,#07120a);
    border:2px solid #22c55e;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:10px;font-weight:700;color:#22c55e;
    letter-spacing:1px;box-shadow:0 0 24px rgba(34,197,94,.30);margin-top:6px">SSC</div>
    """, unsafe_allow_html=True)
with hc:
    st.markdown("## 🛰️ Spaceport | Satellite Situation Center")
    st.caption("Spaceport hub for SSCWeb spacecraft locations, orbit planning, tabular listings and REST web services.")
with hr:
    st.markdown("""
    <div style="margin-top:14px;text-align:right">
      <span style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.35);
      border-radius:20px;padding:4px 12px;font-size:12px;color:#22c55e;font-weight:500">
      Spaceport</span></div>
    """, unsafe_allow_html=True)
st.markdown("<hr style='border-color:#1a2842;margin:8px 0 20px'>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🛰️ SSC Controls")
    start_view = st.radio(
        "Open section",
        ["Overview", "REST API", "Availability", "User Guide"],
        index=0,
    )
    embed_height = st.slider("Embed Height", 520, 920, 700, 20)
    show_embed = st.toggle("Show embedded page", True)

sc1, sc2, sc3, sc4 = st.columns(4)
stat_card(sc1, "🌐", "Portal", "SSCWeb", ACCENT, "Space Physics Data Facility")
stat_card(sc2, "🧭", "Use Case", "Locator", "#38bdf8", "spacecraft position and regions")
stat_card(sc3, "🔌", "API", "REST", "#f59e0b", "official SSC web services")
stat_card(sc4, "📚", "Guide", "SPDF", "#a78bfa", "user guide and listings")

overview_tab, rest_tab, avail_tab, guide_tab = st.tabs([
    "✨ Overview",
    "🔌 REST API",
    "📡 Availability",
    "📚 User Guide",
])

with overview_tab:
    st.markdown("""
    <div class="ssc-card">
      <div style="font-family:'Orbitron',monospace;font-size:18px;font-weight:800;color:#22c55e;margin-bottom:8px">
        What SSCWeb Provides
      </div>
      <div class="muted">
        The Satellite Situation Center Web service is part of SPDF and focuses on spacecraft location data,
        orbit visualization, magnetospheric region context, and planning support across many missions.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("Open SSCWeb Home", SSC_LINKS["home"], use_container_width=True)
        st.link_button("Open SSCWeb Interface", SSC_LINKS["sscweb"], use_container_width=True)
    with c2:
        st.link_button("Open REST Web Services", SSC_LINKS["rest"], use_container_width=True)
        st.link_button("Open Web Services Overview", SSC_LINKS["services"], use_container_width=True)
    if show_embed and start_view == "Overview":
        st.markdown("")
        components.iframe(SSC_LINKS["sscweb"], height=embed_height, scrolling=True)

with rest_tab:
    render_portal(
        "SSC REST API",
        "Spaceport access to official SSC RESTful web services for software integrations that need spacecraft location and related SSC data.",
        SSC_LINKS["rest"],
        embed_height,
    )
    st.markdown("##### Key Links")
    st.markdown(
        f"""
        - REST docs: {SSC_LINKS["rest"]}
        - Web services overview: {SSC_LINKS["services"]}
        - SSC main site: {SSC_LINKS["home"]}
        """
    )

with avail_tab:
    render_portal(
        "Spacecraft Availability & Time Ranges",
        "Browse SSC's spacecraft availability page to see supported missions and their time coverage windows.",
        SSC_LINKS["availability"],
        embed_height,
    )

with guide_tab:
    render_portal(
        "SSC User Guide",
        "The SSC user guide explains the system background, locator workflows, query capabilities, and database context.",
        SSC_LINKS["guide"],
        embed_height,
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="background:#0a0f1a;border:1px solid #1a2842;border-radius:12px;padding:16px 20px">
  <div style="font-size:12px;color:#94a3b8;line-height:1.8">
    <b style="color:#e2e8f0">About this page</b>:
        Spaceport groups the main SSCWeb entry points in one place so you can jump between the portal,
    REST docs, spacecraft availability, and the user guide quickly.
  </div>
</div>
""", unsafe_allow_html=True)
