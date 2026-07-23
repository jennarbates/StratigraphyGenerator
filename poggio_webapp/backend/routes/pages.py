"""Routes for pages."""

from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    send_from_directory,
)

from ..jobs import load_meta, rel_url


bp = Blueprint("pages", __name__)


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

    # Image: preprocessed clean image if present, else the raw scan —
    # unless the scan is a PDF, which a browser <img> can't show.
    img = meta.get("clean_image_path") or meta.get("scan_path")
    if img and Path(img).exists() and not img.lower().endswith(".pdf"):
        out["image_url"] = rel_url(job_id, Path(img))

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

    return jsonify(out)
