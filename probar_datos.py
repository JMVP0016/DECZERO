# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Quick check of the data path. Run it from the project folder:

    python probar_datos.py

It says whether IRSA and AWS answer, and whether datos.py can bring images of
a challenge target (which must work even when IRSA is down).
"""

import time
import urllib.request

import datos

IRSA = "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=circle+269.45+4.69+0.01&MAXREC=1"
AWS = "https://nasa-irsa-spherex.s3.amazonaws.com/?list-type=2&max-keys=1"


def answers(url):
    """True if the service answers without an error."""
    try:
        with urllib.request.urlopen(url, timeout=25) as reply:
            return reply.status == 200, f"HTTP {reply.status}"
    except Exception as error:
        return False, str(error)


print("1. Services")
irsa_ok, irsa_text = answers(IRSA)
aws_ok, aws_text = answers(AWS)
print(f"   IRSA (search): {'OK' if irsa_ok else 'DOWN'} - {irsa_text}")
print(f"   AWS (pixels):  {'OK' if aws_ok else 'DOWN'} - {aws_text}")

print("2. Saved search for Barnard's Star (does not need IRSA)")
try:
    exposures = datos.buscar(269.4521, 4.6934, banda="D2")
    print(f"   OK: {len(exposures)} exposures found")
except Exception as error:
    exposures = []
    print(f"   FAILED: {error}")

print("3. Download of 4 cutouts (from AWS)")
try:
    start = time.time()
    cutouts = datos.obtener(269.4521, 4.6934, fov=6.0, banda="D2", max_n=4)
    sources = {cutout["origen"] for cutout in cutouts}
    print(f"   OK: {len(cutouts)} cutouts from {sources} in {time.time() - start:.0f} s")
except Exception as error:
    cutouts = []
    print(f"   FAILED: {error}")

print("4. Result")
if exposures and cutouts:
    print("   datos.py works for the five targets.")
    if not irsa_ok:
        print("   IRSA is down: only positions far from the five targets will fail today.")
else:
    print("   datos.py is NOT working here. Run 'git pull --rebase origin main' and")
    print("   'pip install -r requirements.txt', then try again. If it still fails,")
    print("   send the full text above to Jonnathan.")
