"""Routes for scans."""

import os

from flask import Blueprint, abort, jsonify, request

from naming import clean_label
from pipeline import preprocess as p_preprocess

from ..config import ALLOWED_SCAN_EXT
from ..jobs import job_dir, load_meta, rel_url, save_meta

bp = Blueprint("scans", __name__)


@bp.route("/api/jobs/<job_id>/scan", methods=["POST"])
def upload_scan(job_id):
    d = job_dir(job_id)
    sheet_type = request.form.get("sheet_type", "illustrator")
    if sheet_type not in ("illustrator", "fieldwall"):
        abort(400, description="sheet_type must be 'illustrator' or 'fieldwall'")

    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, description="no file uploaded")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_SCAN_EXT:
        abort(400, description=f"unsupported file type {ext}")

    scan_path = d / "01_scan" / file.filename
    file.save(scan_path)

    dims = None
    recommendation = None
    if ext != ".pdf":
        try:
            width, height = p_preprocess.probe_dimensions(str(scan_path))
            dims = {"width": width, "height": height}
            recommendation = p_preprocess.recommend_upscale(width, height)
        except Exception:
            pass  # non-fatal: recommendation is a nicety, not required to proceed

    trench_label = clean_label(request.form.get("trench_label"))
    wall_label = clean_label(request.form.get("wall_label"))

    meta = load_meta(job_id)
    meta["sheet_type"] = sheet_type
    if trench_label:
        meta["trench_label"] = trench_label
    if wall_label:
        meta["wall_label"] = wall_label
    meta["scan_path"] = str(scan_path)
    meta["scan_filename"] = file.filename
    save_meta(job_id, meta)

    payload = {
        "scan_url": rel_url(job_id, scan_path),
        "sheet_type": sheet_type,
        "is_pdf": ext == ".pdf",
        "dimensions": dims,
        "recommended_upscale": recommendation,
    }
    if trench_label:
        payload["trench_label"] = trench_label
    if wall_label:
        payload["wall_label"] = wall_label
    return jsonify(payload)
