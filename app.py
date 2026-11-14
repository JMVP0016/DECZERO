# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Minimum version (milestone H1): any coordinate -> real SPHEREx images in time order."""

import re

import astropy.units as u
import numpy as np
import streamlit as st
from astropy.coordinates import SkyCoord
from astropy.time import Time
from PIL import Image

import datos

MAX_IMAGES = 24      # live-mode cap agreed after measurement M0
FOV_ARCMIN = 6.0     # side of each cutout
DISPLAY_PIXELS = 480
BANDS = ["D1", "D2", "D3", "D4", "D5", "D6"]

st.set_page_config(page_title="DecZero · SPHEREx viewer", layout="wide")


def parse_coordinate(text):
    """Accept '150.0 +2.2' (degrees) or '08h55m10.8s -7d14m42.5s'. Return (ra, dec) in degrees."""
    text = text.strip()
    if not text:
        raise ValueError("empty")
    numbers = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)[\s,]+([+-]?\d+(?:\.\d+)?)", text)
    if numbers:
        ra, dec = float(numbers.group(1)), float(numbers.group(2))
    else:
        coord = SkyCoord(text, unit=(u.hourangle, u.deg), frame="icrs")
        ra, dec = float(coord.ra.deg), float(coord.dec.deg)
    if not (0.0 <= ra <= 360.0 and -90.0 <= dec <= 90.0):
        raise ValueError("out of range")
    return ra, dec


def display_limits(cutouts):
    """One contrast range for the whole sequence, so frames can be compared."""
    values = []
    for cutout in cutouts:
        image = cutout["imagen"].astype(float)
        values.append((image - np.nanmedian(image)).ravel())
    values = np.concatenate(values)
    values = values[np.isfinite(values)]
    low, high = np.percentile(values, [1.0, 99.5])
    if high <= low:
        high = low + 1.0
    return low, high


def to_picture(cutout, low, high):
    """Raw cutout -> greyscale picture. Only the sky level is subtracted; nothing is aligned."""
    image = cutout["imagen"].astype(float)
    image = image - np.nanmedian(image)
    scaled = np.clip((image - low) / (high - low), 0.0, 1.0)
    scaled = np.nan_to_num(scaled, nan=0.0)
    pixels = (255 * np.flipud(scaled)).astype(np.uint8)  # FITS row 0 is the bottom row
    return Image.fromarray(pixels).resize((DISPLAY_PIXELS, DISPLAY_PIXELS), Image.NEAREST)


def load(ra, dec, band):
    """Run the search and the downloads, and keep the outcome in the session."""
    st.session_state["result"] = None
    try:
        with st.spinner("Asking the NASA archive (IRSA) which images cover this position..."):
            exposures = datos.buscar(ra, dec, banda=band)
    except Exception as error:
        st.session_state["error"] = (
            "The NASA archive (IRSA) is not responding right now. "
            f"Please try again in a few minutes. Detail: {error}"
        )
        return
    if not exposures:
        st.session_state["error"] = (
            f"SPHEREx has no images of this position in detector {band} yet. "
            "Try another detector or another position."
        )
        return
    with st.spinner(
        f"Found {len(exposures)} images. Downloading up to {MAX_IMAGES}; "
        "this can take a few minutes when the archive is busy..."
    ):
        cutouts = datos.obtener(ra, dec, fov=FOV_ARCMIN, banda=band, max_n=MAX_IMAGES)
    if not cutouts:
        st.session_state["error"] = (
            "The images exist, but the NASA archive (IRSA) rejected every download. "
            "It is probably overloaded; please try again in a few minutes."
        )
        return
    st.session_state["error"] = None
    st.session_state["result"] = {
        "ra": ra, "dec": dec, "band": band,
        "available": len(exposures), "cutouts": cutouts,
    }


st.title("SPHEREx sky viewer")
st.caption(
    "Type any sky position and see the real images NASA's SPHEREx telescope "
    "took of it, in time order. Team DecZero · NASA Space Apps Challenge 2026."
)

params = st.query_params
start_text = f"{params['ra']} {params['dec']}" if "ra" in params and "dec" in params else ""
start_band = params.get("band", "D2")

with st.form("search"):
    left, right = st.columns([3, 1])
    text = left.text_input(
        "Sky position (RA and Dec)",
        value=start_text,
        placeholder="210.80227 54.34895   or   08h55m10.831s -7d14m42.53s",
    )
    band = right.selectbox(
        "Detector (infrared band)",
        BANDS,
        index=BANDS.index(start_band) if start_band in BANDS else 1,
        help="D1 is the bluest (0.75 µm) and D6 the reddest (5 µm).",
    )
    submitted = st.form_submit_button("Show images", type="primary")

first_visit_with_link = bool(start_text) and "result" not in st.session_state

if submitted or first_visit_with_link:
    try:
        ra, dec = parse_coordinate(text)
    except Exception:
        st.session_state["result"] = None
        st.session_state["error"] = (
            "That is not a valid sky position. Write RA and Dec in degrees "
            "(for example 210.80227 54.34895) or as 08h55m10.8s -7d14m42.5s. "
            "Dec must be between -90 and +90."
        )
    else:
        st.query_params.update({"ra": f"{ra:.5f}", "dec": f"{dec:.5f}", "band": band})
        load(ra, dec, band)

if st.session_state.get("error"):
    st.error(st.session_state["error"])

result = st.session_state.get("result")
if result:
    cutouts = result["cutouts"]
    st.success(
        f"Showing {len(cutouts)} of {result['available']} images at "
        f"RA {result['ra']:.5f}°, Dec {result['dec']:.5f}°, detector {result['band']}."
    )

    if len(cutouts) > 1:
        index = st.slider("Image", 1, len(cutouts), 1) - 1
    else:
        index = 0
    cutout = cutouts[index]
    low, high = display_limits(cutouts)

    picture_column, text_column = st.columns([1, 1])
    picture_column.image(to_picture(cutout, low, high))

    date = Time(cutout["fecha"], format="mjd").strftime("%Y-%m-%d %H:%M UTC")
    text_column.metric("Date", date)
    text_column.write(
        f"**Detector:** {cutout['detector']} · "
        f"**Wavelength at this position:** {cutout['longitud_onda']:.2f} µm"
    )
    text_column.write(
        f"**Flagged pixels:** {cutout['porcentaje_marcado']:.1f} % · "
        f"**Data version:** {cutout['version']} · "
        f"**Field:** {FOV_ARCMIN:.0f} arcmin"
    )
    text_column.info(
        "These are raw images, exactly as they arrive: they are **not aligned**, "
        "so the sky can look rotated from one image to the next. Each image is also "
        "taken at a **different wavelength**, so a change in brightness between "
        "images is not by itself a change over time."
    )

    dates = [Time(c["fecha"], format="mjd").strftime("%Y-%m-%d") for c in cutouts]
    st.caption(f"Dates in this sequence: {dates[0]} to {dates[-1]}. Data: NASA/IPAC IRSA, SPHEREx.")
