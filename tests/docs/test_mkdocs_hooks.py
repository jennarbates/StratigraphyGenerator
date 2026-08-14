"""The serve-only navigation hook for the local learning pages.

The pages themselves are draft_docs, so the build-side guarantee (they never
reach the published site) belongs to MkDocs. What the hook owns — and what
these tests pin down — is the navigation: present during serve, untouched
during build, appended once, and silently smaller on machines that do not
have the files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.docs.mkdocs_hooks import SECTION_TITLE, on_config, on_startup


def make_config(tmp_path: Path) -> dict[str, Any]:
    docs_dir = tmp_path / "docs"
    for name in ("plan.md", "assessments.md"):
        page = docs_dir / "learning" / name
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# Page\n", encoding="utf-8")
    return {"nav": [{"Home": "index.md"}], "docs_dir": str(docs_dir)}


def test_build_leaves_the_navigation_alone(tmp_path: Path) -> None:
    on_startup(command="build", dirty=False)
    config = make_config(tmp_path)

    on_config(config)

    assert config["nav"] == [{"Home": "index.md"}]


def test_serve_appends_the_learning_section(tmp_path: Path) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path)

    on_config(config)

    assert config["nav"][-1] == {
        SECTION_TITLE: [
            {"Study plan": "learning/plan.md"},
            {"Assessments": "learning/assessments.md"},
        ]
    }


def test_serve_appends_the_section_once_across_rebuilds(tmp_path: Path) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path)

    on_config(on_config(config))

    titles = [next(iter(item)) for item in config["nav"]]
    assert titles.count(SECTION_TITLE) == 1


def test_serve_skips_pages_missing_from_this_machine(tmp_path: Path) -> None:
    on_startup(command="serve", dirty=False)
    config = make_config(tmp_path)
    (Path(config["docs_dir"]) / "learning" / "assessments.md").unlink()

    on_config(config)

    assert config["nav"][-1] == {SECTION_TITLE: [{"Study plan": "learning/plan.md"}]}
