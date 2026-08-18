"""Which record sets the demo can run against, and where they live.

Two roots, deliberately different in kind:

  ``tests/fixtures/``  tracked and synthetic. T905 ships with the repository,
                       so a fresh clone runs the demo with no setup at all.
  ``local/fixtures/``  untracked and real. Whatever the excavation's own
                       records have been put there is picked up automatically.
                       Nothing is ever copied out of it: the seeder reads these
                       paths in place and writes only into the three runtime
                       roots, all of which are already gitignored.

A dataset is offered only when all three of its files are present. A demo that
half-loads is worse than one that is not offered, because the missing half
looks like a pipeline result.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

# poggio_webapp/demo/datasets.py -> repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

TRACKED_ROOT = REPO_ROOT / "tests" / "fixtures"
LOCAL_ROOT = REPO_ROOT / "local" / "fixtures"

# "t905-2025-layout.json" -> label T905, season 2025.
_LAYOUT_NAME = re.compile(
    r"^(?P<label>[a-z]+\d+)-(?P<season>\d{4})-layout\.json$", re.IGNORECASE
)

_COMPANIONS = ("loci", "special-finds")


@dataclass(frozen=True)
class DemoDataset:
    """One trench's three record files, and whether they are real.

    ``real_records`` is not decoration. It gates wall generation in ``seed``:
    a real trench never gets invented sections drawn for it, however
    convenient that would make the demonstration.
    """

    label: str
    season: str
    root: Path
    layout_path: Path
    loci_path: Path
    finds_path: Path
    real_records: bool

    def layout(self) -> dict:
        return json.loads(self.layout_path.read_text())

    def loci(self) -> dict:
        return json.loads(self.loci_path.read_text())

    def finds(self) -> dict:
        return json.loads(self.finds_path.read_text())

    @property
    def provenance(self) -> str:
        """The badge the interface shows on everything seeded from this set."""
        if self.real_records:
            return f"Real excavation records: {self.label} {self.season}"
        return f"Synthetic demonstration data: {self.label} {self.season}"


def _dataset_at(layout_path: Path, *, real_records: bool):
    match = _LAYOUT_NAME.match(layout_path.name)
    if match is None:
        return None
    label = match.group("label").upper()
    season = match.group("season")
    stem = f"{match.group('label')}-{season}"

    companions = {
        name: layout_path.parent / f"{stem}-{name}.json" for name in _COMPANIONS
    }
    if not all(path.is_file() for path in companions.values()):
        return None

    return DemoDataset(
        label=label,
        season=season,
        root=layout_path.parent,
        layout_path=layout_path,
        loci_path=companions["loci"],
        finds_path=companions["special-finds"],
        real_records=real_records,
    )


def discover() -> dict[str, DemoDataset]:
    """Every complete record set, keyed by trench label.

    Tracked first, then local, so a real trench that happens to share a label
    with a shipped fixture wins -- somebody who put real records on disk meant
    them to be used. In practice they never collide: real trenches at this site
    are T1xx and the synthetic ones are T9xx.
    """
    found: dict[str, DemoDataset] = {}
    for root, real in ((TRACKED_ROOT, False), (LOCAL_ROOT, True)):
        if not root.is_dir():
            continue
        for layout_path in sorted(root.glob("*-layout.json")):
            dataset = _dataset_at(layout_path, real_records=real)
            if dataset is not None:
                found[dataset.label] = dataset
    return found


def get(label: str) -> DemoDataset:
    """One dataset by trench label, or a KeyError naming what is available."""
    available = discover()
    key = label.upper()
    if key not in available:
        raise KeyError(
            f"no record set for trench {label!r}. Available: "
            + (", ".join(sorted(available)) or "none")
        )
    return available[key]
