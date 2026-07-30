from __future__ import annotations

from pathlib import Path

from tools.docs.check_coverage import (
    EXEMPT_STEMS,
    find_uncovered,
    iter_watched_modules,
    main,
)


def make_repository(tmp_path: Path, docs_text: str, modules: dict[str, str]) -> Path:
    """Build a miniature repository with the given modules and one docs page."""

    for relative, body in modules.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.md").write_text(docs_text, encoding="utf-8")
    return tmp_path


def test_module_named_by_path_is_covered(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        "See `poggio_webapp/pipeline/merge_walls.py` for the merge layer.\n",
        {"poggio_webapp/pipeline/merge_walls.py": ""},
    )

    assert find_uncovered(repo) == []


def test_front_matter_source_files_entry_is_covered(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        "---\nsource_files:\n  - poggio_webapp/pipeline/merge_walls.py\n---\n",
        {"poggio_webapp/pipeline/merge_walls.py": ""},
    )

    assert find_uncovered(repo) == []


def test_bare_module_name_does_not_count(tmp_path: Path) -> None:
    """The full path is required, so an ordinary English word cannot cover a
    module by accident -- the failure mode this check exists to prevent."""

    repo = make_repository(
        tmp_path,
        "Several trenches were excavated at the site.\n",
        {"poggio_webapp/backend/routes/trenches.py": ""},
    )

    uncovered = find_uncovered(repo)

    assert [issue.module for issue in uncovered] == [
        "poggio_webapp/backend/routes/trenches.py"
    ]


def test_unmentioned_module_is_reported(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        "This page mentions nothing in particular.\n",
        {"poggio_webapp/pipeline/merge_walls.py": ""},
    )

    uncovered = find_uncovered(repo)

    assert [issue.module for issue in uncovered] == [
        "poggio_webapp/pipeline/merge_walls.py"
    ]


def test_prefix_match_does_not_vacuously_cover(tmp_path: Path) -> None:
    """A page naming `harris.py` must not silently cover `harris_store.py`."""

    repo = make_repository(
        tmp_path,
        "See `poggio_webapp/backend/routes/harris.py` for the routes.\n",
        {
            "poggio_webapp/backend/routes/harris.py": "",
            "poggio_webapp/backend/harris_store.py": "",
        },
    )

    uncovered = find_uncovered(repo)

    assert [issue.module for issue in uncovered] == [
        "poggio_webapp/backend/harris_store.py"
    ]


def test_readme_counts_as_documentation(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        "Nothing here.\n",
        {"poggio_webapp/pipeline/merge_walls.py": ""},
    )
    (repo / "README.md").write_text(
        "Uses `poggio_webapp/pipeline/merge_walls.py` to combine.\n", encoding="utf-8"
    )

    assert find_uncovered(repo) == []


def test_exempt_modules_are_not_watched(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        "Nothing here.\n",
        {"poggio_webapp/pipeline/__init__.py": ""},
    )

    assert iter_watched_modules(repo) == []
    assert "__init__" in EXEMPT_STEMS


def test_pycache_is_ignored(tmp_path: Path) -> None:
    repo = make_repository(
        tmp_path,
        "Nothing here.\n",
        {"poggio_webapp/pipeline/__pycache__/stale.py": ""},
    )

    assert iter_watched_modules(repo) == []


def test_main_returns_one_when_a_module_is_undocumented(
    tmp_path: Path, capsys
) -> None:
    repo = make_repository(
        tmp_path,
        "Nothing here.\n",
        {"poggio_webapp/pipeline/merge_walls.py": ""},
    )

    assert main([str(repo)]) == 1
    assert "merge_walls.py" in capsys.readouterr().out


def test_main_returns_zero_when_every_module_is_documented(
    tmp_path: Path, capsys
) -> None:
    repo = make_repository(
        tmp_path,
        "Uses `poggio_webapp/pipeline/merge_walls.py`.\n",
        {"poggio_webapp/pipeline/merge_walls.py": ""},
    )

    assert main([str(repo)]) == 0
    assert "coverage passed" in capsys.readouterr().out


def test_missing_package_directory_is_not_an_error(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "index.md").write_text("Empty repository.\n", encoding="utf-8")

    assert iter_watched_modules(tmp_path) == []
    assert find_uncovered(tmp_path) == []
