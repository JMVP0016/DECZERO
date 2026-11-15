# HAWAPACHA · SPHEREx sky viewer (team DecZero)

NASA Space Apps Challenge 2026 · Challenge: **Planet X and SPHEREx** · Team DecZero (Ecuador).

A public web page, with no sign-up, where anyone types sky coordinates (RA/Dec)
and sees the real SPHEREx images of that area in time order.

Live app: https://deczero-bggaafdwwenl9wrdvzjlwn.streamlit.app/

> Work in progress. This repository was created on Saturday, November 14, 2026,
> at the start of the hackathon.

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
| `render.py` | Turns data into images and animations | David |
| `objetivos.py` | The five challenge targets (positions still provisional) | David |
| `cache/` | Light cutouts of the five targets (made with `regenerar_cache.py`) and saved searches | David |
| `validacion.ipynb` | The numbers behind each target | David and Henry |

## Findings board (prototype)

Visitors can report something they noticed in a sequence. Each report is stored as
a public issue of this repository, so its creation time is a public timestamp of the
report. Reviewers sign in with a code given by the team; opening a
report and giving a verdict are both recorded with the reviewer's name. A verdict is
a reviewer's opinion, not a confirmed discovery.

Setup (Streamlit secrets): `GITHUB_TOKEN` with Issues read/write on this repository,
and a `[REVIEWERS]` table with one `"code" = "Name, role"` line per reviewer.

## NASA data

- SPHEREx Level 2 spectral images, NASA/IPAC Infrared Science Archive (IRSA).
  The position search uses the IRSA SIA service; the pixels are read from the
  public IRSA copy on AWS Open Data (`s3://nasa-irsa-spherex`). The search
  results for the five challenge targets are stored in `cache/busquedas/`
  (made with `sembrar_busquedas.py`, IRSA SIA service).

## References

To be completed during the hackathon: every external code, text, image and
tool used, even if open source or freely available.

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
| Claude (Anthropic) | Drafting the repository skeleton, the viewer page, the stored-image reader, the findings board, the visual theme and help texts, the dependency-check page and the diagnostics page | `app.py`, `cache_local.py`, `tema.py`, `hallazgos.py`, `pages/3_Findings.py`, `.streamlit/config.toml`, `pages/1_Diagnostics.py`, `pages/2_System_check.py`, `README.md`, `requirements.txt` |
| Claude (Anthropic) | Code review, bug fixes (retries, query cache, flag mask, alignment failures) and synthetic tests | `datos.py`, `proceso.py`, `test_proceso.py`, `sembrar_busquedas.py`, `objetivos.py`, `regenerar_cache.py`, `assets/icon.png` |

Each SI-assisted source file also says so in its header comment.

## License

To be decided by the team before submission.
