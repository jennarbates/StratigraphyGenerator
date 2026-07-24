"""Routes for the 03 - Features (optional) stage.

Wires pipeline/detect_features.py (CV closed-contour proposals) to the
frontend's ftDetect/ftConfirm buttons in static/app/stages/features.js.
Both routes existed only on the frontend until now — this blueprint was
simply never created, so every "Detect feature candidates" click hit
Flask's default 404 handler.
"""

import json
from pathlib import Path

from flask import Blueprint, abort, jsonify, request

from ..jobs import job_dir, load_meta, rel_url, save_meta


bp = Blueprint("features", __name__)


@bp.route("/api/jobs/<job_id>/features/detect", methods=["POST"])
def features_detect(job_id):
    meta = load_meta(job_id)
    image_path = meta.get("clean_image_path") or meta.get("scan_path")
    if not image_path:
        abort(400, description="upload a scan first")
    if image_path.lower().endswith(".pdf"):
        return jsonify({"error": "feature detection works on image scans, "
                                  "not PDFs"}), 400
    if not Path(image_path).exists():
        abort(400, description="the job's scan is missing on disk")

    from pipeline import detect_features as p_detect_features
    out_dir = job_dir(job_id) / "03_extraction"
    try:
        result = p_detect_features.run_detect(image_path, str(out_dir))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    image_kind = "preprocessed" if meta.get("clean_image_path") else "raw scan"

    # Persisted so /features/confirm can build its review overlay against
    # the exact same image, and so the raw CV proposals survive a reload.
    candidates_path = out_dir / "feature_candidates.json"
    candidates_path.write_text(json.dumps(result["features"]))
    meta["features_image_path"] = image_path
    meta["features_image_kind"] = image_kind
    meta["feature_candidates_path"] = str(candidates_path)
    save_meta(job_id, meta)

    return jsonify({
        "features": result["features"],
        "candidate_count": result["candidate_count"],
        "image_url": rel_url(job_id, Path(image_path)),
        "image_kind": image_kind,
        "image_width": result["image_width"],
        "image_height": result["image_height"],
        "debug_image_url": rel_url(job_id, Path(result["debug_image"])),
    })


@bp.route("/api/jobs/<job_id>/features/confirm", methods=["POST"])
def features_confirm(job_id):
    """Install the user-reviewed feature inventory (CV candidates with some
    accepted/rejected, plus any manually drawn) as this job's confirmed
    features. An empty list is a valid, deliberate outcome — the features
    stage is optional and "reject everything, draw nothing" means no
    features, not an error."""
    meta = load_meta(job_id)
    image_path = meta.get("features_image_path")
    if not image_path:
        abort(400, description="run feature detection first")

    body = request.get_json(force=True, silent=True) or {}
    rows = body.get("features") or []

    out = []
    for i, f in enumerate(rows):
        try:
            x, y = float(f["x"]), float(f["y"])
            width, height = float(f["width"]), float(f["height"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": f"feature {i} is missing x/y/width/height"}), 400
        out.append({
            "id": i,
            "display_id": i + 1,
            "x": round(x, 1), "y": round(y, 1),
            "width": round(width, 1), "height": round(height, 1),
            "feature_type": f.get("feature_type") or "other feature",
            "description": f.get("description") or "",
            "points": f.get("points") or None,
            "manual": bool(f.get("manual", False)),
            "status": "approved",
        })

    out_dir = job_dir(job_id) / "03_extraction"
    out_dir.mkdir(parents=True, exist_ok=True)
    confirmed_path = out_dir / "features_confirmed.json"
    confirmed_path.write_text(json.dumps(out, indent=2))

    review_url = None
    if out:
        from pipeline import detect_features as p_detect_features
        review_path = out_dir / "features_reviewed.png"
        try:
            p_detect_features.write_review_overlay(image_path, out, str(review_path))
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        meta["features_review_image_path"] = str(review_path)
        review_url = rel_url(job_id, review_path)

    meta["features_path"] = str(confirmed_path)
    save_meta(job_id, meta)

    return jsonify({"n_confirmed": len(out), "review_image_url": review_url})