"""Validate the documentation visual manifest.

The manifest is the planning record for every teaching visual in the guide: what
it shows, which page it belongs to, what UI state produces it, and whether it
has been reviewed. Capture is manual, so deciding and reviewing an image before
producing it is cheaper than re-shooting it.

Two directions are checked.

Forward: every manifest entry is well formed, and an entry claiming to be
`approved` really has its file on disk.

Reverse: every image actually embedded in the documentation resolves to an
`approved` manifest entry. This is the half that matters in practice -- it stops
an unreviewed screenshot from reaching a published page, and it is why the
manifest cannot drift into being a stale wishlist.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_KEYS = ("id", "type", "pages", "alt", "caption", "status")

# Types are named for how the asset is MAINTAINED, not what it depicts:
#   screenshot -- captured from the running app; needs a fixture and UI state
#   diagram    -- authored artwork committed as a file; redrawn by hand
#   generated  -- produced by a script; needs a regeneration command
#   mermaid    -- fenced source inline in the Markdown; no file of its own
ASSET_TYPES = frozenset({"screenshot", "diagram", "generated", "mermaid"})
STATUSES = frozenset({"planned", "captured", "approved"})

FILE_TYPES = frozenset({"screenshot", "diagram", "generated"})

# A file that must exist, because the entry claims it was produced.
PRODUCED_STATUSES = frozenset({"captured", "approved"})

ASSETS_ROOT = Path("docs/assets")

# Job ids are hex strings. One in a committed filename means the screenshot was
# taken from a real session rather than a fixture, and will never reproduce.
_JOB_ID_RE = re.compile(r"[0-9a-f]{8,}")

_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)]\(\s*(?P<target>[^)\s]+)")

# The SVG contract from the documentation plan. A diagram that fails any of
# these is either unreadable at the published width or invisible to a screen
# reader, so it is checked rather than trusted.
_RASTER_RE = re.compile(r"data:image/(png|jpe?g|gif|webp)", re.IGNORECASE)


def check_svg_contract(path: Path) -> list[str]:
    """Return contract violations for one SVG file."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"could not read SVG: {error}"]

    problems: list[str] = []
    if "viewBox" not in text:
        problems.append("SVG has no viewBox, so it cannot scale")
    if "<title" not in text:
        problems.append("SVG has no <title>")
    if "<desc" not in text:
        problems.append("SVG has no <desc>")
    if re.search(r"<svg[^>]*\swidth=", text):
        problems.append("SVG sets a fixed width; use the viewBox alone")
    if _RASTER_RE.search(text):
        problems.append("SVG embeds raster image data")
    return problems


@dataclass(frozen=True)
class Issue:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    """Return the manifest entries, or raise ValueError if it is not a list."""

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("visual manifest must be a list of entries")
    return raw


def _validate_entry(entry: Any, index: int, repo_root: Path) -> list[Issue]:
    where = f"entry {index}"
    if not isinstance(entry, dict):
        return [Issue(where, "entry must be a mapping")]

    entry_id = entry.get("id")
    if isinstance(entry_id, str) and entry_id:
        where = entry_id

    issues = [
        Issue(where, f"missing required key: {key}")
        for key in REQUIRED_KEYS
        if key not in entry
    ]
    if issues:
        return issues

    asset_type = entry["type"]
    status = entry["status"]

    if asset_type not in ASSET_TYPES:
        issues.append(Issue(where, f"unknown type: {asset_type!r}"))
    if status not in STATUSES:
        issues.append(Issue(where, f"unknown status: {status!r}"))

    for key in ("alt", "caption"):
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(Issue(where, f"{key} must be a non-empty string"))

    pages = entry.get("pages")
    if not isinstance(pages, list) or not pages:
        issues.append(Issue(where, "pages must be a non-empty list"))
    else:
        for page in pages:
            if not isinstance(page, str) or not (repo_root / page).is_file():
                issues.append(Issue(where, f"page does not exist: {page}"))

    issues.extend(_validate_path(entry, where, asset_type, status, repo_root))

    if asset_type == "generated" and not entry.get("regenerate"):
        issues.append(Issue(where, "generated assets need a regenerate command"))
    if asset_type == "screenshot":
        for key in ("fixture", "ui_state"):
            if not entry.get(key):
                issues.append(Issue(where, f"screenshots need {key}"))

    return issues


