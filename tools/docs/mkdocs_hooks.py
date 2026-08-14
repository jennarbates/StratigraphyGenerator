"""MkDocs hooks: reveal the local-only learning pages during `mkdocs serve`.

docs/learning/ holds the study plan and its assessment pack. Those pages are
listed in mkdocs.yml's `draft_docs`, so `mkdocs build` — and with it CI, the
`--strict` check, and the published site — leaves them out, while
`mkdocs serve` renders them for local reading. Drafts stay out of the
configured navigation, because a nav entry for a page the build excludes
would be a broken link and a `--strict` failure. Without help, then, the
served pages would be reachable only by typing their URLs; this hook adds
their section to the navigation when, and only when, they are being served.
(`mkdocs serve --clean` hides drafts again; the added entries then log
warnings, and serving continues.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SECTION_TITLE = "Learning course"
# The gradebook is written by the grade-assessment skill on machines where
# a course is being taken; the existence check below skips it elsewhere.
SECTION_PAGES = (
    ("Study plan", "learning/plan.md"),
    ("Assessments", "learning/assessments.md"),
    ("CS study plan", "learning/cs-plan.md"),
    ("CS assessments", "learning/cs-assessments.md"),
    ("Gradebook", "learning/gradebook.md"),
)

# `on_config` is not told which command is running, so `on_startup` records
# it. MkDocs keeps hook modules loaded across serve's rebuilds, which makes a
# module-level variable the supported place to carry that state.
_command = ""


def on_startup(*, command: str, dirty: bool) -> None:
    """Record whether this run is `build`, `gh-deploy`, or `serve`."""

    del dirty  # Part of the event signature; irrelevant to nav visibility.
    global _command
    _command = command


def on_config(config: Any) -> Any:
    """Append the learning section to the navigation, during serve only."""

    nav = config.get("nav")
    if _command != "serve" or not nav:
        return config

    # The pages are not committed on every machine; a missing file is a
    # machine without the learning material, not an error.
    docs_dir = Path(config["docs_dir"])
    pages = [
        {title: page} for title, page in SECTION_PAGES if (docs_dir / page).exists()
    ]

    already_added = any(
        isinstance(item, dict) and SECTION_TITLE in item for item in nav
    )
    if pages and not already_added:
        nav.append({SECTION_TITLE: pages})
    return config
