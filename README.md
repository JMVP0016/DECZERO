# DecZero · SPHEREx viewer

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

## Files and owners

| File | What it does | Owner |
| :--- | :--- | :--- |
| `app.py` | The web page | Jonnathan |
| `datos.py` | Fetches images from the NASA archive (IRSA) | Geo |
| `proceso.py` | Aligns, groups, stacks, subtracts and measures | Henry |
| `render.py` | Turns data into images and animations | David |
| `objetivos.yaml` | The five challenge targets | David |
| `cache/` | The five targets, already processed | David |
| `validacion.ipynb` | The numbers behind each target | David and Henry |

## NASA data

- SPHEREx Level 2 spectral images, NASA/IPAC Infrared Science Archive (IRSA).

## References

To be completed during the hackathon: every external code, text, image and
tool used, even if open source or freely available.

- IRSA tutorial "Download a collection of SPHEREx Spectral Image cutouts"
  (Caltech/IPAC-IRSA), source of the position query and cutout URL pattern:
  https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts

## Use of SI

SI tools were used as assistants; every SI-drafted file was reviewed and run
by a team member before being committed.

| Tool | Used for | Files |
| :--- | :--- | :--- |
| Claude (Anthropic) | Drafting the repository skeleton, the dependency-check page and the diagnostics page | `app.py`, `pages/1_Diagnostics.py`, `README.md`, `requirements.txt` |

Each SI-assisted source file also says so in its header comment.

## License

To be decided by the team before submission.
