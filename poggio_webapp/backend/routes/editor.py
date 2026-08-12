"""Routes for the manual drawing editor and its model-build lifecycle."""

import json

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    url_for,
)
from pydantic import ValidationError

import storage
from naming import canonical_trench, clean_label
from pipeline import editor as editor_pipeline
from pipeline.editor import (
    create_editor_session,
    finalize_editor_session,
    load_editor_state,
    save_editor_state,
)

from ..jobs import (
    STATUS_MESSAGES,
    durable_status_payload,
    finalization_payload,
    finalization_status_code,
    read_meta,
    refresh_job_status,
    write_meta,
)
from ..services.editor_pipeline import (
    EDITOR_PIPELINE_STATUSES,
    FINALIZATION_LOCK,
    run_editor_pipeline,
)

bp = Blueprint("editor", __name__)


@bp.route("/editor/new", methods=["POST"])
def create_editor():
    body = request.get_json(force=True, silent=True) or {}
    schema_type = body.get("schema_type")
    trench_label = canonical_trench(body.get("trench_label"))
    wall_label = clean_label(body.get("wall_label"))
    try:
        job_id = create_editor_session(
            schema_type,
            trench_label=trench_label,
            wall_label=wall_label,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    payload = {
        "job_id": job_id,
        "schema_type": schema_type,
        "status": "editing",
        "editor_url": url_for("editor.editor_page", job_id=job_id),
    }
    if trench_label:
        payload["trench_label"] = trench_label
    if wall_label:
        payload["wall_label"] = wall_label
    return jsonify(payload)


@bp.route("/editor/<job_id>", methods=["GET"])
def editor_page(job_id):
    session_directory = storage.JOBS_DIR / job_id
    if not session_directory.is_dir():
        abort(404, description="unknown editor session")

    try:
        editor_meta = json.loads((session_directory / "editor_meta.json").read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        abort(404, description="invalid editor session metadata")

    if not isinstance(editor_meta, dict):
        abort(404, description="invalid editor session metadata")
    schema_type = editor_meta.get("schema_type")
    if schema_type not in editor_pipeline.ALLOWED_SCHEMA_TYPES:
        abort(404, description="invalid editor session metadata")

    return render_template(
        "editor.html",
        job_id=job_id,
        schema_type=schema_type,
    )


@bp.route("/editor/<job_id>/save", methods=["POST"])
def save_editor(job_id):
    state = request.get_json(force=True, silent=True) or {}
    try:
        save_editor_state(job_id, state)
    except FileNotFoundError as error:
        abort(404, description=str(error))
    return jsonify({"ok": True})


@bp.route("/editor/<job_id>/state", methods=["GET"])
def get_editor_state(job_id):
    try:
        state = load_editor_state(job_id)
    except FileNotFoundError as error:
        abort(404, description=str(error))
    return jsonify(state)


@bp.route("/api/jobs/<job_id>/status", methods=["GET"])
def get_job_status(job_id):
    job_directory = storage.JOBS_DIR / job_id
    try:
        meta = read_meta(job_directory)
    except FileNotFoundError:
        abort(404, description="unknown job id")
    return jsonify(durable_status_payload(job_id, meta))


@bp.route("/editor/<job_id>/finalize", methods=["POST"])
def finalize_editor(job_id):
    job_directory = storage.JOBS_DIR / job_id
    with FINALIZATION_LOCK:
        try:
            meta = read_meta(job_directory)
        except FileNotFoundError:
            abort(404, description="unknown editor session")
        status = refresh_job_status(job_directory, meta)
        if status in EDITOR_PIPELINE_STATUSES:
            payload = finalization_payload(job_id, job_directory, meta)
            if status == "error":
                payload["error"] = "Model processing could not be completed."
            return jsonify(payload), finalization_status_code(status)

        try:
            finalized = finalize_editor_session(job_id)
        except editor_pipeline.EditorStructuralValidationError as error:
            return jsonify({"error": str(error)}), 400
        except ValidationError:
            return jsonify(
                {
                    "error": "The saved editor data is not valid.",
                }
            ), 400
        except FileNotFoundError:
            abort(404, description="unknown editor session")

        output = finalized.model_dump(mode="json")
        meta.update(
            {
                "status": "finalizing",
                "stage": "finalizing",
                "message": STATUS_MESSAGES["finalizing"],
            }
        )
        meta.pop("pipeline_error", None)
        write_meta(job_directory, meta)

    try:
        task_id = run_editor_pipeline(job_id)
    except Exception:
        meta = read_meta(job_directory)
        meta.update(
            {
                "status": "error",
                "stage": meta.get("stage", "finalizing"),
                "message": "Model processing could not be started.",
                "pipeline_error": "Pipeline startup failed.",
            }
        )
        write_meta(job_directory, meta)
        current_app.logger.exception("Editor pipeline failed for job %s", job_id)
        payload = finalization_payload(
            job_id,
            job_directory,
            meta,
            output,
        )
        payload["error"] = "Model processing could not be started."
        return jsonify(payload), 500

    meta = read_meta(job_directory)
    if task_id is not None:
        meta.update(
            {
                "task_id": task_id,
                "gempy_task_id": task_id,
            }
        )
        if meta.get("status") not in {"complete", "error"}:
            meta.update(
                {
                    "status": "building",
                    "stage": "building",
                    "message": STATUS_MESSAGES["building"],
                }
            )
        write_meta(job_directory, meta)
    payload = finalization_payload(job_id, job_directory, meta, output)
    return jsonify(payload), finalization_status_code(payload["status"])
