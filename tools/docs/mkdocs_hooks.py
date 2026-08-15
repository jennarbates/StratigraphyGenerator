"""MkDocs hooks: reveal the local-only gradebook during `mkdocs serve`.

docs/learning/ holds the study plans and their assessment packs, and those
pages are in the configured navigation like any other. The gradebook is the
exception: the grade-assessment skill writes one reader's own exam scores into
it, so mkdocs.yml lists it in `draft_docs` and `mkdocs build` — and with it CI,
the `--strict` check, and the published site — leaves it out, while
`mkdocs serve` renders it for local reading. Drafts stay out of the configured
navigation, because a nav entry for a page the build excludes would be a broken
link and a `--strict` failure. Without help, then, the served page would be
reachable only by typing its URL; this hook appends it to the learning section
when, and only when, it is being served. (`mkdocs serve --clean` hides drafts
again; the added entry then logs a warning, and serving continues.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SECTION_TITLE = "Learning course"
GRADEBOOK_TITLE = "Gradebook"
GRADEBOOK_PAGE = "learning/gradebook.md"

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
    """Append the gradebook to the learning section, during serve only."""

    nav = config.get("nav")
    if _command != "serve" or not nav:
        return config

    # The gradebook exists only on a machine where a course is being taken; a
    # missing file is a reader who has not sat an exam yet, not an error.
    docs_dir = Path(config["docs_dir"])
    if not (docs_dir / GRADEBOOK_PAGE).exists():
        return config

    section = next(
        (
            item[SECTION_TITLE]
            for item in nav
            if isinstance(item, dict) and SECTION_TITLE in item
        ),
        None,
    )
    if section is None:
        return config

    already_added = any(
        isinstance(entry, dict) and GRADEBOOK_TITLE in entry for entry in section
    )
    if not already_added:
        section.append({GRADEBOOK_TITLE: GRADEBOOK_PAGE})
    return config
