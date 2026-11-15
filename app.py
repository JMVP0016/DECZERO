# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Minimum version (milestone H1): any coordinate -> real SPHEREx images in time order."""

import re

import astropy.units as u
import streamlit as st
from astropy.coordinates import SkyCoord

import fresco

fresco.actualizar()   # after an upload, do not mix the new app.py with old modules in memory

import cache_local
import datos
import hallazgos
import tema
from objetivos import TARGETS
from vista import (MIN_IMAGES_PER_EPOCH, animation, mjd_to_text, single_frames,
                   stacked_frames)

MAX_IMAGES = 24      # live-mode cap agreed after measurement M0
FOV_ARCMIN = 10.0    # side of each cutout
BANDS = ["D1", "D2", "D3", "D4", "D5", "D6"]

MODE_STACKED = "Aligned (best for motion)"
MODE_SINGLE = "Single images (per exposure)"
SPEEDS = {"Slow": 900, "Medium": 450, "Fast": 200}   # milliseconds per frame


st.set_page_config(page_title="HAWAPACHA — Find the change in the sky", page_icon=tema.ICON, layout="wide")
tema.aplicar_tema()


def parse_coordinate(text):
    """Accept '150.0 +2.2' (degrees) or '08h55m10.8s -7d14m42.5s'. Return (ra, dec) in degrees."""
    # a typographic minus or dash pasted from a document must read as a minus sign
    text = text.strip().replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    if not text:
        raise ValueError("empty")
    # two plain numbers are degrees, also when written as ".5" or "10."
    number = r"[+-]?(?:\d+\.?\d*|\.\d+)"
    numbers = re.fullmatch(rf"({number})[\s,]+({number})", text)
    if numbers:
        ra, dec = float(numbers.group(1)), float(numbers.group(2))
    else:
        coord = SkyCoord(text, unit=(u.hourangle, u.deg), frame="icrs")
        ra, dec = float(coord.ra.deg), float(coord.dec.deg)
    if not (0.0 <= ra <= 360.0 and -90.0 <= dec <= 90.0):
        raise ValueError("out of range")
    return ra, dec


FIELDS = {"10 arcmin": 200, "6 arcmin": 120, "4 arcmin": 80}   # side of the view -> grid pixels of 3"


def build_frames(result, mode, ring, grid_pixels=200, invert=False):
    """Frames for this result and view. Kept in the session so the slider answers at once."""
    key = (result["ra"], result["dec"], result["band"], len(result["cutouts"]), mode, ring, grid_pixels, invert)
    kept = st.session_state.get("frames")
    if kept and kept["key"] == key:
        return kept["frames"], kept["info"]
    target = next((t for t in TARGETS if t["name"] == result.get("stored")), None)
    if mode == MODE_STACKED:
        frames, info = stacked_frames(result["cutouts"], result["ra"], result["dec"], ring, target,
                                      grid_pixels=grid_pixels, invert=invert)
    else:
        frames, info = single_frames(result["cutouts"], result["ra"], result["dec"], ring, target,
                                     grid_pixels=grid_pixels, invert=invert)
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
    with tema.cargando(f"Opening the SPHEREx images of {target['name']}", "Stored by the team", lugar=notice):
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
    st.session_state["error_detail"] = None
    try:
        with tema.cargando("Asking NASA which SPHEREx images cover this position", "Searching the archive", lugar=notice):
            exposures = datos.buscar(ra, dec, banda=band)
    except Exception as error:
        st.session_state["error"] = (
            "The NASA archive (IRSA) is not responding right now, so new positions cannot "
            "be searched. Please try again in a few minutes. Meanwhile, the five challenge "
            "targets are stored by the team and always work."
        )
        st.session_state["error_detail"] = f"Technical detail: {error}"
        return
    if not exposures:
        st.session_state["error"] = (
            f"SPHEREx has no images of this position in detector {band} yet. "
            "Try another detector or another position."
        )
        return
    with tema.cargando(
        f"Found {len(exposures)} images. Bringing up to {MAX_IMAGES} of them",
        "This can take about a minute", lugar=notice,
    ):
        cutouts = datos.obtener(ra, dec, fov=FOV_ARCMIN, banda=band, max_n=MAX_IMAGES)
    if not cutouts:
        st.session_state["error"] = (
            "The images exist, but none could be downloaded from the public SPHEREx "
            "copies (AWS and IRSA) right now. Please try again in a few minutes."
        )
        return
    st.session_state["error"] = None
    st.session_state["result"] = {
        "ra": ra, "dec": dec, "band": band,
        "available": len(exposures), "cutouts": cutouts,
    }


tema.navegacion()
tema.portada(compacta=bool(st.session_state.get("result")))
if not st.session_state.get("result"):
    tema.pasos()
    tema.ayuda_boton(st.columns([1, 1.1, 1])[1], clave="help_open_home")
