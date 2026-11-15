# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Turns cutouts into pictures and animations. Used by the app and by hacer_gifs.py."""

import io

import numpy as np
from astropy.time import Time
from PIL import Image, ImageDraw
from scipy import ndimage

import objetivos
import proceso

GRID_PIXELS = 200    # aligned grid: 200 px of 3 arcsec = 10 arcmin
DISPLAY_PIXELS = 480
MIN_IMAGES_PER_EPOCH = 3            # an aligned frame made of fewer images is too noisy to trust
RING_COLOUR = (251, 191, 36)        # amber #FBBF24: centre of the view
EXPECTED_COLOUR = (94, 234, 212)    # turquoise #5EEAD4: where the catalogue says the target should be
NO_DATA_COLOUR = (52, 32, 78)       # purple: no data here (not the same as dark sky)
PIXEL_ARCSEC = 6.15                 # SPHEREx pixel
GRID_ARCSEC = 3.0                   # pixel of the aligned grid


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


def to_picture(image, low, high, mark=None, label="", scale_arcsec=None, compass=False, expected=None):
    """
    2D array -> colour picture of DISPLAY_PIXELS x DISPLAY_PIXELS.
      - A non-square image is padded to a square, never stretched.
      - Pixels without data are purple, so they are not mistaken for dark sky.
      - mark = (x, y) in pixels of the input image draws the amber ring there.
      - expected = (x, y) draws the turquoise cross-hair of the catalogue position.
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
    missing = ~np.isfinite(square)
    rgb[missing] = NO_DATA_COLOUR
    # A hole surrounded by very bright pixels is the overloaded core of a bright
    # star, not missing sky: draw it white, as the star would look, not purple.
    regions, count = ndimage.label(missing)
    for number in range(1, count + 1):
        region = regions == number
        rim = ndimage.binary_dilation(region) & ~missing
        if rim.any() and np.median(square[rim]) >= low + 0.3 * (high - low):
            rgb[region] = (255, 255, 255)
    rgb = np.flipud(rgb)                                        # FITS row 0 is the bottom row
    picture = Image.fromarray(rgb, "RGB").resize((DISPLAY_PIXELS, DISPLAY_PIXELS), Image.NEAREST)

    zoom = DISPLAY_PIXELS / side
    draw = ImageDraw.Draw(picture)
    if mark is not None:
        x = (mark[0] + pad_x + 0.5) * zoom
        y = (side - (mark[1] + pad_y) - 0.5) * zoom
        if 0 <= x <= DISPLAY_PIXELS and 0 <= y <= DISPLAY_PIXELS:
            # dark outline under the amber ring, so it also shows on a bright halo
            draw.ellipse([x - 23, y - 23, x + 23, y + 23], outline=(0, 0, 0), width=4)
            draw.ellipse([x - 22, y - 22, x + 22, y + 22], outline=RING_COLOUR, width=2)
    if expected is not None:
        x = (expected[0] + pad_x + 0.5) * zoom
        y = (side - (expected[1] + pad_y) - 0.5) * zoom
        if 0 <= x <= DISPLAY_PIXELS and 0 <= y <= DISPLAY_PIXELS:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):   # four ticks, open in the middle
                start, end = (x + 7 * dx, y + 7 * dy), (x + 15 * dx, y + 15 * dy)
                draw.line([start, end], fill=(0, 0, 0), width=4)
                draw.line([start, end], fill=EXPECTED_COLOUR, width=2)
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


def single_frames(cutouts, ra, dec, ring, target=None):
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
        expected = None
        if target is not None:
            try:
                x, y = cutout["wcs"].world_to_pixel_values(*objetivos.expected_position(target, cutout["fecha"]))
                expected = (float(x), float(y))
            except Exception:
                expected = None
        label = mjd_to_text(cutout["fecha"], with_time=True)
        frames.append({
            "picture": to_picture(image, low, high, mark=mark, label=label, scale_arcsec=PIXEL_ARCSEC,
                                  expected=expected),
            "label": label,
            "details": (
                f"**Detector:** {cutout['detector']} · "
                f"**Wavelength at this position:** {cutout['longitud_onda']:.2f} µm · "
                f"**Flagged pixels in the whole image:** {cutout['porcentaje_marcado']:.1f} % · "
                f"**Data version:** {cutout['version']}"
            ),
        })
    side = max(max(c["imagen"].shape) for c in cutouts)
    return frames, {"field_arcmin": side * PIXEL_ARCSEC / 60.0}


def stacked_frames(cutouts, ra, dec, ring, target=None, title=""):
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
        label = f"{title}{mjd_to_text(min(dates))} to {mjd_to_text(max(dates))} - {count} images"
        expected = None
        if target is not None:
            x, y = grid.world_to_pixel_values(*objetivos.expected_position(target, float(np.mean(dates))))
            expected = (float(x), float(y))
        frames.append({
            "picture": to_picture(stack, low, high, mark=mark, label=label,
                                  scale_arcsec=GRID_ARCSEC, compass=True, expected=expected),
            "mjd": float(np.mean(dates)),
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
        "noisy": min(count for _, _, _, count in stacks) < MIN_IMAGES_PER_EPOCH,
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
