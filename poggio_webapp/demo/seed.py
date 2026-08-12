"""Write a demonstration trench into the application's runtime storage.

Everything lands in ``storage.JOBS_DIR``, ``storage.TRENCHES_DIR`` and
``storage.MATRICES_DIR``, all three of which are gitignored and all three of
which the application already treats as disposable. Nothing is written into the
repository, and nothing is read out of ``local/`` except the record files
themselves.

The seeder uses the real pipeline wherever one exists -- ``build_grid_config``
for registration, ``run_normalize`` for the normalized extraction,
``harris_store`` for the matrix -- so a demonstration that works is evidence
the pipeline works. A demo with its own private shortcuts would be evidence of
nothing.

Reseeding is destructive by design: every artifact carrying this scenario's
trench label is removed first, so a demonstration always opens on a known
state rather than on whatever the last run left behind.
"""

import argparse
import json
import math
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime

import storage
from backend import harris_store
from naming import canonical_trench, safe_filename
from pipeline import convert_coords, normalizer, site_grid, trench_layout

from . import datasets, walls

# Every seeded job id starts with this, which is how ``reset`` finds them and
# how anything else can tell demonstration data from the operator's own work.
JOB_PREFIX = "demo-"

SHEET_TYPE = "fieldwall"


class DemoError(Exception):
    """A refusal the operator can act on. The message is user-facing."""


@dataclass(frozen=True)
class Scenario:
    name: str
    dataset_label: str
    needs_walls: bool
    complete_registration: bool
    headline: str


SCENARIOS = {
    "stops": Scenario(
        name="stops",
        dataset_label="T905",
        needs_walls=True,
        complete_registration=False,
        headline=(
            "A trench whose northeast corner was never given an opening "
            "elevation. Four walls drawn, three corners surveyed, and a build "
            "that refuses by name on the wall the fourth corner registers."
        ),
    ),
    "complete": Scenario(
        name="complete",
        dataset_label="T905",
        needs_walls=True,
        complete_registration=True,
        headline=(
            "The same trench and the same four wall drawings, with that one "
            "corner elevation supplied. Merges, registers, converts, and hands "
            "off to the model builder."
        ),
    ),
}

WALL_ORDER_NOTE = (
    "Walls are seeded in the order the layout lists them, so each wall's "
    "origin is the corner it starts at."
)


def _counterfactual_label(label: str) -> str:
    """``T905`` -> ``T906``: the same trench with one more number in it.

    The complete run needs its own trench label so both demonstrations can sit
    in the application at once and be compared. Deriving it rather than
    hardcoding it keeps the pair together if the dataset is ever renumbered.
    """
    digits = ""
    while label and label[-1].isdigit():
        digits = label[-1] + digits
        label = label[:-1]
    if not digits:
        raise DemoError(f"trench label {label!r} has no number to increment")
    return f"{label}{int(digits) + 1:0{len(digits)}d}"


def trench_label_for(scenario: Scenario, dataset_label: str | None = None) -> str:
    """The trench label one scenario seeds under.

    The complete run needs its own label so both demonstrations can sit in the
    application at once and be compared side by side. Kept here rather than
    inline in ``seed`` so that removing a demonstration can find the same
    labels seeding it created, without re-deriving the rule and drifting.
    """
    label = dataset_label or scenario.dataset_label
    return _counterfactual_label(label) if scenario.complete_registration else label


def unregistered_corners(layout: dict) -> list[dict]:
    """The corners of this layout with no opening elevation."""
    read = trench_layout.read_layout(layout)
    return [c for c in read["corners"] if c.get("elevation") is None]


