"""Finds logged against an editor session."""

import json
import uuid

import storage

from .schema import REQUIRED_FIND_FIELDS


def add_find(job_id: str, find: dict) -> dict:
    """
    Append an artifact find to an existing job and return the stored find.

    A find may be logged independently of any saved or finalized editor state.
    """
    missing_fields = [
        field for field in REQUIRED_FIND_FIELDS if field not in find
    ]
    if missing_fields:
        raise ValueError(
            f'Missing required find field(s): {", ".join(missing_fields)}'
        )

    session_dir = storage.JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    finds_path = session_dir / "finds.json"
    if not finds_path.exists():
        finds_path.write_text(json.dumps([], indent=2))

    finds = json.loads(finds_path.read_text())
    stored_find = dict(find)
    if "find_id" not in stored_find:
        stored_find["find_id"] = uuid.uuid4().hex[:12]
    finds.append(stored_find)
    finds_path.write_text(json.dumps(finds, indent=2))
    return stored_find


def get_finds(job_id: str) -> list[dict]:
    """Return artifact finds for an existing job, or an empty list if unsaved."""
    session_dir = storage.JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    finds_path = session_dir / "finds.json"
    if not finds_path.exists():
        return []
    return json.loads(finds_path.read_text())


def delete_find(job_id: str, find_id: str) -> None:
    """Delete the artifact find matching find_id from an existing job."""
    finds = get_finds(job_id)
    retained_finds = [
        find for find in finds if find.get("find_id") != find_id
    ]
    if len(retained_finds) == len(finds):
        raise ValueError(f"Find does not exist: {find_id}")

    (storage.JOBS_DIR / job_id / "finds.json").write_text(
        json.dumps(retained_finds, indent=2)
    )


def sync_finds_to_output(job_id: str) -> None:
    """Copy the current artifact finds into an existing finalized output."""
    output_path = storage.JOBS_DIR / job_id / "extraction_output.json"
    if not output_path.exists():
        return

    output = json.loads(output_path.read_text())
    output["finds"] = get_finds(job_id)
    output_path.write_text(json.dumps(output, indent=2))
