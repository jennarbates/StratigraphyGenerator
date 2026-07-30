"""Keep the root README and the documentation site from drifting apart.

The README is a full illustrated mirror of the site, which means two surfaces
have to stay aligned. Alignment by discipline decays, so the parts that can be
checked mechanically are checked here:

* every top-level navigation section is represented by a README heading, so a
  whole section cannot be added to the site and silently missed;
* every link from the README into ``docs/`` targets a page that is actually in
  the navigation, so the README cannot point at an orphan;
* every image the README embeds is an ``approved`` entry in the visual
  manifest, on the same terms as the site's own pages.

What is deliberately *not* checked is prose. The README is a tour and the site
is a manual; demanding matching wording would force one of them to be bad.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

try:  # running as part of the tools.docs package, e.g. from the test suite
    from .check_docs import _MkDocsLoader, load_nav_paths
    from .validate_visual_manifest import load_manifest
except ImportError:  # running as a script, like the other checkers
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_docs import _MkDocsLoader, load_nav_paths
    from validate_visual_manifest import load_manifest

_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<text>.+?)\s*$", re.MULTILINE)
_LINK_RE = re.compile(r"(?<!!)\[[^\]]*]\(\s*(?P<target>[^)\s#]+)")
_IMAGE_RE = re.compile(r"!\[[^\]]*]\(\s*(?P<target>[^)\s]+)")

# Navigation groups that are structural rather than a section a reader would
# look for by name in a README.
IGNORED_NAV_SECTIONS = frozenset({"Home"})


@dataclass(frozen=True)
class Issue:
    message: str

    def __str__(self) -> str:
        return self.message


def nav_sections(config_path: Path) -> list[str]:
    """Top-level navigation group titles, in order."""

    config = (
        yaml.load(config_path.read_text(encoding="utf-8"), Loader=_MkDocsLoader) or {}
    )
    nav = config.get("nav", []) if isinstance(config, dict) else []

    sections: list[str] = []
    for item in nav:
        if isinstance(item, dict):
            for title, value in item.items():
                if isinstance(value, list):
                    sections.append(str(title))
    return sections


def readme_headings(text: str) -> list[str]:
    return [match.group("text").strip() for match in _HEADING_RE.finditer(text)]


def check_sections(text: str, config_path: Path) -> list[Issue]:
    """Every navigation section must appear as a README heading."""

    headings = [heading.casefold() for heading in readme_headings(text)]
    issues = []
    for section in nav_sections(config_path):
        if section in IGNORED_NAV_SECTIONS:
            continue
        if not any(section.casefold() in heading for heading in headings):
            issues.append(
                Issue(f"no README heading covers the '{section}' navigation section")
            )
    return issues


def check_links(text: str, repo_root: Path, config_path: Path) -> list[Issue]:
    """Links into docs/ must target a page that is in the navigation."""

    docs_dir = repo_root / "docs"
    nav = {path.resolve() for path in load_nav_paths(config_path, docs_dir)}

    issues = []
    for match in _LINK_RE.finditer(text):
        target = match.group("target")
        if "://" in target or not target.startswith("docs/"):
            continue
        path = (repo_root / target).resolve()
        if not path.exists():
            issues.append(Issue(f"README links to a missing file: {target}"))
        elif path.suffix == ".md" and path not in nav:
            issues.append(
                Issue(f"README links to a page absent from the navigation: {target}")
            )
    return issues


def check_images(text: str, repo_root: Path) -> list[Issue]:
    """Embedded images must be approved manifest entries."""

    manifest_path = repo_root / "docs" / "assets" / "visual-manifest.yml"
    if not manifest_path.is_file():
        return [Issue("visual manifest not found")]

    approved = {
        Path(str(entry.get("path"))).as_posix()
        for entry in load_manifest(manifest_path)
        if isinstance(entry, dict)
        and entry.get("status") == "approved"
        and entry.get("path")
    }

    issues = []
    for match in _IMAGE_RE.finditer(text):
        target = match.group("target")
        if "://" in target:
            continue
        if target not in approved:
            issues.append(
                Issue(f"README image is not an approved manifest entry: {target}")
            )
    return issues


def run_checks(repo_root: Path) -> list[Issue]:
    """Run every README synchronisation check."""

    repo_root = repo_root.resolve()
    readme = repo_root / "README.md"
    if not readme.is_file():
        return [Issue("README.md not found")]

    config_path = repo_root / "mkdocs.yml"
    if not config_path.is_file():
        return [Issue("mkdocs.yml not found")]

    text = readme.read_text(encoding="utf-8")
    return [
        *check_sections(text, config_path),
        *check_links(text, repo_root, config_path),
        *check_images(text, repo_root),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the synchronisation check as a command-line program."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    issues = run_checks(args.repo_root)
    if issues:
        for issue in sorted(issues, key=str):
            print(issue)
        print(f"\n{len(issues)} README synchronisation problem(s).")
        return 1

    print("README is in step with the documentation navigation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
