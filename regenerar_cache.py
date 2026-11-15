# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Rebuilds cache/<target>/ with light cutouts centred on each target.

Usage:  python regenerar_cache.py              (all five targets)
        python regenerar_cache.py barnard      (only the folders named)

For each target it reads up to MAX_N images of its band from the public AWS copy of
SPHEREx (through datos.obtener), and writes one small FITS per image with the
extensions IMAGE, MASK, VARIANCE and ZODI. The heavy EPSF extension of the IRSA
cutouts is not kept: files go from about 4 MB to about 0.2 MB.
The old files of a target are replaced only if the new download is complete enough.
"""

import glob
import os
import sys

import numpy as np
from astropy.io import fits

import cache_local
import datos
from objetivos import TARGETS

FOV_ARCMIN = 12.0
MAX_N = 40
MIN_OK = 20        # with fewer images than this, the old files are kept


def guardar_recorte(rec, ruta):
    cab = rec["wcs"].to_header(relax=True)          # includes the SIP distortion
    cab["MJD-OBS"] = rec["fecha"]
    cab["DETECTOR"] = rec["detector"]
    cab["WAVELEN"] = (rec["longitud_onda"], "um, at the requested position")
    cab["VERSION"] = rec["version"]
    cab["PCTFLAG"] = (rec["porcentaje_marcado"], "% of flagged pixels")
    cab["ORIGEN"] = rec["origen"]
    cab["SRCFILE"] = os.path.basename(rec["url"])[:68]
    hdus = [
        fits.PrimaryHDU(),
        fits.ImageHDU(rec["imagen"], header=cab, name="IMAGE"),
        fits.ImageHDU(rec["mascara"].astype(np.uint8), name="MASK"),
        fits.ImageHDU(rec["varianza"], name="VARIANCE"),
        fits.ImageHDU(rec["fondo"], name="ZODI"),
    ]
    fits.HDUList(hdus).writeto(ruta, overwrite=True)


elegidos = set(sys.argv[1:])
for objetivo in TARGETS:
    if elegidos and objetivo["folder"] not in elegidos:
        continue
    banda = objetivo["band"]
    recortes = datos.obtener(objetivo["ra"], objetivo["dec"], fov=FOV_ARCMIN, banda=banda, max_n=MAX_N)
    if len(recortes) < MIN_OK:
        print(f"{objetivo['name']}: only {len(recortes)} images arrived; old files kept", flush=True)
        continue
    carpeta = os.path.join(cache_local.DIR_CACHE, objetivo["folder"])
    os.makedirs(carpeta, exist_ok=True)
    for viejo in glob.glob(os.path.join(carpeta, f"*_{banda}_*.fits")):
        os.remove(viejo)
    for i, rec in enumerate(recortes):
        nombre = f"{objetivo['folder']}_{banda}_{i:03d}_mjd{rec['fecha']:.3f}.fits"
        guardar_recorte(rec, os.path.join(carpeta, nombre))
    epocas = sorted({r["epoca"] for r in recortes})
    print(f"{objetivo['name']}: {len(recortes)} images, {len(epocas)} observing periods, "
          f"centred on RA {objetivo['ra']}, Dec {objetivo['dec']}", flush=True)
