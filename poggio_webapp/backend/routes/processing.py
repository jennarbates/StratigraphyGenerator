"""Routes for processing."""

import json
from pathlib import Path

from flask import Blueprint, abort, jsonify, request
from pipeline import convert_coords as p_convert_coords
from pipeline import normalizer as p_normalizer
from pipeline import validator as p_validator

from ..errors import _friendly_error
from ..jobs import job_dir, load_meta, rel_url, save_meta


bp = Blueprint("processing", __name__)


@bp.route("/api/jobs/<job_id>/normalize", methods=["POST"])
def run_normalize(job_id):
    meta = load_meta(job_id)
    if "extraction_path" not in meta:
        abort(400, description="run extraction first")

    out_path = job_dir(job_id) / "04_normalize_validate" / "output_clean.json"
    try:
        data, log = p_normalizer.run_normalize(meta["extraction_path"], str(out_path))
    except Exception as e:
        return jsonify({"error": _friendly_error(e)}), 400

    meta["normalized_path"] = str(out_path)
    save_meta(job_id, meta)
    return jsonify({"data": data, "log": log, "file_url": rel_url(job_id, out_path)})


@bp.route("/api/jobs/<job_id>/validate", methods=["POST"])
def run_validate(job_id):
    meta = load_meta(job_id)
    path = meta.get("normalized_path") or meta.get("extraction_path")
    if not path:
        abort(400, description="run extraction (and ideally normalize) first")

    body = request.get_json(force=True, silent=True) or {}
    try:
        report = p_validator.run_validate(
            path,
            monotonic_tolerance=float(body.get("monotonic_tolerance",
                                                p_validator.DEFAULT_MONOTONIC_TOLERANCE_M)),
            top_continuity_tolerance=float(body.get("top_continuity_tolerance",
                                                     p_validator.DEFAULT_TOP_CONTINUITY_TOLERANCE_M)),
            max_depth=float(body.get("max_depth", p_validator.DEFAULT_MAX_PLAUSIBLE_DEPTH_M)),
        )
    except Exception as e:
        return jsonify({"error": _friendly_error(e)}), 400

    return jsonify(report)


@bp.route("/api/jobs/<job_id>/gridconfig/starter", methods=["GET"])
def gridconfig_starter(job_id):
    meta = load_meta(job_id)
    path = meta.get("normalized_path") or meta.get("extraction_path")
    if not path:
        abort(400, description="run extraction first")
    data = json.loads(Path(path).read_text())
    if "trenchProfiles" not in data and not p_convert_coords.is_field_wall(data):
        return jsonify({"error": "this extraction is neither an illustrator sheet "
                                  "(trenchProfiles) nor a field-wall sheet (loci/layers) — "
                                  "nothing to register"}), 400
    cfg = p_convert_coords.make_starter_config(data)
    return jsonify(cfg)


@bp.route("/api/jobs/<job_id>/convert", methods=["POST"])
def run_convert(job_id):
    meta = load_meta(job_id)
    path = meta.get("normalized_path") or meta.get("extraction_path")
    if not path:
        abort(400, description="run extraction first")

    body = request.get_json(force=True, silent=True) or {}
    grid = body.get("grid_config")
    if not grid:
        abort(400, description="grid_config is required")

    data = json.loads(Path(path).read_text())
    out_csv = job_dir(job_id) / "05_convert_coords" / "points.csv"

    try:
        result = p_convert_coords.run_convert(data, grid, str(out_csv))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if result["n_points"] == 0:
        return jsonify({"error": "conversion produced 0 points. Either no face in the "
                                  "extraction matched a name in the grid config "
                                  f"(unmatched: {', '.join(result['missing_faces']) or 'none'}), "
                                  "or the layers carry no usable boundary coordinates."}), 400

    meta["points_csv"] = result["points_csv"]
    meta["orientations_csv"] = result["orientations_csv"]
    save_meta(job_id, meta)

    result["points_csv_url"] = rel_url(job_id, result["points_csv"])
    result["orientations_csv_url"] = rel_url(job_id, result["orientations_csv"])
    return jsonify(result)
