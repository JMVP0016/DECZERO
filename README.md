# HAWAPACHA · SPHEREx sky viewer (team DecZero)

NASA Space Apps Challenge 2026 · Challenge: **Planet X and SPHEREx** · Team DecZero (Ecuador).

*HAWAPACHA means celestial space, from the Kichwa expression "hawa pacha". The name
joins astronomical exploration with the team's Ecuadorian identity and its place on
the equator line. (Linguistic reference: Kichwa glossary, FLACSO, 2018, p. 79.)*

A public web page, with no sign-up, where anyone types sky coordinates (RA/Dec)
and sees the real SPHEREx images of that area in time order.

Live app: https://deczero-bggaafdwwenl9wrdvzjlwn.streamlit.app/

This repository was created on Saturday, November 14, 2026, at the start of the
hackathon.

## What it does

- Type any sky position (degrees or sexagesimal) and choose one of the six SPHEREx
  detectors. The coordinates stay in the page address, so a view can be shared.
- See the real images in time order: a still frame with a slider and an animation
  that can be downloaded. Two views, both with north up and east left: one frame
  per observing period (median of the images of that period) or one frame per exposure.
- Five challenge targets open with one click from images stored in this repository.
  Three of them are also stored in a second detector (Barnard's Star and RW Aurigae
  in D5, Epsilon Indi B in D3), to compare other infrared colours.
- A cross-hair marks where the catalogue position and proper motion put each target.
- A difference image (last observing period minus the first) and a choice of field
  of view (4, 6 or 10 arcmin).
- A help window with real examples of what counts as a change and what can fool you.
- Visitors can report what they noticed; reports go to a public findings board
  where a reviewer signs a verdict.

## Validation (15 Nov 2026)

Tested on the five targets named by the challenge. The shift of each target between
its first and last observing period was measured on the stored SPHEREx images and
compared with the catalogue proper motion.

| Target | Period | Measured shift (east, north) | Expected | Result |
| :--- | :--- | :--- | :--- | :--- |
| Epsilon Indi B (D2) | 2025.32 to 2026.75 | +5.1", -3.9" | +5.7", -3.6" from proper motion alone; about +5.3", -4.0" with parallax | Agrees |
| Barnard's Star (D2) | 2025.65 to 2026.64 | -0.5", +10.2" | -0.8", +10.3" | North shift agrees; the core is saturated, so only the wings were fitted |
| WISE 0855 (D6) | 2025.88 to 2026.32 | about -2.8", +0.6" (uncertainty about 1") | -3.6", +0.3" | Faint source (about 10 sigma per stacked period) at the expected place; candidate detection, not seen in single exposures |
| RW Aurigae (D2) | 2025.69 to 2026.70 | +0.3", 0.0" | 0.0", 0.0" | No motion, as expected (control) |
| R Draconis (D2) | 2025.47 to 2026.47 | +0.1", -0.3" | about 0 | No motion, as expected (control) |

How it was measured: for Epsilon Indi B and RW Aurigae, a 2D Gaussian fitted in each
exposure and averaged per period; for Barnard's Star and R Draconis, whose cores
saturate, a Moffat profile fitted to the unsaturated wings; for WISE 0855, the centroid
in the stack of each period. Statistical errors are 0.1" to 0.4"; the systematic floor,
from the two controls, is about 0.5" (one SPHEREx pixel is 6.15"). The parallax values
used are approximate.

Limits: brightness changes of RW Aurigae and R Draconis cannot be measured here.
Their cores saturate in detector D2, and each exposure sees the star at a different
wavelength. The app does not detect anything by itself: the person looking at the
sequence is the one who notices a change.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Tests (synthetic data): `pip install pytest` and then `python -m pytest`.

## Files and owners

