# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: parts of this file were revised with an SI tool (Claude,
# Anthropic) and run by the team. See "Use of SI" in README.md.
#
# The TAP query, the cutout URL pattern and the wavelength calculation are
# adapted from the official IRSA tutorial "Download a collection of SPHEREx
# Spectral Image cutouts": https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts
import concurrent.futures
import hashlib
import http.client
import logging
import os
import pickle
import time
import urllib.error

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.utils.data import conf
from astropy.wcs import WCS
from astroquery.ipac.irsa import Irsa

logging.getLogger("astropy").setLevel(logging.ERROR)
conf.remote_timeout = 120

MAX_WORKERS = 3       # descargas simultáneas contra IRSA (se satura con facilidad)
MAX_WORKERS_AWS = 8   # AWS no tiene ese límite
# IRSA responde 503 cuando está saturado; hay que esperar bastante entre intentos.
ESPERAS_REINTENTO = [3, 8, 15, 25]  # segundos; 5 intentos en total
MAX_REINTENTOS = len(ESPERAS_REINTENTO) + 1
DIR_CACHE_LOCAL = "cache_datos_locales"
HORAS_CACHE_BUSQUEDA = 12  # IRSA añade datos una vez por semana

BANDAS_VALIDAS = {f"SPHEREx-D{i}" for i in range(1, 7)}

# Planos de FLAGS que invalidan un píxel. Los nombres vienen de las claves
# MSKNnnnn de la cabecera de la extensión FLAGS de cada archivo.
# No se incluye SOURCE (píxel sobre una fuente conocida): enmascararlo
# borraría justo las estrellas que queremos ver.
PLANOS_MALOS = {
    "TRANSIENT", "OVERFLOW", "SUR_ERROR", "NONFUNC", "MISSING_DATA",
    "HOT", "COLD", "NONLINEAR", "PERSIST", "OUTLIER",
}


def _bits_mascara(cabecera_flags) -> int:
    """Suma los bits de los planos malos leyendo sus nombres de la cabecera."""
    bits = 0
    for clave in cabecera_flags:
        if clave.startswith("MSKN"):
            nombre = str(cabecera_flags[clave]).strip()
            if nombre in PLANOS_MALOS:
                bits |= int(cabecera_flags["MSKM" + clave[4:]])
    return bits


def _normalizar_banda(banda: str) -> str:
    """Convierte 'D2' en 'SPHEREx-D2' para que coincida con la tabla de IRSA."""
    banda = banda.strip()
    if not banda.startswith("SPHEREx-"):
        banda = f"SPHEREx-{banda.upper()}"
    if banda not in BANDAS_VALIDAS:
        raise ValueError(f"Banda no válida: {banda}. Use D1 a D6.")
    return banda


def buscar(ra: float, dec: float, banda: str = None) -> list:
    """
    Pregunta a IRSA qué exposiciones de SPHEREx cubren (ra, dec).
    Devuelve lista ordenada por fecha con: 'fecha', 'detector', 'url', 'epoca'.
    """
    os.makedirs(DIR_CACHE_LOCAL, exist_ok=True)
    clave = hashlib.md5(f"{float(ra):.5f}_{float(dec):.5f}_{banda}".encode()).hexdigest()
    ruta_busqueda = os.path.join(DIR_CACHE_LOCAL, f"busqueda_{clave}.pkl")
    if os.path.exists(ruta_busqueda):
        edad_horas = (time.time() - os.path.getmtime(ruta_busqueda)) / 3600.0
        if edad_horas < HORAS_CACHE_BUSQUEDA:
            with open(ruta_busqueda, "rb") as f:
                return pickle.load(f)

    filtro_banda = ""
    if banda:
        nombre_banda = _normalizar_banda(banda)
        filtro_banda = f"AND p.energy_bandpassname = '{nombre_banda}'"

    query = f"""
    SELECT
        'https://irsa.ipac.caltech.edu/' || a.uri AS base_uri,
        p.time_bounds_lower,
        p.energy_bandpassname
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(POINT('ICRS', {float(ra)}, {float(dec)}), p.poly)
          {filtro_banda}
    ORDER BY p.time_bounds_lower
    """

    tabla = Irsa.query_tap(query).to_table()
    exposiciones = []
    epoca_actual = 0
    fecha_anterior = None

    for row in tabla:
        fecha_mjd = float(row["time_bounds_lower"])
        # Nueva época si pasan más de 30 días entre observaciones
        if fecha_anterior is not None and (fecha_mjd - fecha_anterior) > 30.0:
            epoca_actual += 1
        fecha_anterior = fecha_mjd

        det_str = str(row["energy_bandpassname"]).replace("SPHEREx-", "")
        exposiciones.append({
            "fecha": fecha_mjd,
            "detector": det_str,
            "url": str(row["base_uri"]),
            "epoca": epoca_actual
        })

    # La consulta tarda minutos cuando IRSA está cargado: se guarda en disco.
    with open(ruta_busqueda, "wb") as f:
        pickle.dump(exposiciones, f, protocol=pickle.HIGHEST_PROTOCOL)

    return exposiciones


