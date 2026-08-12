"""Routes for trenches: list them, build one, serve its files.

The grouping and build rules live in backend/services/trench_builder.py. This
module parses requests, maps TrenchBuildError to a 400, and serializes.
"""

import json

from flask import Blueprint, abort, jsonify, request, send_file

from pipeline import (
    geospatial_sheet,
    locus_import,
    trench_layout,
)
from pipeline import (
    merge_walls as p_merge_walls,
)
from pipeline import (
    site_grid as p_site_grid,
)

from ..services.trench_builder import (
    GempyUnavailableError,
    TrenchBuildError,
    build,
    grouped_members,
    label_variants,
    public_member,
    trench_dir,
)

bp = Blueprint("trenches", __name__)


@bp.route("/api/trenches")
def list_trenches():
    grouped = grouped_members()
    payload = {
        "trenches": {
            label: [public_member(m) for m in members]
            for label, members in grouped.items()
        }
    }
    # Only present for trenches whose jobs were recorded under more than one
    # spelling, so the interface can show that a merge happened.
    variants = {
        label: found
        for label, members in grouped.items()
        if (found := label_variants(members))
    }
    if variants:
        payload["label_variants"] = variants
    return jsonify(payload)


@bp.route("/api/trenches/<label>/build", methods=["POST"])
def build_trench(label):
    body = request.get_json(force=True, silent=True) or {}
    try:
        return jsonify(build(label, body))
    except GempyUnavailableError as error:
        return jsonify({"error": str(error)}), 400
    except TrenchBuildError as error:
        abort(400, description=str(error))


@bp.route("/api/trenches/<label>/file")
def get_trench_file(label):
    """Serve a file from one trench directory, refusing to escape it."""
    rel = request.args.get("path")
    if not rel:
        abort(400, description="missing path")
    base = trench_dir(label).resolve()
    target = (base / rel).resolve()
    if base not in target.parents and target != base:
        abort(400, description="invalid path")
    if not target.is_file():
        abort(404)
    return send_file(target)


@bp.route("/api/trenches/<label>/registration")
def get_registration(label):
    """This trench's stored grid config, if one has been derived for it.

    Of the records-derived registration sources -- a trench layout, the
    season's Geospatial Spreadsheet, the demo seeder -- only the demo seeder
    writes its result to the trench directory; the layout and geospatial-sheet
    routes return a config and store nothing. Whatever did land on disk was
    read by nothing, so the interface asked the operator to paste values the
    application had already worked out. Worse, the
    build answers a gridless request with the *starter placeholder*, which it
    then refuses; a trench with a perfectly good surveyed registration on disk
    looked, from the page, like one with no registration at all.

    404 when there is none, which is the ordinary case for a trench built from
    hand-entered values. The response carries ``source`` so the interface can
    say which kind it is loading rather than implying every prefill is
    surveyed.
    """
    path = trench_dir(label) / "grid_config.json"
    if not path.is_file():
        abort(404, description="no registration has been derived for this trench")
    try:
        stored = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        abort(400, description=f"this trench's registration cannot be read: {error}")

    grid = stored.get("grid") if isinstance(stored, dict) else None
    if not isinstance(grid, dict):
        abort(400, description="this trench's registration is not a grid config")

    return jsonify(
        {
            "trench": label,
            "grid": grid,
            "source": p_merge_walls.registration_source(grid) or "unknown",
            "notes": stored.get("notes") or [],
        }
    )


@bp.route("/api/trenches/<label>/layout", methods=["POST"])
def derive_grid_config(label):
    """Turn a trench's surveyed corners into a grid config.

    The corner coordinates already exist -- staked by total station, logged in
    the Geospatial Spreadsheet -- so this replaces hand-typed registration with
    survey data. Nothing is written: the config comes back for the operator to
    check against the drawings and pass to the build.
    """
    body = request.get_json(force=True, silent=True) or {}
    try:
        config, notes = trench_layout.build_grid_config(body)
    except trench_layout.LayoutError as error:
        abort(400, description=str(error))
    return jsonify({"trench": label, "grid": config, "notes": notes})


@bp.route("/api/trenches/<label>/loci/import", methods=["POST"])
def import_loci(label):
    """Read a downloaded Locus Entry export for this trench.

    A file, not the API: Kobo's own guide treats periodic downloads as the
    normal artifact, and reading a file keeps the promise that nothing leaves
    the machine. Column names are never guessed -- the response says which
    mapping was used, and an unrecognised export is refused with its own
    headers listed.
    """
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        abort(400, description="no export file uploaded")
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeError:
        abort(400, description="this export is not UTF-8 text; export it as CSV")

    column_map = request.form.get("column_map")
    if column_map:
        try:
            column_map = json.loads(column_map)
        except json.JSONDecodeError:
            abort(400, description="column_map must be JSON")
    vertical = request.form.get("vertical")
    if vertical:
        try:
            vertical = json.loads(vertical)
        except json.JSONDecodeError:
            abort(400, description="vertical must be JSON")

    try:
        result = locus_import.read_export(
            text, column_map or None, vertical=vertical or None, trench=label
        )
    except locus_import.LocusImportError as error:
        abort(400, description=str(error))
    return jsonify(result)


@bp.route("/api/trenches/geospatial-sheet", methods=["POST"])
def read_geospatial_sheet():
    """Register every trench in a season from its Geospatial Spreadsheet.

    The corner coordinates are already in that file, so this replaces the
    hand-typed registration for a whole season at once. Reads a downloaded CSV
    and writes nothing; each trench's config comes back for checking.

    A trench whose walls cannot be named from its corner labels -- one extended
    mid-season, whose extra vertices are recorded unlabelled -- is reported
    rather than guessed at, because an invented wall name would match nothing
    on any drawing.
    """
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        abort(400, description="no spreadsheet uploaded")
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeError:
        abort(400, description="this spreadsheet is not UTF-8 text; export it as CSV")

    phase = (request.form.get("phase") or geospatial_sheet.OPENING).strip()
    if phase not in geospatial_sheet.PHASES:
        abort(400, description="phase must be " + " or ".join(geospatial_sheet.PHASES))
    try:
        grid_name = p_site_grid.normalize_grid_name(request.form.get("site_grid"))
    except p_site_grid.GridError as error:
        abort(400, description=str(error))

    try:
        sheet = geospatial_sheet.read_sheet(text)
    except geospatial_sheet.SheetError as error:
        abort(400, description=str(error))

    registered = {}
    needs_wall_names = {}
    for label, record in sheet["trenches"].items():
        notes = list(geospatial_sheet.elevation_readiness(record))
        try:
            layout = geospatial_sheet.layout_for(
                record, phase, site_grid=grid_name or None
            )
            config, layout_notes = trench_layout.build_grid_config(layout)
        except (geospatial_sheet.SheetError, trench_layout.LayoutError) as error:
            needs_wall_names[label] = {
                "reason": str(error),
                "corners": record[phase],
            }
            continue
        registered[label] = {
            "grid": config,
            "trenchbook": record["trenchbook"],
            "supervisors": record["supervisors"],
            "notes": notes + layout_notes + record["notes"],
        }

    return jsonify(
        {
            "phase": phase,
            "registered": registered,
            "needs_wall_names": needs_wall_names,
            "notes": sheet["notes"],
        }
    )
