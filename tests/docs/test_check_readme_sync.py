from __future__ import annotations

from pathlib import Path

import yaml

from tools.docs.check_readme_sync import (
    check_images,
    check_links,
    check_sections,
    main,
    nav_sections,
    readme_headings,
    run_checks,
)

NAV = {
    "nav": [
        {"Home": "index.md"},
        {"Start here": [{"Quickstart": "start-here/quickstart.md"}]},
        {"Reference": [{"Data schemas": "reference/data-schemas.md"}]},
    ]
}

README = """# Project

## Start here

See the [quickstart](docs/start-here/quickstart.md).

![A diagram](docs/assets/diagrams/example.svg)

## Reference

See the [data schemas](docs/reference/data-schemas.md).
"""

MANIFEST = [
    {
        "id": "example",
        "type": "generated",
        "path": "docs/assets/diagrams/example.svg",
        "pages": ["README.md"],
        "regenerate": "python tools/docs/generate_diagrams.py",
        "alt": "A diagram",
        "caption": "An example.",
        "status": "approved",
    }
]


def make_repository(tmp_path: Path, readme: str = README, manifest=None) -> Path:
    (tmp_path / "mkdocs.yml").write_text(yaml.safe_dump(NAV), encoding="utf-8")
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")

    for rel in ("start-here/quickstart.md", "reference/data-schemas.md"):
        page = tmp_path / "docs" / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# Page\n", encoding="utf-8")
    (tmp_path / "docs" / "index.md").write_text("# Home\n", encoding="utf-8")

    asset = tmp_path / "docs" / "assets" / "diagrams" / "example.svg"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text("<svg viewBox='0 0 1 1'><title>t</title><desc>d</desc></svg>",
                     encoding="utf-8")

    manifest_path = tmp_path / "docs" / "assets" / "visual-manifest.yml"
    manifest_path.write_text(
        yaml.safe_dump(MANIFEST if manifest is None else manifest), encoding="utf-8"
    )
    return tmp_path


def messages(issues) -> str:
    return "\n".join(str(issue) for issue in issues)


def test_a_synchronised_readme_passes(tmp_path: Path) -> None:
    assert run_checks(make_repository(tmp_path)) == []


def test_this_repository_is_synchronised() -> None:
    """The real README must always stay in step."""

    assert run_checks(Path(__file__).resolve().parents[2]) == []


def test_nav_sections_skips_single_pages() -> None:
    config = Path(__file__).resolve().parents[2] / "mkdocs.yml"
    sections = nav_sections(config)

    assert "Workflows" in sections
    assert "Concepts" in sections
    assert "index.md" not in sections


def test_readme_headings_are_extracted() -> None:
    assert readme_headings("# A\n\ntext\n\n## B\n") == ["A", "B"]


def test_missing_section_is_reported(tmp_path: Path) -> None:
    readme = README.replace("## Reference", "## Something else")
    repo = make_repository(tmp_path, readme=readme)

    assert "'Reference' navigation section" in messages(
        check_sections(readme, repo / "mkdocs.yml")
    )


def test_home_is_not_required_as_a_section(tmp_path: Path) -> None:
    repo = make_repository(tmp_path)

    assert check_sections(README, repo / "mkdocs.yml") == []


def test_link_to_a_missing_page_is_reported(tmp_path: Path) -> None:
    readme = README.replace("docs/reference/data-schemas.md", "docs/reference/gone.md")
    repo = make_repository(tmp_path, readme=readme)

    assert "missing file" in messages(check_links(readme, repo, repo / "mkdocs.yml"))


def test_link_to_an_orphan_page_is_reported(tmp_path: Path) -> None:
    repo = make_repository(tmp_path)
    orphan = repo / "docs" / "orphan.md"
    orphan.write_text("# Orphan\n", encoding="utf-8")
    readme = README + "\nAn [orphan](docs/orphan.md).\n"

    assert "absent from the navigation" in messages(
        check_links(readme, repo, repo / "mkdocs.yml")
    )


def test_external_links_are_ignored(tmp_path: Path) -> None:
    repo = make_repository(tmp_path)
    readme = README + "\n[Elsewhere](https://example.invalid/x).\n"

    assert check_links(readme, repo, repo / "mkdocs.yml") == []


def test_unapproved_image_is_reported(tmp_path: Path) -> None:
    manifest = [{**MANIFEST[0], "status": "planned"}]
    repo = make_repository(tmp_path, manifest=manifest)

    assert "not an approved manifest entry" in messages(check_images(README, repo))


def test_unmanifested_image_is_reported(tmp_path: Path) -> None:
    repo = make_repository(tmp_path, manifest=[])

    assert "not an approved manifest entry" in messages(check_images(README, repo))


def test_missing_readme_is_reported(tmp_path: Path) -> None:
    repo = make_repository(tmp_path)
    (repo / "README.md").unlink()

    assert "README.md not found" in messages(run_checks(repo))


def test_main_returns_one_when_out_of_step(tmp_path: Path, capsys) -> None:
    repo = make_repository(tmp_path, readme=README.replace("## Reference", "## Other"))

    assert main([str(repo)]) == 1
    assert "Reference" in capsys.readouterr().out


def test_main_returns_zero_when_in_step(tmp_path: Path, capsys) -> None:
    repo = make_repository(tmp_path)

    assert main([str(repo)]) == 0
    assert "in step" in capsys.readouterr().out