| File | What it does | Owner |
| :--- | :--- | :--- |
| `app.py` | The web page | Jonnathan |
| `datos.py` | Fetches images from the NASA archive (IRSA) | Geo |
| `proceso.py` | Aligns, groups and stacks the images | Henry, then Darwin |
| `objetivos.py` | The five challenge targets: reference positions and proper motions | David |
| `vista.py` | Turns cutouts into pictures and animations | Jonnathan |
| `gifs/` | One animation per target for the project page (made with `hacer_gifs.py`) | David |
| `cache/` | Light cutouts of the five targets (made with `regenerar_cache.py`) and saved searches | David |
| `cache_local.py` | Reads the stored cutouts | Jonnathan |
| `tema.py` | Look of the page: styles, hero, cards, loading scene | Jonnathan |
| `hallazgos.py`, `pages/3_Findings.py` | Report window and public findings board | Jonnathan |
| `fresco.py` | Reloads the project modules after an upload | Jonnathan |
| `probar_datos.py` | Quick check of the data path | Jonnathan |
| `test_proceso.py` | Tests with synthetic data | Darwin, Jonnathan |

## Findings board (prototype)

Visitors can report something they noticed in a sequence. Each report is stored as
a public issue of this repository, so its creation time is a public timestamp of the
report. Reviewers sign in with a code given by the team; opening a
report and giving a verdict are both recorded with the reviewer's name. A verdict is
a reviewer's opinion, not a confirmed discovery.

Setup (Streamlit secrets): `GITHUB_TOKEN` with Issues read/write on this repository,
and a `[REVIEWERS]` table with one `"code" = "Name, role"` line per reviewer.

## NASA data

- SPHEREx Level 2 spectral images, NASA/IPAC Infrared Science Archive (IRSA),
  collections DR1 and QR3: the latest releases available at IRSA on 15 Nov 2026.
  The position search uses the IRSA SIA service; the pixels are read from the
  public IRSA copy on AWS Open Data (`s3://nasa-irsa-spherex`). The search
  results for the five challenge targets are stored in `cache/busquedas/`
  (made with `sembrar_busquedas.py`, IRSA SIA service).

## References

Software: Streamlit, NumPy, SciPy, Astropy, astroquery, PyVO, reproject, photutils,
Matplotlib, Pillow, imageio, PyYAML, fsspec, s3fs, requests (all open source,
installed from `requirements.txt`).

- AWS Open Data copy of the IRSA SPHEREx archive: `s3://nasa-irsa-spherex`
- GitHub Issues API, used to store the reports of the findings board.
- three.js r160 (MIT licence), used for the 3D scene of the hero, loaded from the
  jsDelivr CDN: https://threejs.org
- Montserrat and Inter typefaces (SIL Open Font License), from Google Fonts.
- SPHEREx mission facts shown in the hero: https://science.nasa.gov/mission/spherex/
- IRSA tutorial "Download a collection of SPHEREx Spectral Image cutouts"
  (Caltech/IPAC-IRSA), source of the position query and cutout URL pattern:
  https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts

## Use of SI

SI tools were used as assistants; every SI-drafted file was reviewed and run
by a team member before being committed.

| Tool | Used for | Files |
| :--- | :--- | :--- |
| Claude (Anthropic) | Drafting the repository skeleton, the viewer page, the stored-image reader, the findings board, the visual theme and help texts, the dependency-check page and the diagnostics page | `app.py`, `cache_local.py`, `tema.py`, `hallazgos.py`, `pages/3_Findings.py`, `.streamlit/config.toml`, `pages/1_Diagnostics.py`, `pages/2_System_check.py`, `fresco.py`, `probar_datos.py`, `hacer_ayuda.py`, `README.md`, `requirements.txt` |
| Claude (Anthropic) | Code review, bug fixes (retries, query cache, flag mask, alignment failures) and synthetic tests | `datos.py`, `proceso.py`, `test_proceso.py`, `sembrar_busquedas.py`, `objetivos.py`, `regenerar_cache.py`, `vista.py`, `hacer_gifs.py`, `assets/icon.png` |

Each SI-assisted source file also says so in its header comment.

## License

To be decided by the team before submission.
