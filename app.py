# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Minimum version (milestone H1): any coordinate -> real SPHEREx images in time order."""

import io
import re

import astropy.units as u
import numpy as np
import streamlit as st
from astropy.coordinates import SkyCoord
from astropy.time import Time
from PIL import Image, ImageDraw

import cache_local
import datos
import hallazgos
import proceso
import tema

MAX_IMAGES = 24      # live-mode cap agreed after measurement M0
FOV_ARCMIN = 10.0    # side of each cutout
GRID_PIXELS = 200    # aligned grid: 200 px of 3 arcsec = 10 arcmin
DISPLAY_PIXELS = 480
BANDS = ["D1", "D2", "D3", "D4", "D5", "D6"]

MODE_SINGLE = "Single images"
MODE_STACKED = "Stacked by epoch"

# The five challenge targets. Positions are approximate, moved to about 2026
# with catalogue proper motions; they will be replaced by objetivos.yaml (David).
TARGETS = [
    {"name": "Barnard's Star", "folder": "barnard", "ra": 269.4463, "dec": 4.7679, "band": "D2"},
    {"name": "WISE 0855", "folder": "wise_0855", "ra": 133.7590, "dec": -7.2421, "band": "D6"},
    {"name": "Epsilon Indi B", "folder": "epsilon_indi_b", "ra": 331.0960, "dec": -56.8013, "band": "D2"},
    {"name": "RW Aurigae", "folder": "rw_aurigae", "ra": 76.9564, "dec": 30.4014, "band": "D2"},
    {"name": "R Draconis", "folder": "r_draconis", "ra": 248.1675, "dec": 66.7550, "band": "D2"},
]

st.set_page_config(page_title="Hawapacha · SPHEREx sky viewer", layout="wide")
tema.aplicar_tema()


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


def mjd_to_text(mjd, with_time=False):
    return Time(mjd, format="mjd").strftime("%Y-%m-%d %H:%M UTC" if with_time else "%Y-%m-%d")


def limits(images):
    """One contrast range for the whole sequence, so frames can be compared."""
    values = np.concatenate([image[np.isfinite(image)].ravel() for image in images])
    if values.size == 0:
        return 0.0, 1.0
    low, high = np.percentile(values, [1.0, 99.5])
    if high <= low:
        high = low + 1.0
    return low, high


def to_picture(image, low, high):
    """2D array -> greyscale picture. FITS row 0 is the bottom row, so it is flipped."""
    scaled = np.clip((image - low) / (high - low), 0.0, 1.0)
    scaled = np.nan_to_num(scaled, nan=0.0)
    pixels = (255 * np.flipud(scaled)).astype(np.uint8)
    return Image.fromarray(pixels).resize((DISPLAY_PIXELS, DISPLAY_PIXELS), Image.NEAREST)


def single_frames(cutouts):
    """Raw images, exactly as they arrive: only the sky level is subtracted."""
    images = []
    for cutout in cutouts:
        image = cutout["imagen"].astype(float)
        images.append(image - np.nanmedian(image))
    low, high = limits(images)
    frames = []
    for cutout, image in zip(cutouts, images):
        frames.append({
            "picture": to_picture(image, low, high),
            "label": mjd_to_text(cutout["fecha"], with_time=True),
            "details": (
                f"**Detector:** {cutout['detector']} · "
                f"**Wavelength at this position:** {cutout['longitud_onda']:.2f} µm · "
                f"**Flagged pixels:** {cutout['porcentaje_marcado']:.1f} % · "
                f"**Data version:** {cutout['version']}"
            ),
        })
    return frames


def stacked_frames(cutouts, ra, dec):
    """Images aligned north up and combined (median) within each observing epoch."""
    grid, shape = proceso.crear_rejilla_norte(ra, dec, tamano_pix=GRID_PIXELS)
    aligned, kept = proceso.reproyectar(
        [c["imagen"] for c in cutouts],
        [c["wcs"] for c in cutouts],
        grid, shape,
        mascaras=[c["mascara"] for c in cutouts],
    )
    by_epoch = {}
    for image, index in zip(aligned, kept):
        by_epoch.setdefault(cutouts[index]["epoca"], []).append((image, cutouts[index]))
    stacks = []
    for epoch in sorted(by_epoch):
        members = by_epoch[epoch]
        with np.errstate(all="ignore"):
            stack = proceso.apilar([image for image, _ in members])
        dates = [c["fecha"] for _, c in members]
        waves = [c["longitud_onda"] for _, c in members]
        stacks.append((stack, dates, waves, len(members)))
    low, high = limits([stack for stack, _, _, _ in stacks])
    frames = []
    for stack, dates, waves, count in stacks:
        frames.append({
            "picture": to_picture(stack, low, high),
            "label": f"{mjd_to_text(min(dates))} to {mjd_to_text(max(dates))}",
            "details": (
                f"**Images combined:** {count} · "
                f"**Wavelengths mixed:** {min(waves):.2f} to {max(waves):.2f} µm · "
                f"**Orientation:** north up, east left"
            ),
        })
    return frames, len(cutouts) - len(kept)


