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

MODE_STACKED = "Aligned (best for spotting motion)"
MODE_SINGLE = "Raw single images"
MIN_IMAGES_PER_EPOCH = 3            # an aligned frame made of fewer images is too noisy to trust
SPEEDS = {"Slow": 900, "Medium": 450, "Fast": 200}   # milliseconds per frame
RING_COLOUR = (251, 191, 36)        # amber #FBBF24: the position that was asked for
NO_DATA_COLOUR = (52, 32, 78)       # purple: no data here (not the same as dark sky)
PIXEL_ARCSEC = 6.15                 # SPHEREx pixel
GRID_ARCSEC = 3.0                   # pixel of the aligned grid

# The five challenge targets. Positions are approximate, moved to about 2026
# with catalogue proper motions; they will be replaced by objetivos.yaml (David).
TARGETS = [
    {"name": "Barnard's Star", "folder": "barnard", "ra": 269.4463, "dec": 4.7679, "band": "D2"},
    {"name": "WISE 0855", "folder": "wise_0855", "ra": 133.7590, "dec": -7.2421, "band": "D6"},
    {"name": "Epsilon Indi B", "folder": "epsilon_indi_b", "ra": 331.0960, "dec": -56.8013, "band": "D2"},
    {"name": "RW Aurigae", "folder": "rw_aurigae", "ra": 76.9564, "dec": 30.4014, "band": "D2"},
    {"name": "R Draconis", "folder": "r_draconis", "ra": 248.1675, "dec": 66.7550, "band": "D2"},
]

st.set_page_config(page_title="HAWAPACHA · SPHEREx sky viewer", page_icon=tema.ICON, layout="wide")
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


def to_picture(image, low, high, mark=None, label="", scale_arcsec=None, compass=False):
    """
    2D array -> colour picture of DISPLAY_PIXELS x DISPLAY_PIXELS.
      - A non-square image is padded to a square, never stretched.
      - Pixels without data are purple, so they are not mistaken for dark sky.
      - mark = (x, y) in pixels of the input image draws the amber ring there.
      - label is written on a strip at the top; scale_arcsec (size of one input
        pixel) adds a 1-arcmin bar; compass adds the orientation note.
    """
    height, width = image.shape
    side = max(height, width)
    pad_y, pad_x = (side - height) // 2, (side - width) // 2
    square = np.full((side, side), np.nan)
    square[pad_y:pad_y + height, pad_x:pad_x + width] = image

    scaled = np.clip((square - low) / (high - low), 0.0, 1.0)
    scaled = np.arcsinh(10.0 * scaled) / np.arcsinh(10.0)      # brings out faint sources
    grey = (255 * np.nan_to_num(scaled, nan=0.0)).astype(np.uint8)
    rgb = np.stack([grey, grey, grey], axis=-1)
    rgb[~np.isfinite(square)] = NO_DATA_COLOUR
    rgb = np.flipud(rgb)                                        # FITS row 0 is the bottom row
    picture = Image.fromarray(rgb, "RGB").resize((DISPLAY_PIXELS, DISPLAY_PIXELS), Image.NEAREST)

    zoom = DISPLAY_PIXELS / side
    draw = ImageDraw.Draw(picture)
    if mark is not None:
        x = (mark[0] + pad_x + 0.5) * zoom
        y = (side - (mark[1] + pad_y) - 0.5) * zoom
        if 0 <= x <= DISPLAY_PIXELS and 0 <= y <= DISPLAY_PIXELS:
            draw.ellipse([x - 17, y - 17, x + 17, y + 17], outline=RING_COLOUR, width=2)
    if label:
        draw.rectangle([0, 0, DISPLAY_PIXELS, 18], fill=(0, 0, 0))
        draw.text((6, 4), label, fill=(255, 255, 255))
    if scale_arcsec:
        bar = 60.0 / scale_arcsec * zoom                        # one arcminute, in display pixels
        y = DISPLAY_PIXELS - 14
        draw.rectangle([8, y - 14, 8 + bar + 8, y + 8], fill=(0, 0, 0))
        draw.line([12, y + 3, 12 + bar, y + 3], fill=(255, 255, 255), width=2)
        draw.text((12, y - 11), "1 arcmin", fill=(255, 255, 255))
    if compass:
        draw.rectangle([DISPLAY_PIXELS - 104, DISPLAY_PIXELS - 20, DISPLAY_PIXELS, DISPLAY_PIXELS], fill=(0, 0, 0))
        draw.text((DISPLAY_PIXELS - 98, DISPLAY_PIXELS - 16), "N up, E left", fill=(255, 255, 255))
    return picture


