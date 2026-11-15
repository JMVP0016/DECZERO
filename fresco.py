# DecZero - NASA Space Apps Challenge 2026 - Planet X and SPHEREx
# SI disclosure: this file was drafted with an SI tool (Claude, Anthropic)
# and reviewed and run by the team. See "Use of SI" in README.md.
"""
Keeps the project's own modules up to date in a running app.

After a new version is uploaded, the hosting service runs the new app.py but may
keep the previous copy of the other modules in memory. That mix caused an
AttributeError on the published app. This reloads a module when its file on
disk is newer than the copy in memory.
"""

import importlib
import os
import sys

# dependencies first
MODULES = ["proceso", "datos", "cache_local", "objetivos", "vista", "tema", "hallazgos"]


def actualizar():
    """Reload each project module whose file changed since it was loaded."""
    for name in MODULES:
        module = sys.modules.get(name)
        if module is None:
            continue   # not imported yet: the normal import will read the new file
        try:
            changed = os.path.getmtime(module.__file__)
        except (OSError, AttributeError, TypeError):
            continue
        # no mark yet means we cannot tell how old the copy in memory is: reload once
        if getattr(module, "_fresco_mtime", None) != changed:
            module = importlib.reload(module)
            module._fresco_mtime = changed