has_result = bool(st.session_state.get("result"))

params = st.query_params
start_text = f"{params['ra']} {params['dec']}" if "ra" in params and "dec" in params else ""
start_band = params.get("band", "D2")

# With a sequence on screen, the search form and the targets fold into one line,
# so the pictures are visible without scrolling.
if has_result:
    chooser = st.expander("Change position or target")
else:
    tema.seccion(1, "Explore any position")
    chooser = st.container()

with chooser:
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
    if not has_result:
        notice = st.empty()   # waiting scene and errors appear here, right under the form

    if has_result:
        st.caption("Or open one of the five challenge targets:")
    else:
        tema.seccion(2, "Or start with the five challenge targets")
    clicked = tema.tarjetas(TARGETS, compactas=has_result)

if has_result:
    notice = st.empty()       # the chooser is folded: show messages under it, not inside

first_visit_with_link = bool(start_text) and "result" not in st.session_state

if clicked:
    st.query_params.update({
        "ra": f"{clicked['ra']:.5f}", "dec": f"{clicked['dec']:.5f}", "band": clicked["band"],
    })
    load_target(clicked)
    st.session_state["scroll_top"] = True
    st.rerun()   # redraw the form so it shows the position and detector just loaded
elif submitted or first_visit_with_link:
    try:
        ra, dec = parse_coordinate(text)
    except Exception:
        st.session_state["result"] = None
        st.session_state["error_detail"] = None
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
        if st.session_state.get("result"):
            st.session_state["scroll_top"] = True
            st.rerun()            # redraw with the slim header, so the sequence is in view

if st.session_state.get("error"):
    with notice.container():
        st.error(st.session_state["error"])
        if st.session_state.get("error_detail"):
            st.caption(st.session_state["error_detail"])