def single_frames(cutouts, ra, dec, ring):
    """One frame per image. Only the sky level is subtracted; nothing is aligned."""
    images = []
    for cutout in cutouts:
        image = cutout["imagen"].astype(float)
        images.append(image - np.nanmedian(image))
    low, high = limits(images)
    frames = []
    for cutout, image in zip(cutouts, images):
        mark = None
        if ring:
            try:
                x, y = cutout["wcs"].world_to_pixel_values(ra, dec)
                mark = (float(x), float(y))
            except Exception:
                mark = None
        label = mjd_to_text(cutout["fecha"], with_time=True)
        frames.append({
            "picture": to_picture(image, low, high, mark=mark, label=label, scale_arcsec=PIXEL_ARCSEC),
            "label": label,
            "details": (
                f"**Detector:** {cutout['detector']} · "
                f"**Wavelength at this position:** {cutout['longitud_onda']:.2f} µm · "
                f"**Flagged pixels:** {cutout['porcentaje_marcado']:.1f} % · "
                f"**Data version:** {cutout['version']}"
            ),
        })
    side = max(max(c["imagen"].shape) for c in cutouts)
    return frames, {"field_arcmin": side * PIXEL_ARCSEC / 60.0}


def stacked_frames(cutouts, ra, dec, ring):
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

    # An epoch with very few images gives a noisy frame full of holes, which looks
    # like things appearing and disappearing. Leave those out when enough remain.
    solid = {e: m for e, m in by_epoch.items() if len(m) >= MIN_IMAGES_PER_EPOCH}
    thin = len(by_epoch) - len(solid)
    if len(solid) >= 2:
        by_epoch = solid
    else:
        thin = 0

    stacks = []
    for epoch in sorted(by_epoch):
        members = by_epoch[epoch]
        with np.errstate(all="ignore"):
            stack = proceso.apilar([image for image, _ in members])
        dates = [c["fecha"] for _, c in members]
        waves = [c["longitud_onda"] for _, c in members]
        stacks.append((stack, dates, waves, len(members)))
    low, high = limits([stack for stack, _, _, _ in stacks])

    mark = None
    if ring:
        x, y = grid.world_to_pixel_values(ra, dec)
        mark = (float(x), float(y))
    frames = []
    for stack, dates, waves, count in stacks:
        label = f"{mjd_to_text(min(dates))} to {mjd_to_text(max(dates))}"
        frames.append({
            "picture": to_picture(stack, low, high, mark=mark, label=label,
                                  scale_arcsec=GRID_ARCSEC, compass=True),
            "label": label,
            "details": (
                f"**Images combined:** {count} · "
                f"**Wavelengths mixed:** {min(waves):.2f} to {max(waves):.2f} µm · "
                f"**Orientation:** north up, east left"
            ),
        })
    return frames, {
        "field_arcmin": GRID_PIXELS * GRID_ARCSEC / 60.0,
        "not_aligned": len(cutouts) - len(kept),
        "thin_epochs": thin,
    }


def animation(frames, milliseconds):
    """Animated GIF of the given frames. Each picture already carries its date."""
    pictures = [frame["picture"] for frame in frames]
    buffer = io.BytesIO()
    pictures[0].save(
        buffer, format="GIF", save_all=True, append_images=pictures[1:],
        duration=milliseconds, loop=0,
    )
    return buffer.getvalue()