def supplied_corner_elevation(layout: dict, loci_document: dict, corner: dict):
    """A stand-in elevation for a corner that was never measured.

    Taken from the nearest reading on the *opening* locus, by plan distance.
    Two constraints, and both of them matter:

    Only the first locus. Its opening surface is the ground surface, which is
    what a corner elevation is. Reading from any locus would have taken the
    nearest number in the file, and on this trench the nearest number to the
    unmeasured corner is Locus 3's floor -- exposed at the bottom of the
    excavation, 0.3 m down. Used as a ground surface it would have put every
    depth on that wall a third of a metre out, in a direction nothing
    downstream could detect.

    Nearest, not interpolated across the corners. This trench's southwest
    corner stands on an old spoil heap half a metre above the other three, so
    fitting a plane through them would carry that heap into a value meant to
    stand for undisturbed ground.

    It is a fabrication either way, which is the point of the pairing. The
    ``stops`` scenario shows what the application does when this number is
    absent; this one exists to show what it does when the number is there.
    """
    numbered = [
        locus for locus in (loci_document.get("loci") or [])
        if isinstance(locus.get("locus"), int)
    ]
    opening_locus = min(numbered, key=lambda locus: locus["locus"], default=None)
    readings = [
        (vertex["gridX"], vertex["gridY"], vertex["elevation"])
        for vertex in ((opening_locus or {}).get("opening_vertices") or [])
        if isinstance(vertex.get("elevation"), (int, float))
        and isinstance(vertex.get("gridX"), (int, float))
        and isinstance(vertex.get("gridY"), (int, float))
    ]
    if not readings:
        raise DemoError(
            "the locus record has no opening readings on its first locus to "
            f"stand in for the unmeasured elevation at {corner['label']}"
        )
    x, y, elevation = min(
        readings,
        key=lambda r: math.dist((r[0], r[1]), (corner["gridX"], corner["gridY"])),
    )
    distance = math.dist((x, y), (corner["gridX"], corner["gridY"]))
    return round(elevation, 2), (
        f"corner {corner['label']} has no surveyed opening elevation; the "
        f"complete run stands in {elevation:.2f} from the nearest reading on "
        f"locus {opening_locus['locus']}, {distance:.2f} m away. This is a "
        f"demonstration value, not a measurement"
    )


def complete_layout(layout: dict, loci_document: dict):
    """The layout with every corner carrying an elevation. Returns (layout, notes)."""
    filled = json.loads(json.dumps(layout))
    notes = []
    missing = unregistered_corners(layout)
    if not missing:
        return filled, ["every corner in this layout already has an elevation"]

    read = trench_layout.read_layout(layout)
    by_label = {c["label"]: c for c in read["corners"]}
    for corner in missing:
        elevation, note = supplied_corner_elevation(
            layout, loci_document, by_label[corner["label"]])
        notes.append(note)
        for entry in filled["corners"]:
            if str(entry.get("label")) == corner["label"]:
                entry["elevation"] = elevation
    return filled, notes


def _wall_lengths(grid: dict, wall_names: list[str]) -> dict[str, float]:
    """Each wall's length, from its origin to the next wall's origin.

    The drawn sheets have to be as long as the survey says the walls are, or
    ``check_trench_grid_config``'s corner-adjacency check reports four walls
    that do not meet.
    """
    faces = grid.get("faces") or {}
    lengths = {}
    for index, name in enumerate(wall_names):
        here = faces[name]
        following = faces[wall_names[(index + 1) % len(wall_names)]]
        lengths[name] = math.dist(
            (here["originX"], here["originY"]),
            (following["originX"], following["originY"]),
        )
    return lengths


# ---------------------------------------------------------------------------
# Removing a previous run
# ---------------------------------------------------------------------------


def reset(trench_label: str) -> list[str]:
    """Remove every artifact a previous seed of this trench left behind."""
    removed = []
    canonical = canonical_trench(trench_label) or trench_label
    prefix = f"{JOB_PREFIX}{canonical.lower()}-"

    if storage.JOBS_DIR.exists():
        for directory in sorted(storage.JOBS_DIR.iterdir()):
            if directory.is_dir() and directory.name.startswith(prefix):
                shutil.rmtree(directory)
                removed.append(f"job {directory.name}")

    trench_directory = storage.TRENCHES_DIR / safe_filename(canonical, "trench")
    if trench_directory.is_dir():
        shutil.rmtree(trench_directory)
        removed.append(f"trench {trench_directory.name}")

    for summary in harris_store.list_matrices():
        if canonical_trench(summary.get("trench")) == canonical:
            shutil.rmtree(storage.MATRICES_DIR / summary["matrix_id"])
            removed.append(f"matrix {summary['matrix_id']}")

    return removed


# ---------------------------------------------------------------------------
# Writing each kind of artifact
# ---------------------------------------------------------------------------


