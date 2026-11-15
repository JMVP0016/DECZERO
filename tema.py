# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Look of the app: CSS, header, help texts and footer. All visible text in English."""

import os
from contextlib import contextmanager

import streamlit as st

ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")

PROJECT_NAME = "HAWAPACHA"
TAGLINE = "Find the change in the sky."

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;800&family=Inter:wght@400;600&display=swap');

/* Text font. Do not use a wildcard selector here: it would also replace the
   icon font of Streamlit and the icons would show up as words. */
html, body, .stApp, .stMarkdown, p, label, input, textarea, li { font-family: 'Inter', sans-serif; }
[data-testid="stIconMaterial"], .material-symbols-rounded, .material-icons {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}
h1, h2, h3, .dz-title { font-family: 'Montserrat', sans-serif; letter-spacing: -0.01em; }

/* less empty space at the top, comfortable width */
.block-container { padding-top: 3.8rem; max-width: 1150px; }  /* room for Streamlit's own top bar */

/* hero: a dark panel with a planet horizon, stars and the name. CSS only. */
.dz-hero {
  position: relative; overflow: hidden; border-radius: 22px;
  padding: clamp(1.2rem, 2.6vw, 2rem) clamp(1.1rem, 3.4vw, 2.6rem) 1rem;
  margin-bottom: 1.4rem;
  background:
    radial-gradient(120% 90% at 50% -10%, #16335c 0%, #0d1d38 38%, #070c16 78%);
  border: 1px solid rgba(72,224,203,0.14);
}
/* stars: three layers of tiny dots that twinkle at different speeds */
.dz-stars, .dz-stars::before, .dz-stars::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background-repeat: repeat;
}
.dz-stars {
  background-image:
    radial-gradient(1px 1px at 12% 22%, #fff 99%, transparent),
    radial-gradient(1px 1px at 31% 61%, #cfe9ff 99%, transparent),
    radial-gradient(1.5px 1.5px at 47% 14%, #fff 99%, transparent),
    radial-gradient(1px 1px at 63% 44%, #fff 99%, transparent),
    radial-gradient(1px 1px at 78% 19%, #bfeee6 99%, transparent),
    radial-gradient(1.5px 1.5px at 88% 52%, #fff 99%, transparent),
    radial-gradient(1px 1px at 22% 78%, #fff 99%, transparent),
    radial-gradient(1px 1px at 55% 71%, #cfe9ff 99%, transparent);
  background-size: 260px 190px; opacity: 0.85;
  animation: dz-twinkle 6s ease-in-out infinite alternate;
}
.dz-stars::before {
  background-image:
    radial-gradient(1px 1px at 8% 48%, #fff 99%, transparent),
    radial-gradient(1px 1px at 38% 31%, #fff 99%, transparent),
    radial-gradient(1px 1px at 71% 66%, #cfe9ff 99%, transparent),
    radial-gradient(1px 1px at 93% 27%, #fff 99%, transparent);
  background-size: 190px 140px; opacity: 0.7;
  animation: dz-twinkle 9s ease-in-out infinite alternate-reverse;
}
/* the planet: a huge circle whose top edge is the lit horizon */
.dz-planet {
  position: absolute; left: 50%; top: calc(100% - clamp(4.4rem, 8vw, 6rem)); width: 210%; aspect-ratio: 1 / 1;
  transform: translateX(-50%); border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle at 50% 0%, #10294d 0%, #091528 22%, #060b14 55%);
  box-shadow:
    0 0 0 1px rgba(140,225,255,0.55),
    0 -6px 26px 2px rgba(72,224,203,0.45),
    0 -28px 90px 10px rgba(47,128,237,0.45),
    0 -70px 180px 30px rgba(47,128,237,0.22);
  animation: dz-glow 8s ease-in-out infinite alternate;
}
.dz-hero-inner { position: relative; z-index: 2; animation: dz-rise 0.9s ease-out both; }
.dz-kicker { color: #48E0CB; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; }
.dz-brand { display: flex; align-items: center; gap: 1rem; margin: 0.35rem 0 0.45rem 0; }
.dz-brand svg { width: clamp(56px, 7vw, 84px); height: auto; flex-shrink: 0; }
.dz-title { font-size: clamp(2.2rem, 6vw, 4.1rem); font-weight: 800; line-height: 0.95; margin: 0; color: #F5F6F8; letter-spacing: 0.01em; }
.dz-tagline { font-size: clamp(1.05rem, 2.2vw, 1.5rem); color: #F5F6F8; margin: 0 0 0.3rem 0; font-family: 'Montserrat', sans-serif; font-weight: 600; }
.dz-sub { font-size: 1rem; color: #AEB8CC; margin: 0; max-width: 46rem; }
.dz-facts { position: relative; z-index: 2; display: flex; flex-wrap: wrap; justify-content: center; gap: 0.7rem 2.6rem; margin-top: clamp(1.5rem, 4.5vw, 3.1rem); }
.dz-fact { text-align: center; }
.dz-fact b { display: block; font-family: 'Montserrat', sans-serif; font-size: clamp(1rem, 2vw, 1.35rem); color: #F5F6F8; }
.dz-fact span { font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; color: #8FD9CE; }

@keyframes dz-twinkle { from { opacity: 0.35; } to { opacity: 0.9; } }
@keyframes dz-glow { from { filter: brightness(0.9); } to { filter: brightness(1.2); } }
@keyframes dz-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  .dz-stars, .dz-stars::before, .dz-planet, .dz-hero-inner { animation: none; }
}

/* small note inside the hero: the scene was drawn with SI assistance */
.dz-si { position: absolute; z-index: 2; right: 0.9rem; bottom: 0.35rem; font-size: 0.62rem; color: #9AA7BD; margin: 0; }

/* review states: amber ring while waiting, turquoise dot once there is a verdict */
.dz-state { display: inline-flex; align-items: center; gap: 0.45rem; font-weight: 600; font-size: 0.9rem; }
.dz-state i { width: 0.7rem; height: 0.7rem; border-radius: 50%; display: inline-block; box-sizing: border-box; }
.dz-state.waiting { color: #FBBF24; } .dz-state.waiting i { border: 2px solid #FBBF24; }
.dz-state.done { color: #48E0CB; } .dz-state.done i { background: #48E0CB; }
[data-testid="stMetricValue"], [data-testid="stCaptionContainer"] { font-variant-numeric: tabular-nums; }

/* numbered section labels, as in the brand sheet */
.dz-section { display: flex; align-items: baseline; gap: 0.7rem; margin: 1.6rem 0 0.6rem 0; }
.dz-section i { font-style: normal; color: #48E0CB; font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 0.85rem; letter-spacing: 0.1em; }
.dz-section b { font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.1em; text-transform: uppercase; color: #F5F6F8; }
.dz-section::after { content: ""; flex: 1; height: 1px; background: rgba(232,236,244,0.14); }

/* help cards */
.dz-card { background: #131D2E; border: 1px solid rgba(232,236,244,0.10); border-radius: 12px; padding: 0.9rem 1rem; height: 100%; }
.dz-card h4 { font-family: 'Montserrat', sans-serif; font-size: 1rem; margin: 0 0 0.35rem 0; color: #48E0CB; }
.dz-card p { font-size: 0.92rem; line-height: 1.45; margin: 0; color: #C9D1E0; }

/* sky images: framed like instrument panels */
[data-testid="stImage"] img {
  border-radius: 12px; border: 1px solid rgba(72,224,203,0.35);
  box-shadow: 0 0 0 4px rgba(72,224,203,0.06), 0 12px 30px rgba(0,0,0,0.45);
}
[data-testid="stImageCaption"], [data-testid="stCaptionContainer"] { letter-spacing: 0.02em; }
[data-testid="stMetricLabel"] p { color: #48E0CB; font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 600; }
[data-testid="stMetricValue"] { font-family: 'Montserrat', sans-serif; font-weight: 800; }

/* top menu */
.dz-nav-gap { height: 0.2rem; }
[data-testid="stPageLink"] a { border-radius: 999px; border: 1px solid rgba(232,236,244,0.16); padding: 0.3rem 1rem; width: fit-content; max-width: none; white-space: nowrap; }
[data-testid="stPageLink"] a * { white-space: nowrap; overflow: visible; text-overflow: clip; }
[data-testid="stPageLink"] a:hover { border-color: #48E0CB; }
[data-testid="stPageLink"] p { font-family: 'Montserrat', sans-serif; font-weight: 600; font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; }

/* loading scene */
.dz-loader { display: flex; flex-direction: column; align-items: center; padding: 1.4rem 1rem 1.6rem 1rem;
  border-radius: 18px; border: 1px solid rgba(72,224,203,0.18);
  background: radial-gradient(90% 120% at 50% 0%, #13294a 0%, #0b1526 60%, #070c16 100%); }
.dz-loader svg { width: min(260px, 60vw); height: auto; }
.dz-loader .dz-orbit { transform-origin: 100px 100px; animation: dz-spin 9s linear infinite; }
.dz-loader .dz-craft { transform-origin: 100px 104px; animation: dz-sway 5s ease-in-out infinite alternate; }
.dz-loader .dz-band { opacity: 0.12; animation: dz-band 2.4s ease-in-out infinite; }
.dz-loader .dz-band:nth-child(2) { animation-delay: 0.2s; } .dz-loader .dz-band:nth-child(3) { animation-delay: 0.4s; }
.dz-loader .dz-band:nth-child(4) { animation-delay: 0.6s; } .dz-loader .dz-band:nth-child(5) { animation-delay: 0.8s; }
.dz-loader .dz-band:nth-child(6) { animation-delay: 1.0s; }
.dz-loader .dz-dot { animation: dz-twinkle 2.8s ease-in-out infinite alternate; }
.dz-loader-text { font-family: 'Montserrat', sans-serif; font-weight: 600; color: #F5F6F8; margin: 0.4rem 0 0.15rem 0; text-align: center; }
.dz-loader-sub { color: #8FD9CE; font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; margin: 0; text-align: center; }
.dz-loader-note { color: #9AA7BD; font-size: 0.75rem; margin: 0.6rem 0 0 0; }
@keyframes dz-spin { to { transform: rotate(360deg); } }
@keyframes dz-sway { from { transform: rotate(-24deg); } to { transform: rotate(-14deg); } }
@keyframes dz-band { 0%, 100% { opacity: 0.10; } 50% { opacity: 0.95; } }
@media (prefers-reduced-motion: reduce) {
  .dz-loader .dz-orbit, .dz-loader .dz-craft, .dz-loader .dz-band, .dz-loader .dz-dot { animation: none; }
  .dz-loader .dz-band { opacity: 0.6; }
}
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button { border-radius: 10px; font-weight: 600; }
/* dark text on the turquoise button, so it stays readable */
button[kind="primary"], button[kind="primaryFormSubmit"] { color: #0C1421 !important; }
button[kind="primary"] p, button[kind="primaryFormSubmit"] p { color: #0C1421 !important; }

.dz-footer { color: #8792A8; font-size: 0.8rem; border-top: 1px solid rgba(232,236,244,0.12); padding-top: 0.8rem; margin-top: 1.6rem; }
.dz-footer a { color: #AEB8CC; }
</style>
"""


# The Hawapacha mark: a sky circle crossed by the equator line, with two objects.
LOGO_SVG = """
<svg viewBox="0 0 120 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="HAWAPACHA logo">
  <circle cx="60" cy="50" r="40" fill="none" stroke="#F5F6F8" stroke-width="6"/>
  <circle cx="44" cy="32" r="6" fill="#48E0CB"/>
  <circle cx="76" cy="68" r="6" fill="#48E0CB"/>
  <rect x="8" y="47" width="104" height="6" rx="2" fill="#48E0CB"/>
</svg>
"""


# SPHEREx drawn in the brand colours: three nested cone-shaped shields around the
# telescope, the spacecraft body and its flat solar panel. The six lines are the six
# detector bands sweeping the sky. Simplified drawing by the team, not an official image.
LOADER_SVG = """
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Drawing of the SPHEREx space telescope scanning the sky">
  <circle class="dz-dot" cx="24" cy="38" r="1.2" fill="#F5F6F8"/>
  <circle class="dz-dot" cx="172" cy="52" r="1.4" fill="#F5F6F8" style="animation-delay:.7s"/>
  <circle class="dz-dot" cx="150" cy="168" r="1.1" fill="#F5F6F8" style="animation-delay:1.3s"/>
  <circle class="dz-dot" cx="36" cy="150" r="1.3" fill="#F5F6F8" style="animation-delay:.3s"/>
  <g class="dz-orbit">
    <ellipse cx="100" cy="100" rx="88" ry="88" fill="none" stroke="#48E0CB" stroke-opacity="0.35"
             stroke-width="1.2" stroke-dasharray="3 7"/>
    <circle cx="188" cy="100" r="3.2" fill="#48E0CB"/>
  </g>
  <g class="dz-craft">
    <g>
      <line class="dz-band" x1="76" y1="56" x2="60" y2="14" stroke="#48E0CB" stroke-width="2.2" stroke-linecap="round"/>
      <line class="dz-band" x1="86" y1="56" x2="77" y2="12" stroke="#48E0CB" stroke-width="2.2" stroke-linecap="round"/>
      <line class="dz-band" x1="95" y1="56" x2="92" y2="10" stroke="#48E0CB" stroke-width="2.2" stroke-linecap="round"/>
      <line class="dz-band" x1="105" y1="56" x2="108" y2="10" stroke="#48E0CB" stroke-width="2.2" stroke-linecap="round"/>
      <line class="dz-band" x1="114" y1="56" x2="123" y2="12" stroke="#48E0CB" stroke-width="2.2" stroke-linecap="round"/>
      <line class="dz-band" x1="124" y1="56" x2="140" y2="14" stroke="#48E0CB" stroke-width="2.2" stroke-linecap="round"/>
    </g>
    <polygon points="52,60 148,60 120,128 80,128" fill="#0C1421" stroke="#F5F6F8" stroke-width="3" stroke-linejoin="round"/>
    <polygon points="64,68 136,68 116,128 84,128" fill="#101B2C" stroke="#F5F6F8" stroke-opacity="0.8" stroke-width="2.4" stroke-linejoin="round"/>
    <polygon points="76,76 124,76 111,128 89,128" fill="#16233A" stroke="#F5F6F8" stroke-opacity="0.65" stroke-width="2" stroke-linejoin="round"/>
    <ellipse cx="100" cy="78" rx="15" ry="3.4" fill="#48E0CB" fill-opacity="0.55"/>
    <rect x="84" y="128" width="32" height="22" rx="3" fill="#131D2E" stroke="#F5F6F8" stroke-width="2.4"/>
    <rect x="118" y="132" width="40" height="9" rx="2" fill="#48E0CB"/>
    <line x1="131" y1="132" x2="131" y2="141" stroke="#0C1421" stroke-width="1.4"/>
    <line x1="144" y1="132" x2="144" y2="141" stroke="#0C1421" stroke-width="1.4"/>
  </g>
</svg>
"""


def loader_html(mensaje, detalle=""):
    return (
        f'<div class="dz-loader">{LOADER_SVG}'
        f'<p class="dz-loader-text">{mensaje}</p>'
        f'<p class="dz-loader-sub">{detalle}</p>'
        '<p class="dz-loader-note">Simplified drawing of SPHEREx, made by the team with SI assistance</p>'
        "</div>"
    )


@contextmanager
def cargando(mensaje, detalle=""):
    """Show the animated SPHEREx scene while a slow step runs, then remove it."""
    lugar = st.empty()
    lugar.markdown(loader_html(mensaje, detalle), unsafe_allow_html=True)
    try:
        yield
    finally:
        lugar.empty()


def estado(texto, revisado):
    """Review state as a label with a shape, not colour alone."""
    clase = "done" if revisado else "waiting"
    return f'<span class="dz-state {clase}"><i></i>{texto}</span>'


def navegacion():
    """Top menu with only the pages meant for visitors. Internal pages stay reachable by URL."""
    try:
        izquierda, derecha, _ = st.columns([1.1, 2, 5])
        izquierda.page_link("app.py", label="Viewer")
        derecha.page_link("pages/3_Findings.py", label="Findings board")
    except Exception:
        # page_link needs the multipage context; fall back to plain links
        st.markdown("[Viewer](/) · [Findings board](/Findings)")


def aplicar_tema():
    """Inject the CSS. Call once, right after st.set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)


# Mission facts shown in the hero. Source: https://science.nasa.gov/mission/spherex/
FACTS = [
    ("102 colours", "of infrared light"),
    ("0.75 – 5 µm", "wavelength range"),
    ("Whole sky", "mapped every six months"),
]


HERO_3D = True          # False shows the plain CSS hero (no WebGL, no external script)
HERO_3D_HEIGHT = 340    # pixels of the embedded scene

# 3D hero. The text is normal HTML; behind it, a WebGL scene drawn with three.js
# (https://threejs.org, MIT licence) shows a rotating planet, stars with depth and a
# simple model of SPHEREx. If WebGL or the script is not available, the CSS planet
# and stars stay visible, so the hero never appears empty.
HERO_3D_TEMPLATE = """
<!DOCTYPE html><html><head><meta charset="utf-8">
__CSS__
<style>
  html, body { margin: 0; height: 100%; background: transparent; overflow: hidden; }
  .dz-hero { height: 100%; box-sizing: border-box; margin: 0; }
  #dz-scene { position: absolute; inset: 0; width: 100%; height: 100%; display: block;
              opacity: 0; transition: opacity 0.8s ease; z-index: 1; }
  .dz-3d-on #dz-scene { opacity: 1; }
  .dz-3d-on .dz-stars, .dz-3d-on .dz-planet { display: none; }
  @media (max-width: 640px) { .dz-sub { display: none; } .dz-facts { gap: 0.4rem 1.4rem; }
    .dz-kicker { font-size: 0.62rem; letter-spacing: 0.1em; } }
</style></head>
<body>
<div class="dz-hero" id="dz-hero">
  <div class="dz-stars"></div>
  <div class="dz-planet"></div>
  <canvas id="dz-scene"></canvas>
  <div class="dz-hero-inner">
    <div class="dz-kicker">Team DecZero · NASA Space Apps Challenge 2026</div>
    <div class="dz-brand">__LOGO__<div class="dz-title">__NAME__</div></div>
    <p class="dz-tagline">__TAGLINE__</p>
    <p class="dz-sub">Real infrared images from NASA's SPHEREx space telescope,
    for any position in the sky, in time order.</p>
  </div>
  <div class="dz-facts">__FACTS__</div>
  <p class="dz-si">Planet and SPHEREx illustration made by the team with SI assistance; not an official image</p>
</div>
<script type="module">
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js";

const hero = document.getElementById("dz-hero");
const canvas = document.getElementById("dz-scene");
const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 2, 0.1, 400);
camera.position.set(0, 0, 10);

// ---- stars with depth
const starCount = 1500, starPos = new Float32Array(starCount * 3);
for (let i = 0; i < starCount; i++) {
  starPos[3 * i] = (Math.random() - 0.5) * 60;
  starPos[3 * i + 1] = (Math.random() - 0.35) * 22;
  starPos[3 * i + 2] = -4 - Math.random() * 50;
}
const starGeo = new THREE.BufferGeometry();
starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
  color: 0xdfeeff, size: 0.11, sizeAttenuation: true, transparent: true, opacity: 0.9 }));
scene.add(stars);

// ---- planet: procedural surface, lit from behind the horizon
const R = 30, horizonY = -1.25;
const planet = new THREE.Mesh(
  new THREE.SphereGeometry(R, 128, 96),
  new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      varying vec3 vPos; varying vec3 vNormalW; varying vec3 vViewDir;
      void main() {
        vPos = position;
        vec4 world = modelMatrix * vec4(position, 1.0);
        vNormalW = normalize(mat3(modelMatrix) * normal);
        vViewDir = normalize(cameraPosition - world.xyz);
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: `
      varying vec3 vPos; varying vec3 vNormalW; varying vec3 vViewDir;
      float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float noise(vec3 p) {
        vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(hash(i), hash(i + vec3(1,0,0)), f.x),
                       mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
                   mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
                       mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
      }
      float fbm(vec3 p) { float v = 0.0, a = 0.5;
        for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; } return v; }
      void main() {
        float n = fbm(vPos * 0.55);
        vec3 deep = vec3(0.027, 0.055, 0.105), mid = vec3(0.055, 0.150, 0.300);
        vec3 col = mix(deep, mid, smoothstep(0.35, 0.75, n));
        col += vec3(0.28, 0.88, 0.80) * 0.10 * smoothstep(0.62, 0.9, n);   // faint teal veins
        vec3 sun = normalize(vec3(0.0, 0.55, -1.0));                        // light from behind the limb
        float lit = clamp(dot(vNormalW, sun) * 1.6 + 0.25, 0.0, 1.0);
        col *= 0.35 + 0.9 * lit;
        float rim = pow(1.0 - clamp(dot(vNormalW, vViewDir), 0.0, 1.0), 7.0);
        col += vec3(0.28, 0.88, 0.80) * rim * 0.55 + vec3(0.18, 0.50, 0.93) * rim * 0.35;
        gl_FragColor = vec4(col, 1.0);
      }`
  }));
planet.position.set(0, horizonY - R, 0);
planet.rotation.z = 0.35;
scene.add(planet);

// ---- atmosphere halo
const halo = new THREE.Mesh(
  new THREE.SphereGeometry(R * 1.018, 96, 64),
  new THREE.ShaderMaterial({
    side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    vertexShader: `varying vec3 vN; void main() { vN = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec3 vN; void main() {
      float i = pow(clamp(0.62 - dot(vN, vec3(0.0, 0.0, 1.0)), 0.0, 1.0), 4.5);
      gl_FragColor = vec4(mix(vec3(0.18, 0.50, 0.93), vec3(0.28, 0.88, 0.80), 0.5) * i * 2.4, i); }`
  }));
halo.position.copy(planet.position);
scene.add(halo);

// ---- SPHEREx: three nested cone shields, body and solar panel, in line-art style
const craft = new THREE.Group();
const dark = new THREE.MeshStandardMaterial({ color: 0x1c2f4f, emissive: 0x0b1626, metalness: 0.3, roughness: 0.5, side: THREE.DoubleSide });
const ringMat = new THREE.MeshBasicMaterial({ color: 0xf5f6f8 });
function ring(radius, y) {
  const r = new THREE.Mesh(new THREE.TorusGeometry(radius, 0.022, 8, 64), ringMat);
  r.rotation.x = Math.PI / 2; r.position.y = y; craft.add(r);
}
const white = new THREE.LineBasicMaterial({ color: 0xf5f6f8 });
function part(geometry, material, x, y, z) {
  const mesh = new THREE.Mesh(geometry, material); mesh.position.set(x, y, z); craft.add(mesh);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 25), white);
  edges.position.copy(mesh.position); craft.add(edges); return mesh;
}
[[1.00, 0.42, 1.30], [0.82, 0.36, 1.18], [0.64, 0.30, 1.06]].forEach(([top, bottom, h]) => {
  part(new THREE.CylinderGeometry(top, bottom, h, 48, 1, true), dark, 0, h / 2, 0);
  ring(top, h);                                       // bright rim of each shield
});
const mirror = new THREE.Mesh(new THREE.CircleGeometry(0.34, 40),
  new THREE.MeshBasicMaterial({ color: 0x48e0cb, transparent: true, opacity: 0.85, side: THREE.DoubleSide }));
mirror.rotation.x = -Math.PI / 2; mirror.position.y = 0.42; craft.add(mirror);
part(new THREE.BoxGeometry(0.62, 0.46, 0.62), dark, 0, -0.23, 0);
part(new THREE.BoxGeometry(1.0, 0.05, 0.56),
  new THREE.MeshStandardMaterial({ color: 0x48e0cb, emissive: 0x1f7a6e, metalness: 0.2, roughness: 0.4 }), 0.82, -0.2, 0);
craft.rotation.set(0.35, 0.4, -0.55);
scene.add(craft);

scene.add(new THREE.AmbientLight(0x8fa8d0, 0.9));
const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(-4, 6, 8); scene.add(key);
const teal = new THREE.PointLight(0x48e0cb, 30, 40); teal.position.set(6, -1, 4); scene.add(teal);

// ---- layout, pointer and animation
let wide = true;
function resize() {
  const w = hero.clientWidth, h = hero.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  wide = w / h > 1.9;
  craft.scale.setScalar(wide ? 0.78 : 0.42);
}
window.addEventListener("resize", resize); resize();

const pointer = { x: 0, y: 0 };
window.addEventListener("pointermove", (e) => {
  pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
  pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
});

function frame(ms) {
  const t = ms / 1000;
  planet.material.uniforms.uTime.value = t;
  planet.rotation.y = t * 0.012;                       // the planet turns slowly
  stars.rotation.z = t * 0.004;
  const half = Math.tan(THREE.MathUtils.degToRad(17.5)) * 10 * camera.aspect;
  const baseX = wide ? half * 0.6 : half * 0.42;
  craft.position.set(baseX + Math.sin(t * 0.25) * 0.3, (wide ? 0.35 : 1.35) + Math.sin(t * 0.6) * 0.1, 1.2);
  craft.rotation.y = 0.4 + t * 0.22;                   // SPHEREx turns on its axis
  camera.position.x += (pointer.x * 0.7 - camera.position.x) * 0.04;
  camera.position.y += (-pointer.y * 0.35 - camera.position.y) * 0.04;
  camera.lookAt(0, 0, 0);
  renderer.render(scene, camera);
  if (!still) requestAnimationFrame(frame);
}
frame(0);
document.body.classList.add("dz-3d-on");               // only now hide the CSS fallback
if (!still) requestAnimationFrame(frame);
</script>
</body></html>
"""


def _embed(html, height):
    """Embed an HTML document in its own frame, with whichever function this Streamlit has."""
    if hasattr(st, "iframe"):          # current Streamlit
        st.iframe(html, height=height)
    else:                              # older Streamlit
        import streamlit.components.v1 as components
        components.html(html, height=height, scrolling=False)


def _facts_html():
    return "".join(
        f'<div class="dz-fact"><b>{big}</b><span>{small}</span></div>' for big, small in FACTS
    )


def portada():
    """Hero: who we are, the name of the project and one line that says what it does."""
    if HERO_3D:
        html = (
            HERO_3D_TEMPLATE
            .replace("__CSS__", CSS)
            .replace("__LOGO__", LOGO_SVG)
            .replace("__NAME__", PROJECT_NAME)
            .replace("__TAGLINE__", TAGLINE)
            .replace("__FACTS__", _facts_html())
        )
        _embed(html, HERO_3D_HEIGHT)
        return
    facts = _facts_html()
    st.markdown(
        f"""
        <div class="dz-hero">
          <div class="dz-stars"></div>
          <div class="dz-planet"></div>
          <div class="dz-hero-inner">
            <div class="dz-kicker">Team DecZero · NASA Space Apps Challenge 2026</div>
            <div class="dz-brand">{LOGO_SVG}<div class="dz-title">{PROJECT_NAME}</div></div>
            <p class="dz-tagline">{TAGLINE}</p>
            <p class="dz-sub">Real infrared images from NASA's SPHEREx space telescope,
            for any position in the sky, in time order.</p>
          </div>
          <div class="dz-facts">{facts}</div>
          <p class="dz-si">Planet illustration made by the team with SI assistance; not an official image</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def seccion(numero, titulo):
    """Numbered section label, for example: 01 EXPLORE."""
    st.markdown(
        f'<div class="dz-section"><i>{numero:02d}</i><b>{titulo}</b></div>',
        unsafe_allow_html=True,
    )


HELP = [
    ("What am I looking at?",
     "Real pictures of the same small patch of sky, taken on different dates by "
     "NASA's SPHEREx space telescope in infrared light."),
    ("What should I look for?",
     "In the aligned view, a dot that changes place between dates may be something nearby "
     "moving across the sky. A dot that gets brighter or fainter may be a variable star."),
    ("What can fool me?",
     "A dot that shows up in only one picture is usually a cosmic ray or a bad pixel. "
     "Each picture is also taken in a slightly different infrared colour, so brightness "
     "can change for that reason alone."),
]


def ayuda():
    """Three short help cards, side by side on wide screens and stacked on phones."""
    for column, (title, text) in zip(st.columns(len(HELP)), HELP):
        column.markdown(
            f'<div class="dz-card"><h4>{title}</h4><p>{text}</p></div>',
            unsafe_allow_html=True,
        )


def pie():
    """Footer with data credits."""
    st.markdown(
        """
        <div class="dz-footer">
          HAWAPACHA, by team DecZero (Ecuador).
          Data: SPHEREx spectral images, NASA/IPAC Infrared Science Archive (IRSA),
          read from the public IRSA copy on AWS Open Data.
          Mission facts: <a href="https://science.nasa.gov/mission/spherex/">science.nasa.gov/mission/spherex</a>.
          This is a student project for the NASA Space Apps Challenge; it is not a NASA product.
          Code: <a href="https://github.com/JMVP0016/DECZERO">github.com/JMVP0016/DECZERO</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
