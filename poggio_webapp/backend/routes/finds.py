"""Routes for finds logged against a job."""

from flask import Blueprint, jsonify, render_template, request

from pipeline import editor as editor_pipeline

from ..jobs import job_list

bp = Blueprint("finds", __name__)


@bp.route("/finds")
def finds_page():
    return render_template("finds.html", jobs=job_list())


@bp.route("/finds/<job_id>/new", methods=["POST"])
def create_find(job_id):
    body = request.get_json(force=True, silent=True) or {}
    try:
        stored_find = editor_pipeline.add_find(job_id, body)
        editor_pipeline.sync_finds_to_output(job_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify(stored_find)


@bp.route("/finds/<job_id>", methods=["GET"])
def list_finds(job_id):
    try:
        finds = editor_pipeline.get_finds(job_id)
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify(finds)


@bp.route("/finds/<job_id>/<find_id>", methods=["DELETE"])
def remove_find(job_id, find_id):
    try:
        editor_pipeline.delete_find(job_id, find_id)
        editor_pipeline.sync_finds_to_output(job_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 404
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify({"ok": True})
