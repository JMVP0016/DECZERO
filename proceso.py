import numpy as np

def agrupar(fechas, modo="epoca", n_dias=14):
    """
    Agrupa índices de exposiciones por época/visita o por ventanas de N días.
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
        diff = fechas_ord[i] - (fecha_inicio_grupo if modo == "ventana" else fechas_ord[i-1])
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