def _write_wall_job(
    dataset,
    *,
    trench_label,
    wall_label,
    profile,
    scenario_name,
):
    """One job directory, taken through the real normalizer."""
    job_id = (
        f"{JOB_PREFIX}{trench_label.lower()}-"
        f"{safe_filename(wall_label.replace(' ', '-'), 'wall').lower()}"
    )
    job_directory = storage.JOBS_DIR / job_id
    (job_directory / "03_extraction").mkdir(parents=True, exist_ok=True)
    (job_directory / "04_normalize_validate").mkdir(parents=True, exist_ok=True)

    extraction_path = job_directory / "03_extraction" / "extraction.json"
    extraction_path.write_text(json.dumps(profile, indent=2))

    normalized_path = job_directory / "04_normalize_validate" / "output_clean.json"
    normalizer.run_normalize(str(extraction_path), str(normalized_path))

    now = datetime.now(UTC).isoformat()
    meta = {
        "job_id": job_id,
        "created_at": now,
        "updated_at": now,
        "status": "extracted",
        "source": "demo",
        "sheet_type": SHEET_TYPE,
        "trench_label": trench_label,
        "wall_label": wall_label,
        "season": dataset.season,
        "site_grid": site_grid.POGGIO_CIVITATE,
        "extraction_path": str(extraction_path),
        "normalized_path": str(normalized_path),
        "demo": {
            "scenario": scenario_name,
            "dataset": f"{dataset.label} {dataset.season}",
            "provenance": dataset.provenance,
            "generated_sections": True,
            # The job list shows the last six characters of a job id, which is
            # right for the uuids the application generates and useless for
            # these: 'demo-t905-north-wall' renders as 'h-wall'. A seeded job
            # knows what it is, so it says so.
            "title": f"{trench_label} {wall_label}",
        },
    }
    (job_directory / "meta.json").write_text(json.dumps(meta, indent=2))
    return job_id


def _write_grid_config(trench_label, grid, notes):
    """The registration, kept where the trench's own files live.

    The build takes its grid config in the request body, so this copy is for
    reading and for ``demo run`` to post back -- not something the application
    picks up on its own.
    """
    directory = storage.TRENCHES_DIR / safe_filename(trench_label, "trench")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "grid_config.json"
    path.write_text(json.dumps({"grid": grid, "notes": notes}, indent=2))
    return path


def _write_harris_matrix(dataset, trench_label, source_job_ids):
    """This trench's stratigraphy, as a stored matrix.

    Correlations and relations come straight from the fixture's own
    ``stratigraphy`` block. The abutments do not: 'is bound to' has no
    representation in a younger-to-older graph, so they are dropped here and
    the count of what was dropped is returned rather than passed over.
    """
    document = dataset.loci()
    stratigraphy = document.get("stratigraphy") or {}
    loci = {
        locus["locus"]: locus
        for locus in (document.get("loci") or [])
        if isinstance(locus.get("locus"), int)
    }

    matrix = harris_store.create_matrix({
        "title": f"{trench_label} {dataset.season} stratigraphy",
        "site": site_grid.POGGIO_CIVITATE,
        "trench": trench_label,
    })

    unit_ids = {}
    units = []
    for number in sorted(loci):
        record = loci[number]
        unit_id = f"unit-{number:012x}"
        unit_ids[number] = unit_id
        unit_type = record.get("unit_type")
        units.append({
            "id": unit_id,
            # The converter's own surface name, not the bare locus number.
            # ``series_order._unit_surface`` only expands a bare number for a
            # unit carrying a FieldWallProfile source_ref, and these units
            # cannot carry one: SourceRef.job_id must be twelve hex digits and
            # the demo's job ids are readable names. Labelling them the way the
            # converter names surfaces is the documented alternative, and it
            # is what makes the matrix order this model rather than refuse it.
            "label": convert_coords.surface_id(number),
            "unit_type": (
                unit_type
                if unit_type in {"deposit", "cut", "structure", "interface",
                                 "natural"}
                else "unknown"
            ),
            "description": record.get("summary"),
            "source_refs": [],
        })

    relations = []
    for index, relation in enumerate(stratigraphy.get("relations") or []):
        younger = unit_ids.get(relation.get("younger"))
        older = unit_ids.get(relation.get("older"))
        if younger is None or older is None:
            continue
        relations.append({
            "id": f"rel-{index:012x}",
            "younger_id": younger,
            "older_id": older,
            "kind": relation.get("kind") if relation.get("kind") in {
                "above", "cuts", "fills", "precedes", "other"} else "other",
            "evidence": relation.get("evidence") or "",
            "source": "manual",
            "notes": None,
        })

    correlations = []
    for index, correlation in enumerate(stratigraphy.get("correlations") or []):
        members = [unit_ids[n] for n in (correlation.get("loci") or [])
                   if n in unit_ids]
        if len(set(members)) < 2:
            continue
        correlations.append({
            "id": f"corr-{index:012x}",
            "unit_ids": members,
            "notes": correlation.get("note") or correlation.get("evidence"),
        })

    candidate = matrix.model_dump(mode="python")
    candidate.update({
        "units": units,
        "relations": relations,
        "correlations": correlations,
        "source_job_ids": [],
        "notes": (
            f"Seeded by the {trench_label} demonstration from "
            f"{dataset.label} {dataset.season}. {dataset.provenance}."
        ),
    })
    saved = harris_store.save_matrix(
        matrix.matrix_id, candidate, matrix.revision)

    dropped = len(stratigraphy.get("abutments") or [])
    return saved.matrix_id, dropped


