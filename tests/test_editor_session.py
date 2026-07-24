import json
import re
from datetime import datetime, timedelta

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


def test_create_editor_session_writes_draft_meta():
    job_id = editor.create_editor_session("FieldWallProfile")
    job_dir = editor.JOBS_DIR / job_id
    meta_path = job_dir / "meta.json"

    assert meta_path.exists()
    metadata = json.loads(meta_path.read_text())
    assert set(metadata) == {
        "job_id",
        "schema_type",
        "sheet_type",
        "source",
        "status",
        "created_at",
        "updated_at",
    }
    assert metadata["job_id"] == job_id
    assert metadata["source"] == "manual_editor"
    assert metadata["status"] == "editing"
    assert not (job_dir / "extraction_output.json").exists()
    assert not (job_dir / "06_gempy_model").exists()


def test_create_editor_session_maps_archaeological_schema_to_illustrator():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")

    metadata = json.loads(
        (editor.JOBS_DIR / job_id / "meta.json").read_text()
    )
    assert metadata["schema_type"] == "ArchaeologicalDiagram"
    assert metadata["sheet_type"] == "illustrator"


def test_create_editor_session_maps_fieldwall_schema_to_fieldwall():
    job_id = editor.create_editor_session("FieldWallProfile")

    metadata = json.loads(
        (editor.JOBS_DIR / job_id / "meta.json").read_text()
    )
    assert metadata["schema_type"] == "FieldWallProfile"
    assert metadata["sheet_type"] == "fieldwall"


def test_create_editor_session_writes_parseable_created_and_updated_timestamps():
    job_id = editor.create_editor_session("FieldWallProfile")

    metadata = json.loads(
        (editor.JOBS_DIR / job_id / "meta.json").read_text()
    )
    created_at = datetime.fromisoformat(metadata["created_at"])
    updated_at = datetime.fromisoformat(metadata["updated_at"])

    assert created_at == updated_at
    assert created_at.utcoffset() == timedelta(0)
    assert updated_at.utcoffset() == timedelta(0)
    assert metadata["created_at"] == metadata["updated_at"]


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
