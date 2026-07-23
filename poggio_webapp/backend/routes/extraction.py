"""Routes for extraction."""

import json
import os
from pathlib import Path

from flask import Blueprint, abort, jsonify, request
from pipeline import convert_coords as p_convert_coords

from ..jobs import job_dir, load_meta, rel_url, save_meta
from ..tasks import start_task


bp = Blueprint("extraction", __name__)


@bp.route("/api/jobs/<job_id>/extract", methods=["POST"])
def run_extract(job_id):
    meta = load_meta(job_id)
    if "clean_image_path" not in meta:
        abort(400, description="run preprocess first")

    body = request.get_json(force=True, silent=True) or {}
    api_key = body.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "no Gemini API key provided (and GEMINI_API_KEY not set "
                                  "in the server environment)"}), 400

    image_path = meta["clean_image_path"]
    out_dir = job_dir(job_id) / "03_extraction"
    sheet_type = meta.get("sheet_type", "illustrator")
    max_output_tokens = int(body.get("max_output_tokens", 65536))

    try:
        if sheet_type == "illustrator":
            from pipeline import extract_illustrator as p_extract_illustrator
            out_path = out_dir / "output.json"
            task_id = start_task(
                p_extract_illustrator.run_extraction,
                image_path, str(out_path), api_key,
                max_output_tokens=max_output_tokens,
            )
        else:
            square_cm = body.get("square_cm")
            if not square_cm:
                return jsonify({"error": "square_cm is required for field-wall sheets"}), 400
            from pipeline import extract_fieldwall as p_extract_fieldwall
            out_path = out_dir / "field_wall.json"
            task_id = start_task(
                p_extract_fieldwall.run_extraction,
                image_path, float(square_cm), str(out_path), api_key,
                max_output_tokens=max_output_tokens,
            )
    except ImportError as e:
        return jsonify({"error": f"missing dependency: {e}. Install with "
                                  f"`pip install google-genai pillow pydantic --break-system-packages`."}), 400

    meta["extraction_path"] = str(out_path)
    meta["extraction_task_id"] = task_id
    # a normalize run from a previous extraction no longer describes this one
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)
    return jsonify({"task_id": task_id})


@bp.route("/api/jobs/<job_id>/extract/upload", methods=["POST"])
def upload_extraction(job_id):
    """Reuse a previous extraction JSON instead of calling Gemini.

    Accepts a multipart .json upload, checks that it parses and matches one
    of the two known schemas, and installs it as this job's extraction so
    normalize / validate / convert / visualize pick it up unchanged. Does
    not require preprocess to have run — the whole point is skipping the
    image-analysis path.
    """
    meta = load_meta(job_id)

    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, description="no file uploaded")
    if os.path.splitext(file.filename)[1].lower() != ".json":
        abort(400, description="expected a .json file")

    raw = file.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"not valid JSON: {e}"}), 400

    if isinstance(data, dict) and "trenchProfiles" in data:
        detected = "illustrator"
    elif isinstance(data, dict) and p_convert_coords.is_field_wall(data):
        detected = "fieldwall"
    else:
        return jsonify({"error": "this JSON is neither an illustrator extraction "
                                  "(trenchProfiles) nor a field-wall extraction "
                                  "(loci/layers) — refusing to install it"}), 400

    out_path = job_dir(job_id) / "03_extraction" / "uploaded.json"
    out_path.write_text(raw)

    meta["extraction_path"] = str(out_path)
    meta["sheet_type"] = detected
    meta.pop("extraction_task_id", None)
    meta.pop("normalized_path", None)  # belongs to the previous extraction
    save_meta(job_id, meta)

    return jsonify({"raw_json": raw, "sheet_type": detected,
                    "file_url": rel_url(job_id, out_path)})
