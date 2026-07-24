"""Filesystem storage for editor sessions."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"
ALLOWED_SCHEMA_TYPES = {"ArchaeologicalDiagram", "FieldWallProfile"}


def create_editor_session(schema_type: str) -> str:
    """
    Create an editor job directory and store its session metadata.

    Raises ValueError when schema_type is not supported.
    """
    if schema_type not in ALLOWED_SCHEMA_TYPES:
        raise ValueError(f"Unsupported schema_type: {schema_type}")

    job_id = uuid.uuid4().hex[:12]
    session_dir = JOBS_DIR / job_id
    session_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_type": schema_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (session_dir / "editor_meta.json").write_text(
        json.dumps(metadata, indent=2)
    )
    return job_id


def save_editor_state(job_id: str, state: dict) -> None:
    """Overwrite the saved opaque editor state for an existing job."""
    session_dir = JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    (session_dir / "editor_state.json").write_text(
        json.dumps(state, indent=2)
    )


def load_editor_state(job_id: str) -> dict:
    """Load saved opaque editor state, or return an empty state if unsaved."""
    session_dir = JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    state_path = session_dir / "editor_state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text())
