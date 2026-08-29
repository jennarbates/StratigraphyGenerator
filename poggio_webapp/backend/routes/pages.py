"""Page routes, and the visualizer's file-discovery endpoint.

Manifest reading and validation live in backend/services/viewer_files.py.
"""

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)

import storage
from pipeline import normalizer

from ..jobs import job_dir, job_list, job_record, load_meta, rel_url
from ..services.viewer_files import find_viewer_manifest, model3d_from_manifest

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    return render_template("index.html", jobs=job_list(), result_job=None)


@bp.route("/jobs/<job_id>")
def job_results(job_id):
    job = job_record(storage.JOBS_DIR / job_id)
    if job is None:
        abort(404, description="unknown job id")
    if job["status"] == "editing":
        return redirect(url_for("editor.editor_page", job_id=job_id))
    return render_template("index.html", jobs=job_list(), result_job=job)


@bp.route("/trenches")
def trenches_page():
    """The multi-wall trench list. Every trench, wall and build state on it
    comes from /api/trenches at run time, so nothing job-specific is rendered
    into the shell."""
    return render_template("trenches.html")


@bp.route("/visualizer")
def visualizer():
    return send_from_directory(current_app.static_folder, "visualizer.html")


def _has_canonical_source(job_directory):
    """True when load_canonical() would have something to read."""
    candidates = (
        Path("04_normalize_validate") / normalizer.CANONICAL_FILENAME,
        *normalizer.CANONICAL_SOURCES,
    )
    return any((job_directory / candidate).is_file() for candidate in candidates)


@bp.route("/api/jobs/<job_id>/canonical")
def job_canonical(job_id):
    """The job's canonical section document: the artifact when the job has
    one, else canonicalized on read (D4)."""
    try:
        document = normalizer.load_canonical(job_dir(job_id))
    except FileNotFoundError:
        abort(404, description="job has no extraction to canonicalize")
    except ValueError as error:
        abort(422, description=str(error))
    return jsonify(document)


@bp.route("/api/jobs/<job_id>/visualizer-files")
def visualizer_files(job_id):
    """Everything the visualizer can auto-load for this job, so the user
    doesn't have to re-pick files the server already has. The canonical
    document is listed first; the legacy files stay behind it for A/B
    compare, adapted client-side by the same shim that handles old saved
    files."""
    meta = load_meta(job_id)
    out = {"sheet_type": meta.get("sheet_type"), "jsons": []}

    # marker_calib (origin_px + px_per_m) was computed against the ROTATED
    # working copy written by markers/detect, not the raw scan or the
    # (possibly differently-sized) preprocessed clean image. Serving any
    # other image alongside it would silently misplace the overlay, so if
    # calibration exists, that rotated copy (not clean/scan) is the image
    # this job hands to the visualizer.
    calib = meta.get("marker_calib")
    rotated_candidate = job_dir(job_id) / "03_extraction" / "marker_source_rotated.png"

    if calib and rotated_candidate.exists():
        out["image_url"] = rel_url(job_id, rotated_candidate)
        out["calibration"] = calib
    else:
        # Image: preprocessed clean image if present, else the raw scan,
        # unless the scan is a PDF, which a browser <img> can't show.
        img = (
            meta.get("manual_image_path")
            or meta.get("clean_image_path")
            or meta.get("scan_path")
        )
        if img and Path(img).exists() and not img.lower().endswith(".pdf"):
            out["image_url"] = rel_url(job_id, Path(img))
            manual_calib = meta.get("manual_calibration")
            if manual_calib and img == meta.get("manual_image_path"):
                out["calibration"] = manual_calib
        # calib exists but we can't trust it against whatever image we just
        # served (rotated copy missing), so omit it rather than misalign.

    def add(label, path_str, front=False):
        if path_str and Path(path_str).exists():
            entry = {"label": label, "url": rel_url(job_id, Path(path_str))}
            out["jsons"].insert(0, entry) if front else out["jsons"].append(entry)

    add("normalized", meta.get("normalized_path"))
    add("raw extraction", meta.get("extraction_path"))
    if _has_canonical_source(job_dir(job_id)):
        out["jsons"].insert(
            0,
            {"label": "canonical", "url": f"/api/jobs/{job_id}/canonical"},
        )

    job_directory = job_dir(job_id).resolve()
    manifest_path = find_viewer_manifest(job_directory, meta)
    if manifest_path is not None:
        model3d = model3d_from_manifest(
            job_id,
            job_directory,
            manifest_path,
        )
        if model3d is not None:
            out["model3d"] = model3d

    return jsonify(out)
