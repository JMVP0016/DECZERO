# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""Proves that every dependency installs and imports in the cloud."""

import importlib
import platform

import streamlit as st

st.set_page_config(page_title="System check · DecZero", layout="wide")

st.title("System check")
st.caption("DecZero · NASA Space Apps Challenge 2026 · Planet X and SPHEREx")

# Every library the project needs. If one fails to import here,
# it will fail on Sunday too, so we want to see it now.
LIBRARIES = [
    "numpy",
    "astropy",
    "astroquery",
    "pyvo",
    "reproject",
    "photutils",
    "matplotlib",
    "PIL",
    "imageio",
    "yaml",
    "fsspec",
    "s3fs",
]

st.subheader("Dependency check")
st.write(f"Python {platform.python_version()}")

rows = []
failed = []
for name in LIBRARIES:
    try:
        module = importlib.import_module(name)
        rows.append(
            {"library": name, "status": "ok", "version": getattr(module, "__version__", "?")}
        )
    except Exception as error:  # show any import problem, whatever its type
        rows.append({"library": name, "status": "FAILED", "version": str(error)})
        failed.append(name)

st.dataframe(rows, hide_index=True, use_container_width=True)

if failed:
    st.error("Failed to import: " + ", ".join(failed))
else:
    st.success("All libraries imported without error.")
