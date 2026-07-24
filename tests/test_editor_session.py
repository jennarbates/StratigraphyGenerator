import json
import re
from datetime import datetime

import pytest

from poggio_webapp.pipeline import editor


@pytest.fixture(autouse=True)
def isolate_jobs_dir(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(editor, "JOBS_DIR", jobs_dir)


def test_create_editor_session_writes_metadata():
    job_id = editor.create_editor_session("FieldWallProfile")

    assert job_id
    assert re.fullmatch(r"[0-9a-f]{12}", job_id)

    meta_path = editor.JOBS_DIR / job_id / "editor_meta.json"
    assert meta_path.exists()

    metadata = json.loads(meta_path.read_text())
    assert metadata["schema_type"] == "FieldWallProfile"
    assert datetime.fromisoformat(metadata["created_at"])


def test_create_editor_session_rejects_unknown_schema_type():
    with pytest.raises(ValueError):
        editor.create_editor_session("bogus")


def test_save_then_load_editor_state_round_trips_nested_dict():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = {
        "features": [
            {"id": 1, "coordinates": [12.5, 8.25]},
            {"id": 2, "coordinates": [3.0, 4.0]},
        ],
        "settings": {"snap": True},
    }

    editor.save_editor_state(job_id, state)

    assert editor.load_editor_state(job_id) == state


def test_load_editor_state_without_saved_state_returns_empty_dict():
    job_id = editor.create_editor_session("FieldWallProfile")

    assert editor.load_editor_state(job_id) == {}


def test_save_editor_state_for_nonexistent_job_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        editor.save_editor_state("missing-job", {"a": 1})


def test_load_editor_state_for_nonexistent_job_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        editor.load_editor_state("missing-job")


def test_save_editor_state_overwrites_instead_of_merging():
    job_id = editor.create_editor_session("FieldWallProfile")
    editor.save_editor_state(job_id, {"a": 1})

    editor.save_editor_state(job_id, {"b": 2})

    assert editor.load_editor_state(job_id) == {"b": 2}
