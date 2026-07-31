"""Report application modules that no documentation page mentions.

A module counts as covered only when its full repository-relative path appears
somewhere in the documentation corpus -- prose, a code span, or a front-matter
`source_files` entry.

The full path is required deliberately. Matching a bare module name would let
ordinary English cover a module by accident: `trenches.py` would look
documented because the word "trenches" appears throughout the archaeology
prose, which is exactly how multi-wall trench support reached `main` with no
page describing it.

This is a coverage floor, not a quality measure. It proves a module was named,
not that it was explained.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

WATCHED_PACKAGES = (
    "poggio_webapp/pipeline",
    "poggio_webapp/backend",
    "poggio_webapp/demo",
)

# Top-level modules that sit beside those packages rather than inside them.
# `storage.py` reached `main` unmentioned because the watch list covered only
# the two packages, so single files are enumerated explicitly.
WATCHED_MODULES = (
    "poggio_webapp/app.py",
    "poggio_webapp/storage.py",
)

# Modules that exist for reasons no reader needs documented.
EXEMPT_STEMS = frozenset({"__init__"})


@dataclass(frozen=True)
class Uncovered:
    module: str

    def __str__(self) -> str:
        return f"{self.module}: no documentation page names this path"


def iter_watched_modules(repo_root: Path) -> list[Path]:
    """Return the application modules that documentation should mention."""

    modules: list[Path] = []
    for package in WATCHED_PACKAGES:
        package_dir = repo_root / package
        if not package_dir.is_dir():
            continue
        for path in sorted(package_dir.rglob("*.py")):
            if path.stem in EXEMPT_STEMS:
                continue
            if "__pycache__" in path.parts:
                continue
            modules.append(path)

    for relative in WATCHED_MODULES:
        path = repo_root / relative
        if path.is_file():
            modules.append(path)

    return sorted(modules, key=lambda p: p.as_posix())


def documentation_text(repo_root: Path) -> str:
    """Concatenate every documentation source a reader could reach."""

    parts: list[str] = []
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.rglob("*.md")):
            if path.relative_to(docs_dir).parts[0] == "_meta":
                continue
            parts.append(path.read_text(encoding="utf-8"))

    for extra in ("README.md", "poggio_webapp/README.md"):
        path = repo_root / extra
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))

    return "\n".join(parts)


def find_uncovered(repo_root: Path) -> list[Uncovered]:
    """Report watched modules absent from the documentation corpus."""

    text = documentation_text(repo_root)
    uncovered: list[Uncovered] = []

    for module in iter_watched_modules(repo_root):
        relative = module.relative_to(repo_root).as_posix()
        if relative not in text:
            uncovered.append(Uncovered(relative))

    return uncovered


def main(argv: Sequence[str] | None = None) -> int:
    """Run the coverage check as a command-line program."""

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

    uncovered = find_uncovered(repo_root)
    if uncovered:
        for issue in uncovered:
            print(issue)
        print(f"\n{len(uncovered)} module(s) undocumented.")
        return 1

    total = len(iter_watched_modules(repo_root))
    print(f"Documentation coverage passed: {total} modules mentioned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
