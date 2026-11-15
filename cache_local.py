# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Lee los recortes ya guardados en cache/<objetivo>/ para que los cinco objetivos
del reto carguen al instante, sin consultar a IRSA ni a AWS.

Acepta tres formatos de archivo:
  - ligero (guardar_recorte): extensiones IMAGE, MASK, VARIANCE, ZODI.
  - en bruto de IRSA: IMAGE, FLAGS, VARIANCE, ZODI, EPSF, WCS-WAVE.
  - ya alineado al norte (Geo, 15 nov): IMAGE, VARIANCE, FLAGS, ZODI, LAMBDA,
    con NORTEUP en la cabecera y la longitud de onda de cada píxel en LAMBDA.
Devuelve la misma lista de diccionarios que datos.obtener().
"""

import glob
import os

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

import datos

DIR_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# Número de bit de cada plano de FLAGS que se enmascara (los mismos nombres que
# datos.PLANOS_MALOS), leídos de las claves MSKNnnnn de un archivo original de IRSA.
# Se usa solo cuando el archivo guardado no trae esos nombres en su cabecera.
BITS_MALOS = {0: "TRANSIENT", 1: "OVERFLOW", 2: "SUR_ERROR", 6: "NONFUNC", 9: "MISSING_DATA",
              10: "HOT", 11: "COLD", 15: "NONLINEAR", 17: "PERSIST", 19: "OUTLIER"}
MASCARA_FIJA = sum(1 << bit for bit in BITS_MALOS)


def disponibles(carpeta: str, banda: str) -> list:
    """Rutas de los archivos guardados de un objetivo en una banda (D1 a D6)."""
    patron = os.path.join(DIR_CACHE, carpeta, f"*_{banda}_*.fits")
    return sorted(glob.glob(patron))


def _leer(ruta: str, ra=None, dec=None) -> dict:
    with fits.open(ruta) as hdul:
        cabecera = hdul["IMAGE"].header
        imagen = np.array(hdul["IMAGE"].data, dtype=np.float32)
        wcs = WCS(cabecera)

        if "MASK" in hdul:  # formato ligero
            mascara = np.array(hdul["MASK"].data) != 0
            longitud_onda = float(cabecera.get("WAVELEN", np.nan))
            version = str(cabecera.get("VERSION", ""))
            detector = str(cabecera.get("DETECTOR", "?"))
        elif "LAMBDA" in hdul:  # ya alineado al norte, con FLAGS sin nombres de plano
            flags = np.array(hdul["FLAGS"].data, dtype=np.int64)
            mascara = ((flags & MASCARA_FIJA) != 0) | ~np.isfinite(imagen)
            version = str(cabecera.get("VERSION", ""))
            detector = str(cabecera.get("DETECTOR", "?"))
            longitud_onda = float(cabecera.get("WAVE_UM", np.nan))   # en el centro del recorte
            if ra is not None:   # mejor: la del píxel donde está el objetivo
                try:
                    x, y = wcs.world_to_pixel_values(ra, dec)
                    valor = float(hdul["LAMBDA"].data[int(round(float(y))), int(round(float(x)))])
                    if np.isfinite(valor):
                        longitud_onda = valor
                except Exception:
                    pass
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


def bandas(carpeta: str) -> list:
    """Detectores (D1 a D6) con recortes guardados para este objetivo."""
    return [banda for banda in ("D1", "D2", "D3", "D4", "D5", "D6") if disponibles(carpeta, banda)]


def leer_objetivo(carpeta: str, banda: str, ra=None, dec=None) -> list:
    """
    Todos los recortes guardados de un objetivo y una banda, ordenados por fecha
    y con su número de época. Lista vacía si no hay ninguno.
    Un archivo dañado se salta; no impide cargar los demás.
    """
    recortes = {}
    for ruta in disponibles(carpeta, banda):
        try:
            recorte = _leer(ruta, ra, dec)
        except Exception as error:
            print(f"[Aviso] No se pudo leer {os.path.basename(ruta)}: {error}")
            continue
        recortes.setdefault(round(recorte["fecha"], 5), recorte)  # sin fechas repetidas
    return datos._asignar_epocas(list(recortes.values()))
