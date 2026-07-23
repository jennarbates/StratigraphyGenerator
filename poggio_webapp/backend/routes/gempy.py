"""Routes for gempy."""

from flask import Blueprint, abort, jsonify, request

from ..jobs import job_dir, load_meta, rel_url
from ..tasks import TASKS, start_task


bp = Blueprint("gempy", __name__)


@bp.route("/api/jobs/<job_id>/gempy", methods=["POST"])
def run_gempy(job_id):
    meta = load_meta(job_id)
    if "points_csv" not in meta:
        abort(400, description="run coordinate conversion first")

    body = request.get_json(force=True, silent=True) or {}
    out_prefix = str(job_dir(job_id) / "06_gempy_model" / "trench_model")

    try:
        from pipeline import build_gempy as p_build_gempy
    except Exception as e:
        return jsonify({"error": f"gempy import failed: {e}. Install with "
                                  f"`pip install gempy gempy_viewer --break-system-packages`."}), 400

    kwargs = dict(
        project_name=body.get("project_name", "trench_model"),
        resolution=tuple(body.get("resolution", [50, 50, 30])),
        extent=body.get("extent"),
        padding_xy=float(body.get("padding_xy", 2.0)),
        padding_z=float(body.get("padding_z", 1.0)),
        series_order=body.get("series_order"),
        make_plot=bool(body.get("make_plot", True)),
        section_direction=body.get("section_direction", "y"),
        vertical_exaggeration=float(body.get("vertical_exaggeration", 5.0)),
        make_meshes=bool(body.get("make_meshes", True)),
        save_model=bool(body.get("save_model", True)),
        make_zoom_plot=bool(body.get("make_zoom_plot", True)),
        zoom_surfaces=body.get("zoom_surfaces"),
        zoom_vertical_exaggeration=body.get("zoom_vertical_exaggeration"),
    )

    task_id = start_task(
        p_build_gempy.run_build,
        meta["points_csv"], meta["orientations_csv"], out_prefix,
        **kwargs,
    )
    return jsonify({"task_id": task_id})


@bp.route("/api/jobs/<job_id>/gempy/result/<task_id>")
def gempy_result_urls(job_id, task_id):
    """Convert absolute output paths from a finished gempy task into file URLs."""
    t = TASKS.get(task_id)
    if not t or t["status"] != "done":
        abort(400, description="task not done")
    outputs = t["result"].get("outputs", {})
    urls = {}
    for k, v in outputs.items():
        if isinstance(v, list):
            urls[k] = [rel_url(job_id, p) for p in v]
        else:
            urls[k] = rel_url(job_id, v)
    return jsonify({
        "extent": t["result"].get("extent"),
        "series_order": t["result"].get("series_order"),
        "single_face_note": t["result"].get("single_face_note"),
        "outputs": urls,
    })
