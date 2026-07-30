"""Job directories, metadata, and safe file paths.

WARNING (Phase 2 of MODULARIZATION_PLAN.md): this module currently reads the
jobs directory from two different places.

  * ``job_dir`` and everything built on it use ``config.JOBS_DIR``, bound at
    import time by the ``from .config import JOBS_DIR`` below.
  * ``job_record`` / ``job_list`` use ``editor_pipeline.JOBS_DIR``, which
    ``pipeline/editor.py`` derives independently from ``__file__``.

The two agree in production and disagree under test, where fixtures patch one
or the other. This split arrived with the Phase 1 move and is preserved
verbatim rather than silently "fixed" — unifying it changes behaviour and
belongs in its own commit. Likewise ``load_meta``/``save_meta`` (keyed by
job_id, tolerant of a missing file) and ``read_meta``/``write_meta`` (keyed by
directory, stamps ``updated_at``, raises on a missing file) are two different
contracts that Phase 2 reconciles.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import abort

from pipeline import editor as editor_pipeline

from .config import JOBS_DIR
from .tasks import TASKS

STATUS_MESSAGES = {
    "editing": "Continue editing the drawing.",
    "finalizing": "Preparing the drawing for model processing.",
    "normalizing": "Normalizing the drawing data.",
    "validating": "Validating the normalized drawing data.",
    "converting": "Converting the drawing to model coordinates.",
    "building": "Building the 3D model.",
    "complete": "The 3D model is ready.",
    "error": "Model processing could not be completed.",
}


def job_dir(job_id):
    d = JOBS_DIR / job_id
    if not d.exists():
        abort(404, description="unknown job id")
    return d


def meta_path(job_id):
    return job_dir(job_id) / "meta.json"


def load_meta(job_id):
    mp = meta_path(job_id)
    if not mp.exists():
        return {}
    return json.loads(mp.read_text())


def save_meta(job_id, meta):
    meta_path(job_id).write_text(json.dumps(meta, indent=2))


def rel_url(job_id, abs_path):
    """Build the /api/jobs/<id>/file?path=... URL for a path inside the job dir."""
    rel = os.path.relpath(str(abs_path), str(job_dir(job_id)))
    return f"/api/jobs/{job_id}/file?path={rel}"


def safe_job_path(job_id, rel_path):
    """Resolve rel_path under the job dir, refusing to escape it."""
    base = job_dir(job_id).resolve()
    target = (base / rel_path).resolve()
    if base not in target.parents and target != base:
        abort(400, description="invalid path")
    return target


# ---------------------------------------------------------------------------
# Job metadata and record assembly, moved verbatim out of app.py in Phase 1.
# These are keyed by directory rather than job_id; see the module docstring.
# ---------------------------------------------------------------------------


def write_meta(job_directory, meta):
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    (job_directory / "meta.json").write_text(json.dumps(meta, indent=2))


def read_meta(job_directory):
    return json.loads((job_directory / "meta.json").read_text())


def job_status(job_directory, meta):
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


def refresh_job_status(job_directory, meta):
    status = job_status(job_directory, meta)
    if status != meta.get("status"):
        meta["status"] = status
        write_meta(job_directory, meta)
    return status


def load_finalized_output(job_directory):
    output_path = job_directory / "extraction_output.json"
    if not output_path.exists():
        return None
    return json.loads(output_path.read_text())


def finalization_payload(job_id, job_directory, meta, output=None):
    status = refresh_job_status(job_directory, meta)
    payload = {
        "job_id": job_id,
        "status": status,
        "results_url": f"/jobs/{job_id}",
        "visualizer_url": f"/visualizer?job={job_id}",
        "output": (
            load_finalized_output(job_directory)
            if output is None
            else output
        ),
    }
    task_id = meta.get("task_id") or meta.get("gempy_task_id")
    if task_id is not None:
        payload["task_id"] = task_id
    return payload


def finalization_status_code(status):
    if status == "error":
        return 500
    if status == "complete":
        return 200
    return 202


def job_file_url(job_id, job_directory, path):
    if path is None:
        return None
    relative_path = Path(path).relative_to(job_directory).as_posix()
    return f"/api/jobs/{job_id}/file?path={relative_path}"


def durable_status_payload(job_id, meta):
    status = meta.get("status", "extracted")
    stage = meta.get("stage") or status
    message = (
        meta.get("message")
        or meta.get("pipeline_error")
        or STATUS_MESSAGES.get(status, "Model processing is in progress.")
    )
    return {
        "job_id": job_id,
        "status": status,
        "stage": stage,
        "message": message,
        "results_url": f"/jobs/{job_id}",
    }


def job_record(job_directory):
    meta_file = job_directory / "meta.json"
    if not meta_file.exists():
        return None
    meta = json.loads(meta_file.read_text())
    job_id = meta.get("job_id", job_directory.name)
    source = meta.get("source", "extraction")
    status = job_status(job_directory, meta)
    model_paths = sorted(
        (job_directory / "06_gempy_model").glob("*.gempy")
    )
    section_paths = sorted(
        path
        for path in (job_directory / "06_gempy_model").glob("*section*.png")
        if "zoom" not in path.name
    )
    mesh_paths = sorted(
        (job_directory / "06_gempy_model").glob("*_meshes/*.obj")
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
        "model_url": job_file_url(
            job_id,
            job_directory,
            model_paths[0] if model_paths else None,
        ),
        "section_url": job_file_url(
            job_id,
            job_directory,
            section_paths[0] if section_paths else None,
        ),
        "mesh_urls": [
            {
                "name": path.stem.replace("_", " "),
                "url": job_file_url(job_id, job_directory, path),
            }
            for path in mesh_paths
        ],
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


def job_list():
    jobs = []
    for job_directory in editor_pipeline.JOBS_DIR.iterdir():
        if job_directory.is_dir():
            job = job_record(job_directory)
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
