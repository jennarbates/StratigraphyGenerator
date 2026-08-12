"""Job directories, metadata, and safe file paths.

All paths resolve through ``storage.JOBS_DIR``, read at call time so a single
assignment redirects every consumer.

There is one implementation of reading and one of writing job metadata.
``read_meta``/``write_meta`` take either a job_id or an already-resolved
directory; ``load_meta``/``save_meta`` are the job_id-shaped aliases the route
modules use. Passing a job_id resolves it through ``job_dir``, which aborts 404
for an unknown job; passing a Path does not, so callers holding a directory
they already validated (or one that may legitimately not exist yet) keep plain
``FileNotFoundError`` semantics.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from flask import abort

import storage

from .tasks import TASKS

_REQUIRED = object()

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
    """The directory for one job, refusing any id that is not a child of it.

    The containment check is the point, not the existence check. ``job_id``
    arrives straight off the URL, and a Flask string converter rejects a slash
    but not a dot: ``/api/jobs/../file?path=storage.py`` resolved
    ``JOBS_DIR / ".."`` to ``poggio_webapp/`` and handed that to
    ``safe_job_path``, whose own containment test then compared against the
    already-escaped base and passed. Every file under the application root,
    and every other job's files, were readable through one route.

    This is the same escape ``naming.safe_filename`` documents closing for
    ``/api/trenches/<label>/file``; the fix was applied to one route and never
    generalised. Resolving first and requiring the parent to be the jobs root
    closes it for any id, including one that is nothing but dots.
    """
    d = storage.JOBS_DIR / job_id
    if d.resolve().parent != storage.JOBS_DIR.resolve() or not d.exists():
        abort(404, description="unknown job id")
    return d


def meta_path(job):
    """The meta.json path for a job_id or an already-resolved directory.

    A job_id goes through ``job_dir``, so an unknown job aborts 404 before any
    filesystem read. A Path is trusted as-is.
    """
    if isinstance(job, Path):
        return job / "meta.json"
    return job_dir(job) / "meta.json"


def read_meta(job, default=_REQUIRED):
    """A job's metadata.

    With no default, a missing file raises FileNotFoundError and a corrupt one
    raises JSONDecodeError — callers acting on one known job want to know.

    With a default, both cases return it. A meta.json that cannot be parsed is
    no more usable than one that is not there, and the callers that scan every
    job directory must not let one damaged job break the whole listing.
    """
    path = meta_path(job)
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        if default is _REQUIRED:
            raise
        return default
    except (OSError, UnicodeError, json.JSONDecodeError):
        if default is _REQUIRED:
            raise
        return default


def write_meta(job, meta, *, stamp=True):
    """Persist a job's metadata, stamping ``updated_at`` by default.

    ``job_list`` sorts on ``updated_at``, so every write stamps it — including
    the extraction-flow writes that previously did not, and whose jobs
    therefore always sorted on ``created_at``.
    """
    if stamp:
        meta["updated_at"] = datetime.now(UTC).isoformat()
    meta_path(job).write_text(json.dumps(meta, indent=2))


def load_meta(job_id):
    """Tolerant read used by the route modules: {} for a job with no meta."""
    return read_meta(job_id, {})


def save_meta(job_id, meta):
    return write_meta(job_id, meta)


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
# Job record assembly, moved out of app.py in Phase 1.
# ---------------------------------------------------------------------------


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
    meta = read_meta(job_directory, None)
    if meta is None:
        return None
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
        # Carried through verbatim so the interface can label demonstration
        # data as such. The seeder distinguishes synthetic records from real
        # ones in this block, and that distinction is exactly the thing that
        # must not be lost between disk and screen.
        "demo": meta.get("demo") if isinstance(meta.get("demo"), dict) else None,
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
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.timestamp()
    except (OverflowError, ValueError):
        return float("-inf")


def job_list():
    jobs = []
    for job_directory in storage.JOBS_DIR.iterdir():
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
