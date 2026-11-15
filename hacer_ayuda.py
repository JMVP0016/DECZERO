# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Makes the small pictures of the help window (assets/help/*.png) from the stored
SPHEREx images of the challenge targets. Run:  python hacer_ayuda.py
"""

import os

from PIL import Image

import cache_local
import vista
from objetivos import TARGETS

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "help")
SIDE = 300   # each half of a help picture, in pixels


def target(folder):
    return next(t for t in TARGETS if t["folder"] == folder)


def frames(folder, single=False):
    t = target(folder)
    cutouts = cache_local.leer_objetivo(t["folder"], t["band"])
    make = vista.single_frames if single else vista.stacked_frames
    return make(cutouts, t["ra"], t["dec"], True, t)[0]


def crop(picture, zoom=1.0):
    """Centre of the picture, enlarged zoom times, as a SIDE x SIDE square."""
    size = picture.size[0]
    half = size / zoom / 2
    box = (size / 2 - half, size / 2 - half, size / 2 + half, size / 2 + half)
    return picture.crop(tuple(int(v) for v in box)).resize((SIDE, SIDE), Image.NEAREST)


def pair(left, right, name):
    sheet = Image.new("RGB", (2 * SIDE + 6, SIDE), (11, 18, 32))
    sheet.paste(left, (0, 0))
    sheet.paste(right, (SIDE + 6, 0))
    sheet.save(os.path.join(OUT, name))
    print(name)


def main():
    os.makedirs(OUT, exist_ok=True)
    eps = frames("epsilon_indi_b")
    eps_single = frames("epsilon_indi_b", single=True)
    barnard = frames("barnard")
    draconis_single = frames("r_draconis", single=True)

    pair(crop(eps[0]["picture"]), crop(eps_single[0]["picture"]), "views.png")           # aligned vs single
    pair(crop(eps[0]["picture"], 3), crop(eps[-1]["picture"], 3), "moved.png")           # first vs last period
    pair(crop(eps_single[6]["picture"], 2), crop(eps_single[7]["picture"], 2), "colour.png")   # minutes apart
    pair(crop(barnard[0]["picture"], 2), crop(draconis_single[3]["picture"]), "fooled.png")    # white core, blocks
    pair(crop(eps[-1]["picture"]), crop(eps[-1]["picture"], 3), "marks.png")             # ring and cross-hair


if __name__ == "__main__":
    main()
