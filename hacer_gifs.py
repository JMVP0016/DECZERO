# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Makes one animated GIF per challenge target for the project page, in gifs/.

Usage:  python hacer_gifs.py

Each GIF is the aligned view of the app: one band, north up and east left, one
contrast range for the whole sequence, one frame per observing period, with the
dates and the number of images combined written on every frame. The amber ring is
the centre of the view and the turquoise cross-hair is the catalogue position
moved to that date with the proper motion (objetivos.py).
"""

import os

import cache_local
import vista
from objetivos import TARGETS

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gifs")
MILISEGUNDOS = 900

os.makedirs(CARPETA, exist_ok=True)
for objetivo in TARGETS:
    recortes = cache_local.leer_objetivo(objetivo["folder"], objetivo["band"])
    if not recortes:
        print(f"{objetivo['name']}: no stored images, skipped")
        continue
    titulo = f"{objetivo['name']} - SPHEREx {objetivo['band']} - "
    cuadros, _ = vista.stacked_frames(recortes, objetivo["ra"], objetivo["dec"], True, objetivo, titulo)
    ruta = os.path.join(CARPETA, f"{objetivo['folder']}_{objetivo['band']}.gif")
    with open(ruta, "wb") as archivo:
        archivo.write(vista.animation(cuadros, MILISEGUNDOS))
    print(f"{objetivo['name']}: {len(cuadros)} frames, {os.path.getsize(ruta) / 1e3:.0f} kB -> {ruta}")
