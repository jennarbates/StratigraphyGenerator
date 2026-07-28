"""Routes for pages."""

import json
import math
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    send_from_directory,
)

from ..jobs import job_dir, load_meta, rel_url


bp = Blueprint("pages", __name__)


def _is_within(path, directory):
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _find_viewer_manifest(job_directory, meta):
    outputs = meta.get("model_outputs")
    configured = (
        outputs.get("viewer_manifest")
        if isinstance(outputs, dict)
        else None
    )
    if isinstance(configured, str) and configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            candidate = job_directory / candidate
        candidate = candidate.resolve()
        if _is_within(candidate, job_directory) and candidate.is_file():
            return candidate

    conventional = (
        job_directory
        / "06_gempy_model"
        / "trench_model_viewer.json"
    ).resolve()
    if _is_within(conventional, job_directory) and conventional.is_file():
        return conventional
    return None


def _valid_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _has_valid_manifest_fields(manifest):
    coordinate_system = manifest.get("coordinate_system")
    extent = manifest.get("extent")
    resolution = manifest.get("resolution")
    series_order = manifest.get("series_order")
    single_face_note = manifest.get("single_face_note")
    surfaces = manifest.get("surfaces")
    lith_block_path = manifest.get("lith_block_path")

    return (
        type(manifest.get("schema_version")) is int
        and manifest["schema_version"] == 1
        and manifest.get("kind") == "gempy-surface-model"
        and isinstance(coordinate_system, dict)
        and coordinate_system.get("units") == "m"
        and coordinate_system.get("up_axis") == "Z"
        and isinstance(extent, list)
        and len(extent) == 6
        and all(_valid_number(value) for value in extent)
        and extent[0] < extent[1]
        and extent[2] < extent[3]
        and extent[4] < extent[5]
        and isinstance(resolution, list)
        and len(resolution) == 3
        and all(
            type(value) is int and value > 0
            for value in resolution
        )
        and isinstance(series_order, list)
        and all(isinstance(name, str) for name in series_order)
        and (
            single_face_note is None
            or isinstance(single_face_note, str)
        )
        and isinstance(surfaces, list)
        and isinstance(lith_block_path, str)
        and bool(lith_block_path)
    )


def _resolve_manifest_artifact(manifest_directory, job_directory, path_str):
    if not isinstance(path_str, str) or not path_str:
        return None
    relative = Path(path_str)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    candidate = (manifest_directory / relative).resolve()
    if not _is_within(candidate, job_directory) or not candidate.is_file():
        return None
    return candidate


def _validated_volume_metadata(volume, resolution):
    if not isinstance(volume, dict):
        return None

    shape = volume.get("shape")
    axes = volume.get("axes")
    lithologies = volume.get("lithologies")
    if not (
        type(volume.get("schema_version")) is int
        and volume["schema_version"] == 1
        and volume.get("format") == "raw"
        and volume.get("dtype") == "uint16-le"
        and volume.get("layout") == "C"
        and axes == ["x", "y", "z"]
        and isinstance(shape, list)
        and len(shape) == 3
        and all(type(value) is int and value > 0 for value in shape)
        and shape == resolution
        and isinstance(volume.get("path"), str)
        and bool(volume["path"])
        and isinstance(lithologies, list)
    ):
        return None

    normalized_lithologies = []
    seen_ids = set()
    for lithology in lithologies:
        if not isinstance(lithology, dict):
            return None
        lithology_id = lithology.get("id")
        name = lithology.get("name")
        if not (
            type(lithology_id) is int
            and 0 <= lithology_id <= 65535
            and lithology_id not in seen_ids
            and isinstance(name, str)
            and bool(name)
        ):
            return None
        seen_ids.add(lithology_id)
        normalized_lithologies.append({
            "id": lithology_id,
            "name": name,
        })

    return {
        "schema_version": volume["schema_version"],
        "format": volume["format"],
        "dtype": volume["dtype"],
        "layout": volume["layout"],
        "axes": list(axes),
        "shape": list(shape),
        "path": volume["path"],
        "lithologies": normalized_lithologies,
    }


