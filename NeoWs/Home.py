import streamlit as st
import requests

st.set_page_config(
    page_title="Spaceport",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');
html, body, [class*="css"] { background-color: #04060f !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"] { background:#0b0f1e !important; border-right:1px solid #1a2340; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
[data-testid="stSidebarNav"] a { color:#64748b !important; font-family:'Space Mono',monospace; font-size:13px; }
[data-testid="stSidebarNav"] a:hover { color:#4f8ef7 !important; background:rgba(79,142,247,0.08) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { color:#4f8ef7 !important; background:rgba(79,142,247,0.12) !important; }
h1,h2,h3 { color:#e2e8f0 !important; }
.stButton button { background:#0f1626 !important; border:1px solid #1a2340 !important; color:#94a3b8 !important; }
.stButton button:hover { border-color:#4f8ef7 !important; color:#4f8ef7 !important; }
[data-testid="stTextInput"] input {
  background:#0f1626 !important; border:2px solid #1a2340 !important;
  border-radius:30px !important; color:#e2e8f0 !important;
  font-family:'Space Mono',monospace !important; font-size:15px !important;
  padding:14px 24px !important; transition:border-color .2s, box-shadow .2s;
}
[data-testid="stTextInput"] input:focus {
  border-color:#4f8ef7 !important;
  box-shadow:0 0 24px rgba(79,142,247,.25) !important;
}
/* Suggestion dropdown rows */
.sugg-row {
  display:flex; align-items:center; gap:10px;
  padding:9px 16px; border-bottom:1px solid #1a2340;
  background:#0b0f1e; cursor:pointer; transition:background .15s;
}
.sugg-row:hover { background:#0f1626; }
.sugg-row:last-child { border-bottom:none; border-radius:0 0 14px 14px; }
.sugg-row:first-child { border-radius:14px 14px 0 0; }
.sugg-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.sugg-label { font-size:13px; font-weight:700; color:#e2e8f0; font-family:'Space Mono',monospace; }
.sugg-desc  { font-size:10px; color:#475569; margin-top:1px; }
.sugg-badge { font-size:9px; padding:1px 8px; border-radius:20px; margin-left:auto;
              white-space:nowrap; font-family:'Space Mono',monospace; flex-shrink:0; }
</style>
""", unsafe_allow_html=True)

NASA_KEY = "n5HmtrBzx47IgEZaYmMKGpchBgyf1vxhfiIl7zoA"

# ══════════════════════════════════════════════════════════════════════════════
# 📚  EXPANDED SEARCH CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════
CATALOGUE = [
    # ── Kepler planets ────────────────────────────────────────────────────────
    {"label":"🪐 Kepler-22 b",      "desc":"Super-Earth in habitable zone of sun-like star",       "page":"pages/Exoplanet.py","tags":["kepler","kepler-22","kepler22","exoplanet","habitable","super-earth"]},
    {"label":"🌌 Kepler-452 b",     "desc":"Earth's cousin — sun-like star, 1.5× Earth size",      "page":"pages/Exoplanet.py","tags":["kepler","kepler-452","kepler452","exoplanet","earth-like"]},
    {"label":"🌠 Kepler-186 f",     "desc":"First Earth-size planet in habitable zone",            "page":"pages/Exoplanet.py","tags":["kepler","kepler-186","kepler186","exoplanet","habitable","earth"]},
    {"label":"🪐 Kepler-20 e/f",    "desc":"First Earth-size planets around a sun-like star",      "page":"pages/Exoplanet.py","tags":["kepler","kepler-20","kepler20","exoplanet","earth-size"]},
    {"label":"🌍 Kepler-62 f",      "desc":"Super-Earth in habitable zone, ~1200 light-years",     "page":"pages/Exoplanet.py","tags":["kepler","kepler-62","kepler62","exoplanet","habitable"]},
    {"label":"💫 Kepler-69 c",      "desc":"Super-Earth near habitable zone of sun-like star",     "page":"pages/Exoplanet.py","tags":["kepler","kepler-69","kepler69","exoplanet","habitable"]},
    {"label":"🌌 Kepler-442 b",     "desc":"One of the most Earth-like confirmed exoplanets",      "page":"pages/Exoplanet.py","tags":["kepler","kepler-442","kepler442","exoplanet","earth-like","habitable"]},
    {"label":"⭐ Kepler-438 b",     "desc":"Rocky exoplanet with high Earth Similarity Index",     "page":"pages/Exoplanet.py","tags":["kepler","kepler-438","kepler438","exoplanet","rocky","habitable"]},
    {"label":"🌠 Kepler-1649 c",    "desc":"Almost Earth-size planet in habitable zone",           "page":"pages/Exoplanet.py","tags":["kepler","kepler-1649","exoplanet","habitable","earth"]},
    {"label":"🔭 Kepler Mission",   "desc":"Browse all Kepler-discovered exoplanets",              "page":"pages/Exoplanet.py","tags":["kepler","mission","exoplanet","nasa","discovery"]},
    # ── TRAPPIST planets ──────────────────────────────────────────────────────
    {"label":"🌍 TRAPPIST-1 b",     "desc":"Innermost TRAPPIST-1 rocky planet",                   "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","trappist1","exoplanet","rocky"]},
    {"label":"🌍 TRAPPIST-1 c",     "desc":"Second TRAPPIST-1 rocky planet — hot surface",        "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","exoplanet","rocky"]},
    {"label":"🌍 TRAPPIST-1 d",     "desc":"Third TRAPPIST-1 planet — inner edge habitable zone", "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","exoplanet","habitable","rocky"]},
    {"label":"🌱 TRAPPIST-1 e",     "desc":"Best habitable-zone candidate in TRAPPIST-1",         "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","exoplanet","habitable","rocky","water"]},
    {"label":"🌍 TRAPPIST-1 f",     "desc":"Fifth TRAPPIST-1 planet — icy or temperate",          "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","exoplanet","habitable","rocky"]},
    {"label":"🌍 TRAPPIST-1 g",     "desc":"Sixth TRAPPIST-1 planet — outer habitable zone",      "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","exoplanet","habitable"]},
    {"label":"🌍 TRAPPIST-1 h",     "desc":"Outermost TRAPPIST-1 planet — likely icy",            "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","exoplanet","icy"]},
    {"label":"⭐ TRAPPIST-1 System","desc":"7-planet system — all rocky, 3 in habitable zone",    "page":"pages/Exoplanet.py","tags":["trappist","trappist-1","system","exoplanet","habitable","rocky"]},
    # ── Nebulae ───────────────────────────────────────────────────────────────
    {"label":"🌌 Carina Nebula",    "desc":"Cosmic Cliffs — stunning JWST first-light image",     "page":"pages/JWST.py",    "tags":["nebula","carina","jwst","webb","infrared","cosmic cliffs","star formation"]},
    {"label":"💫 Pillars of Creation","desc":"Eagle Nebula — iconic star-forming pillars",         "page":"pages/JWST.py",    "tags":["nebula","pillars","creation","m16","eagle","jwst","star formation"]},
    {"label":"🪐 Southern Ring Nebula","desc":"Planetary nebula — dying star JWST image",          "page":"pages/JWST.py",    "tags":["nebula","southern ring","planetary","jwst","webb","dying star"]},
    {"label":"🌠 Tarantula Nebula", "desc":"30 Doradus — largest star-forming nebula in LMC",     "page":"pages/JWST.py",    "tags":["nebula","tarantula","30 doradus","jwst","star formation","lmc"]},
    {"label":"✨ Orion Nebula",     "desc":"M42 — nearest massive star-forming region",            "page":"pages/OuterSpace.py","tags":["nebula","orion","m42","star formation","hubble","nasa images"]},
    {"label":"🌸 Helix Nebula",     "desc":"Eye of God — closest planetary nebula to Earth",      "page":"pages/OuterSpace.py","tags":["nebula","helix","planetary","hubble","nasa images"]},
    {"label":"🌀 Cat's Eye Nebula", "desc":"Complex planetary nebula with concentric shells",      "page":"pages/OuterSpace.py","tags":["nebula","cats eye","planetary","hubble","nasa images"]},
    {"label":"💜 Lagoon Nebula",    "desc":"M8 — bright emission nebula in Sagittarius",          "page":"pages/OuterSpace.py","tags":["nebula","lagoon","m8","emission","nasa images","hubble"]},
    {"label":"🔴 Omega Nebula",     "desc":"M17 Swan Nebula — active star-forming region",        "page":"pages/OuterSpace.py","tags":["nebula","omega","swan","m17","star formation","nasa images"]},
    {"label":"🟣 Trifid Nebula",    "desc":"M20 — rare combination of emission and reflection",   "page":"pages/OuterSpace.py","tags":["nebula","trifid","m20","emission","reflection","nasa images"]},
    {"label":"🌌 Horsehead Nebula", "desc":"Barnard 33 — iconic dark nebula in Orion",            "page":"pages/OuterSpace.py","tags":["nebula","horsehead","dark","barnard","orion","hubble","nasa images"]},
    {"label":"🔭 Crab Nebula",      "desc":"M1 — supernova remnant from 1054 AD",                 "page":"pages/OuterSpace.py","tags":["nebula","crab","m1","supernova","remnant","pulsar","nasa images"]},
    {"label":"🌊 Bubble Nebula",    "desc":"NGC 7635 — stellar wind bubble around bright star",   "page":"pages/OuterSpace.py","tags":["nebula","bubble","ngc 7635","hubble","stellar wind","nasa images"]},
    {"label":"🔭 JWST Nebula Gallery","desc":"All nebula images from James Webb Telescope",       "page":"pages/JWST.py",    "tags":["nebula","jwst","webb","gallery","infrared","nasa"]},
    # ── Solar flares & space weather ──────────────────────────────────────────
    {"label":"🌩️ Solar Flares",     "desc":"X-ray solar flare events from DONKI database",        "page":"pages/DONKI.py",   "tags":["solar flare","flare","sun","xray","x-ray","donki","cme","space weather"]},
    {"label":"☀️ X-Class Flares",   "desc":"Most powerful solar flare classification",            "page":"pages/DONKI.py",   "tags":["solar flare","x-class","xclass","sun","donki","powerful","space weather"]},
    {"label":"🌤️ M-Class Flares",   "desc":"Moderate solar flares — can cause radio blackouts",  "page":"pages/DONKI.py",   "tags":["solar flare","m-class","mclass","sun","donki","moderate"]},
    {"label":"☀️ CME Solar Storms",  "desc":"Coronal Mass Ejections and propagation maps",        "page":"pages/DONKI.py",   "tags":["solar flare","cme","coronal","mass ejection","donki","storm","sun"]},
    {"label":"🌍 Geomagnetic Storms","desc":"Aurora visibility, Kp index, G-scale alerts",        "page":"pages/DONKI.py",   "tags":["solar flare","geomagnetic","storm","aurora","kp","donki","borealis"]},
    {"label":"💨 Solar Wind",        "desc":"High-speed solar wind stream sectors",               "page":"pages/DONKI.py",   "tags":["solar wind","wind","hss","donki","heliosphere","space weather"]},
    {"label":"🌌 Space Weather",     "desc":"All space weather events — DONKI full dashboard",    "page":"pages/DONKI.py",   "tags":["space weather","donki","sun","solar","storm","flare","cme"]},
    # ── Aurora / Northern Lights ──────────────────────────────────────────────
    {"label":"🌌 Aurora Borealis",   "desc":"Northern Lights visibility from geomagnetic storms", "page":"pages/DONKI.py",   "tags":["aurora","borealis","northern lights","kp","geomagnetic","donki"]},
    {"label":"🌠 Aurora Australis",  "desc":"Southern Lights — aurora visibility maps",           "page":"pages/DONKI.py",   "tags":["aurora","australis","southern lights","kp","geomagnetic","donki"]},
    # ── Galaxies ──────────────────────────────────────────────────────────────
    {"label":"🌌 Andromeda Galaxy",  "desc":"M31 — nearest large galaxy, 2.5M light-years away", "page":"pages/OuterSpace.py","tags":["galaxy","andromeda","m31","nasa images","spiral","neighbour"]},
    {"label":"🌀 Whirlpool Galaxy",  "desc":"M51 — interacting galaxy pair with grand spiral",    "page":"pages/JWST.py",    "tags":["galaxy","whirlpool","m51","spiral","jwst","webb","interacting"]},
    {"label":"🌸 Cartwheel Galaxy",  "desc":"Rare ring galaxy imaged by James Webb",              "page":"pages/JWST.py",    "tags":["galaxy","cartwheel","ring","jwst","webb","infrared"]},
    {"label":"🔭 Stephan's Quintet", "desc":"5-galaxy group in Webb's iconic first image",        "page":"pages/JWST.py",    "tags":["galaxy","stephans","quintet","jwst","webb","group","cluster"]},
    {"label":"🌌 SMACS Deep Field",  "desc":"Deepest infrared view — hundreds of galaxies",       "page":"pages/JWST.py",    "tags":["galaxy","smacs","deep field","jwst","webb","cluster","infrared"]},
    {"label":"💥 Galaxy Cluster",    "desc":"Gravitational lensing galaxy clusters from JWST",   "page":"pages/JWST.py",    "tags":["galaxy","cluster","lensing","jwst","webb","abell","infrared"]},
    # ── Mars ──────────────────────────────────────────────────────────────────
    {"label":"🔴 Mars Weather",      "desc":"InSight lander temperature, wind, pressure on Mars","page":"pages/InSight.py",  "tags":["mars","weather","insight","temperature","wind","pressure","sol"]},
    {"label":"🌡️ Mars Temperature",  "desc":"Daily Mars atmosphere temperature from InSight",    "page":"pages/InSight.py",  "tags":["mars","temperature","cold","insight","atmosphere","sol"]},
    {"label":"🗺️ Trek WMTS",         "desc":"Moon, Mars and Vesta Trek WMTS portals & docs",     "page":"pages/TrekWMTS.py","tags":["trek","wmts","moon","mars","vesta","map","tiles","nasa trek"]},
    {"label":"🌕 Moon Trek",         "desc":"Official NASA Moon Trek portal and WMTS links",      "page":"pages/TrekWMTS.py","tags":["moon","trek","wmts","lunar","map","tiles"]},
    {"label":"🔴 Mars Trek",         "desc":"Official NASA Mars Trek portal and WMTS links",      "page":"pages/TrekWMTS.py","tags":["mars","trek","wmts","planetary","map","tiles"]},
    {"label":"🪨 Vesta Trek",        "desc":"Official NASA Vesta Trek portal and WMTS links",     "page":"pages/TrekWMTS.py","tags":["vesta","trek","wmts","asteroid","map","tiles"]},
    {"label":"🛰️ Satellite Situation Center","desc":"NASA SSCWeb spacecraft positions and orbit services","page":"pages/SatelliteSituationCenter.py","tags":["ssc","satellite situation center","sscweb","spdf","orbit","spacecraft","rest"]},
    {"label":"📡 SSC REST API",      "desc":"Official SSC RESTful web services documentation",    "page":"pages/SatelliteSituationCenter.py","tags":["ssc","rest","api","spdf","web services","spacecraft"]},
    {"label":"📚 SSC User Guide",    "desc":"NASA SSCWeb guide for locator, queries and database", "page":"pages/SatelliteSituationCenter.py","tags":["ssc","guide","locator","query","satellite","spdf"]},
    # ── Asteroids ─────────────────────────────────────────────────────────────
    {"label":"🪐 Near-Earth Asteroids","desc":"Track asteroids approaching Earth this week",     "page":"pages/NeoWs.py",   "tags":["asteroid","neo","near earth","neows","space rock","orbit"]},
    {"label":"⚠️ Hazardous Asteroids","desc":"Potentially hazardous asteroid watch list",        "page":"pages/NeoWs.py",   "tags":["asteroid","hazardous","pha","impact","danger","neows"]},
    {"label":"💫 Asteroid Orbital Map","desc":"Interactive inner solar system asteroid orbits",  "page":"pages/NeoWs.py",   "tags":["asteroid","orbital","map","solar system","neows","orbit"]},
    {"label":"☄️ Comets & NEOs",     "desc":"Near-Earth Objects including comets",               "page":"pages/NeoWs.py",   "tags":["comet","neo","near earth","neows","object","orbit"]},
    # ── Planets ───────────────────────────────────────────────────────────────
    {"label":"🪐 Jupiter (Webb)",    "desc":"Webb's stunning view of Jupiter's storms & rings",  "page":"pages/JWST.py",    "tags":["jupiter","planet","rings","storms","jwst","webb","infrared","gas giant"]},
    {"label":"🪐 Saturn & Rings",    "desc":"Saturn ring system imagery from NASA archives",     "page":"pages/OuterSpace.py","tags":["saturn","rings","planet","nasa images","cassini","gas giant"]},
    {"label":"🌊 Neptune Rings",     "desc":"Webb's first clear view of Neptune's rings",        "page":"pages/JWST.py",    "tags":["neptune","rings","planet","jwst","webb","ice giant","infrared"]},
    {"label":"🟠 Mars Surface Maps", "desc":"Mars Trek mapping portal and WMTS surface layers",  "page":"pages/TrekWMTS.py","tags":["mars","surface","map","trek","wmts","red planet"]},
    {"label":"🌍 Earth from Space",  "desc":"Full-disc Earth imagery from DSCOVR satellite",    "page":"pages/EPIC.py",    "tags":["earth","planet","space","orbit","satellite","epic","dscovr"]},
    # ── Stars & stellar objects ────────────────────────────────────────────────
    {"label":"⭐ Wolf-Rayet Stars",  "desc":"Massive stellar winds — Webb's WR 140 imagery",     "page":"pages/JWST.py",    "tags":["star","wolf-rayet","wr140","jwst","webb","massive","stellar wind"]},
    {"label":"🌟 Star Formation",    "desc":"Protostellar jets, stellar nurseries from Webb",    "page":"pages/JWST.py",    "tags":["star","formation","protostar","nursery","jwst","webb","infrared"]},
    {"label":"💀 Supernova Remnants","desc":"Exploded star remnants in NASA image archive",      "page":"pages/OuterSpace.py","tags":["star","supernova","remnant","explosion","nasa images","hubble"]},
    {"label":"🔵 Neutron Stars",     "desc":"Pulsar and neutron star imagery & data",            "page":"pages/OuterSpace.py","tags":["star","neutron","pulsar","neutron star","nasa images"]},
    # ── APOD ──────────────────────────────────────────────────────────────────
    {"label":"🔭 Today's APOD",      "desc":"NASA Astronomy Picture of the Day",                 "page":"pages/APOD.py",    "tags":["apod","astronomy","picture","day","daily","photo","cosmos"]},
    {"label":"🌌 APOD Gallery",      "desc":"Browse thousands of daily astronomy images",        "page":"pages/APOD.py",    "tags":["apod","gallery","cosmos","nebula","galaxy","stars","image"]},
    {"label":"🎲 Random APOD",       "desc":"Discover random gems from 10,000+ APOD archive",  "page":"pages/APOD.py",    "tags":["apod","random","surprise","astronomy","image","archive"]},
    # ── Earth & atmosphere ────────────────────────────────────────────────────
    {"label":"🌍 EPIC Earth Images", "desc":"Full-disc Earth photos from DSCOVR at L1",         "page":"pages/EPIC.py",    "tags":["earth","epic","dscovr","blue marble","full disc","satellite","orbit"]},
    {"label":"🛰️ GIBS Satellite Imagery","desc":"1,000+ real-time Earth observation layers",    "page":"pages/GIBS.py",    "tags":["earth","gibs","satellite","modis","viirs","imagery","wms","real-time"]},
    {"label":"🔥 Fire Thermal Imagery","desc":"MODIS/VIIRS active fire and thermal detection",  "page":"pages/GIBS.py",    "tags":["fire","thermal","modis","gibs","wildfire","satellite","earth"]},
    {"label":"❄️ Sea Ice & Snow",    "desc":"Arctic/Antarctic ice and snow cover layers",        "page":"pages/GIBS.py",    "tags":["ice","snow","arctic","antarctic","gibs","sea ice","cryosphere"]},
    {"label":"🌊 Sea Surface Temp",  "desc":"Global ocean SST from GHRSST and MODIS",           "page":"pages/GIBS.py",    "tags":["sea surface","temperature","sst","ocean","gibs","modis","thermal"]},
    # ── Natural events ────────────────────────────────────────────────────────
    {"label":"🔥 Wildfires (EONET)", "desc":"Active wildfire events from Earth Observatory",    "page":"pages/EONET.py",   "tags":["wildfire","fire","eonet","natural event","earth","burn"]},
    {"label":"🌪️ Hurricanes & Storms","desc":"Tropical cyclones and severe weather events",     "page":"pages/EONET.py",   "tags":["hurricane","cyclone","storm","severe","eonet","weather","tropical"]},
    {"label":"🌋 Volcanoes (EONET)", "desc":"Active volcanic eruptions tracked worldwide",       "page":"pages/EONET.py",   "tags":["volcano","eruption","lava","eonet","geological","magma"]},
    {"label":"🌊 Floods & Droughts", "desc":"Flood and drought events from EONET tracker",      "page":"pages/EONET.py",   "tags":["flood","drought","water","eonet","natural event","disaster"]},
    {"label":"🌍 EONET Event Tracker","desc":"All 13 Earth natural event categories",           "page":"pages/EONET.py",   "tags":["eonet","event","earth","natural","earthquake","drought","all"]},
    # ── Deep space ────────────────────────────────────────────────────────────
    {"label":"🌌 JADES Deep Field",  "desc":"Webb's deepest survey — thousands of galaxies",    "page":"pages/JWST.py",    "tags":["deep field","jades","jwst","webb","galaxy","infrared","distant"]},
    {"label":"🔭 Hubble Deep Field", "desc":"Iconic Hubble ultra-deep space imagery",            "page":"pages/OuterSpace.py","tags":["deep field","hubble","deep space","galaxy","ultra","nasa images"]},
    {"label":"🌌 Pandora's Cluster", "desc":"Abell 2744 — galaxy cluster from Webb",             "page":"pages/JWST.py",    "tags":["pandora","abell","galaxy cluster","jwst","webb","lensing"]},
    # ── Image library ─────────────────────────────────────────────────────────
    {"label":"🌠 NASA Image Library","desc":"140,000+ NASA images, videos and audio files",      "page":"pages/OuterSpace.py","tags":["nasa","image","video","audio","library","archive","photo","media"]},
    {"label":"🚀 Space Launch Photos","desc":"Rocket launches and historic mission imagery",     "page":"pages/OuterSpace.py","tags":["launch","rocket","shuttle","apollo","saturn","nasa","boost"]},
    {"label":"👨‍🚀 Astronaut Photos", "desc":"EVA, ISS and astronaut imagery",                  "page":"pages/OuterSpace.py","tags":["astronaut","spacewalk","eva","iss","nasa","space station","suit"]},
    {"label":"🌌 Galaxy & Nebula Photos","desc":"Deep space imagery from Hubble & NASA archives","page":"pages/OuterSpace.py","tags":["galaxy","nebula","deep space","hubble","nasa images","cosmos"]},
    {"label":"🔭 Hubble Images",     "desc":"Hubble Space Telescope imagery archive",            "page":"pages/OuterSpace.py","tags":["hubble","hst","telescope","nasa images","deep space","galaxy","nebula"]},
    # ── Exoplanet categories ──────────────────────────────────────────────────
    {"label":"🌊 K2-18 b",           "desc":"Mini-Neptune with water vapour detected",           "page":"pages/Exoplanet.py","tags":["k2-18","k218","exoplanet","water","mini-neptune","atmosphere"]},
    {"label":"🔥 Hot Jupiters",      "desc":"Gas giants orbiting extremely close to their stars","page":"pages/Exoplanet.py","tags":["hot jupiter","gas giant","exoplanet","close orbit","55 cnc","hd 209458"]},
    {"label":"🌍 Super-Earths",      "desc":"Exoplanets larger than Earth but smaller than Neptune","page":"pages/Exoplanet.py","tags":["super earth","super-earth","exoplanet","rocky","large","planet"]},
    {"label":"🌱 Habitable Zone",    "desc":"Exoplanets with Earth-like temperatures",           "page":"pages/Exoplanet.py","tags":["habitable","zone","earth-like","life","water","liquid","exoplanet"]},
    {"label":"🔬 TESS Discoveries",  "desc":"Exoplanets found by NASA's TESS mission",           "page":"pages/Exoplanet.py","tags":["tess","exoplanet","transit","discovery","nasa","mission"]},
    {"label":"🌌 Exoplanet Explorer","desc":"Browse all 5,800+ confirmed exoplanets",            "page":"pages/Exoplanet.py","tags":["exoplanet","planet","star","nasa","archive","kepler","tess","all"]},
    {"label":"🌙 Proxima Centauri b","desc":"Nearest known exoplanet — ~4.2 light-years away",  "page":"pages/Exoplanet.py","tags":["proxima","centauri","nearest","exoplanet","rocky","habitable"]},
    {"label":"⭐ HD 209458 b",       "desc":"First transiting exoplanet — 'hot Jupiter'",        "page":"pages/Exoplanet.py","tags":["hd209458","hd 209458","transit","exoplanet","hot jupiter","first"]},
]

PAGE_COLORS = {
    "pages/Exoplanet.py":"#22d3ee","pages/TrekWMTS.py":"#60a5fa",
    "pages/JWST.py":"#818cf8","pages/APOD.py":"#a78bfa","pages/EPIC.py":"#a855f7",
    "pages/GIBS.py":"#38bdf8","pages/NeoWs.py":"#4f8ef7","pages/DONKI.py":"#f59e0b",
    "pages/EONET.py":"#22c55e","pages/InSight.py":"#f97316","pages/OuterSpace.py":"#e8b84b",
    "pages/SatelliteSituationCenter.py":"#22c55e",
}
PAGE_NAMES = {
    "pages/Exoplanet.py":"Exoplanet","pages/TrekWMTS.py":"TrekWMTS",
    "pages/JWST.py":"JWST","pages/APOD.py":"APOD","pages/EPIC.py":"EPIC",
    "pages/GIBS.py":"GIBS","pages/NeoWs.py":"NeoWs","pages/DONKI.py":"DONKI",
    "pages/EONET.py":"EONET","pages/InSight.py":"InSight","pages/OuterSpace.py":"OuterSpace",
    "pages/SatelliteSituationCenter.py":"Satellite Situation Center",
}

def get_suggestions(query: str, max_results: int = 10) -> list:
    if not query or len(query.strip()) < 2:
        return []
    q = query.strip().lower()
    words = q.split()
    scored = []
    seen = set()
    for item in CATALOGUE:
        score = 0
        ll   = item["label"].lower()
        dl   = item["desc"].lower()
        tags = item["tags"]
        # Exact / prefix on full label
        if ll.startswith(q):             score += 150
        elif q in ll:                    score += 100
        # Prefix match on each tag — "kep" → "kepler", "trap" → "trappist"
        for w in words:
            for tag in tags:
                if tag == w:             score += 90
                elif tag.startswith(w): score += 70
                elif w in tag:          score += 40
        # Description match
        if q in dl:                      score += 30
        for w in words:
            if w in dl:                  score += 15
        key = item["label"]
        if score > 0 and key not in seen:
            scored.append((score, item))
            seen.add(key)
    scored.sort(key=lambda x: x[0], reverse=True)
    return [i for _, i in scored[:max_results]]

def nasa_images_search(query: str, n: int = 6) -> list:
    try:
        r = requests.get(
            "https://images-api.nasa.gov/search",
            params={"q": query, "media_type": "image", "page_size": n},
            timeout=10,
        )
        if r.status_code == 200:
            items = r.json().get("collection", {}).get("items", [])
            out = []
            for item in items:
                meta  = (item.get("data") or [{}])[0]
                links = item.get("links", [])
                thumb = next((l["href"] for l in links if l.get("rel") == "preview"), "")
                out.append({
                    "title": meta.get("title","Untitled"),
                    "thumb": thumb,
                    "date":  (meta.get("date_created","") or "")[:10],
                    "url":   f"https://images.nasa.gov/details/{meta.get('nasa_id','')}",
                })
            return out
    except Exception:
        pass
    return []


import json as _json
import re as _re

# ══════════════════════════════════════════════════════════════════════════════
# 🗺️  HERO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center;padding:28px 20px 10px">
  <div style="display:inline-flex;align-items:center;gap:16px;background:#e8dcc5;
  border:1px solid #cdbb9d;border-radius:28px;padding:18px 26px;box-shadow:0 20px 60px rgba(0,0,0,.28);
  margin-bottom:16px">
    <svg width="66" height="66" viewBox="0 0 66 66" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Spaceport logo icon">
      <circle cx="33" cy="34" r="21" fill="#81594C"/>
      <ellipse cx="24" cy="23" rx="3.2" ry="3.2" fill="#F3EBDD"/>
      <ellipse cx="16.5" cy="31.5" rx="2.2" ry="2.2" fill="#F3EBDD"/>
      <ellipse cx="31" cy="30" rx="2.2" ry="2.2" fill="#F3EBDD"/>
      <ellipse cx="29" cy="31" rx="31" ry="9.5" transform="rotate(-18 29 31)" stroke="#81594C" stroke-width="3" fill="none"/>
    </svg>
    <div style="font-family:'Orbitron',sans-serif;font-size:52px;line-height:1;color:#6b3f31;font-weight:900;letter-spacing:-1px">
      Spaceport
    </div>
  </div>
  <p style="color:#94a3b8;font-size:12px;max-width:560px;margin:0 auto;line-height:1.6">
  Spaceport brings together open space and Earth data — asteroids · space weather · exoplanets · Mars · imagery · maps</p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔍  SEARCH BAR  (Streamlit-native — works fully server-side)
# ══════════════════════════════════════════════════════════════════════════════
if "search_sel" not in st.session_state:
    st.session_state.search_sel = None
if "search_q" not in st.session_state:
    st.session_state.search_q = ""

# Custom CSS for the search input
st.markdown("""
<style>
[data-testid="stTextInput"] input {
  background:#0f1626 !important; border:2px solid #1e2d4a !important;
  border-radius:30px !important; color:#e2e8f0 !important;
  font-family:'Space Mono',monospace !important; font-size:15px !important;
  padding:14px 24px !important;
}
[data-testid="stTextInput"] input:focus {
  border-color:#4f8ef7 !important;
  box-shadow:0 0 20px rgba(79,142,247,.25) !important;
}
/* Suggestion buttons */
div[data-testid="stHorizontalBlock"] .stButton button {
  background:#0b0f1e !important; border:1px solid #1a2340 !important;
  border-radius:0 !important; color:#e2e8f0 !important;
  text-align:left !important; padding:10px 16px !important;
  width:100% !important; font-family:'Space Mono',monospace !important;
  font-size:12px !important;
}
div[data-testid="stHorizontalBlock"] .stButton button:hover {
  background:#0f1830 !important; border-color:#4f8ef7 !important;
}
</style>""", unsafe_allow_html=True)

_, _sc, _ = st.columns([1, 4, 1])
with _sc:
    _raw_q = st.text_input(
        "🔍 search",
        value=st.session_state.search_q,
        placeholder="🔍  Search — 'kep', 'trap', 'nebula', 'solar flare', 'mars', 'galaxy'…",
        label_visibility="collapsed",
        key="main_search_input",
    )

# Sync query to session state
if _raw_q != st.session_state.search_q:
    st.session_state.search_q = _raw_q
    st.session_state.search_sel = None

_q = _raw_q.strip()

# ── Hint chips ────────────────────────────────────────────────────────────────
if not _q:
    _hints = ["kepler","trappist","nebula","solar flare","galaxy","mars","asteroid","aurora","jwst","hubble"]
    _chip_html = "".join(
        f'<span style="background:#0f1626;border:1px solid #1a2340;border-radius:20px;'
        f'padding:4px 13px;font-size:10px;color:#4f8ef7;font-family:Space Mono,monospace;'
        f'cursor:pointer;margin:2px">{h}</span>'
        for h in _hints
    )
    st.markdown(
        f'<div style="text-align:center;margin:6px 0 14px;display:flex;flex-wrap:wrap;'
        f'gap:6px;justify-content:center">{_chip_html}</div>',
        unsafe_allow_html=True)

# ── Live suggestions dropdown ─────────────────────────────────────────────────
if _q and len(_q) >= 1 and st.session_state.search_sel is None:
    _sugs = get_suggestions(_q, max_results=10)
    if _sugs:
        _, _dc, _ = st.columns([1, 4, 1])
        with _dc:
            # Dropdown container
            st.markdown("""
            <div style="background:#090d1a;border:2px solid #4f8ef7;border-top:none;
            border-radius:0 0 14px 14px;overflow:hidden;margin-top:-8px;
            box-shadow:0 16px 48px rgba(0,0,0,.85)">
            """, unsafe_allow_html=True)

            for _sug in _sugs:
                _c  = PAGE_COLORS.get(_sug["page"], "#4f8ef7")
                _pn = PAGE_NAMES.get(_sug["page"], "")
                _lbl = _sug["label"]
                _desc = _sug["desc"]

                # Highlight matching chars: matched = dim, rest = bold
                _ql = _q.lower()
                _matched = [False] * len(_lbl)
                _idx = _lbl.lower().find(_ql)
                while _idx != -1:
                    for _i in range(_idx, min(_idx + len(_ql), len(_lbl))):
                        _matched[_i] = True
                    _idx = _lbl.lower().find(_ql, _idx + 1)

                _hl_html = ""
                _ci = 0
                while _ci < len(_lbl):
                    _cls = _matched[_ci]
                    _chunk = ""
                    while _ci < len(_lbl) and _matched[_ci] == _cls:
                        _chunk += _lbl[_ci]
                        _ci += 1
                    if _cls:
                        _hl_html += f'<span style="color:#64748b;font-weight:400">{_chunk}</span>'
                    else:
                        _hl_html += f'<span style="color:#e2e8f0;font-weight:700">{_chunk}</span>'

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;padding:10px 18px;
                border-bottom:1px solid #111827;background:#090d1a;
                cursor:pointer" id="sug_{_sug['label'][:10].replace(' ','_')}">
                  <div style="width:30px;height:30px;border-radius:50%;flex-shrink:0;
                  background:{_c}18;border:1px solid {_c}44;display:flex;
                  align-items:center;justify-content:center;font-size:12px">{_lbl[:2]}</div>
                  <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-family:'Space Mono',monospace;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_hl_html}</div>
                    <div style="font-size:9px;color:#2e3d52;margin-top:1px">{_desc}</div>
                  </div>
                  <span style="background:{_c}18;border:1px solid {_c}44;
                  border-radius:20px;padding:2px 8px;font-size:8px;color:{_c};
                  white-space:nowrap;flex-shrink:0;font-family:Space Mono,monospace">{_pn}</span>
                </div>""", unsafe_allow_html=True)

                if st.button(f"→ {_lbl}", key=f"btn_sug_{_lbl}", use_container_width=True,
                             help=_desc):
                    st.session_state.search_sel = _sug
                    st.session_state.search_q   = _lbl
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📋  DETAIL PANEL — shown when a suggestion is clicked or Enter pressed
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_nasa_images(query, n=6):
    try:
        r = requests.get("https://images-api.nasa.gov/search",
                         params={"q": query, "media_type": "image", "page_size": n},
                         timeout=10)
        if r.status_code == 200:
            items = r.json().get("collection", {}).get("items", [])
            out = []
            for it in items:
                meta  = (it.get("data") or [{}])[0]
                links = it.get("links", [])
                thumb = next((l["href"] for l in links if l.get("rel") == "preview"), "")
                out.append({
                    "title": meta.get("title", ""),
                    "thumb": thumb,
                    "date":  (meta.get("date_created", "") or "")[:10],
                    "url":   f"https://images.nasa.gov/details/{meta.get('nasa_id','')}",
                })
            return out
    except Exception:
        pass
    return []

# Show detail when item selected OR when Enter is pressed with a query
_show_detail = None
if st.session_state.search_sel:
    _show_detail = st.session_state.search_sel
elif _q and len(_q) >= 2:
    # On Enter: find the best match
    _best = get_suggestions(_q, max_results=1)
    if _best:
        _show_detail = _best[0]

if _show_detail:
    _it    = _show_detail
    _color = PAGE_COLORS.get(_it["page"], "#4f8ef7")
    _pname = PAGE_NAMES.get(_it["page"], "")
    _clean = _re.sub(r"[^\w\s\-()\.]", "", _it["label"]).strip()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Detail card ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#0a0e1f;border:2px solid {_color}66;border-radius:18px;
    padding:24px 28px;margin-bottom:18px;
    box-shadow:0 0 60px {_color}18">
      <div style="display:flex;align-items:flex-start;gap:18px;flex-wrap:wrap">
        <div style="width:56px;height:56px;border-radius:14px;flex-shrink:0;
        background:{_color}22;border:2px solid {_color}55;display:flex;
        align-items:center;justify-content:center;font-size:26px">{_it["label"][:2]}</div>
        <div style="flex:1;min-width:200px">
          <div style="font-family:'Space Mono',monospace;font-size:20px;font-weight:700;
          color:{_color};margin-bottom:6px">{_it["label"]}</div>
          <div style="font-size:13px;color:#94a3b8;line-height:1.7;margin-bottom:10px">
          {_it["desc"]}</div>
          <div style="display:flex;flex-wrap:wrap;gap:5px">
            {''.join(f'<span style="background:#0f1626;border:1px solid #1a2340;border-radius:12px;padding:2px 10px;font-size:9px;color:#475569;font-family:Space Mono,monospace">{t}</span>' for t in _it["tags"][:10])}
          </div>
        </div>
        <span style="background:{_color}18;border:1px solid {_color}44;border-radius:20px;
        padding:5px 14px;font-size:11px;color:{_color};font-family:'Space Mono',monospace;
        white-space:nowrap">{_pname}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── NASA Images ───────────────────────────────────────────────────────────
    with st.spinner(f"🔭 Loading images for {_clean}…"):
        _imgs = _fetch_nasa_images(_clean, n=6)

    if _imgs:
        st.markdown(
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:2px;color:#334155;margin:0 0 10px;'
            f'font-family:Space Mono,monospace">🌠 Related NASA Images</div>',
            unsafe_allow_html=True)
        _ic = st.columns(6)
        for _ii, _img in enumerate(_imgs):
            _img_col = _ic[_ii % 6]
            _img_col.markdown(f"""
            <div style="background:#0f1626;border:1px solid #1a2340;border-radius:10px;
            overflow:hidden;margin-bottom:6px">
              <a href="{_img['url']}" target="_blank" style="text-decoration:none">
                {'<img src="' + _img["thumb"] + '" style="width:100%;height:120px;object-fit:cover;display:block" loading="lazy"/>' if _img["thumb"] else '<div style="height:120px;background:#07090e;display:flex;align-items:center;justify-content:center;color:#334155;font-size:9px">No preview</div>'}
                <div style="padding:6px 8px">
                  <div style="font-size:9px;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{_img['title'][:36]}</div>
                  <div style="font-size:8px;color:#334155;margin-top:1px;font-family:Space Mono,monospace">{_img['date']}</div>
                </div>
              </a>
            </div>""", unsafe_allow_html=True)

    # ── Open page button ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, _btn_c, _ = st.columns([1, 2, 1])
    with _btn_c:
        st.page_link(_it["page"],
                     label=f"🚀 Open {_pname} Dashboard →",
                     use_container_width=True)
        if st.button("✕ Clear & search again", use_container_width=True, key="clear_sel"):
            st.session_state.search_sel = None
            st.session_state.search_q   = ""
            st.rerun()

st.markdown("<hr style='border-color:#1a2340;margin:12px 0 20px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🃏  DASHBOARD CARDS
# ══════════════════════════════════════════════════════════════════════════════
row1_cols = st.columns(4, gap="small")
row2_cols = st.columns(4, gap="small")
row3_cols = st.columns(4, gap="small")

CARDS = [
    (row1_cols,0,"#4f8ef7","🪐","NeoWs",     "Near Earth Objects & asteroid tracker.",                  "pages/NeoWs.py",     "🪐 NeoWs"),
    (row1_cols,1,"#f59e0b","🌩️","DONKI",     "Space weather, CMEs, solar flares & storms.",            "pages/DONKI.py",     "🌩️ DONKI"),
    (row1_cols,2,"#22c55e","🌍","EONET",     "Earth natural events tracker.",                           "pages/EONET.py",     "🌍 EONET"),
    (row1_cols,3,"#a855f7","📷","EPIC",      "Full-disc Earth photos from DSCOVR at L1.",              "pages/EPIC.py",      "📷 EPIC"),
    (row2_cols,0,"#a78bfa","🔭","APOD",      "Astronomy Picture of the Day since 1995.",               "pages/APOD.py",      "🔭 APOD"),
    (row2_cols,1,"#22d3ee","🌌","Exoplanet", "5,800+ confirmed planets beyond our solar system.",      "pages/Exoplanet.py", "🌌 Exoplanet"),
    (row2_cols,2,"#38bdf8","🛰️","GIBS",      "1,000+ global satellite imagery layers near real-time.","pages/GIBS.py",      "🛰️ GIBS"),
    (row2_cols,3,"#f97316","🔴","InSight",   "Daily Mars weather — temp, wind & pressure.",            "pages/InSight.py",   "🔴 InSight"),
    (row3_cols,0,"#60a5fa","🗺️","TrekWMTS",  "Moon, Mars and Vesta Trek with VR Tech WMTS portals & docs.",          "pages/TrekWMTS.py", "🗺️ TrekWMTS"),
    (row3_cols,1,"#818cf8","🔭","JWST",      "James Webb Telescope — deepest infrared images ever.",   "pages/JWST.py",      "🔭 JWST"),
    (row3_cols,2,"#e8b84b","🌠","OuterSpace","140,000+ NASA images, videos & audio files.",            "pages/OuterSpace.py","🌠 OuterSpace"),
    (row3_cols,3,"#22c55e","🛰️","SSC",       "Satellite Situation Center spacecraft orbit services.",   "pages/SatelliteSituationCenter.py","🛰️ Satellite Situation Center"),
]

for col_list,idx,color,emoji,title,desc,page,label in CARDS:
    with col_list[idx]:
        st.markdown(f"""
        <div style="background:#0f1626;border:1px solid #1a2340;border-top:3px solid {color};
        border-radius:14px;padding:18px 16px;text-align:center;min-height:180px;
        display:flex;flex-direction:column;justify-content:center">
          <div style="font-size:28px;margin-bottom:8px">{emoji}</div>
          <div style="font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:5px">{title}</div>
          <div style="font-size:10px;color:#64748b;line-height:1.5">{desc}</div>
        </div>""", unsafe_allow_html=True)
        st.page_link(page, label=label, use_container_width=True)

# ── Stats strip ───────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;
padding:14px 0;border-top:1px solid #1a2340;border-bottom:1px solid #1a2340">
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#4f8ef7;font-weight:700">12</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🚀 APIs</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#22d3ee;font-weight:700">5,800+</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🌌 Exoplanets</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#38bdf8;font-weight:700">1,000+</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🛰️ GIBS Layers</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#a78bfa;font-weight:700">10k+</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🔭 APOD Archive</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#e8b84b;font-weight:700">140k+</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🌠 Media Assets</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#818cf8;font-weight:700">13.6B</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🔭 JWST yrs</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#fb923c;font-weight:700">M+</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">🚗 Rover Photos</div></div>
  <div style="text-align:center;padding:0 10px"><div style="font-family:'Space Mono',monospace;font-size:17px;color:#ef4444;font-weight:700">∞</div><div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px">⚡ Real-time</div></div>
</div>""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#1e293b;font-size:10px;font-family:'Space Mono',monospace;
padding:12px 0 24px">
  🛰️ api.nasa.gov · epic.gsfc.nasa.gov · eonet.gsfc.nasa.gov · apod.nasa.gov
  · exoplanetarchive.ipac.caltech.edu · gibs.earthdata.nasa.gov · images.nasa.gov
</div>""", unsafe_allow_html=True)