result = st.session_state.get("result")
if result:
    tema.seccion(1, "The sequence")
    cutouts = result["cutouts"]
    if result.get("stored"):
        st.success(
            f"{result['stored']}: {len(cutouts)} images stored by the team "
            "(the Aligned view combines them into one frame per observing period), "
            f"detector {result['band']}, around RA {result['ra']:.5f}°, Dec {result['dec']:.5f}°."
        )
    else:
        st.success(
            f"Showing {len(cutouts)} of {result['available']} images at "
            f"RA {result['ra']:.5f}°, Dec {result['dec']:.5f}°, detector {result['band']}."
        )

    hint_column, help_column = st.columns([3.6, 1.4], vertical_alignment="center")
    tema.ayuda_boton(help_column)
    hint_column.caption(
        "Look for a dot that changes place between observing periods while the stars around it "
        "stay put. Amber ring: centre of the view. Purple: no data."
    )
    view_column, field_column, ring_column, report_column = st.columns(
        [4.5, 1.1, 1.5, 1.4], vertical_alignment="bottom")
    field = field_column.container(key="opt_field").selectbox(
        "Field of view", list(FIELDS),
        help="Side of the patch of sky shown. A smaller field zooms in on the centre.",
    )
    mode = view_column.radio("View", [MODE_STACKED, MODE_SINGLE], horizontal=True)
    look = ring_column.container(key="opt_ring")
    invert = look.checkbox(
        "White sky", value=False,
        help="Dark stars on a white background. Many people find faint dots easier to see this way.")
    ring = look.checkbox("Show the ring", value=True,
                                help="The amber ring marks the centre of the view: the position asked for, or the team's position for one of the five targets.")
    # a second report button, visible without scrolling; the window opens further down
    report_now = hallazgos.can_report() and report_column.button(
        "Report a finding", key="report_open_top", use_container_width=True,
        help="Noticed something in these images? Publish it on the Findings board.",
    )
    frames, info = build_frames(result, mode, ring, FIELDS[field], invert)
    if info.get("not_aligned"):
        st.warning(f"{info['not_aligned']} images could not be aligned and were left out.")
    if info.get("thin_epochs"):
        st.caption(
            f"{info['thin_epochs']} observing period(s) with fewer than {MIN_IMAGES_PER_EPOCH} "
            "images are not shown here: their frames are too noisy to compare. "
            f"They are in “{MODE_SINGLE}”."
        )

    # Controls first, in one row, so the two pictures below start at the same height.
    blink, speed, show_difference = False, "Medium", False
    if info.get("noisy") and len(frames) > 1:
        st.caption("Some observing periods here have very few images, so their frames are noisy.")
    if len(frames) > 1:
        frame_column, speed_column, blink_column, difference_column = st.columns(
            [1.8, 1.1, 1.2, 1.2], vertical_alignment="bottom")
        index = frame_column.slider("Frame (still picture)", 1, len(frames), 1) - 1
        speed = speed_column.container(key="opt_speed").select_slider(
            "Animation speed", list(SPEEDS), value="Medium")
        aligned_view = mode == MODE_STACKED
        blink = blink_column.checkbox(
            "First and last date only", value=False, disabled=not aligned_view,
            help="Blink between the two dates that are furthest apart. Only in the aligned view: "
                 "single images are too noisy to blink first against last.",
        ) and aligned_view
        show_difference = difference_column.checkbox(
            "Difference image", value=False,
            disabled=not (aligned_view and info.get("difference") is not None),
            help="Shows the last observing period minus the first, in place of the animation. "
                 "What did not change cancels out. Only in the aligned view.",
        ) and aligned_view and info.get("difference") is not None
    else:
        index = 0
        st.caption("Only one observing period is available here, so there is nothing to compare yet.")
    frame = frames[index]

    picture_column, movie_column = st.columns(2)
    picture_column.markdown('<p class="dz-plabel">Still frame · move the slider</p>', unsafe_allow_html=True)
    if show_difference:
        movie_column.markdown('<p class="dz-plabel">Difference · last period minus first</p>', unsafe_allow_html=True)
    elif len(frames) > 1:
        movie_column.markdown('<p class="dz-plabel">Animation · plays by itself</p>', unsafe_allow_html=True)
    picture_column.image(frame["picture"], caption=f"Frame {index + 1} of {len(frames)} · {frame['label']}")
    with picture_column.expander("Technical details of this frame"):
        st.write(frame["details"])

    if show_difference:
        movie_column.image(
            info["difference"],
            caption="White: brighter in the last period. Black: brighter in the first. Grey: no change.",
        )
        movie_column.caption(
            "An object that moved shows as a black spot next to a white one. Bright stars leave "
            "rings and smudges here, because each period mixes different infrared colours."
        )
    elif len(frames) > 1:
        # the GIF is kept too: encoding 40 frames on every slider move made it lag
        gif_key = (st.session_state["frames"]["key"], speed, blink)
        kept_gif = st.session_state.get("gif")
        if kept_gif and kept_gif["key"] == gif_key:
            gif = kept_gif["bytes"]
        else:
            shown = [frames[0], frames[-1]] if blink else frames
            gif = animation(shown, SPEEDS[speed])
            st.session_state["gif"] = {"key": gif_key, "bytes": gif}
        movie_column.image(
            gif,
            caption="First and last date, alternating" if blink else "The whole sequence, in time order",
        )
        movie_column.download_button(
            "Download animation (GIF)", gif, file_name="spherex_sequence.gif", mime="image/gif"
        )

    hallazgos.report_button(
        result["ra"], result["dec"], result["band"], mode, frame["label"], frame["picture"],
        open_now=report_now,
    )

    legend = (
        "**Amber ring:** the centre of this view"
        + (" (the team's position for this target). " if result.get("stored") else " (the position you asked for). ")
        + ("**Turquoise cross-hair:** where the catalogue position and proper motion say this "
           "target should be on that date. " if result.get("stored") else "") +
        "**Purple:** no data: small squares are pixels flagged as bad, large areas are the edge "
        "of the detector. **Plain white:** the star overloaded the detector there, so neither "
        "its exact centre nor its brightness can be measured. White blocks with straight edges "
        "next to a bright star are flagged pixels too, not objects."
    )
    if mode == MODE_STACKED:
        st.info(
            legend + "\n\n"
            "Each frame is the middle value (median) of all the images of one observing period, "
            "lined up so that **north is up and east is left**. A dot that changes place between "
            "frames, while the other stars stay put, may be something moving across the sky. The "
            "images in a frame were taken in **different infrared colours**, so small brightness "
            "differences between frames are expected."
        )
    else:
        st.info(
            legend + "\n\n"
            "These are single exposures, turned so that **north is up and east is left**; nothing "
            "is combined, so they are noisier and have purple gaps where pixels were flagged as "
            "bad. Each one sees the spot in a **different infrared colour**: a star that looks "
            "brighter or fainter from one exposure to the next has usually not changed."
        )


    st.caption(
        f"Field: {info['field_arcmin']:.0f} arcmin across. Dates in this sequence: "
        f"{mjd_to_text(cutouts[0]['fecha'])} to {mjd_to_text(cutouts[-1]['fecha'])}. "
        "Data: NASA/IPAC IRSA, SPHEREx."
    )

if not has_result:   # with a sequence open, the guide is the button next to the pictures
    tema.seccion(3, "How to read the images")
    tema.ayuda()
tema.pie()
if st.session_state.pop("scroll_top", False):
    tema.subir()   # on a phone the page would stay halfway down after opening a sequence