def _write_finds(dataset, job_id, wall_label):
    """The season's findspots, logged against one of the trench's jobs.

    Finds attach to a job because that is where the application keeps them.
    Every one carries its recorded grid position and elevation unchanged, so
    the findspots that contradict their locus still do.
    """
    from pipeline import editor as editor_pipeline

    written = 0
    skipped = []
    for find in dataset.finds().get("finds") or []:
        if any(find.get(key) is None
               for key in ("gridX", "gridY", "elevation", "locus")):
            skipped.append(find.get("sf"))
            continue
        editor_pipeline.add_find(job_id, {
            "face_id": wall_label,
            "x": find["gridX"],
            "y": find["gridY"],
            "elevation": find["elevation"],
            "locus": str(find["locus"]),
            "description": find.get("description") or "",
            "find_id": f"demo-sf-{find['sf']:03d}",
            "catalog": find.get("catalog"),
            "recorded_date": find.get("date"),
        })
        written += 1
    return written, skipped


# ---------------------------------------------------------------------------
# The seeder
# ---------------------------------------------------------------------------


def seed(scenario_name: str, *, dataset_label: str | None = None) -> dict:
    """Seed one scenario and return a summary of what was written."""
    try:
        scenario = SCENARIOS[scenario_name]
    except KeyError:
        raise DemoError(
            f"unknown scenario {scenario_name!r}. Available: "
            + ", ".join(sorted(SCENARIOS))
        ) from None

    try:
        dataset = datasets.get(dataset_label or scenario.dataset_label)
    except KeyError as error:
        raise DemoError(str(error)) from error

    if scenario.needs_walls and dataset.real_records:
        raise DemoError(
            f"{dataset.label} is a real record set, and this scenario draws "
            "the four wall sections it needs. Invented sections do not go "
            "under a real trench's label. Run this scenario against a "
            "synthetic dataset, or seed the records only with "
            f"--no-walls --dataset {dataset.label}"
        )

    storage.ensure_dirs()
    layout = dataset.layout()
    loci_document = dataset.loci()
    notes = []

    if scenario.complete_registration:
        layout, supplied_notes = complete_layout(layout, loci_document)
        notes.extend(supplied_notes)
    trench_label = trench_label_for(scenario, dataset.label)

    removed = reset(trench_label)

    grid, layout_notes = trench_layout.build_grid_config(layout)
    notes.extend(layout_notes)
    grid_path = _write_grid_config(trench_label, grid, notes)

    wall_names = trench_layout.read_layout(layout)["walls"]
    job_ids = []
    if scenario.needs_walls:
        lengths = _wall_lengths(grid, wall_names)
        surfaces = _drawing_surfaces(grid, wall_names, layout, loci_document)
        for index, wall_label in enumerate(wall_names):
            profile = walls.wall_profile(
                loci_document,
                trench_label=trench_label,
                wall_label=wall_label,
                surface_z=surfaces[wall_label],
                length_m=lengths[wall_label],
                phase_index=index,
            )
            job_ids.append(_write_wall_job(
                dataset,
                trench_label=trench_label,
                wall_label=wall_label,
                profile=profile,
                scenario_name=scenario.name,
            ))

    matrix_id, dropped_abutments = _write_harris_matrix(
        dataset, trench_label, job_ids)

    finds_written, finds_skipped = (0, [])
    if job_ids:
        finds_written, finds_skipped = _write_finds(
            dataset, job_ids[0], wall_names[0])

    unregistered = [c["label"] for c in unregistered_corners(layout)]

    return {
        "scenario": scenario.name,
        "headline": scenario.headline,
        "dataset": f"{dataset.label} {dataset.season}",
        "provenance": dataset.provenance,
        "trench": trench_label,
        "removed": removed,
        "jobs": job_ids,
        "walls": wall_names,
        "grid_config": str(grid_path),
        "unregistered_corners": unregistered,
        "matrix_id": matrix_id,
        "dropped_abutments": dropped_abutments,
        "finds": finds_written,
        "finds_skipped": finds_skipped,
        "notes": notes,
    }


