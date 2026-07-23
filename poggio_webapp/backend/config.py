"""Shared filesystem configuration."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

ALLOWED_SCAN_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".tif",
    ".tiff",
}

JOBS_DIR.mkdir(exist_ok=True)
