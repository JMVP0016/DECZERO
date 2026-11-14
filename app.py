import glob
import os
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from astropy.io import fits
from astropy.wcs import WCS

import datos
import proceso

st.set_page_config(page_title="DECZERO — SPHEREx Pipeline", layout="wide")
st.title("DECZERO — Procesamiento y Apilado Científico SPHEREx")
st.caption("Ingesta de recortes, corrección de luz zodiacal, reproyección Norte-arriba y apilado por épocas.")

OBJETOS = {
    "Estrella de Barnard (Movimiento propio)": {"carpeta": "barnard", "ra": 269.45207, "dec": 4.69339},
    "Epsilon Indi B (Enana marrón cercana)": {"carpeta": "epsilon_indi_b", "ra": 330.84023, "dec": -56.78598},
    "RW Aurigae (Estrella variable joven)": {"carpeta": "rw_aurigae", "ra": 76.95653, "dec": 30.40144},
    "R Draconis (Variable tipo Mira)": {"carpeta": "r_draconis", "ra": 248.16364, "dec": 66.75567},
    "WISE 0855 (Enana marrón ultrafría)": {"carpeta": "wise_0855", "ra": 133.79083, "dec": -7.24389},
}

def cargar_desde_cache_local(carpeta: str, max_n: int) -> list:
    archivos = sorted(glob.glob(os.path.join("cache", carpeta, "*.fits")))[:max_n]
    recortes = []
    for ruta in archivos:
        with fits.open(ruta) as hdul:
            header = hdul["IMAGE"].header
            img = np.array(hdul["IMAGE"].data, dtype=np.float32)
            zodi = np.array(hdul["ZODI"].data, dtype=np.float32) if "ZODI" in hdul else np.zeros_like(img)
            if "FLAGS" in hdul:
                flags = np.array(hdul["FLAGS"].data, dtype=np.int32)
                bits_malos = datos._bits_mascara(hdul["FLAGS"].header)
                mascara = (flags & bits_malos) != 0
            else:
                mascara = np.zeros(img.shape, dtype=bool)
            recortes.append({
                "imagen": img,
                "fondo": zodi,
                "mascara": mascara,
                "wcs": WCS(header),
                "fecha": float(header.get("MJD-OBS", header.get("MJD-BEG", 0.0))),
                "detector": f"D{header.get('DETECTOR', '?')}",
            })
    return recortes

with st.sidebar:
    st.header("Configuración")
    nombre_obj = st.selectbox("Objeto celeste", list(OBJETOS.keys()))
    info_obj = OBJETOS[nombre_obj]
    fuente = st.radio("Fuente de datos", ["Caché local (cache/)", "Consulta IRSA en vivo (datos.obtener)"])
    banda = st.selectbox("Detector / Banda SPHEREx", ["D2", "D1", "D3", "D4", "D5", "D6"])
    max_n = st.slider("Máximo de recortes", min_value=3, max_value=50, value=15)
    modo_grupo = st.selectbox("Agrupamiento temporal", ["epoca", "dias"])
    ejecutar = st.button("Procesar y Apilar", type="primary", use_container_width=True)

if ejecutar:
    with st.spinner("Cargando recortes y ejecutando pipeline..."):
        if fuente.startswith("Caché"):
            recortes = cargar_desde_cache_local(info_obj["carpeta"], max_n)
            ra_centro, dec_centro = info_obj["ra"], info_obj["dec"]
        else:
            recortes = datos.obtener(info_obj["ra"], info_obj["dec"], fov=12.0, banda=banda, max_n=max_n)
            ra_centro, dec_centro = info_obj["ra"], info_obj["dec"]

        if not recortes:
            st.error("No se encontraron recortes para esta selección.")
            st.stop()

        w0 = recortes[0]["wcs"]
        x_chk, y_chk = w0.world_to_pixel_values(ra_centro, dec_centro)
        if not (0 <= x_chk < recortes[0]["imagen"].shape[1] and 0 <= y_chk < recortes[0]["imagen"].shape[0]):
            c = w0.pixel_to_world(58, 58)
            ra_centro, dec_centro = float(c.ra.deg), float(c.dec.deg)

        imgs_limpias = [
            proceso.restar_fondo(r["imagen"] - r["fondo"], mascara=r["mascara"])
            for r in recortes
        ]
        wcs_list = [r["wcs"] for r in recortes]
        mascaras = [r["mascara"] for r in recortes]
        fechas = [r["fecha"] for r in recortes]

        rejilla, forma = proceso.crear_rejilla_norte(ra_centro, dec_centro, tamano_pix=64, escala_arcsec=6.2)
        alineados, indices_ok = proceso.reproyectar(imgs_limpias, wcs_list, rejilla, forma, mascaras=mascaras)

        if not alineados:
            st.error("Ningún recorte pudo reproyectarse sobre la rejilla.")
            st.stop()

        imagen_final = proceso.apilar(alineados)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recortes cargados", len(recortes))
    c2.metric("Alineados válidos", len(alineados))
    c3.metric("Píxeles NaN finales", int(np.isnan(imagen_final).sum()))
    c4.metric("Señal máxima (MJy/sr)", f"{float(np.nanmax(imagen_final)):.2f}")

    def mostrar_imagen(ax, matriz, titulo):
        vmin, vmax = np.nanpercentile(matriz, [5, 99.5])
        im = ax.imshow(matriz, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax)
        ax.set_title(titulo)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    st.subheader("Comparación Visual: Recorte Individual Crudo vs. Apilado Norte-Arriba")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    mostrar_imagen(axes[0], recortes[0]["imagen"], f"Crudo individual #0 (MJD {fechas[0]:.1f})")
    mostrar_imagen(axes[1], imagen_final, f"Apilado Norte-arriba ({len(alineados)} recortes)")
    st.pyplot(fig)

    fechas_ok = [fechas[i] for i in indices_ok]
    grupos = proceso.agrupar(fechas_ok, modo=modo_grupo)
    if len(grupos) >= 2:
        st.subheader(f"Evolución Temporal ({len(grupos)} épocas detectadas)")
        cols_ep = st.columns(min(len(grupos), 3))
        for idx_g, (etiqueta, idxs) in enumerate(list(grupos.items())[:3]):
            stack_ep = proceso.apilar([alineados[i] for i in idxs])
            fig_ep, ax_ep = plt.subplots(figsize=(4.5, 4.2))
            mostrar_imagen(ax_ep, stack_ep, f"{etiqueta} ({len(idxs)} recortes)")
            cols_ep[idx_g].pyplot(fig_ep)