def _drawing_surfaces(grid, wall_names, layout, loci_document):
    """Each wall's ground surface, for measuring the drawn depths from.

    A wall is drawn whether or not its corner was ever surveyed -- the tape
    goes down from the ground either way, and that is exactly the situation
    this pair of demonstrations is about. So a face with no ``surfaceZ`` in the
    grid config still gets a surface here, borrowed from the nearest reading,
    and the *registration* is left missing. The drawing is not the thing that
    is absent; the survey is.
    """
    read = trench_layout.read_layout(layout)
    by_label = {c["label"]: c for c in read["corners"]}
    surfaces = {}
    for index, name in enumerate(wall_names):
        configured = (grid.get("faces") or {}).get(name, {}).get("surfaceZ")
        if isinstance(configured, (int, float)):
            surfaces[name] = float(configured)
            continue
        corner = read["corners"][index]
        elevation, _ = supplied_corner_elevation(
            layout, loci_document, by_label[corner["label"]])
        surfaces[name] = elevation
    return surfaces


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _format(summary: dict) -> str:
    lines = [
        f"Seeded the {summary['scenario']!r} demonstration as trench "
        f"{summary['trench']}.",
        f"  {summary['headline']}",
        "",
        f"  Record set     {summary['dataset']} ({summary['provenance']})",
        f"  Walls          {len(summary['jobs'])} job(s): "
        + (", ".join(summary["jobs"]) or "none"),
        f"  Harris matrix  {summary['matrix_id']} "
        f"({summary['dropped_abutments']} abutment(s) dropped: a "
        f"younger-to-older graph has nowhere to put them)",
        f"  Finds          {summary['finds']} logged"
        + (f", {len(summary['finds_skipped'])} skipped for missing values"
           if summary["finds_skipped"] else ""),
        f"  Registration   {summary['grid_config']}",
    ]
    if summary["unregistered_corners"]:
        lines.append(
            "  Unregistered   "
            + ", ".join(summary["unregistered_corners"])
            + "  <- the build will refuse on the wall this corner registers")
    if summary["notes"]:
        lines.append("")
        lines.append("  Notes from the layout:")
        lines.extend(f"    - {note}" for note in summary["notes"])
    lines += [
        "",
        "  Open http://localhost:5000/trenches and build "
        f"{summary['trench']}, or run `make demo-run`.",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m demo.seed",
        description="Seed a demonstration trench into the application.")
    parser.add_argument(
        "scenario", nargs="?", choices=sorted(SCENARIOS),
        help="which demonstration to seed")
    parser.add_argument(
        "--dataset", default=None,
        help="trench label of the record set to use "
             "(default: the scenario's own)")
    parser.add_argument(
        "--list", action="store_true",
        help="list the available record sets and exit")
    args = parser.parse_args(argv)

    if args.list:
        for label, dataset in sorted(datasets.discover().items()):
            print(f"{label:<8} {dataset.provenance}")
        return 0

    if args.scenario is None:
        parser.exit(2, "error: a scenario is required unless --list is given\n")

    try:
        summary = seed(args.scenario, dataset_label=args.dataset)
    except DemoError as error:
        parser.exit(2, f"error: {error}\n")
    print(_format(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
