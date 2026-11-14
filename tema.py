# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Look of the app: CSS, header, help texts and footer. All visible text in English."""

import streamlit as st

PROJECT_NAME = "HAWAPACHA"
TAGLINE = "Type a spot in the sky. Watch it change."      # to be confirmed by the team

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
.block-container { padding-top: 2.2rem; max-width: 1150px; }

/* header */
.dz-hero { padding: 0.4rem 0 1.1rem 0; border-bottom: 1px solid rgba(232,236,244,0.12); margin-bottom: 1.2rem; }
.dz-brand { display: flex; align-items: center; gap: 1.1rem; margin: 0.35rem 0 0.5rem 0; }
.dz-brand svg { width: clamp(64px, 9vw, 96px); height: auto; flex-shrink: 0; }
.dz-kicker { color: #48E0CB; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; }
.dz-title { font-size: clamp(2.2rem, 6vw, 4rem); font-weight: 800; line-height: 1; margin: 0; color: #F5F6F8; letter-spacing: 0.01em; }
.dz-tagline { font-size: 1.15rem; color: #AEB8CC; margin: 0; }

/* help cards */
.dz-card { background: #131D2E; border: 1px solid rgba(232,236,244,0.10); border-radius: 12px; padding: 0.9rem 1rem; height: 100%; }
.dz-card h4 { font-family: 'Montserrat', sans-serif; font-size: 1rem; margin: 0 0 0.35rem 0; color: #48E0CB; }
.dz-card p { font-size: 0.92rem; line-height: 1.45; margin: 0; color: #C9D1E0; }

/* rounded images and buttons */
[data-testid="stImage"] img { border-radius: 10px; }
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
<svg viewBox="0 0 120 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Hawapacha logo">
  <circle cx="60" cy="50" r="40" fill="none" stroke="#F5F6F8" stroke-width="6"/>
  <circle cx="44" cy="32" r="6" fill="#48E0CB"/>
  <circle cx="76" cy="68" r="6" fill="#48E0CB"/>
  <rect x="8" y="47" width="104" height="6" rx="2" fill="#48E0CB"/>
</svg>
"""


def aplicar_tema():
    """Inject the CSS. Call once, right after st.set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)


def portada():
    """Header: who we are, the name of the project and one line that says what it does."""
    st.markdown(
        f"""
        <div class="dz-hero">
          <div class="dz-kicker">Team DecZero · NASA Space Apps Challenge 2026</div>
          <div class="dz-brand">{LOGO_SVG}<div class="dz-title">{PROJECT_NAME}</div></div>
          <p class="dz-tagline">{TAGLINE} Real infrared images from NASA's SPHEREx
          space telescope, for any position, in time order.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


HELP = [
    ("What am I looking at?",
     "Real pictures of the same small patch of sky, taken on different dates by "
     "NASA's SPHEREx space telescope in infrared light."),
    ("What should I look for?",
     "A dot that changes place between dates is something nearby moving across the sky. "
     "A dot that gets brighter or fainter may be a variable star."),
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
          Data: SPHEREx spectral images, NASA/IPAC Infrared Science Archive (IRSA),
          read from the public IRSA copy on AWS Open Data.
          This is a student project for the NASA Space Apps Challenge; it is not a NASA product.
          Code: <a href="https://github.com/JMVP0016/DECZERO">github.com/JMVP0016/DECZERO</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
