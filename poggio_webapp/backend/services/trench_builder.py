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

import csv
import json
from pathlib import Path

import storage
from naming import canonical_trench, safe_filename
from pipeline import (
    convert_coords,
    merge_walls,
    series_order,
    site_elevation,
    site_grid,
    true_dip,
)

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
        # Canonicalized on read, not just on write: jobs created before the
        # rule existed still carry whatever the operator typed, and grouping
        # them by the raw string is exactly the split this closes.
        label = canonical_trench(meta.get("trench_label"))
        if not label:
            continue
        normalized = meta.get("normalized_path")
        wall_label = meta.get("wall_label")
        season = meta.get("season")
        locus_epoch = meta.get("locus_epoch")
        grouped.setdefault(label, []).append({
            "job_id": meta.get("job_id") or job_directory.name,
            "wall_label": wall_label if isinstance(wall_label, str) else None,
            "sheet_type": meta.get("sheet_type"),
            "season": season if isinstance(season, str) else None,
            "locus_epoch": (
                locus_epoch if isinstance(locus_epoch, str) else None),
            # What the operator actually typed. Kept so the canonicalization
            # can be seen rather than inferred: a job that was grouped under a
            # label it does not literally carry should be able to say so.
            "recorded_label": meta.get("trench_label"),
            "site_grid": (
                meta["site_grid"] if isinstance(meta.get("site_grid"), str)
                else None),
            "has_normalized": bool(
                normalized and Path(normalized).is_file()),
            "_normalized_path": normalized,
        })
    for members in grouped.values():
        members.sort(key=lambda m: (m["wall_label"] or "", m["job_id"]))
    return grouped


def public_member(member):
    return {k: v for k, v in member.items() if not k.startswith("_")}


def label_variants(members):
    """The distinct spellings this trench's jobs were recorded under.

    Canonicalization is not a mutation here -- stored metadata keeps whatever
    the operator typed, and grouping normalizes on read. That preserves the
    transcription, but it means jobs can be silently merged under a label none
    of them literally carries. Returning the variants lets the interface show
    the merge instead of hiding it, which is the same choice the merge layer
    makes when it reports a Munsell disagreement rather than resolving it out
    of sight.

    Sorted, and empty when every job already agreed with the canonical form.
    """
    canonical = {canonical_trench(m.get("recorded_label")) for m in members}
    recorded = {
        m["recorded_label"] for m in members
        if isinstance(m.get("recorded_label"), str) and m["recorded_label"].strip()
    }
    if len(recorded) < 2 and recorded <= canonical:
        return []
    return sorted(recorded)


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


def check_locus_epochs(members, notes):
    """Refuse to merge sheets whose locus numbers may not mean the same thing.

    *Excavation and Documentation Procedures* makes locus numbering conditional
    on how a trench was reopened:

      * reopened in consecutive years -- numbering CONTINUES ("if the last
        locus excavated ... in prior year was Locus 10, you will begin
        excavating in Locus 11");
      * reopened after a gap -- "you may treat this as a new trench opening --
        you do not need to continue with any locus sequences";
      * an administratively new trench over older ones -- restarts at Locus 1.

    So neither (trench, locus) nor (trench, season, locus) is a safe fixed key.
    The first fuses two deposits when numbering restarted; the second splits
    one deposit that ran across two consecutive seasons, which is ordinary.

    What the application cannot do is work out which case applies, so the
    numbering epoch is declared rather than inferred. Consecutive seasons pass
    without one, because that is the case where numbering demonstrably
    continues. A gap does not: guessing there would either fuse two deposits
    into one model surface or split one into two, and both look plausible in
    the output.
    """
    epochs = sorted({m["locus_epoch"] for m in members if m["locus_epoch"]})
    if len(epochs) > 1:
        raise TrenchBuildError(
            "these sheets declare different locus numbering epochs ("
            + ", ".join(repr(e) for e in epochs)
            + "). Locus numbers restart at each epoch, so the same number "
            "means different deposits on either side of one. Build each epoch "
            "as its own trench")
    if epochs:
        undeclared = [m["job_id"] for m in members if not m["locus_epoch"]]
        if undeclared:
            notes.append(
                f"jobs {', '.join(undeclared)} declare no locus epoch; taking "
                f"them as part of {epochs[0]!r}, the only one declared")
        return

    seasons = sorted({m["season"] for m in members if m["season"]})
    if len(seasons) < 2:
        return

    years = sorted({int(s) for s in seasons if s.isdigit() and len(s) == 4})
    unparsed = [s for s in seasons if not (s.isdigit() and len(s) == 4)]
    if unparsed:
        raise TrenchBuildError(
            "these sheets span more than one season and at least one season is "
            "not a 4-digit year ("
            + ", ".join(repr(s) for s in unparsed)
            + "), so whether their locus numbering continues cannot be "
            "determined. Set a locus_epoch on each job")
    if years == list(range(years[0], years[-1] + 1)):
        notes.append(
            f"sheets span consecutive seasons {years[0]}-{years[-1]}; locus "
            "numbering continues across those, so their locus numbers are "
            "being read as one sequence")
        return

    missing = [y for y in range(years[0], years[-1] + 1) if y not in years]
    raise TrenchBuildError(
        "these sheets span non-consecutive seasons ("
        + ", ".join(str(y) for y in years)
        + f"; nothing from {', '.join(str(y) for y in missing)}). A trench "
        "reopened after a gap may restart its locus numbering, so the same "
        "locus number need not mean the same deposit. Set a locus_epoch on "
        "each job to say which numbering sequence it belongs to")


