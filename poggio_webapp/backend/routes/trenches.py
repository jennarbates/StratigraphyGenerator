"""Routes for trenches: group per-wall jobs and build one combined model.

One job holds one sheet, and a field sheet records one wall, so a whole trench
lives across several jobs that share a `trench_label` (written by the scan
upload and editor-creation routes). These routes group those jobs and run the
merge layer in `pipeline/merge_walls.py` over their normalized extractions,
then hand the result to the existing single-model pipeline.

The build deliberately refuses two things rather than guessing: it will not
build without a grid config, and it will not build on the starter placeholder
registration. Merged models amplify mis-registration -- placeholder values put
the walls in a row 10 m apart instead of around a pit, which produces a
confident-looking model of nothing.
"""

import json
import re
from pathlib import Path

from flask import Blueprint, abort, jsonify, request, send_file
from pipeline import convert_coords, merge_walls, true_dip

from ..config import JOBS_DIR, TRENCHES_DIR
from ..tasks import start_task


bp = Blueprint("trenches", __name__)


def safe_label(label):
    """A filesystem-safe directory name for a trench label.

    Same pattern build_gempy.safe_filename() uses for surface names; copied
    rather than imported so this module never imports the gempy stack.
    """
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(label)).strip("_") or "trench"


def _read_meta(job_directory):
    """A job's meta dict, or None when it is missing or unreadable."""
    try:
        meta = json.loads((job_directory / "meta.json").read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return meta if isinstance(meta, dict) else None


def _grouped_members():
    """{trench_label: [member, ...]} across every readable job.

    Jobs without a usable `trench_label` are skipped silently -- most jobs are
    single sheets that were never assigned to a trench. Members carry a private
    `_normalized_path` for the build; the listing route drops it.
    """
    grouped = {}
    if not JOBS_DIR.exists():
        return grouped
    for job_directory in sorted(JOBS_DIR.iterdir()):
        if not job_directory.is_dir():
            continue
        meta = _read_meta(job_directory)
        if meta is None:
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


def _public(member):
    return {k: v for k, v in member.items() if not k.startswith("_")}


@bp.route("/api/trenches")
def list_trenches():
    return jsonify({
        "trenches": {
            label: [_public(m) for m in members]
            for label, members in _grouped_members().items()
        }
    })


def _resolve_wall_labels(members, notes):
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
        abort(400, description=(
            "two or more sheets claim the same wall of this trench "
            f"({described}). Each job must describe a different wall"))


@bp.route("/api/trenches/<label>/build", methods=["POST"])
def build_trench(label):
    body = request.get_json(force=True, silent=True) or {}
    members = _grouped_members().get(label.strip())
    if not members:
        abort(400, description=(
            f"no jobs are labelled trench {label!r}; set a trench label on "
            "each wall's job first"))

    unready = [m["job_id"] for m in members if not m["has_normalized"]]
    if unready:
        abort(400, description=(
            "these jobs have no normalized extraction yet: "
            + ", ".join(unready)
            + ". Finalize or normalize each wall before building the trench"))

    notes = []
    _resolve_wall_labels(members, notes)

    sheets = []
    for member in members:
        try:
            data = json.loads(Path(member["_normalized_path"]).read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            abort(400, description=(
                f"could not read the normalized extraction for job "
                f"{member['job_id']}: {error}"))
        sheets.append((member["wall_label"], data))

    try:
        merged, merge_notes = merge_walls.merge_extractions(
            sheets, correlation=body.get("correlation"))
    except ValueError as error:
        abort(400, description=str(error))
    notes.extend(merge_notes)

    grid = body.get("grid")
    if not grid:
        return jsonify({
            "needs_grid": True,
            "starter": merge_walls.make_trench_starter_config(merged),
            "notes": notes,
        })

    try:
        grid_warnings = merge_walls.check_trench_grid_config(grid, merged)
    except ValueError as error:
        abort(400, description=str(error))

    # Scoped to the merged trench's own faces (check_trench_grid_config has
    # already proved every one of them is present), so a stale entry left in
    # the operator's config cannot block an otherwise valid build.
    faces_cfg = (grid or {}).get("faces") or {}
    placeholders = [name for name in merge_walls._face_names(merged)
                    if merge_walls._is_placeholder(faces_cfg[name])]
    if placeholders:
        abort(400, description=(
            "these faces still carry the starter placeholder registration: "
            + ", ".join(repr(name) for name in sorted(placeholders))
            + ". Fill in real survey values (originX, originY, surfaceZ, "
              "bearing_deg) before building; placeholders would place the "
              "walls in a row instead of around the pit"))

    trench_directory = TRENCHES_DIR / safe_label(label)
    model_directory = trench_directory / "06_gempy_model"
    model_directory.mkdir(parents=True, exist_ok=True)
    merged_path = trench_directory / "merged.json"
    merged_path.write_text(json.dumps(merged, indent=2))

    points_csv = trench_directory / "points.csv"
    conversion = convert_coords.run_convert(merged, grid, str(points_csv))
    notes.extend(conversion.get("notes") or [])
    if conversion["missing_faces"]:
        abort(400, description=(
            "the grid config has no entry for these faces: "
            + ", ".join(repr(name) for name in conversion["missing_faces"])
            + " -- they would be dropped from the model"))
    if not conversion["n_points"]:
        abort(400, description=(
            "conversion produced no interface points; check that the walls' "
            "layers have boundary points"))

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
            abort(400, description=str(error))
        notes.extend(order_notes)

    try:
        from pipeline import build_gempy as p_build_gempy
    except Exception as error:
        return jsonify({"error": f"gempy import failed: {error}. Install with "
                                 f"`pip install gempy gempy_viewer "
                                 f"--break-system-packages`."}), 400

    task_id = start_task(
        p_build_gempy.run_build,
        conversion["points_csv"],
        conversion["orientations_csv"],
        str(model_directory / "trench_model"),
        project_name=safe_label(label),
        series_order=series_order,
    )
    return jsonify({
        "task_id": task_id,
        "notes": notes,
        "grid_warnings": grid_warnings,
    })


@bp.route("/api/trenches/<label>/file")
def get_trench_file(label):
    """Serve a file from one trench directory, refusing to escape it."""
    rel = request.args.get("path")
    if not rel:
        abort(400, description="missing path")
    base = (TRENCHES_DIR / safe_label(label)).resolve()
    target = (base / rel).resolve()
    if base not in target.parents and target != base:
        abort(400, description="invalid path")
    if not target.is_file():
        abort(404)
    return send_file(target)
