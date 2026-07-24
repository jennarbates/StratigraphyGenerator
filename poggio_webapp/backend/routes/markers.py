"""Routes for markers."""

import json
import os
from pathlib import Path

from flask import Blueprint, abort, jsonify, request

from ..errors import _friendly_error
from ..jobs import job_dir, load_meta, rel_url, save_meta
from ..tasks import start_task


bp = Blueprint("markers", __name__)


@bp.route("/api/jobs/<job_id>/markers/preview", methods=["POST"])
def markers_preview(job_id):
    """Write the rotated working copy the user clicks reference points on.
    All later pixel coordinates are in this rotated frame."""
    meta = load_meta(job_id)
    if "scan_path" not in meta:
        abort(400, description="upload a scan first")
    if meta["scan_path"].lower().endswith(".pdf"):
        return jsonify({"error": "marker detection works on photo scans, not "
                                  "PDFs — upload the photo directly"}), 400
    body = request.get_json(force=True, silent=True) or {}
    rotate = int(body.get("rotate", 0))
    from pipeline import detect_markers as p_detect_markers
    out_dir = job_dir(job_id) / "03_extraction"
    out_path = out_dir / "marker_source_rotated.png"
    try:
        w, h = p_detect_markers.write_rotated_preview(
            meta["scan_path"], rotate, str(out_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    meta["marker_rotate"] = rotate
    save_meta(job_id, meta)
    return jsonify({"image_url": rel_url(job_id, out_path),
                    "width": w, "height": h})


@bp.route("/api/jobs/<job_id>/markers/detect", methods=["POST"])
def markers_detect(job_id):
    meta = load_meta(job_id)
    if "scan_path" not in meta:
        abort(400, description="upload a scan first")
    body = request.get_json(force=True, silent=True) or {}
    for k in ("square_cm", "origin_px", "ref_px", "ref_meters", "bottom_px_y"):
        if body.get(k) in (None, "", []):
            return jsonify({"error": f"{k} is required — click the wall's "
                                      "top-left, top-right, and lowest point, "
                                      "and give the real width between the top "
                                      "corners"}), 400
    from pipeline import detect_markers as p_detect_markers
    out_dir = job_dir(job_id) / "03_extraction"
    try:
        result = p_detect_markers.run_detect(
            meta["scan_path"],
            origin_px=body["origin_px"], ref_px=body["ref_px"],
            ref_meters=float(body["ref_meters"]),
            bottom_px_y=float(body["bottom_px_y"]),
            square_cm=float(body["square_cm"]),
            out_dir=str(out_dir),
            rotate=int(body.get("rotate", meta.get("marker_rotate", 0))),
            min_marker_paper_mm=float(body.get("min_marker_paper_mm", 0.5)),
            max_marker_paper_mm=float(body.get("max_marker_paper_mm", 2.5)),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    markers_path = out_dir / "markers.json"
    markers_path.write_text(json.dumps(result["markers"]))
    # Not the final markers_path used downstream — /markers/confirm
    # overwrites this once a person has reviewed the candidates. Keeping it
    # here too means "confirm" is optional: assign still works on the raw
    # CV output if someone skips straight past review.
    meta["markers_path"] = str(markers_path)
    meta["marker_square_cm"] = float(body["square_cm"])
    meta["marker_calib"] = {"origin_px": result["origin_px"],
                            "px_per_m": result["px_per_m"]}
    save_meta(job_id, meta)

    return jsonify({
        "markers": result["markers"],
        "rejected": result["rejected"],
        "n_accepted": result["n_accepted"],
        "n_rejected_in_box": result["n_rejected_in_box"],
        "px_per_m": result["px_per_m"],
        "debug_image_url": rel_url(job_id, result["debug_image"]),
        "csv_url": rel_url(job_id, result["csv"]),
    })


@bp.route("/api/jobs/<job_id>/markers/confirm", methods=["POST"])
def markers_confirm(job_id):
    """Install the user-reviewed feature list (CV candidates with some
    toggled off, plus any manually added) as this job's markers. Pixel
    coordinates are trusted as given; x_m/depth_m are always recomputed
    from them here (not taken from the client) so a manually-added point
    and a CV point are calibrated identically."""
    meta = load_meta(job_id)
    calib = meta.get("marker_calib")
    if not calib:
        abort(400, description="run marker detection first")
    body = request.get_json(force=True, silent=True) or {}
    points = body.get("markers") or []
    if not points:
        return jsonify({"error": "at least one confirmed feature is required"}), 400

    ox, oy = calib["origin_px"]
    px_per_m = calib["px_per_m"]
    out = []
    for i, p in enumerate(points):
        try:
            px, py = float(p["pixel_x"]), float(p["pixel_y"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": f"feature {i} is missing pixel_x/pixel_y"}), 400
        out.append({
            "id": i,
            "pixel_x": round(px, 1), "pixel_y": round(py, 1),
            "x_m": round((px - ox) / px_per_m, 3),
            "depth_m": round((py - oy) / px_per_m, 3),
            "diam_px": round(float(p.get("diam_px") or 0), 1),
            "circularity": round(float(p.get("circularity") if p.get("circularity") is not None else 1.0), 3),
            "manual": bool(p.get("manual", False)),
        })

    out_dir = job_dir(job_id) / "03_extraction"
    out_dir.mkdir(parents=True, exist_ok=True)
    markers_path = out_dir / "markers_confirmed.json"
    markers_path.write_text(json.dumps(out, indent=2))
    meta["markers_path"] = str(markers_path)
    save_meta(job_id, meta)
    return jsonify({"markers": out, "n_confirmed": len(out)})


@bp.route("/api/jobs/<job_id>/markers/assign", methods=["POST"])
def markers_assign(job_id):
    """Async (calls Gemini): classify the confirmed markers into
    top-of-locus/final-base/noise and read the sheet's labels. Does NOT
    assemble geometry or install an extraction yet — the result is a
    proposal for the user to review/correct; call /markers/finalize with
    the (possibly edited) result to actually build the extraction."""
    meta = load_meta(job_id)
    if "markers_path" not in meta:
        abort(400, description="run marker detection (and ideally confirm "
                               "features) first")
    body = request.get_json(force=True, silent=True) or {}
    api_key = body.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "no Gemini API key provided (and "
                                  "GEMINI_API_KEY not set in the server "
                                  "environment)"}), 400

    markers = json.loads(Path(meta["markers_path"]).read_text())
    rotated = job_dir(job_id) / "03_extraction" / "marker_source_rotated.png"
    if not rotated.exists():
        abort(400, description="rotated working image missing — re-run "
                               "marker detection")

    try:
        from pipeline import assign_markers as p_assign_markers
        task_id = start_task(
            p_assign_markers.classify_markers,
            str(rotated), markers, meta.get("marker_square_cm", 20.0), api_key,
            max_output_tokens=int(body.get("max_output_tokens", 65536)),
        )
    except ImportError as e:
        return jsonify({"error": f"missing dependency: {e}. Install with "
                                  f"`pip install google-genai pillow pydantic "
                                  f"--break-system-packages`."}), 400

    return jsonify({"task_id": task_id})


@bp.route("/api/jobs/<job_id>/markers/finalize", methods=["POST"])
def markers_finalize(job_id):
    """Synchronous, no network call: assemble the (possibly user-edited)
    classification result + the immutable CV marker coordinates into the
    extraction JSON, and install it as this job's extraction."""
    meta = load_meta(job_id)
    if "markers_path" not in meta:
        abort(400, description="run marker detection first")
    body = request.get_json(force=True, silent=True) or {}
    result_dict = body.get("result")
    if not result_dict or not result_dict.get("assignments"):
        return jsonify({"error": "no classification to finalize — run "
                                  "/markers/assign first"}), 400

    markers = json.loads(Path(meta["markers_path"]).read_text())
    out_path = job_dir(job_id) / "03_extraction" / "field_wall_cv.json"
    try:
        from pipeline import assign_markers as p_assign_markers
        raw_json, warning = p_assign_markers.finalize_assignments(
            markers, result_dict, str(out_path))
    except Exception as e:
        return jsonify({"error": _friendly_error(e)}), 400

    meta["extraction_path"] = str(out_path)
    meta["sheet_type"] = "fieldwall"
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)
    return jsonify({"raw_json": raw_json, "warning": warning})
