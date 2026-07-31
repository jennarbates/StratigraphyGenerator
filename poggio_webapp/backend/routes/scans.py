"""Routes for scans."""

import os

from flask import Blueprint, abort, jsonify, request
from werkzeug.utils import secure_filename

from naming import canonical_trench, clean_label
from pipeline import preprocess as p_preprocess
from pipeline import site_grid as p_site_grid

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

    # The uploaded name is client-supplied and is joined onto a storage root.
    # secure_filename strips directory components and anything else that is not
    # a safe path component; an ordinary name like "field-wall.png" survives
    # unchanged. A name that reduces to nothing keeps the extension we already
    # validated, so the file is still recognisable downstream.
    filename = secure_filename(file.filename) or f"scan{ext}"
    scan_path = d / "01_scan" / filename
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

    # The trench label is an identifier and is canonicalized; the wall label is
    # free text ("north wall") and is only tidied.
    trench_label = canonical_trench(request.form.get("trench_label"))
    wall_label = clean_label(request.form.get("wall_label"))
    season = clean_label(request.form.get("season"))
    locus_epoch = clean_label(request.form.get("locus_epoch"))
    try:
        site_grid_name = p_site_grid.normalize_grid_name(
            request.form.get("site_grid"))
    except p_site_grid.GridError as error:
        abort(400, description=str(error))

    meta = load_meta(job_id)
    meta["sheet_type"] = sheet_type
    if trench_label:
        meta["trench_label"] = trench_label
    if wall_label:
        meta["wall_label"] = wall_label
    if season:
        meta["season"] = season
    if locus_epoch:
        meta["locus_epoch"] = locus_epoch
    if site_grid_name:
        meta["site_grid"] = site_grid_name
    meta["scan_path"] = str(scan_path)
    meta["scan_filename"] = filename
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
    if season:
        payload["season"] = season
    if locus_epoch:
        payload["locus_epoch"] = locus_epoch
    if site_grid_name:
        payload["site_grid"] = site_grid_name
    return jsonify(payload)