def check_site_grid(members, grid, notes):
    """Refuse to build a trench whose sheets disagree about which grid.

    Poggio Civitate runs two local grids -- the hill and Vescovado di Murlo --
    so a pair of coordinates is only a location once the grid is named. The two
    origins are about 1.5 million metres apart once projected, so a mismatch is
    never a near miss that a tolerance could absorb: it is one wall of the
    trench placed in another village.

    Returns the agreed grid name, or '' when no sheet declared one. Not
    declaring is permitted -- most existing jobs predate the field, and every
    trench modelled so far is on one grid -- but a *disagreement* is not.
    """
    declared = sorted({m["site_grid"] for m in members if m["site_grid"]})
    if len(declared) > 1:
        raise TrenchBuildError(
            "these sheets are recorded against different site grids ("
            + ", ".join(repr(name) for name in declared)
            + "). The two local grids have origins about 1.5 million metres "
            "apart, so their coordinates cannot be combined into one trench")

    from_sheets = declared[0] if declared else ""
    from_config = ""
    if isinstance(grid, dict):
        try:
            from_config = site_grid.normalize_grid_name(grid.get("site_grid"))
        except site_grid.GridError as error:
            raise TrenchBuildError(str(error)) from error

    if from_sheets and from_config and from_sheets != from_config:
        raise TrenchBuildError(
            f"the grid config is for site grid {from_config!r} but these "
            f"sheets were recorded against {from_sheets!r}. One of the two is "
            "wrong, and the difference is not a rounding error")

    agreed = from_config or from_sheets
    if not agreed:
        notes.append(
            "no site grid is declared on these sheets or in the grid config. "
            "Poggio Civitate runs two local grids, so record which one these "
            "coordinates belong to")
    return agreed


def check_vertical_frame(grid, notes):
    """Report on a grid config's vertical block, refusing what cannot resolve.

    A trench still recorded below datum with no datum-nail elevation cannot
    produce absolute elevations at all, and defaulting the datum to zero would
    put the model tens of metres from the trench while looking entirely
    consistent. Everything else is a note: by the site's own rule below-datum
    is transitional paperwork, which is worth saying out loud but is not this
    application's to refuse.
    """
    vertical = (grid or {}).get("vertical")
    if not isinstance(vertical, dict):
        return
    try:
        site_elevation.normalize_frame(vertical.get("frame"))
        description = site_elevation.describe(vertical)
    except site_elevation.ElevationError as error:
        raise TrenchBuildError(str(error)) from error

    if (vertical.get("entryForm") == "below-datum"
            and site_elevation.datum_absolute_z(vertical) is None):
        raise TrenchBuildError(
            "this trench's elevations are recorded below datum and the datum "
            "nail's own absolute elevation is not recorded, so they cannot be "
            "resolved. Enter the datum elevation before building -- treating "
            "a missing datum as zero would place the model tens of metres "
            "from the trench without anything downstream noticing")
    notes.append(description)


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
                    if merge_walls.is_placeholder(faces_cfg[name], grid)]
    if placeholders:
        raise TrenchBuildError(
            "these faces still carry the starter placeholder registration: "
            + ", ".join(repr(name) for name in sorted(placeholders))
            + ". Fill in real survey values (originX, originY, surfaceZ, "
              "bearing_deg) before building; placeholders would place the "
              "walls in a row instead of around the pit")


