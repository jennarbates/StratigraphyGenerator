"""Creating, saving and loading an editor session on disk."""

import json
import uuid
from datetime import datetime, timezone

import storage
from naming import clean_label

from .schema import ALLOWED_SCHEMA_TYPES, SHEET_TYPES_BY_SCHEMA


def create_editor_session(
    schema_type: str,
    *,
    trench_label=None,
    wall_label=None,
) -> str:
    """
    Create an editor job directory and store its session metadata.

    trench_label and wall_label are optional; when non-empty after stripping
    they are recorded in the draft meta so the job can be grouped by trench.

    Raises ValueError when schema_type is not supported.
    """
    if schema_type not in ALLOWED_SCHEMA_TYPES:
        raise ValueError(f"Unsupported schema_type: {schema_type}")

    job_id = uuid.uuid4().hex[:12]
    session_dir = storage.JOBS_DIR / job_id
    session_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "schema_type": schema_type,
        "created_at": created_at,
    }
    (session_dir / "editor_meta.json").write_text(
        json.dumps(metadata, indent=2)
    )
    draft_metadata = {
        "job_id": job_id,
        "schema_type": schema_type,
        "sheet_type": SHEET_TYPES_BY_SCHEMA[schema_type],
        "source": "manual_editor",
        "status": "editing",
        "created_at": created_at,
        "updated_at": created_at,
    }
    if clean_label(trench_label):
        draft_metadata["trench_label"] = clean_label(trench_label)
    if clean_label(wall_label):
        draft_metadata["wall_label"] = clean_label(wall_label)
    (session_dir / "meta.json").write_text(
        json.dumps(draft_metadata, indent=2)
    )
    return job_id


def save_editor_state(job_id: str, state: dict) -> None:
    """Overwrite the saved opaque editor state for an existing job."""
    session_dir = storage.JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    (session_dir / "editor_state.json").write_text(
        json.dumps(state, indent=2)
    )


def load_editor_state(job_id: str) -> dict:
    """Load saved opaque editor state, or return an empty state if unsaved."""
    session_dir = storage.JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    state_path = session_dir / "editor_state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text())
