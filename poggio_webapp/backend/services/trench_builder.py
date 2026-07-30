"""Grouping per-wall jobs into a trench and building one merged model.

One job holds one sheet, and a field sheet records one wall, so a whole trench
lives across several jobs sharing a ``trench_label``. This module groups those
jobs, runs the merge layer over their normalized extractions, and hands the
result to the model builder.

The build deliberately refuses two things rather than guessing: it will not
build without a grid config, and it will not build on the starter placeholder
registration. Merged models amplify mis-registration -- placeholder values put
the walls in a row 10 m apart instead of around a pit, which produces a
confident-looking model of nothing.

Refusals raise ``TrenchBuildError`` rather than calling ``abort``. The route
maps that to a 400; keeping Flask out of here is what lets the rules be tested
without an app, and what stopped this from being another 110-line view
function.
"""

import json
from pathlib import Path

from pipeline import convert_coords, merge_walls, true_dip

import storage
from naming import safe_filename

from ..jobs import read_meta
from ..tasks import start_task


class TrenchBuildError(Exception):
    """A refusal the operator can act on. The message is user-facing."""


class GempyUnavailableError(TrenchBuildError):
    """gempy is not installed. The route reports this as an {"error": ...}
    body rather than a refusal message, matching the previous behaviour."""


def safe_label(label):
    """A filesystem-safe directory name for a trench label."""
    return safe_filename(label, "trench")


def trench_dir(label):
    return storage.TRENCHES_DIR / safe_label(label)


def grouped_members():
    """{trench_label: [member, ...]} across every readable job.

    Jobs without a usable `trench_label` are skipped silently -- most jobs are
    single sheets that were never assigned to a trench. Members carry a private
    `_normalized_path` for the build; the listing route drops it.
    """
    grouped = {}
    if not storage.JOBS_DIR.exists():
        return grouped
    for job_directory in sorted(storage.JOBS_DIR.iterdir()):
        if not job_directory.is_dir():
            continue
        meta = read_meta(job_directory, None)
        if not isinstance(meta, dict):
            continue
        label = meta.get("trench_label")
        if not isinstance(label, str) or not label.strip():
            continue
        normalized = meta.get("normalized_path")
        wall_label = meta.get("wall_label")
        grouped.setdefault(label.strip(), []).append({
            "job_id": meta.get("job_id") or job_directory.name,
            "wall_label": wall_label if isinstance(wall_label, str) else None,
            "sheet_type": meta.get("sheet_type"),
            "has_normalized": bool(
                normalized and Path(normalized).is_file()),
            "_normalized_path": normalized,
        })
    for members in grouped.values():
        members.sort(key=lambda m: (m["wall_label"] or "", m["job_id"]))
    return grouped


def public_member(member):
    return {k: v for k, v in member.items() if not k.startswith("_")}


def resolve_wall_labels(members, notes):
    """Give every member a wall label, deriving one where the operator left it
    blank. Duplicates are fatal: two faces with one name would collide in the
    merged document, and GemPy fuses faces by exact name."""
    for member in members:
        if not member["wall_label"]:
            derived = f"{member['sheet_type'] or 'wall'} {member['job_id']}"
            member["wall_label"] = derived
            notes.append(
                f"job {member['job_id']} has no wall_label; using {derived!r} "
                "as its face name. Set a wall label so the face names match "
                "your survey and the grid config")

    by_label = {}
    for member in members:
        by_label.setdefault(member["wall_label"].lower(), []).append(member)
    clashes = [group for group in by_label.values() if len(group) > 1]
    if clashes:
        described = "; ".join(
            f"{group[0]['wall_label']!r}: "
            + ", ".join(m["job_id"] for m in group)
            for group in clashes)
        raise TrenchBuildError(
            "two or more sheets claim the same wall of this trench "
            f"({described}). Each job must describe a different wall")


