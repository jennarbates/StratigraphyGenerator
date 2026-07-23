"""Routes for task status."""

import time

from flask import Blueprint, abort, jsonify

from ..tasks import TASKS


bp = Blueprint("task_status", __name__)


@bp.route("/api/tasks/<task_id>")
def task_status(task_id):
    t = TASKS.get(task_id)
    if not t:
        abort(404)
    resp = {"status": t["status"], "log": t["log"],
            "elapsed_seconds": round(time.time() - t["started_at"])}
    if t["status"] == "done":
        r = t["result"]
        # extraction returns str or (str, warning); gempy returns a dict
        if isinstance(r, tuple):
            resp["raw_json"] = r[0]
            resp["warning"] = r[1]
        elif isinstance(r, str):
            resp["raw_json"] = r
        else:
            resp["result"] = r
    elif t["status"] == "error":
        resp["error"] = t["error"]
        resp["error_detail"] = t.get("error_detail")
    return jsonify(resp)