PREFIJO_IRSA = "https://irsa.ipac.caltech.edu/ibe/data/spherex/"
PREFIJO_AWS = "https://nasa-irsa-spherex.s3.amazonaws.com/"
ESCALA_PIXEL_ARCSEC = 6.15  # tamaño nominal del píxel de SPHEREx


def _url_aws(url: str) -> str:
    """Convierte la URL de IRSA en la del mismo archivo en el almacenamiento público de AWS."""
    base = url.split("?")[0]
    if not base.startswith(PREFIJO_IRSA):
        raise ValueError(f"URL no reconocida: {base}")
    return PREFIJO_AWS + base[len(PREFIJO_IRSA):]


def _bajar_aws(url: str, ra: float, dec: float, fov: float) -> dict:
    """
    Lee de AWS solo el trozo de imagen alrededor de (ra, dec), sin pasar por IRSA
    y sin descargar la extensión EPSF (el 96 % del peso de un recorte de IRSA).
    """
    url_s3 = _url_aws(url)
    coord = SkyCoord(ra=float(ra) * u.degree, dec=float(dec) * u.degree, frame="icrs")
    medio = int(np.ceil(float(fov) * 60.0 / ESCALA_PIXEL_ARCSEC / 2.0))

    with fits.open(url_s3, use_fsspec=True,
                   fsspec_kwargs={"block_size": 1_000_000, "cache_type": "bytes"}) as hdulist:
        header = hdulist["IMAGE"].header
        version = hdulist[0].header.get("VERSION", "")

        wcs_completo = WCS(header)
        x, y = wcs_completo.world_to_pixel(coord)
        x, y = float(x), float(y)
        ny, nx = int(header["NAXIS2"]), int(header["NAXIS1"])
        if not (0 <= x < nx and 0 <= y < ny):
            raise ValueError("La coordenada cae fuera de esta exposición.")

        spectral_wcs = WCS(header, fobj=hdulist, key="W")
        spectral_wcs.sip = None
        wavelength, _ = spectral_wcs.pixel_to_world(x, y)
        wl_um = float(wavelength.to(u.micrometer).value)

        xi, yi = int(round(x)), int(round(y))
        y0, y1 = max(0, yi - medio), min(ny, yi + medio)
        x0, x1 = max(0, xi - medio), min(nx, xi + medio)
        zona = (slice(y0, y1), slice(x0, x1))

        imagen = np.array(hdulist["IMAGE"].section[zona], dtype=np.float32)
        flags = np.array(hdulist["FLAGS"].section[zona], dtype=np.int32)
        varianza = np.array(hdulist["VARIANCE"].section[zona], dtype=np.float32)
        fondo = np.array(hdulist["ZODI"].section[zona], dtype=np.float32)
        bits = _bits_mascara(hdulist["FLAGS"].header)
        detector = f"D{header.get('DETECTOR', '?')}"
        fecha = float(header.get("MJD-OBS", header.get("MJD-BEG", 0.0)))

    mascara = (flags & bits) != 0
    return {
        "imagen": imagen,
        "varianza": varianza,
        "indicadores": flags,
        "mascara": mascara,
        "porcentaje_marcado": 100.0 * float(np.sum(mascara)) / float(mascara.size),
        "fondo": fondo,
        "wcs": wcs_completo[zona],
        "coordenadas": (float(ra), float(dec)),
        "fecha": fecha,
        "detector": detector,
        "longitud_onda": wl_um,
        "version": version,
        "url": url_s3,
        "origen": "AWS",
    }


