from __future__ import annotations

from pathlib import Path

import pytest

from tools.docs.check_docs import (
    REQUIRED_FRONT_MATTER_KEYS,
    find_broken_relative_links,
    find_missing_image_alt_text,
    find_orphan_pages,
    iter_markdown_files,
    load_nav_paths,
    main,
    run_checks,
    validate_front_matter,
)


COMPLETE_FRONT_MATTER = """\
---
title: Test page
audience: beginner
status: current
source_files:
  - README.md
verified_against: abc1234
---

# Test page
"""


def write_markdown(path: Path, content: str = COMPLETE_FRONT_MATTER) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def make_repository(tmp_path: Path, page_content: str = COMPLETE_FRONT_MATTER) -> Path:
    write_markdown(tmp_path / "docs" / "index.md", page_content)
    (tmp_path / "README.md").write_text("# Repository\n", encoding="utf-8")
    (tmp_path / "mkdocs.yml").write_text(
        "nav:\n  - Home: index.md\n",
        encoding="utf-8",
    )
    return tmp_path


def test_markdown_discovery_excludes_meta(tmp_path: Path) -> None:
    page = write_markdown(tmp_path / "docs" / "index.md")
    write_markdown(tmp_path / "docs" / "_meta" / "page-template.md")

    assert iter_markdown_files(tmp_path / "docs") == [page.resolve()]


def test_load_nav_paths_handles_mkdocs_python_name_tag(tmp_path: Path) -> None:
    config = tmp_path / "mkdocs.yml"
    config.write_text(
        """\
markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - format: !!python/name:pymdownx.superfences.fence_code_format
nav:
  - Guide:
      - Home: index.md
""",
        encoding="utf-8",
    )

    assert load_nav_paths(config, tmp_path / "docs") == {
        (tmp_path / "docs" / "index.md").resolve()
    }


def test_valid_relative_markdown_link_passes(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    target = write_markdown(docs_dir / "guide.md")
    page = write_markdown(docs_dir / "index.md", "[Guide](guide.md)\n")

    assert target.exists()
    assert find_broken_relative_links(page, docs_dir, tmp_path) == []


def test_relative_link_may_leave_docs_for_repository_target(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    (tmp_path / "README.md").write_text("# Repository\n", encoding="utf-8")
    page = write_markdown(docs_dir / "index.md", "[Repository](../README.md)\n")

    assert find_broken_relative_links(page, docs_dir, tmp_path) == []


def test_missing_relative_markdown_link_fails(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    page = write_markdown(docs_dir / "index.md", "[Missing](missing.md)\n")

    issues = find_broken_relative_links(page, docs_dir, tmp_path)

    assert len(issues) == 1
    assert "missing.md" in issues[0].message


def test_valid_relative_image_passes(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    image = docs_dir / "assets" / "profile.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"test image")
    page = write_markdown(
        docs_dir / "index.md",
        "![A synthetic trench profile](assets/profile.png)\n",
    )

    assert find_broken_relative_links(page, docs_dir, tmp_path) == []


def test_missing_relative_image_fails(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    page = write_markdown(
        docs_dir / "index.md",
        "![A synthetic trench profile](assets/missing.png)\n",
    )

    issues = find_broken_relative_links(page, docs_dir, tmp_path)

    assert len(issues) == 1
    assert "assets/missing.png" in issues[0].message


def test_external_urls_are_ignored(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    page = write_markdown(
        docs_dir / "index.md",
        "\n".join(
            (
                "[HTTP](http://example.com/page)",
                "[HTTPS](https://example.com/page)",
                "[Email](mailto:docs@example.com)",
            )
        ),
    )

    assert find_broken_relative_links(page, docs_dir, tmp_path) == []


def test_same_page_anchors_are_ignored(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    page = write_markdown(docs_dir / "index.md", "[Details](#details)\n")

    assert find_broken_relative_links(page, docs_dir, tmp_path) == []


def test_image_with_empty_alt_text_fails(tmp_path: Path) -> None:
    page = write_markdown(tmp_path / "docs" / "index.md", "![](image.png)\n")

    issues = find_missing_image_alt_text(page)

    assert len(issues) == 1
    assert "alt text" in issues[0].message


def test_complete_front_matter_passes(tmp_path: Path) -> None:
    page = write_markdown(tmp_path / "docs" / "index.md")

    assert validate_front_matter(page) == []


@pytest.mark.parametrize("missing_key", REQUIRED_FRONT_MATTER_KEYS)
def test_each_missing_required_front_matter_key_fails(
    tmp_path: Path,
    missing_key: str,
) -> None:
    values = {
        "title": "Test page",
        "audience": "beginner",
        "status": "current",
        "source_files": ["README.md"],
        "verified_against": "abc1234",
    }
    del values[missing_key]
    front_matter_lines = ["---"]
    for key, value in values.items():
        if isinstance(value, list):
            front_matter_lines.extend((f"{key}:", f"  - {value[0]}"))
        else:
            front_matter_lines.append(f"{key}: {value}")
    front_matter_lines.extend(("---", "", "# Test page", ""))
    page = write_markdown(
        tmp_path / missing_key / "index.md",
        "\n".join(front_matter_lines),
    )

    issues = validate_front_matter(page)

    assert len(issues) == 1
    assert missing_key in issues[0].message


def test_page_absent_from_nav_is_reported_as_orphaned(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    orphan = write_markdown(docs_dir / "orphan.md")

    issues = find_orphan_pages(docs_dir, set())

    assert len(issues) == 1
    assert issues[0].path == orphan.resolve()
    assert "navigation" in issues[0].message


def test_page_present_in_nav_is_not_reported(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    page = write_markdown(docs_dir / "index.md")

    assert find_orphan_pages(docs_dir, {page}) == []


def test_main_returns_zero_for_clean_temporary_repository(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_repository(tmp_path)

    assert main([str(tmp_path)]) == 0
    assert "passed" in capsys.readouterr().out.lower()


def test_main_returns_one_when_an_issue_exists(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_repository(
        tmp_path,
        COMPLETE_FRONT_MATTER + "\n[Missing](missing.md)\n",
    )

    assert main([str(tmp_path)]) == 1
    assert "missing.md" in capsys.readouterr().out


def test_run_checks_checks_links_in_root_readme(tmp_path: Path) -> None:
    make_repository(tmp_path)
    (tmp_path / "README.md").write_text("[Missing](missing.md)\n", encoding="utf-8")

    issues = run_checks(tmp_path)

    assert len(issues) == 1
    assert issues[0].path == tmp_path / "README.md"
    assert "missing.md" in issues[0].message
