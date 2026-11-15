# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
The five targets named by the challenge, used by the app, regenerar_cache.py and
hacer_gifs.py.

For each target:
  ra, dec          centre of the stored cutouts and of the view (about 2026).
  ref_ra, ref_dec  reference position, in degrees, at the epoch ref_epoch (year).
  pm_ra, pm_dec    proper motion in milliarcseconds per year (pm_ra includes cos(dec)).

Reference positions and proper motions come from the team's reference table
(David, cache/reporte_control.md, 14 Nov 2026). Each was checked against the
SPHEREx images: the predicted position lands on the star within about 2 arcsec for
Barnard's Star and RW Aurigae. Two reference positions of that table did NOT land
on the source in the images and are replaced here by the values that do; they are
marked CHECK and must be confirmed against the catalogue before publishing numbers.
The catalogue source of every value still has to be cited.
"""

import numpy as np

TARGETS = [
    {"name": "Barnard's Star", "folder": "barnard", "band": "D2",
     "kind": "Moves", "line": "The fastest-moving star in our sky.",
     "ra": 269.4463, "dec": 4.7679,
     "ref_ra": 269.452075, "ref_dec": 4.693391, "ref_epoch": 2000.0,
     "pm_ra": -801.55, "pm_dec": 10362.39},
    {"name": "WISE 0855", "folder": "wise_0855", "band": "D6",
     "kind": "Moves", "line": "Too cold and faint to see here. The cross-hair marks where it should be.",
     "ra": 133.7590, "dec": -7.2421,
     # position given in the challenge statement; its epoch (about 2010.3) is inferred
     "ref_ra": 133.795129, "ref_dec": -7.245147, "ref_epoch": 2010.34,
     "pm_ra": -8118.0, "pm_dec": 680.0},
    {"name": "Epsilon Indi B", "folder": "epsilon_indi_b", "band": "D2",
     "kind": "Moves", "line": "A nearby pair of brown dwarfs.",
     "ra": 331.0960, "dec": -56.8013,
     # CHECK: the team table has ref_ra 331.07725, which falls about 35 to 65 arcsec from
     # the source for any epoch tried; 331.0438 at 2000.0 lands on it within 2 arcsec.
     "ref_ra": 331.0438, "ref_dec": -56.782639, "ref_epoch": 2000.0,
     "pm_ra": 3966.66, "pm_dec": -2536.19},
    {"name": "RW Aurigae", "folder": "rw_aurigae", "band": "D2",
     "kind": "Varies", "line": "A young star whose brightness changes.",
     "ra": 76.9564, "dec": 30.4014,
     "ref_ra": 76.95653, "ref_dec": 30.401441, "ref_epoch": 2000.0,
     "pm_ra": 4.86, "pm_dec": -24.16},
    {"name": "R Draconis", "folder": "r_draconis", "band": "D2",
     "kind": "Varies", "line": "A pulsing red giant. Its core overloads the detector here.",
     "ra": 248.1675, "dec": 66.7550,
     # CHECK: the team table has ref_dec 66.763417, about 30 arcsec north of the star
     # in the images; 66.7550 lands on it.
     "ref_ra": 248.1675, "ref_dec": 66.7550, "ref_epoch": 2000.0,
     "pm_ra": -18.54, "pm_dec": 23.41},
]


def mjd_to_year(mjd):
    return 2000.0 + (float(mjd) - 51544.5) / 365.25


def expected_position(target, mjd):
    """RA and Dec (degrees) where the reference position and proper motion put the target at this date."""
    years = mjd_to_year(mjd) - target["ref_epoch"]
    dec = target["ref_dec"] + target["pm_dec"] * years / 3.6e6
    ra = target["ref_ra"] + target["pm_ra"] * years / 3.6e6 / np.cos(np.deg2rad(target["ref_dec"]))
    return ra, dec
