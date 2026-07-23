"""Routes for jobs."""

import uuid

from flask import (
    Blueprint,
    abort,
    jsonify,
    request,
    send_file,
)

from ..config import JOBS_DIR
from ..jobs import safe_job_path, save_meta


bp = Blueprint("jobs", __name__)


@bp.route("/api/jobs", methods=["POST"])
def create_job():
    job_id = uuid.uuid4().hex[:12]
    d = JOBS_DIR / job_id
    for sub in ["01_scan", "02_preprocess", "03_extraction",
                "04_normalize_validate", "05_convert_coords", "06_gempy_model"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    save_meta(job_id, {"job_id": job_id, "sheet_type": None})
    return jsonify({"job_id": job_id})


@bp.route("/api/jobs/<job_id>/file")
def get_file(job_id):
    rel = request.args.get("path")
    if not rel:
        abort(400, description="missing path")
    path = safe_job_path(job_id, rel)
    if not path.exists():
        abort(404)
    return send_file(path)