def _load_sheets(members):
    sheets = []
    for member in members:
        try:
            data = json.loads(Path(member["_normalized_path"]).read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise TrenchBuildError(
                f"could not read the normalized extraction for job "
                f"{member['job_id']}: {error}") from error
        sheets.append((member["wall_label"], data))
    return sheets


def _check_registration(grid, merged):
    """Scoped to the merged trench's own faces (check_trench_grid_config has
    already proved every one of them is present), so a stale entry left in the
    operator's config cannot block an otherwise valid build."""
    faces_cfg = (grid or {}).get("faces") or {}
    placeholders = [name for name in merge_walls.face_names(merged)
                    if merge_walls.is_placeholder(faces_cfg[name])]
    if placeholders:
        raise TrenchBuildError(
            "these faces still carry the starter placeholder registration: "
            + ", ".join(repr(name) for name in sorted(placeholders))
            + ". Fill in real survey values (originX, originY, surfaceZ, "
              "bearing_deg) before building; placeholders would place the "
              "walls in a row instead of around the pit")


def build(label, body):
    """Build the merged model for one trench.

    Returns either ``{"needs_grid": True, ...}`` when the caller has not
    supplied a grid config yet, or ``{"task_id": ...}`` once the build starts.
    Raises TrenchBuildError for anything the operator must fix first.
    """
    members = grouped_members().get(label.strip())
    if not members:
        raise TrenchBuildError(
            f"no jobs are labelled trench {label!r}; set a trench label on "
            "each wall's job first")

    unready = [m["job_id"] for m in members if not m["has_normalized"]]
    if unready:
        raise TrenchBuildError(
            "these jobs have no normalized extraction yet: "
            + ", ".join(unready)
            + ". Finalize or normalize each wall before building the trench")

    notes = []
    resolve_wall_labels(members, notes)
    sheets = _load_sheets(members)

    try:
        merged, merge_notes = merge_walls.merge_extractions(
            sheets, correlation=body.get("correlation"))
    except ValueError as error:
        raise TrenchBuildError(str(error)) from error
    notes.extend(merge_notes)

    grid = body.get("grid")
    if not grid:
        return {
            "needs_grid": True,
            "starter": merge_walls.make_trench_starter_config(merged),
            "notes": notes,
        }

    try:
        grid_warnings = merge_walls.check_trench_grid_config(grid, merged)
    except ValueError as error:
        raise TrenchBuildError(str(error)) from error

    _check_registration(grid, merged)

    trench_directory = trench_dir(label)
    model_directory = trench_directory / "06_gempy_model"
    model_directory.mkdir(parents=True, exist_ok=True)
    merged_path = trench_directory / "merged.json"
    merged_path.write_text(json.dumps(merged, indent=2))

    points_csv = trench_directory / "points.csv"
    conversion = convert_coords.run_convert(merged, grid, str(points_csv))
    notes.extend(conversion.get("notes") or [])
    if conversion["missing_faces"]:
        raise TrenchBuildError(
            "the grid config has no entry for these faces: "
            + ", ".join(repr(name) for name in conversion["missing_faces"])
            + " -- they would be dropped from the model")
    if not conversion["n_points"]:
        raise TrenchBuildError(
            "conversion produced no interface points; check that the walls' "
            "layers have boundary points")

    # Only merged trenches can do this: one wall alone can measure the dip in
    # its own plane and nothing more, and an apparent dip is always shallower
    # than the true one. With two walls the plane is determined, so every seed
    # for a surface can carry the same real orientation instead of two
    # disagreeing shadows of it. Single-sheet builds never come through here.
    notes.extend(true_dip.apply_true_dip(
        conversion["points_csv"], conversion["orientations_csv"], grid))

    series_order = body.get("series_order")
    if not series_order:
        try:
            series_order, order_notes = merge_walls.merged_series_order(merged)
        except ValueError as error:
            raise TrenchBuildError(str(error)) from error
        notes.extend(order_notes)

    # Imported here, not at module scope: gempy is an optional extra and every
    # refusal above must work without it installed.
    try:
        from pipeline import build_gempy
    except Exception as error:
        raise GempyUnavailableError(
            f"gempy import failed: {error}. Install with "
            f"`pip install gempy gempy_viewer --break-system-packages`."
        ) from error

    task_id = start_task(
        build_gempy.run_build,
        conversion["points_csv"],
        conversion["orientations_csv"],
        str(model_directory / "trench_model"),
        project_name=safe_label(label),
        series_order=series_order,
    )
    return {
        "task_id": task_id,
        "notes": notes,
        "grid_warnings": grid_warnings,
    }