def _modelled_surfaces(points_csv):
    """The surface names the converted points actually contain."""
    surfaces = set()
    with open(points_csv, newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("surface") or "").strip()
            if name:
                surfaces.add(name)
    return surfaces


def _harris_order(label, surfaces, notes):
    """A series order from this trench's Harris matrix, or None.

    None means "no matrix to use", which is ordinary. A matrix that exists but
    cannot order this model is an error worth raising: it means the record and
    the model disagree about what is in the trench, and quietly falling back
    would hide that.
    """
    from .. import harris_store

    candidates = series_order.matrices_for_trench(
        label, harris_store.list_matrices())
    if not candidates:
        return None
    if len(candidates) > 1:
        titles = ", ".join(
            f"{c['title']!r} ({c['matrix_id']})" for c in candidates)
        raise TrenchBuildError(
            f"more than one Harris matrix is recorded for this trench: "
            f"{titles}. Keep one, or pass an explicit series_order")

    summary = candidates[0]
    try:
        matrix = harris_store.load_matrix(summary["matrix_id"])
    except harris_store.HarrisStoreError as error:
        raise TrenchBuildError(
            f"the Harris matrix for this trench could not be read: {error}"
        ) from error

    try:
        order, arbitrary, order_notes = series_order.from_harris(
            matrix, available_surfaces=surfaces)
    except series_order.SeriesOrderError as error:
        raise TrenchBuildError(str(error)) from error

    notes.append(
        f"using the Harris matrix {summary['title']!r} "
        f"({summary['matrix_id']}, revision {summary['revision']}) for "
        "stratigraphic order")
    notes.extend(order_notes)
    return order, arbitrary


def resolve_series_order(label, body, merged, points_csv, notes):
    """Pick the best available evidence for stratigraphic order.

    Precedence, best first: an order supplied with the request, this trench's
    Harris matrix, the layer sequence recorded on the walls. If none of those
    yields one, ``run_build`` falls back to sorting by mean elevation -- and
    labels it, because at this site that assumption is documented as sometimes
    false rather than merely imprecise.

    Returns ``(order, source, arbitrary_pairs)``.
    """
    supplied = body.get("series_order")
    if supplied:
        notes.append(series_order.describe(series_order.SUPPLIED))
        return supplied, series_order.SUPPLIED, []

    surfaces = _modelled_surfaces(points_csv)
    harris = _harris_order(label, surfaces, notes)
    if harris is not None:
        order, arbitrary = harris
        return order, series_order.HARRIS, arbitrary

    try:
        order, order_notes = merge_walls.merged_series_order(merged)
    except ValueError as error:
        raise TrenchBuildError(str(error)) from error
    notes.extend(order_notes)
    if order:
        notes.append(series_order.describe(series_order.RECORDED))
        return order, series_order.RECORDED, []

    notes.append("WARNING: " + series_order.describe(series_order.ELEVATION))
    return None, series_order.ELEVATION, []


def build(label, body):
    """Build the merged model for one trench.

    Returns either ``{"needs_grid": True, ...}`` when the caller has not
    supplied a grid config yet, or ``{"task_id": ...}`` once the build starts.
    Raises TrenchBuildError for anything the operator must fix first.
    """
    # Canonicalized so a request for "T-104" finds the group that "T104"
    # built, matching how grouped_members() keys it.
    canonical = canonical_trench(label)
    members = grouped_members().get(canonical)
    if not members:
        raise TrenchBuildError(
            f"no jobs are labelled trench {canonical or label!r}; set a trench "
            "label on each wall's job first")

    unready = [m["job_id"] for m in members if not m["has_normalized"]]
    if unready:
        raise TrenchBuildError(
            "these jobs have no normalized extraction yet: "
            + ", ".join(unready)
            + ". Finalize or normalize each wall before building the trench")

    notes = []
    check_locus_epochs(members, notes)
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

    check_site_grid(members, grid, notes)
    check_vertical_frame(grid, notes)

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

    series_order, order_source, arbitrary_pairs = resolve_series_order(
        label, body, merged, conversion["points_csv"], notes)

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
        surface_labels=conversion.get("surface_labels"),
        order_source=order_source,
        arbitrary_pairs=arbitrary_pairs,
    )
    return {
        "task_id": task_id,
        "notes": notes,
        "grid_warnings": grid_warnings,
    }

