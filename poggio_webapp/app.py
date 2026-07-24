"""Trench Digitization Pipeline backend entry point."""

import os

from backend import create_app
from flask import abort, jsonify, request
from pipeline.editor import (
    create_editor_session,
    finalize_editor_session,
    load_editor_state,
    save_editor_state,
)
from pydantic import ValidationError

app = create_app()


@app.route("/editor/new", methods=["POST"])
def create_editor():
    body = request.get_json(force=True, silent=True) or {}
    try:
        job_id = create_editor_session(body.get("schema_type"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"job_id": job_id})


@app.route("/editor/<job_id>/save", methods=["POST"])
def save_editor(job_id):
    state = request.get_json(force=True, silent=True) or {}
    try:
        save_editor_state(job_id, state)
    except FileNotFoundError as error:
        abort(404, description=str(error))
    return jsonify({"ok": True})


@app.route("/editor/<job_id>/state", methods=["GET"])
def get_editor_state(job_id):
    try:
        state = load_editor_state(job_id)
    except FileNotFoundError as error:
        abort(404, description=str(error))
    return jsonify(state)


@app.route("/editor/<job_id>/finalize", methods=["POST"])
def finalize_editor(job_id):
    try:
        finalized = finalize_editor_session(job_id)
    except ValidationError as error:
        return jsonify({"error": str(error)}), 400
    except FileNotFoundError as error:
        abort(404, description=str(error))
    return jsonify(finalized.model_dump(mode="json"))


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=debug,
        port=int(os.environ.get("PORT", 5000)),
    )
