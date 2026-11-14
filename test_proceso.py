# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and run by the team. See "Use of SI" in README.md.
"""Pruebas con datos sintéticos. Ejecutar con: python -m pytest"""

import numpy as np
from astropy.wcs import WCS

import proceso


def _wcs_girado(ra, dec, grados, escala_arcsec=6.15, centro=30):
    """WCS de un recorte como los de SPHEREx: girado y con píxel de 6.15 arcsec."""
    angulo = np.deg2rad(grados)
    escala = escala_arcsec / 3600.0
    w = WCS(naxis=2)
    w.wcs.crpix = [centro, centro]
    w.wcs.crval = [ra, dec]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.cd = np.array([
        [-escala * np.cos(angulo), escala * np.sin(angulo)],
        [escala * np.sin(angulo), escala * np.cos(angulo)],
    ])
    return w


def test_agrupar_por_epoca():
    assert proceso.agrupar([0, 1, 2, 180, 181, 400]) == [[0, 1, 2], [3, 4], [5]]


def test_agrupar_por_ventana_de_14_dias():
    grupos = proceso.agrupar([0, 5, 13, 14, 15, 40], modo="ventana", n_dias=14)
    assert grupos == [[0, 1, 2], [3, 4], [5]]


def test_apilar_ignora_nan():
    cubo = np.ones((3, 4, 4))
    cubo[0, 0, 0] = np.nan
    assert np.allclose(proceso.apilar(cubo), 1.0)


def test_restar_fondo_con_mascara():
    imagen = np.full((10, 10), 5.0)
    imagen[0, 0] = 1000.0
    mascara = np.zeros((10, 10), dtype=bool)
    mascara[0, 0] = True
    resultado = proceso.restar_fondo(imagen, mascara)
    assert np.isnan(resultado[0, 0])
    assert np.nanmax(np.abs(resultado)) == 0.0


def test_reproyectar_centra_la_estrella():
    ra, dec = 210.8, 54.35
    rejilla, forma = proceso.crear_rejilla_norte(ra, dec)
    imagen = np.zeros((59, 59))
    imagen[29, 29] = 100.0  # estrella en el píxel de referencia
    alineados, indices = proceso.reproyectar(
        [imagen], [_wcs_girado(ra, dec, 30)], rejilla, forma
    )
    assert indices == [0]
    assert alineados[0].shape == forma
    y, x = np.unravel_index(np.nanargmax(alineados[0]), forma)
    x_esperado, y_esperado = rejilla.world_to_pixel_values(ra, dec)
    assert abs(x - x_esperado) <= 1 and abs(y - y_esperado) <= 1


def test_reproyectar_descarta_el_recorte_que_falla():
    ra, dec = 210.8, 54.35
    rejilla, forma = proceso.crear_rejilla_norte(ra, dec)
    imagen = np.zeros((59, 59))
    alineados, indices = proceso.reproyectar(
        [imagen, imagen], [_wcs_girado(ra, dec, 0), None], rejilla, forma
    )
    assert indices == [0]
    assert proceso.apilar(alineados).shape == forma
