"""Routes for preprocess."""

from flask import Blueprint, abort, jsonify, request
from pipeline import preprocess as p_preprocess

from ..jobs import job_dir, load_meta, rel_url, save_meta


bp = Blueprint("preprocess", __name__)


@bp.route("/api/jobs/<job_id>/preprocess", methods=["POST"])
def run_preprocess(job_id):
    meta = load_meta(job_id)
    if "scan_path" not in meta:
        abort(400, description="upload a scan first")

    body = request.get_json(force=True, silent=True) or {}
    outdir = job_dir(job_id) / "02_preprocess"

    try:
        result = p_preprocess.run_preprocess(
            meta["scan_path"], str(outdir),
            upscale=float(body.get("upscale", 2.0)),
            deskew_flag=bool(body.get("deskew", False)),
            highcontrast=bool(body.get("highcontrast", False)),
            pdf_dpi=int(body.get("pdf_dpi", 300)),
            pdf_page=int(body.get("pdf_page", 1)),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    outputs = {k: rel_url(job_id, v) for k, v in result["outputs"].items()}
    meta["clean_image_path"] = result["outputs"]["clean"]
    save_meta(job_id, meta)

    return jsonify({"deskew_angle": result["deskew_angle"], "outputs": outputs})
