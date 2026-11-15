# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Makes one animated GIF per challenge target for the project page, in gifs/, and
one small still picture per target for the cards of the app, in assets/thumbs/.

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

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(AQUI, "gifs")
MINIATURAS = os.path.join(AQUI, "assets", "thumbs")
MILISEGUNDOS = 900

os.makedirs(CARPETA, exist_ok=True)
os.makedirs(MINIATURAS, exist_ok=True)
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

    # Card picture: the middle of the first frame, with no marks or labels on it.
    limpios, _ = vista.stacked_frames(recortes, objetivo["ra"], objetivo["dec"], False, None, "", plain=True)
    lado = vista.DISPLAY_PIXELS
    centro = limpios[0]["picture"].crop((lado // 4, lado // 4, 3 * lado // 4, 3 * lado // 4))
    centro.save(os.path.join(MINIATURAS, f"{objetivo['folder']}.png"))
