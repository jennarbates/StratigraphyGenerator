"""The serve-only navigation hook for the local gradebook.

The learning course itself is in the configured navigation, so it needs no
hook. The gradebook is a draft_doc, which means the build-side guarantee (it
never reaches the published site) belongs to MkDocs. The hook owns the
navigation, which is what these tests pin down: the gradebook is appended to
the learning section during serve, left alone during build, appended once
across rebuilds, and silently absent on machines that do not have the file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.docs.mkdocs_hooks import (
    GRADEBOOK_PAGE,
    GRADEBOOK_TITLE,
    SECTION_TITLE,
    on_config,
    on_startup,
)


def make_config(tmp_path: Path, *, gradebook: bool = True) -> dict[str, Any]:
    docs_dir = tmp_path / "docs"
    if gradebook:
        page = docs_dir / GRADEBOOK_PAGE
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# Gradebook\n", encoding="utf-8")
    nav = [
        {"Home": "index.md"},
        {SECTION_TITLE: [{"Study plan": "learning/plan.md"}]},
    ]
    return {"nav": nav, "docs_dir": str(docs_dir)}


def learning_section(config: dict[str, Any]) -> list[Any]:
    return next(item[SECTION_TITLE] for item in config["nav"] if SECTION_TITLE in item)


def test_build_leaves_the_navigation_alone(tmp_path: Path) -> None:
    on_startup(command="build", dirty=False)
    config = make_config(tmp_path)

    on_config(config)

    assert learning_section(config) == [{"Study plan": "learning/plan.md"}]


def test_serve_appends_the_gradebook(tmp_path: Path) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path)

    on_config(config)

    assert learning_section(config)[-1] == {GRADEBOOK_TITLE: GRADEBOOK_PAGE}


def test_serve_appends_the_gradebook_once_across_rebuilds(tmp_path: Path) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path)

    on_config(on_config(config))

    titles = [next(iter(entry)) for entry in learning_section(config)]
    assert titles.count(GRADEBOOK_TITLE) == 1


def test_serve_skips_a_gradebook_missing_from_this_machine(tmp_path: Path) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path, gradebook=False)

    on_config(config)

    assert learning_section(config) == [{"Study plan": "learning/plan.md"}]


def test_serve_tolerates_a_navigation_without_the_learning_section(
    tmp_path: Path,
) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path)
    config["nav"] = [{"Home": "index.md"}]

    on_config(config)

    assert config["nav"] == [{"Home": "index.md"}]
