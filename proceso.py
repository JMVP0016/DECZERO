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
        limite = n_dias if modo == "ventana" else 30.0
        
        if diff <= limite:
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

def restar_fondo(imagen):
    """
    Resta el nivel de fondo del cielo (mediana espacial)
    sin normalizar ni escalar el brillo de las fuentes.
    """
    img = np.asarray(imagen, dtype=float)
    fondo = np.nanmedian(img)
    return img - fondo

def crear_rejilla_norte(ra_centro, dec_centro, tamano_pix=64, escala_arcsec=3.0):
    """
    Crea un WCS de referencia orientado con Norte arriba y Este a la izquierda,
    con resolución de ~3 segundos de arco por píxel.
    """
    escala_deg = escala_arcsec / 3600.0
    w = WCS(naxis=2)
    w.wcs.crpix = [tamano_pix / 2.0, tamano_pix / 2.0]
    w.wcs.cdelt = np.array([-escala_deg, escala_deg])
    w.wcs.crval = [ra_centro, dec_centro]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    return w, (tamano_pix, tamano_pix)

def reproyectar(recortes, wcs_list, rejilla_wcs, shape_salida):
    """
    Lleva una lista de recortes 2D a la misma rejilla común norte-arriba.
    Si falla en algún recorte, conserva el recorte original con fondo restado.
    """
    alineados = []
    for img, wcs_in in zip(recortes, wcs_list):
        img_sin_fondo = restar_fondo(img)
        try:
            reproj, _ = reproject_interp(
                (img_sin_fondo, wcs_in),
                rejilla_wcs,
                shape_out=shape_salida
            )
            alineados.append(reproj)
        except Exception:
            alineados.append(img_sin_fondo)
    return alineados