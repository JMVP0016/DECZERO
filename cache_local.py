# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Lee los recortes ya guardados en cache/<objetivo>/ para que los cinco objetivos
del reto carguen al instante, sin consultar a IRSA ni a AWS.

Acepta los dos formatos de archivo:
  - ligero (guardar_recorte): extensiones IMAGE, MASK, VARIANCE, ZODI.
  - en bruto de IRSA: IMAGE, FLAGS, VARIANCE, ZODI, EPSF, WCS-WAVE.
Devuelve la misma lista de diccionarios que datos.obtener().
"""

import glob
import os

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import datos

DIR_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def disponibles(carpeta: str, banda: str) -> list:
    """Rutas de los archivos guardados de un objetivo en una banda (D1 a D6)."""
    patron = os.path.join(DIR_CACHE, carpeta, f"*_{banda}_*.fits")
    return sorted(glob.glob(patron))


def _leer(ruta: str) -> dict:
    with fits.open(ruta) as hdul:
        cabecera = hdul["IMAGE"].header
        imagen = np.array(hdul["IMAGE"].data, dtype=np.float32)
        wcs = WCS(cabecera)

        if "MASK" in hdul:  # formato ligero
            mascara = np.array(hdul["MASK"].data) != 0
            longitud_onda = float(cabecera.get("WAVELEN", np.nan))
            version = str(cabecera.get("VERSION", ""))
            detector = str(cabecera.get("DETECTOR", "?"))
        else:               # recorte en bruto de IRSA
            flags = np.array(hdul["FLAGS"].data, dtype=np.int32)
            mascara = (flags & datos._bits_mascara(hdul["FLAGS"].header)) != 0
            version = str(hdul[0].header.get("VERSION", ""))
            detector = f"D{cabecera.get('DETECTOR', '?')}"
            # Longitud de onda en el centro del recorte, como en el tutorial de IRSA.
            try:
                espectral = WCS(cabecera, fobj=hdul, key="W")
                espectral.sip = None
                onda, _ = espectral.pixel_to_world(imagen.shape[1] / 2.0, imagen.shape[0] / 2.0)
                longitud_onda = float(onda.to("um").value)
            except Exception:
                longitud_onda = float("nan")

        return {
            "imagen": imagen,
            "varianza": np.array(hdul["VARIANCE"].data, dtype=np.float32),
            "fondo": np.array(hdul["ZODI"].data, dtype=np.float32),
            "mascara": mascara,
            "porcentaje_marcado": 100.0 * float(mascara.sum()) / float(mascara.size),
            "wcs": wcs,
            "fecha": float(cabecera.get("MJD-OBS", 0.0)),
            "detector": detector if detector.startswith("D") else f"D{detector}",
            "longitud_onda": longitud_onda,
            "version": version,
            "url": os.path.basename(ruta),
            "origen": "cache",
        }


def leer_objetivo(carpeta: str, banda: str) -> list:
    """
    Todos los recortes guardados de un objetivo y una banda, ordenados por fecha
    y con su número de época. Lista vacía si no hay ninguno.
    Un archivo dañado se salta; no impide cargar los demás.
    """
    recortes = {}
    for ruta in disponibles(carpeta, banda):
        try:
            recorte = _leer(ruta)
        except Exception as error:
            print(f"[Aviso] No se pudo leer {os.path.basename(ruta)}: {error}")
            continue
        recortes.setdefault(round(recorte["fecha"], 5), recorte)  # sin fechas repetidas
    return datos._asignar_epocas(list(recortes.values()))