def bajar(url: str, ra: float, dec: float, fov: float = 12.0) -> dict:
    """
    Pide un recorte centrado en (ra, dec) con tamaño fov (en minutos de arco).
    Devuelve solo lo necesario en memoria y cierra el archivo FITS.
    Primero lo intenta por AWS (rápido y sin la saturación de IRSA); si falla,
    usa el servicio de recortes de IRSA con reintentos.
    """
    try:
        return _bajar_aws_con_reintento(url, ra, dec, fov)
    except ValueError:
        raise  # la coordenada no está en la imagen: IRSA tampoco la tendría
    except Exception:
        return _bajar_irsa(url, ra, dec, fov)


def _bajar_aws_con_reintento(url: str, ra: float, dec: float, fov: float) -> dict:
    """Dos intentos por AWS. Un ValueError (coordenada fuera) no se reintenta."""
    try:
        return _bajar_aws(url, ra, dec, fov)
    except ValueError:
        raise
    except Exception as e:
        print(f"[Aviso] AWS falló, segundo intento: {e}")
        time.sleep(2)
        return _bajar_aws(url, ra, dec, fov)


def _bajar_irsa(url: str, ra: float, dec: float, fov: float = 12.0) -> dict:
    """Ruta de respaldo: servicio de recortes de IRSA, con reintentos largos."""
    size_deg = float(fov) / 60.0  # Convertir minutos de arco a grados
    if "?center=" in url:
        url_cutout = url
    else:
        url_cutout = f"{url}?center={float(ra)},{float(dec)}d&size={size_deg}"

    coord = SkyCoord(ra=float(ra) * u.degree, dec=float(dec) * u.degree, frame="icrs")

    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            with fits.open(url_cutout, cache=False) as hdulist:
                # Extensiones: 1=IMAGE, 2=FLAGS, 3=VARIANCE, 4=ZODI, 5=EPSF, 6=WCS-WAVE
                header = hdulist[1].header
                version = hdulist[0].header.get("VERSION", "")

                # Calcular longitud de onda central en (ra, dec) como en el tutorial
                spatial_wcs = WCS(header)
                x, y = spatial_wcs.world_to_pixel(coord)
                spectral_wcs = WCS(header, fobj=hdulist, key="W")
                spectral_wcs.sip = None
                wavelength, _ = spectral_wcs.pixel_to_world(x, y)
                wl_um = float(wavelength.to(u.micrometer).value)

                # Copiar únicamente los arreglos numéricos necesarios y soltar el resto
                imagen = np.array(hdulist["IMAGE"].data, dtype=np.float32)
                flags = np.array(hdulist["FLAGS"].data, dtype=np.int32)
                varianza = np.array(hdulist["VARIANCE"].data, dtype=np.float32)
                fondo = np.array(hdulist["ZODI"].data, dtype=np.float32)

                bits = _bits_mascara(hdulist["FLAGS"].header)
                mascara = (flags & bits) != 0
                pct_marcado = 100.0 * float(np.sum(mascara)) / float(mascara.size)

                return {
                    "imagen": imagen,
                    "varianza": varianza,
                    "indicadores": flags,
                    "mascara": mascara,
                    "porcentaje_marcado": pct_marcado,
                    "fondo": fondo,
                    "wcs": spatial_wcs,
                    "coordenadas": (float(ra), float(dec)),
                    "fecha": float(header.get("MJD-OBS", header.get("MJD-BEG", 0.0))),
                    "detector": f"D{header.get('DETECTOR', '?')}",
                    "longitud_onda": wl_um,
                    "version": version,
                    "url": url_cutout,
                    "origen": "IRSA",
                }
        except (TimeoutError, OSError, http.client.HTTPException) as e:
            # Solo se reintentan fallos de red (incluye el 503 de IRSA saturado).
            # Un error de programación sale de inmediato, sin esperar.
            if intento == MAX_REINTENTOS:
                raise RuntimeError(f"Error tras {MAX_REINTENTOS} intentos en {url_cutout}: {e}")
            time.sleep(ESPERAS_REINTENTO[intento - 1])


