"""Job directories, metadata, and safe file paths."""

import json
import os

from flask import abort

from .config import JOBS_DIR


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