def _validate_path(
    entry: dict[str, Any],
    where: str,
    asset_type: str,
    status: str,
    repo_root: Path,
) -> list[Issue]:
    raw_path = entry.get("path")

    if asset_type == "mermaid":
        if raw_path:
            return [Issue(where, "mermaid entries are inline and take no path")]
        return []

    if asset_type not in FILE_TYPES:
        return []

    if not isinstance(raw_path, str) or not raw_path.strip():
        return [Issue(where, f"{asset_type} entries need a path")]

    path = Path(raw_path)
    if ASSETS_ROOT not in path.parents:
        return [Issue(where, f"path must sit under {ASSETS_ROOT}/: {raw_path}")]

    issues: list[Issue] = []
    if _JOB_ID_RE.search(path.stem):
        issues.append(
            Issue(where, f"filename contains an unstable job id: {path.name}")
        )
    if status in PRODUCED_STATUSES and not (repo_root / path).is_file():
        issues.append(
            Issue(where, f"status is {status!r} but the file is missing: {raw_path}")
        )
    elif path.suffix.lower() == ".svg" and (repo_root / path).is_file():
        issues.extend(
            Issue(where, problem) for problem in check_svg_contract(repo_root / path)
        )
    return issues


def iter_documentation_pages(repo_root: Path) -> list[Path]:
    """Return every Markdown page a reader can reach."""

    pages: list[Path] = []
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        pages.extend(
            path
            for path in sorted(docs_dir.rglob("*.md"))
            if path.relative_to(docs_dir).parts[0] != "_meta"
        )
    readme = repo_root / "README.md"
    if readme.is_file():
        pages.append(readme)
    return pages


def find_unmanifested_images(
    entries: list[dict[str, Any]],
    repo_root: Path,
) -> list[Issue]:
    """Report embedded images with no approved manifest entry."""

    approved: set[str] = set()
    known: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        normalized = Path(raw_path).as_posix()
        known[normalized] = str(entry.get("status"))
        if entry.get("status") == "approved":
            approved.add(normalized)

    issues: list[Issue] = []
    for page in iter_documentation_pages(repo_root):
        text = page.read_text(encoding="utf-8")
        where = page.relative_to(repo_root).as_posix()
        for match in _IMAGE_RE.finditer(text):
            target = match.group("target")
            if "://" in target:
                continue
            resolved = (page.parent / target).resolve()
            try:
                relative = resolved.relative_to(repo_root.resolve()).as_posix()
            except ValueError:
                issues.append(Issue(where, f"image leaves the repository: {target}"))
                continue

            if relative in approved:
                continue
            if relative in known:
                issues.append(
                    Issue(
                        where,
                        f"image is embedded but its manifest status is "
                        f"{known[relative]!r}, not 'approved': {relative}",
                    )
                )
            else:
                issues.append(Issue(where, f"image has no manifest entry: {relative}"))
    return issues


def validate_manifest_entries(
    entries: list[dict[str, Any]],
    repo_root: Path,
) -> list[Issue]:
    """Validate entries and their agreement with the documentation."""

    issues: list[Issue] = []
    seen: set[str] = set()

    for index, entry in enumerate(entries):
        issues.extend(_validate_entry(entry, index, repo_root))
        if isinstance(entry, dict):
            entry_id = entry.get("id")
            if isinstance(entry_id, str) and entry_id:
                if entry_id in seen:
                    issues.append(Issue(entry_id, "duplicate asset id"))
                seen.add(entry_id)

    issues.extend(find_unmanifested_images(entries, repo_root))
    return issues


def run_checks(repo_root: Path) -> list[Issue]:
    """Run every visual-manifest check for a repository."""

    repo_root = repo_root.resolve()
    manifest_path = repo_root / ASSETS_ROOT / "visual-manifest.yml"
    if not manifest_path.is_file():
        return [Issue(str(ASSETS_ROOT / "visual-manifest.yml"), "manifest not found")]

    try:
        entries = load_manifest(manifest_path)
    except (ValueError, yaml.YAMLError) as error:
        return [Issue(manifest_path.name, f"could not read manifest: {error}")]

    return validate_manifest_entries(entries, repo_root)


def summarize(entries: list[dict[str, Any]]) -> str:
    """A one-line count of entries by status."""

    counts = {status: 0 for status in sorted(STATUSES)}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("status") in counts:
            counts[entry["status"]] += 1
    parts = ", ".join(f"{count} {status}" for status, count in counts.items())
    return f"{len(entries)} visuals ({parts})"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validator as a command-line program."""

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
        for issue in sorted(issues, key=str):
            print(issue)
        print(f"\n{len(issues)} problem(s) in the visual manifest.")
        return 1

    manifest_path = repo_root / ASSETS_ROOT / "visual-manifest.yml"
    print(f"Visual manifest passed: {summarize(load_manifest(manifest_path))}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