def _repartir_entre_epocas(exposiciones: list, max_n: int) -> list:
    """Reparte el límite max_n equitativamente entre las épocas disponibles."""
    if not max_n or len(exposiciones) <= max_n:
        return exposiciones

    por_epoca = {}
    for exp in exposiciones:
        por_epoca.setdefault(exp["epoca"], []).append(exp)

    epocas = sorted(por_epoca.keys())
    cupo = max(1, max_n // len(epocas))
    seleccion = []

    for ep in epocas:
        lista = por_epoca[ep]
        indices = np.linspace(0, len(lista) - 1, min(len(lista), cupo), dtype=int)
        for idx in indices:
            if len(seleccion) < max_n:
                seleccion.append(lista[idx])

    seleccion.sort(key=lambda x: x["fecha"])
    return seleccion


def obtener(ra: float, dec: float, fov: float = 12.0, banda: str = "D2", max_n: int = 40) -> list:
    """
    Une buscar() y la descarga, reparte max_n entre épocas, baja primero por AWS y luego por IRSA
    y guarda en disco para responder en < 2 segundos si se vuelve a pedir la misma coordenada.
    """
    os.makedirs(DIR_CACHE_LOCAL, exist_ok=True)
    clave = hashlib.md5(f"{ra:.5f}_{dec:.5f}_{fov:.2f}_{banda}_{max_n}".encode()).hexdigest()
    ruta_pkl = os.path.join(DIR_CACHE_LOCAL, f"recortes_{clave}.pkl")

    if os.path.exists(ruta_pkl):
        with open(ruta_pkl, "rb") as f:
            return pickle.load(f)

    exposiciones = buscar(ra, dec, banda=banda)
    seleccion = _repartir_entre_epocas(exposiciones, max_n=max_n)

    def _descargar(funcion, exposiciones_a_bajar, trabajadores):
        """Baja en paralelo; devuelve (recortes, exposiciones que fallaron)."""
        hechos, fallidos = [], []
        with concurrent.futures.ThreadPoolExecutor(max_workers=trabajadores) as executor:
            futuros = {
                executor.submit(funcion, exp["url"], ra, dec, fov): exp
                for exp in exposiciones_a_bajar
            }
            for futuro in concurrent.futures.as_completed(futuros):
                exp_meta = futuros[futuro]
                try:
                    rec = futuro.result()
                except ValueError:
                    continue  # la coordenada cae fuera de esa exposición
                except Exception as err:
                    print(f"[Aviso] Fallo en {funcion.__name__}: {err}")
                    fallidos.append(exp_meta)
                    continue
                rec["fecha"] = exp_meta["fecha"]
                rec["detector"] = exp_meta["detector"]
                rec["epoca"] = exp_meta["epoca"]
                hechos.append(rec)
        return hechos, fallidos

    # 1) Todo por AWS, con más descargas a la vez.
    resultados, pendientes = _descargar(_bajar_aws_con_reintento, seleccion, MAX_WORKERS_AWS)
    # 2) Lo que AWS no pudo dar se pide a IRSA, despacio.
    if pendientes:
        de_irsa, pendientes = _descargar(_bajar_irsa, pendientes, MAX_WORKERS)
        resultados.extend(de_irsa)

    resultados.sort(key=lambda x: x["fecha"])

    # Solo se guarda si llegaron todos: una descarga incompleta guardada
    # se devolvería incompleta para siempre.
    if resultados and not pendientes:
        with open(ruta_pkl, "wb") as f:
            pickle.dump(resultados, f, protocol=pickle.HIGHEST_PROTOCOL)

    return resultados