def animation(frames):
    """Animated GIF of the sequence, with the date written on every frame."""
    pictures = []
    for frame in frames:
        picture = frame["picture"].convert("RGB")
        draw = ImageDraw.Draw(picture)
        draw.rectangle([0, 0, DISPLAY_PIXELS, 18], fill=(0, 0, 0))
        draw.text((6, 4), frame["label"], fill=(255, 255, 255))
        pictures.append(picture)
    buffer = io.BytesIO()
    pictures[0].save(
        buffer, format="GIF", save_all=True, append_images=pictures[1:],
        duration=600, loop=0,
    )
    return buffer.getvalue()


def stored_target(ra, dec, band):
    """The challenge target at this position (within 3 arcmin) and band, if any."""
    here = SkyCoord(ra * u.deg, dec * u.deg)
    for target in TARGETS:
        there = SkyCoord(target["ra"] * u.deg, target["dec"] * u.deg)
        if target["band"] == band and here.separation(there).arcmin <= 3.0:
            return target
    return None


def load_target(target):
    """One of the five targets: stored images if we have them, live download otherwise."""
    cutouts = cache_local.leer_objetivo(target["folder"], target["band"])
    if not cutouts:
        load(target["ra"], target["dec"], target["band"])
        return
    st.session_state["error"] = None
    st.session_state["result"] = {
        "ra": target["ra"], "dec": target["dec"], "band": target["band"],
        "available": len(cutouts), "cutouts": cutouts, "stored": target["name"],
    }


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


tema.portada()

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

st.caption("Or try one of the five targets of the challenge:")
clicked = None
for column, target in zip(st.columns(len(TARGETS)), TARGETS):
    if column.button(target["name"], use_container_width=True):
        clicked = target

first_visit_with_link = bool(start_text) and "result" not in st.session_state

if clicked:
    st.query_params.update({
        "ra": f"{clicked['ra']:.5f}", "dec": f"{clicked['dec']:.5f}", "band": clicked["band"],
    })
    load_target(clicked)
elif submitted or first_visit_with_link:
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
        target = stored_target(ra, dec, band)
        if target:
            load_target(target)   # a direct link to a target loads instantly
        else:
            load(ra, dec, band)

if st.session_state.get("error"):
    st.error(st.session_state["error"])

result = st.session_state.get("result")
if result:
    cutouts = result["cutouts"]
    if result.get("stored"):
        st.success(
            f"{result['stored']}: {len(cutouts)} images stored by the team, "
            f"detector {result['band']}, around RA {result['ra']:.5f}°, Dec {result['dec']:.5f}°."
        )
    else:
        st.success(
            f"Showing {len(cutouts)} of {result['available']} images at "
            f"RA {result['ra']:.5f}°, Dec {result['dec']:.5f}°, detector {result['band']}."
        )

    mode = st.radio("View", [MODE_SINGLE, MODE_STACKED], horizontal=True)
    if mode == MODE_STACKED:
        frames, dropped = stacked_frames(cutouts, result["ra"], result["dec"])
        if dropped:
            st.warning(f"{dropped} images could not be aligned and were left out.")
    else:
        frames = single_frames(cutouts)

    if len(frames) > 1:
        index = st.slider("Frame", 1, len(frames), 1) - 1
    else:
        index = 0
    frame = frames[index]

    picture_column, movie_column = st.columns(2)
    picture_column.image(frame["picture"], caption=f"Frame {index + 1} of {len(frames)}")
    picture_column.metric("Date", frame["label"])
    picture_column.write(frame["details"])

    if len(frames) > 1:
        gif = animation(frames)
        movie_column.image(gif, caption="The whole sequence, in time order")
        movie_column.download_button(
            "Download animation (GIF)", gif, file_name="spherex_sequence.gif", mime="image/gif"
        )

    if mode == MODE_STACKED:
        st.info(
            "Each frame is the median of all images taken in one observing epoch, "
            "aligned so that **north is up and east is left**. Something that changes "
            "position between frames is moving across the sky. Note that the images "
            "combined in a frame were taken at **different wavelengths** within the detector band. "
            "A black disc in the middle of a very bright star is not real: the star saturated "
            "the detector there, and those pixels were removed."
        )
    else:
        st.info(
            "These are raw images, exactly as they arrive: they are **not aligned**, "
            "so the sky can look rotated from one image to the next. Each image is also "
            "taken at a **different wavelength**, so a change in brightness between "
            "images is not by itself a change over time."
        )

    hallazgos.report_form(result["ra"], result["dec"], result["band"], mode, frame["label"])

    st.caption(
        f"Field: {FOV_ARCMIN:.0f} arcmin across. Dates in this sequence: "
        f"{mjd_to_text(cutouts[0]['fecha'])} to {mjd_to_text(cutouts[-1]['fecha'])}. "
        "Data: NASA/IPAC IRSA, SPHEREx."
    )

st.write("")
tema.ayuda()
tema.pie()
