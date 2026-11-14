# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: parts of this file were revised with an SI tool (Claude,
# Anthropic) and run by the team. See "Use of SI" in README.md.
import numpy as np
from astropy.wcs import WCS
from reproject import reproject_interp

def agrupar(fechas, modo="epoca", n_dias=14):
    """
    Agrupa índices de exposiciones por época/visita o por ventanas de N días.
    Para R Draconis se usa modo='ventana' con n_dias=14.
    """
    fechas = np.asarray(fechas)
    orden = np.argsort(fechas)
    fechas_ord = fechas[orden]
    grupos = []
    if len(fechas_ord) == 0:
        return grupos

    grupo_actual = [int(orden[0])]
    fecha_inicio_grupo = fechas_ord[0]

    for i in range(1, len(fechas_ord)):
        diff = fechas_ord[i] - (fecha_inicio_grupo if modo == "ventana" else fechas_ord[i - 1])
        if modo == "ventana":
            mismo_grupo = diff < n_dias  # ventana de exactamente n_dias
        else:
            mismo_grupo = diff <= 30.0

        if mismo_grupo:
            grupo_actual.append(int(orden[i]))
        else:
            grupos.append(grupo_actual)
            grupo_actual = [int(orden[i])]
            fecha_inicio_grupo = fechas_ord[i]
            
    grupos.append(grupo_actual)
    return grupos

def apilar(imagenes):
    """
    Combina una lista o array 3D de imágenes (N, alto, ancho) en una sola imagen 2D.
    """
    cubo = np.asarray(imagenes, dtype=float)
    if cubo.ndim != 3 or cubo.shape[0] == 0:
        raise ValueError("Se espera un array 3D con al menos una imagen.")
    
    return np.nanmedian(cubo, axis=0)

def restar_fondo(imagen, mascara=None):
    """
    Resta el nivel de fondo del cielo (mediana espacial)
    sin normalizar ni escalar el brillo de las fuentes.
    Si se pasa una máscara (True = píxel defectuoso), esos píxeles
    quedan como NaN y no entran en la mediana ni en el apilado.
    """
    img = np.array(imagen, dtype=float)
    if mascara is not None:
        img[np.asarray(mascara, dtype=bool)] = np.nan
    fondo = np.nanmedian(img)
    return img - fondo

def crear_rejilla_norte(ra_centro, dec_centro, tamano_pix=120, escala_arcsec=3.0):
    """
    Crea un WCS de referencia orientado con Norte arriba y Este a la izquierda,
    con resolución de ~3 segundos de arco por píxel.
    Con 120 píxeles el campo es de 6 minutos de arco, igual que un recorte de 0.1 grados.
    Al dibujar hay que usar origin="lower" para que el norte quede arriba.
    """
    escala_deg = escala_arcsec / 3600.0
    w = WCS(naxis=2)
    w.wcs.crpix = [(tamano_pix + 1) / 2.0, (tamano_pix + 1) / 2.0]  # centro exacto
    w.wcs.cdelt = np.array([-escala_deg, escala_deg])
    w.wcs.crval = [ra_centro, dec_centro]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    return w, (tamano_pix, tamano_pix)

def reproyectar(recortes, wcs_list, rejilla_wcs, shape_salida, mascaras=None):
    """
    Lleva una lista de recortes 2D a la misma rejilla común norte-arriba.

    Devuelve (alineados, indices_ok):
      - alineados: imágenes ya alineadas, todas con forma shape_salida.
      - indices_ok: posición en la lista de entrada de cada imagen alineada,
        para poder emparejarla con su fecha y su detector.
    Un recorte que no se puede alinear se descarta: nunca se devuelve sin
    alinear, porque al apilarlo crearía movimientos falsos.
    """
    if mascaras is None:
        mascaras = [None] * len(recortes)

    alineados = []
    indices_ok = []
    for i, (img, wcs_in, mascara) in enumerate(zip(recortes, wcs_list, mascaras)):
        try:
            img_sin_fondo = restar_fondo(img, mascara)
            reproj, _ = reproject_interp(
                (img_sin_fondo, wcs_in),
                rejilla_wcs,
                shape_out=shape_salida
            )
        except Exception as error:
            print(f"[Aviso] Recorte {i} descartado al reproyectar: {error}")
            continue
        alineados.append(reproj)
        indices_ok.append(i)
    return alineados, indices_ok
