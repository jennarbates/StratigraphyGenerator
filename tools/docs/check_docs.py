"""Validate the repository's Markdown documentation."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import unquote, urlsplit

import yaml


REQUIRED_FRONT_MATTER_KEYS = (
    "title",
    "audience",
    "status",
    "source_files",
    "verified_against",
)

_INLINE_LINK_RE = re.compile(
    r"!?\[[^\]]*]\(\s*(?P<target><[^>]*>|[^)\s]+)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)]\(")
_IGNORED_SCHEMES = frozenset({"http", "https", "mailto"})


class _MkDocsLoader(yaml.SafeLoader):
    """Safe YAML loader that treats MkDocs Python-name tags as plain text."""


def _construct_python_name(
    loader: _MkDocsLoader,
    tag_suffix: str,
    node: yaml.Node,
) -> str:
    loader.construct_scalar(node)
    return tag_suffix


_MkDocsLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:",
    _construct_python_name,
)


@dataclass(frozen=True)
class Issue:
    path: Path
    message: str


def iter_markdown_files(docs_dir: Path) -> list[Path]:
    """Return documentation Markdown files, excluding the metadata templates."""

    return sorted(
        (
            path.resolve()
            for path in docs_dir.rglob("*.md")
            if path.relative_to(docs_dir).parts[0] != "_meta"
        ),
        key=lambda path: path.as_posix(),
    )


def _iter_nav_values(nav: Any) -> list[str]:
    if isinstance(nav, str):
        return [nav]
    if isinstance(nav, list):
        values: list[str] = []
        for item in nav:
            values.extend(_iter_nav_values(item))
        return values
    if isinstance(nav, dict):
        values = []
        for item in nav.values():
            values.extend(_iter_nav_values(item))
        return values
    return []


def load_nav_paths(config_path: Path, docs_dir: Path) -> set[Path]:
    """Load Markdown source paths referenced by the MkDocs navigation."""

    config = (
        yaml.load(config_path.read_text(encoding="utf-8"), Loader=_MkDocsLoader) or {}
    )
    nav = config.get("nav", []) if isinstance(config, dict) else []

    nav_paths: set[Path] = set()
    for value in _iter_nav_values(nav):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path.lower().endswith(".md"):
            continue
        nav_paths.add((docs_dir / unquote(parsed.path)).resolve())
    return nav_paths


def _link_target_path(
    target: str,
    markdown_path: Path,
    repo_root: Path,
) -> Path | None:
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]

    parsed = urlsplit(target)
    if parsed.scheme.lower() in _IGNORED_SCHEMES or parsed.netloc:
        return None
    if not parsed.path:
        return None

    decoded_path = unquote(parsed.path)
    if decoded_path.startswith("/"):
        return (repo_root / decoded_path.lstrip("/")).resolve()
    return (markdown_path.parent / decoded_path).resolve()


def find_broken_relative_links(
    markdown_path: Path,
    docs_dir: Path,
    repo_root: Path,
) -> list[Issue]:
    """Report missing local targets referenced by a Markdown page."""

    del docs_dir  # Links may intentionally point outside docs but inside the repo.

    issues: list[Issue] = []
    text = markdown_path.read_text(encoding="utf-8")
    resolved_repo_root = repo_root.resolve()

    for match in _INLINE_LINK_RE.finditer(text):
        target = match.group("target")
        target_path = _link_target_path(target, markdown_path, resolved_repo_root)
        if target_path is None:
            continue

        try:
            target_path.relative_to(resolved_repo_root)
        except ValueError:
            issues.append(
                Issue(
                    markdown_path,
                    f"relative link target leaves the repository: {target}",
                )
            )
            continue

        if not target_path.exists():
            issues.append(
                Issue(markdown_path, f"relative link target does not exist: {target}")
            )

    return issues


def find_missing_image_alt_text(markdown_path: Path) -> list[Issue]:
    """Report Markdown images whose alt text is empty."""

    text = markdown_path.read_text(encoding="utf-8")
    return [
        Issue(markdown_path, "image is missing alt text")
        for match in _IMAGE_RE.finditer(text)
        if not match.group("alt").strip()
    ]


def validate_front_matter(markdown_path: Path) -> list[Issue]:
    """Report malformed or incomplete YAML front matter."""

    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return [Issue(markdown_path, "missing YAML front matter")]

    try:
        closing_index = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        return [Issue(markdown_path, "YAML front matter is not closed")]

    try:
        metadata = yaml.safe_load("\n".join(lines[1:closing_index]))
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", None) or "invalid YAML"
        return [Issue(markdown_path, f"malformed YAML front matter: {problem}")]

    if not isinstance(metadata, dict):
        return [Issue(markdown_path, "YAML front matter must be a mapping")]

    return [
        Issue(markdown_path, f"missing required front matter key: {key}")
        for key in REQUIRED_FRONT_MATTER_KEYS
        if key not in metadata
    ]


def find_orphan_pages(
    docs_dir: Path,
    nav_paths: set[Path],
) -> list[Issue]:
    """Report documentation pages that are absent from the MkDocs navigation."""

    resolved_nav_paths = {path.resolve() for path in nav_paths}
    return [
        Issue(path, "page is absent from MkDocs navigation")
        for path in iter_markdown_files(docs_dir)
        if path.resolve() not in resolved_nav_paths
    ]


def run_checks(repo_root: Path) -> list[Issue]:
    """Run every documentation validation check for a repository."""

    repo_root = repo_root.resolve()
    docs_dir = repo_root / "docs"
    nav_paths = load_nav_paths(repo_root / "mkdocs.yml", docs_dir)
    markdown_files = iter_markdown_files(docs_dir)

    issues: list[Issue] = []
    checked_files = list(markdown_files)
    readme_path = repo_root / "README.md"
    if readme_path.exists():
        checked_files.append(readme_path)

    for markdown_path in checked_files:
        issues.extend(
            find_broken_relative_links(markdown_path, docs_dir, repo_root)
        )
        issues.extend(find_missing_image_alt_text(markdown_path))

    markdown_file_set = set(markdown_files)
    for markdown_path in sorted(nav_paths, key=lambda path: path.as_posix()):
        if markdown_path in markdown_file_set:
            issues.extend(validate_front_matter(markdown_path))

    issues.extend(find_orphan_pages(docs_dir, nav_paths))
    return sorted(issues, key=lambda issue: (issue.path.as_posix(), issue.message))


def main(argv: Sequence[str] | None = None) -> int:
    """Run the checker as a command-line program."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repo_root",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="repository root (defaults to the current directory)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    issues = run_checks(repo_root)
    if issues:
        for issue in issues:
            try:
                display_path = issue.path.relative_to(repo_root)
            except ValueError:
                display_path = issue.path
            print(f"{display_path}: {issue.message}")
        return 1

    print("Documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
