"""Trench Digitization Pipeline backend entry point."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from backend import create_app
from backend.tasks import TASKS, start_task
from flask import abort, jsonify, redirect, render_template, request, url_for
from pipeline import convert_coords, editor as editor_pipeline, normalizer, validator
from pipeline.editor import (
    create_editor_session,
    finalize_editor_session,
    load_editor_state,
    save_editor_state,
)
from pydantic import ValidationError

app = create_app()

EDITOR_PIPELINE_STATUSES = {
    "finalizing",
    "normalizing",
    "validating",
    "converting",
    "building",
    "complete",
    "error",
}
PIPELINE_SUBDIRECTORIES = (
    "01_scan",
    "02_preprocess",
    "03_extraction",
    "04_normalize_validate",
    "05_convert_coords",
    "06_gempy_model",
)
_EDITOR_FINALIZATION_LOCK = threading.Lock()
_EDITOR_META_LOCK = threading.Lock()


def _save_meta(job_directory, meta):
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    (job_directory / "meta.json").write_text(json.dumps(meta, indent=2))


def _load_meta(job_directory):
    return json.loads((job_directory / "meta.json").read_text())


def _run_editor_build(job_directory, build_fn, *args, log_cb=None):
    try:
        result = build_fn(*args, log_cb=log_cb)
    except Exception:
        with _EDITOR_META_LOCK:
            meta = _load_meta(job_directory)
            meta.update({
                "status": "error",
                "pipeline_error": "Model building failed.",
            })
            _save_meta(job_directory, meta)
        raise

    with _EDITOR_META_LOCK:
        meta = _load_meta(job_directory)
        meta["status"] = "complete"
        meta.pop("pipeline_error", None)
        _save_meta(job_directory, meta)
    return result


def _run_editor_pipeline(job_id):
    job_directory = editor_pipeline.JOBS_DIR / job_id
    for subdirectory in PIPELINE_SUBDIRECTORIES:
        (job_directory / subdirectory).mkdir(exist_ok=True)

    editor_meta = json.loads(
        (job_directory / "editor_meta.json").read_text()
    )
    editor_state = load_editor_state(job_id)
    extraction_path = job_directory / "extraction_output.json"
    meta = _load_meta(job_directory)
    meta.update({
        "job_id": job_id,
        "sheet_type": (
            "fieldwall"
            if editor_meta["schema_type"] == "FieldWallProfile"
            else "illustrator"
        ),
        "source": "manual_editor",
        "extraction_path": str(extraction_path),
        "status": "normalizing",
    })
    _save_meta(job_directory, meta)

    normalized_path = (
        job_directory / "04_normalize_validate" / "output_clean.json"
    )
    normalized, normalization_log = normalizer.run_normalize(
        str(extraction_path),
        str(normalized_path),
    )
    meta.update({
        "normalized_path": str(normalized_path),
        "normalization_log": normalization_log,
        "status": "validating",
    })
    _save_meta(job_directory, meta)

    validation_report = validator.run_validate(str(normalized_path))
    meta.update({
        "validation_report": validation_report,
        "status": "converting",
    })
    _save_meta(job_directory, meta)

    grid_config = editor_state.get("gridConfig")
    if not grid_config:
        grid_config = convert_coords.make_starter_config(normalized)
    points_path = job_directory / "05_convert_coords" / "points.csv"
    conversion = convert_coords.run_convert(
        normalized,
        grid_config,
        str(points_path),
    )
    if conversion["n_points"] == 0:
        raise ValueError("conversion produced 0 points")

    meta.update({
        "points_csv": conversion["points_csv"],
        "orientations_csv": conversion["orientations_csv"],
        "status": "building",
    })
    _save_meta(job_directory, meta)

    from pipeline import build_gempy

    output_prefix = str(
        job_directory / "06_gempy_model" / "trench_model"
    )
    with _EDITOR_META_LOCK:
        task_id = start_task(
            _run_editor_build,
            job_directory,
            build_gempy.run_build,
            meta["points_csv"],
            meta["orientations_csv"],
            output_prefix,
        )
        meta = _load_meta(job_directory)
        meta.update({
            "task_id": task_id,
            "gempy_task_id": task_id,
        })
        _save_meta(job_directory, meta)
    return task_id


def _job_status(job_directory, meta):
    if meta.get("status") in {"editing", "complete", "error"}:
        return meta["status"]
    task = TASKS.get(meta.get("task_id") or meta.get("gempy_task_id"))
    if task:
        return {
            "done": "complete",
            "error": "error",
            "running": "building",
        }.get(task["status"], task["status"])
    if list((job_directory / "06_gempy_model").glob("*.gempy")):
        return "complete"
    return meta.get("status", "extracted")


def _refresh_job_status(job_directory, meta):
    status = _job_status(job_directory, meta)
    if status != meta.get("status"):
        meta["status"] = status
        _save_meta(job_directory, meta)
    return status


def _load_finalized_output(job_directory):
    output_path = job_directory / "extraction_output.json"
    if not output_path.exists():
        return None
    return json.loads(output_path.read_text())


def _finalization_payload(job_id, job_directory, meta, output=None):
    status = _refresh_job_status(job_directory, meta)
    payload = {
        "job_id": job_id,
        "status": status,
        "results_url": f"/jobs/{job_id}",
        "visualizer_url": f"/visualizer?job={job_id}",
        "output": (
            _load_finalized_output(job_directory)
            if output is None
            else output
        ),
    }
    task_id = meta.get("task_id") or meta.get("gempy_task_id")
    if task_id is not None:
        payload["task_id"] = task_id
    return payload


def _finalization_status_code(status):
    if status == "error":
        return 500
    if status == "complete":
        return 200
    return 202


def _job_file_url(job_id, job_directory, path):
    if path is None:
        return None
    relative_path = Path(path).relative_to(job_directory).as_posix()
    return f"/api/jobs/{job_id}/file?path={relative_path}"


def _job_record(job_directory):
    meta_path = job_directory / "meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    job_id = meta.get("job_id", job_directory.name)
    source = meta.get("source", "extraction")
    status = _job_status(job_directory, meta)
    model_paths = sorted(
        (job_directory / "06_gempy_model").glob("*.gempy")
    )
    section_paths = sorted(
        path
        for path in (job_directory / "06_gempy_model").glob("*section*.png")
        if "zoom" not in path.name
    )
    return {
        "job_id": job_id,
        "source": source,
        "source_label": (
            "Created from scratch"
            if source == "manual_editor"
            else "Extraction"
        ),
        "status": status,
        "results_url": (
            f"/editor/{job_id}"
            if status == "editing"
            else f"/jobs/{job_id}"
        ),
        "created_at": meta.get("created_at"),
        "updated_at": meta.get("updated_at"),
        "visualizer_url": f"/visualizer?job={job_id}",
        "model_url": _job_file_url(
            job_id,
            job_directory,
            model_paths[0] if model_paths else None,
        ),
        "section_url": _job_file_url(
            job_id,
            job_directory,
            section_paths[0] if section_paths else None,
        ),
    }


def _timestamp_sort_value(value):
    if not isinstance(value, str):
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (OverflowError, ValueError):
        return float("-inf")


def _job_list():
    jobs = []
    for job_directory in editor_pipeline.JOBS_DIR.iterdir():
        if job_directory.is_dir():
            job = _job_record(job_directory)
            if job:
                jobs.append(job)
    return sorted(
        jobs,
        key=lambda job: (
            _timestamp_sort_value(
                job.get("updated_at") or job.get("created_at")
            ),
            _timestamp_sort_value(job.get("created_at")),
            job["job_id"],
        ),
        reverse=True,
    )


def render_index():
    return render_template("index.html", jobs=_job_list(), result_job=None)


app.view_functions["pages.index"] = render_index


@app.route("/jobs/<job_id>")
def job_results(job_id):
    job = _job_record(editor_pipeline.JOBS_DIR / job_id)
    if job is None:
        abort(404, description="unknown job id")
    if job["status"] == "editing":
        return redirect(url_for("editor_page", job_id=job_id))
    return render_template("index.html", jobs=_job_list(), result_job=job)


@app.route("/finds")
def finds_page():
    return render_template("finds.html", jobs=_job_list())


@app.route("/finds/<job_id>/new", methods=["POST"])
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


@app.route("/finds/<job_id>", methods=["GET"])
def list_finds(job_id):
    try:
        finds = editor_pipeline.get_finds(job_id)
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify(finds)


@app.route("/finds/<job_id>/<find_id>", methods=["DELETE"])
def remove_find(job_id, find_id):
    try:
        editor_pipeline.delete_find(job_id, find_id)
        editor_pipeline.sync_finds_to_output(job_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 404
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify({"ok": True})


@app.route("/editor/new", methods=["POST"])
def create_editor():
    body = request.get_json(force=True, silent=True) or {}
    schema_type = body.get("schema_type")
    try:
        job_id = create_editor_session(schema_type)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({
        "job_id": job_id,
        "schema_type": schema_type,
        "status": "editing",
        "editor_url": url_for("editor_page", job_id=job_id),
    })


@app.route("/editor/<job_id>", methods=["GET"])
def editor_page(job_id):
    session_directory = editor_pipeline.JOBS_DIR / job_id
    if not session_directory.is_dir():
        abort(404, description="unknown editor session")

    try:
        editor_meta = json.loads(
            (session_directory / "editor_meta.json").read_text()
        )
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
    job_directory = editor_pipeline.JOBS_DIR / job_id
    with _EDITOR_FINALIZATION_LOCK:
        try:
            meta = _load_meta(job_directory)
        except FileNotFoundError:
            abort(404, description="unknown editor session")
        status = _refresh_job_status(job_directory, meta)
        if status in EDITOR_PIPELINE_STATUSES:
            payload = _finalization_payload(job_id, job_directory, meta)
            if status == "error":
                payload["error"] = "Model processing could not be completed."
            return jsonify(payload), _finalization_status_code(status)

        try:
            finalized = finalize_editor_session(job_id)
        except editor_pipeline.EditorStructuralValidationError as error:
            return jsonify({"error": str(error)}), 400
        except ValidationError:
            return jsonify({
                "error": "The saved editor data is not valid.",
            }), 400
        except FileNotFoundError:
            abort(404, description="unknown editor session")

        output = finalized.model_dump(mode="json")
        meta["status"] = "finalizing"
        meta.pop("pipeline_error", None)
        _save_meta(job_directory, meta)

    try:
        task_id = _run_editor_pipeline(job_id)
    except Exception:
        meta = _load_meta(job_directory)
        meta.update({
            "status": "error",
            "pipeline_error": "Pipeline startup failed.",
        })
        _save_meta(job_directory, meta)
        app.logger.exception("Editor pipeline failed for job %s", job_id)
        payload = _finalization_payload(
            job_id,
            job_directory,
            meta,
            output,
        )
        payload["error"] = "Model processing could not be started."
        return jsonify(payload), 500

    meta = _load_meta(job_directory)
    if task_id is not None:
        meta.update({
            "task_id": task_id,
            "gempy_task_id": task_id,
        })
        if meta.get("status") not in {"complete", "error"}:
            meta["status"] = "building"
        _save_meta(job_directory, meta)
    payload = _finalization_payload(job_id, job_directory, meta, output)
    return jsonify(payload), _finalization_status_code(payload["status"])


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=debug,
        port=int(os.environ.get("PORT", 5000)),
    )
