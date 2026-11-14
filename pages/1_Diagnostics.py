# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
#
# The TAP query and the cutout URL pattern are adapted from the official
# IRSA tutorial "Download a collection of SPHEREx Spectral Image cutouts":
# https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts
"""Measurement M0: how long one IRSA query and N cutouts take from this machine."""

import io
import time
import urllib.request

import streamlit as st
from astropy.io import fits
from astroquery.ipac.irsa import Irsa

st.set_page_config(page_title="Diagnostics · DecZero", layout="wide")
st.title("Diagnostics (M0)")
st.caption(
    "One position query to IRSA and a few cutouts, with times and sizes. "
    "Run it here and on a laptop to compare cloud against local."
)

left, right = st.columns(2)
ra = left.number_input("RA (deg)", value=210.80227, format="%.5f")
dec = left.number_input("Dec (deg)", value=54.34895, format="%.5f")
size = right.number_input("Cutout size (deg)", value=0.1, min_value=0.01, max_value=0.5)
band = right.selectbox("Detector", [f"SPHEREx-D{i}" for i in range(1, 7)], index=1)
count = st.slider("Cutouts to download", 1, 20, 10)

if st.button("Run measurement", type="primary"):
    query = f"""
    SELECT 'https://irsa.ipac.caltech.edu/' || a.uri
               || '?center={ra},{dec}d&size={size}' AS uri,
           p.time_bounds_lower
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
      AND p.energy_bandpassname = '{band}'
    ORDER BY p.time_bounds_lower
    """

    with st.spinner("Querying IRSA..."):
        start = time.time()
        try:
            table = Irsa.query_tap(query).to_table()
        except Exception as error:
            st.error(f"The query failed after {time.time() - start:.1f} s: {error}")
            st.stop()
        query_seconds = time.time() - start

    st.write(f"Query: **{query_seconds:.1f} s** · images found: **{len(table)}**")
    if len(table) == 0:
        st.warning("No SPHEREx images cover this position in this detector.")
        st.stop()

    rows = []
    progress = st.progress(0.0)
    subset = table[:count]
    for index, row in enumerate(subset):
        entry = {"mjd": float(row["time_bounds_lower"])}
        start = time.time()
        try:
            data = urllib.request.urlopen(row["uri"], timeout=120).read()
            entry["seconds"] = round(time.time() - start, 2)
            entry["MB"] = round(len(data) / 1e6, 2)
            with fits.open(io.BytesIO(data)) as hdus:
                entry["version"] = hdus[0].header.get("VERSION", "")
                entry["extensions"] = ", ".join(hdu.name for hdu in hdus[1:])
                entry["image shape"] = str(hdus[1].data.shape)
            entry["status"] = "ok"
        except Exception as error:
            entry["seconds"] = round(time.time() - start, 2)
            entry["status"] = f"FAILED: {error}"
        rows.append(entry)
        progress.progress((index + 1) / len(subset))

    good = [entry for entry in rows if entry["status"] == "ok"]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    if good:
        mean_seconds = sum(entry["seconds"] for entry in good) / len(good)
        mean_mb = sum(entry["MB"] for entry in good) / len(good)
        a, b, c, d = st.columns(4)
        a.metric("Query", f"{query_seconds:.1f} s")
        b.metric("Per cutout", f"{mean_seconds:.1f} s")
        c.metric("Per cutout", f"{mean_mb:.1f} MB")
        d.metric("Failed", f"{len(rows) - len(good)} of {len(rows)}")
    else:
        st.error("Every cutout failed. IRSA may not be reachable from this machine.")
