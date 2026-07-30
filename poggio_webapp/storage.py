"""The single definition of where this app keeps things on disk.

A leaf module: it imports nothing from ``backend`` or ``pipeline``, so both
layers can depend on it without inverting the dependency direction.

Read these through the module — ``storage.JOBS_DIR``, never
``from storage import JOBS_DIR``. The ``from`` form binds the value at import
time, which is what previously left four modules holding private copies that a
test could not redirect. Reading the attribute at call time means one
assignment moves every consumer at once, which is exactly what the test
fixtures rely on.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

JOBS_DIR = BASE_DIR / "jobs"
TRENCHES_DIR = BASE_DIR / "trenches"
MATRICES_DIR = BASE_DIR / "matrices"

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


def ensure_dirs():
    """Create the writable roots if they are missing."""
    for directory in (JOBS_DIR, TRENCHES_DIR, MATRICES_DIR):
        directory.mkdir(exist_ok=True)


ensure_dirs()