def _model3d_from_manifest(job_id, job_directory, manifest_path):
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        current_app.logger.warning(
            "Ignoring unreadable 3D viewer manifest: %s",
            error,
        )
        return None

    if not isinstance(manifest, dict) or not _has_valid_manifest_fields(manifest):
        current_app.logger.warning(
            "Ignoring unsupported or malformed 3D viewer manifest."
        )
        return None

    warnings = []
    surfaces = []
    manifest_directory = manifest_path.parent
    for entry in manifest["surfaces"]:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("name"), str)
            or not entry["name"]
        ):
            warnings.append("A surface entry is malformed and was omitted.")
            continue
        name = entry["name"]
        mesh_path = _resolve_manifest_artifact(
            manifest_directory,
            job_directory,
            entry.get("mesh_path"),
        )
        if mesh_path is None:
            warnings.append(f"Surface {name!r} mesh is unavailable.")
            continue
        surfaces.append({
            "name": name,
            "url": rel_url(job_id, mesh_path),
        })

    if not surfaces:
        current_app.logger.warning(
            "Ignoring 3D viewer manifest with no available surfaces."
        )
        return None

    model3d = {
        "schema_version": manifest["schema_version"],
        "kind": manifest["kind"],
        "coordinate_system": {
            "units": manifest["coordinate_system"]["units"],
            "up_axis": manifest["coordinate_system"]["up_axis"],
        },
        "extent": manifest["extent"],
        "resolution": manifest["resolution"],
        "series_order": manifest["series_order"],
        "single_face_note": manifest["single_face_note"],
        "surfaces": surfaces,
        "warnings": warnings,
    }

    lith_block_path = _resolve_manifest_artifact(
        manifest_directory,
        job_directory,
        manifest["lith_block_path"],
    )
    if lith_block_path is None:
        warnings.append("Lithology block is unavailable.")
    else:
        model3d["lith_block_url"] = rel_url(job_id, lith_block_path)

    raw_volume = manifest.get("volume")
    if raw_volume is not None:
        volume = _validated_volume_metadata(
            raw_volume,
            manifest["resolution"],
        )
        if volume is None:
            warnings.append("Lithology volume metadata is unsupported or malformed.")
        else:
            volume_path = _resolve_manifest_artifact(
                manifest_directory,
                job_directory,
                volume.pop("path"),
            )
            if volume_path is None:
                warnings.append("Lithology volume is unavailable.")
            else:
                volume["url"] = rel_url(job_id, volume_path)
                model3d["volume"] = volume

    return model3d


@bp.route("/")
def index():
    return send_from_directory(current_app.template_folder, "index.html")


@bp.route("/visualizer")
def visualizer():
    return send_from_directory(current_app.static_folder, "visualizer.html")


@bp.route("/api/jobs/<job_id>/visualizer-files")
def visualizer_files(job_id):
    """Everything the visualizer can auto-load for this job, so the user
    doesn't have to re-pick files the server already has. JSONs are served
    as-is; the visualizer normalizes either extraction shape client-side."""
    meta = load_meta(job_id)
    out = {"sheet_type": meta.get("sheet_type"), "jsons": []}

    # marker_calib (origin_px + px_per_m) was computed against the ROTATED
    # working copy written by markers/detect, not the raw scan or the
    # (possibly differently-sized) preprocessed clean image. Serving any
    # other image alongside it would silently misplace the overlay, so if
    # calibration exists, that rotated copy — not clean/scan — is the image
    # this job hands to the visualizer.
    calib = meta.get("marker_calib")
    rotated_candidate = job_dir(job_id) / "03_extraction" / "marker_source_rotated.png"

    if calib and rotated_candidate.exists():
        out["image_url"] = rel_url(job_id, rotated_candidate)
        out["calibration"] = calib
    else:
        # Image: preprocessed clean image if present, else the raw scan —
        # unless the scan is a PDF, which a browser <img> can't show.
        img = (meta.get("manual_image_path") or meta.get("clean_image_path")
               or meta.get("scan_path"))
        if img and Path(img).exists() and not img.lower().endswith(".pdf"):
            out["image_url"] = rel_url(job_id, Path(img))
            manual_calib = meta.get("manual_calibration")
            if manual_calib and img == meta.get("manual_image_path"):
                out["calibration"] = manual_calib
        # calib exists but we can't trust it against whatever image we just
        # served (rotated copy missing) — omit it rather than misalign.

    def add(label, path_str, front=False):
        if path_str and Path(path_str).exists():
            entry = {"label": label, "url": rel_url(job_id, Path(path_str))}
            out["jsons"].insert(0, entry) if front else out["jsons"].append(entry)

    add("normalized", meta.get("normalized_path"))
    add("raw extraction", meta.get("extraction_path"))

    # Field-wall JSON is served raw: the visualizer adapts the
    # FieldWallProfile shape itself (see ingest() in visualizer.html), and
    # unlike fieldwall_to_profiles() it keeps topBoundary and features —
    # the Python adapter only carries what convert() needs. Serving both
    # raw and normalized also keeps A/B compare working for field sheets.

    job_directory = job_dir(job_id).resolve()
    manifest_path = _find_viewer_manifest(job_directory, meta)
    if manifest_path is not None:
        model3d = _model3d_from_manifest(
            job_id,
            job_directory,
            manifest_path,
        )
        if model3d is not None:
            out["model3d"] = model3d

    return jsonify(out)