def build_frames(result, mode, ring):
    """Frames for this result and view. Kept in the session so the slider answers at once."""
    key = (result["ra"], result["dec"], result["band"], len(result["cutouts"]), mode, ring)
    kept = st.session_state.get("frames")
    if kept and kept["key"] == key:
        return kept["frames"], kept["info"]
    if mode == MODE_STACKED:
        frames, info = stacked_frames(result["cutouts"], result["ra"], result["dec"], ring)
    else:
        frames, info = single_frames(result["cutouts"], result["ra"], result["dec"], ring)
    st.session_state["frames"] = {"key": key, "frames": frames, "info": info}
    return frames, info


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
    with tema.cargando(f"Opening the SPHEREx images of {target['name']}", "Stored by the team"):
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
        with tema.cargando("Asking NASA which SPHEREx images cover this position", "Searching the archive"):
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
    with tema.cargando(
        f"Found {len(exposures)} images. Bringing up to {MAX_IMAGES} of them",
        "This can take about a minute",
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


tema.navegacion()
tema.portada()
tema.seccion(1, "Explore any position")

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

tema.seccion(2, "Or start with the five challenge targets")
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
    st.rerun()   # redraw the form so it shows the position and detector just loaded
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
    tema.seccion(3, "The sequence")
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

    st.caption(
        "Look for a dot that leaves the amber ring or changes brightness from one date "
        "to the next. A dot that shows up in a single frame is usually a cosmic ray or a bad pixel."
    )
    view_column, ring_column = st.columns([3, 1])
    mode = view_column.radio("View", [MODE_STACKED, MODE_SINGLE], horizontal=True)
    ring = ring_column.checkbox("Show the ring", value=True,
                                help="The amber ring marks the position that was asked for.")
    frames, info = build_frames(result, mode, ring)
    if info.get("not_aligned"):
        st.warning(f"{info['not_aligned']} images could not be aligned and were left out.")
    if info.get("thin_epochs"):
        st.caption(
            f"{info['thin_epochs']} observing period(s) with fewer than {MIN_IMAGES_PER_EPOCH} "
            "images are not shown here: their frames are too noisy to compare. "
            f"They are in “{MODE_SINGLE}”."
        )

    if len(frames) > 1:
        index = st.slider("Frame", 1, len(frames), 1) - 1
    else:
        index = 0
    frame = frames[index]

    picture_column, movie_column = st.columns(2)
    picture_column.image(frame["picture"], caption=f"Frame {index + 1} of {len(frames)}")
    picture_column.metric("Date", frame["label"])
    with picture_column.expander("Technical details of this frame"):
        st.write(frame["details"])

    if len(frames) > 1:
        speed_column, blink_column = movie_column.columns(2)
        speed = speed_column.select_slider("Animation speed", list(SPEEDS), value="Medium")
        blink = blink_column.checkbox("First and last date only", value=False,
                                      help="Blink between the two dates that are furthest apart.")
        shown = [frames[0], frames[-1]] if blink else frames
        gif = animation(shown, SPEEDS[speed])
        movie_column.image(
            gif,
            caption="First and last date, alternating" if blink else "The whole sequence, in time order",
        )
        movie_column.download_button(
            "Download animation (GIF)", gif, file_name="spherex_sequence.gif", mime="image/gif"
        )

    legend = (
        "**Amber ring:** the position you asked for. "
        "**Purple:** no data there. "
        "**Black hole inside a very bright star:** the star overloaded the detector; it is not real."
    )
    if mode == MODE_STACKED:
        st.info(
            legend + "\n\n"
            "Each frame combines (median) the images of one observing period, aligned so that "
            "**north is up and east is left**. A dot that changes place between frames may be "
            "something moving across the sky. The images combined in a frame were taken at "
            "**different wavelengths** within the detector band."
        )
    else:
        st.info(
            legend + "\n\n"
            "These are single images with only the sky level subtracted. They are **not aligned**: "
            "the sky looks rotated and shifted from one image to the next, so a dot changing place "
            "here does not mean it moved. Each image is also taken at a **different wavelength**, "
            "so a change in brightness is not by itself a change over time."
        )

    hallazgos.report_form(result["ra"], result["dec"], result["band"], mode, frame["label"])

    st.caption(
        f"Field: {info['field_arcmin']:.0f} arcmin across. Dates in this sequence: "
        f"{mjd_to_text(cutouts[0]['fecha'])} to {mjd_to_text(cutouts[-1]['fecha'])}. "
        "Data: NASA/IPAC IRSA, SPHEREx."
    )

tema.seccion(4 if st.session_state.get("result") else 3, "How to read the images")
tema.ayuda()
tema.pie()
