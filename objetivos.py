# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
The five targets named by the challenge, used by the app and by regenerar_cache.py.

PROVISIONAL POSITIONS: catalogue positions moved to about 2026 with approximate
proper motions, good enough to centre a 12-arcmin cutout. They must be replaced by
positions with a cited source (Gaia DR3 or the discovery papers) before any
measurement is published.
"""

TARGETS = [
    {"name": "Barnard's Star", "folder": "barnard", "ra": 269.4463, "dec": 4.7679, "band": "D2"},
    {"name": "WISE 0855", "folder": "wise_0855", "ra": 133.7590, "dec": -7.2421, "band": "D6"},
    {"name": "Epsilon Indi B", "folder": "epsilon_indi_b", "ra": 331.0960, "dec": -56.8013, "band": "D2"},
    {"name": "RW Aurigae", "folder": "rw_aurigae", "ra": 76.9564, "dec": 30.4014, "band": "D2"},
    {"name": "R Draconis", "folder": "r_draconis", "ra": 248.1675, "dec": 66.7550, "band": "D2"},
]
