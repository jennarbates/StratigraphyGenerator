import json
import re
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline import editor
from pipeline.extract_fieldwall import FieldWallProfile
from pipeline.extract_illustrator import ArchaeologicalDiagram


@pytest.fixture(autouse=True)
def isolate_jobs_dir(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(editor, "JOBS_DIR", jobs_dir)


@pytest.fixture
def find_data():
    return {
        "face_id": "south",
        "x": 1.25,
        "y": 0.45,
        "elevation": 287.35,
        "locus": "1042",
        "description": "",
    }


def test_add_find_on_fresh_job_assigns_id_without_editor_or_output(find_data):
    job_id = editor.create_editor_session("FieldWallProfile")
    job_dir = editor.JOBS_DIR / job_id

    stored_find = editor.add_find(job_id, find_data)

    assert re.fullmatch(r"[0-9a-f]{12}", stored_find["find_id"])
    assert not (job_dir / "editor_state.json").exists()
    assert not (job_dir / "extraction_output.json").exists()
    assert json.loads((job_dir / "finds.json").read_text()) == [stored_find]


@pytest.mark.parametrize(
    "missing_field",
    ["face_id", "x", "y", "elevation", "locus", "description"],
)
def test_add_find_missing_required_field_raises_value_error(
    find_data,
    missing_field,
):
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    del find_data[missing_field]

    with pytest.raises(ValueError, match=missing_field):
        editor.add_find(job_id, find_data)


def test_add_find_for_unknown_job_raises_file_not_found(find_data):
    with pytest.raises(FileNotFoundError):
        editor.add_find("missing-job", find_data)


def test_get_finds_without_finds_file_returns_empty_list():
    job_id = editor.create_editor_session("FieldWallProfile")

    assert editor.get_finds(job_id) == []
    assert not (editor.JOBS_DIR / job_id / "editor_state.json").exists()
    assert not (editor.JOBS_DIR / job_id / "extraction_output.json").exists()


def test_add_find_twice_then_get_finds_returns_both_in_order(find_data):
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    first = editor.add_find(job_id, find_data)
    second_data = {**find_data, "locus": "1043", "x": 2.5}
    second = editor.add_find(job_id, second_data)

    assert editor.get_finds(job_id) == [first, second]
    assert first["find_id"] != second["find_id"]


def test_delete_find_removes_only_matching_entry(find_data):
    job_id = editor.create_editor_session("FieldWallProfile")
    first = editor.add_find(job_id, find_data)
    second = editor.add_find(
        job_id,
        {**find_data, "locus": "1043", "description": "Bronze fragment"},
    )

    editor.delete_find(job_id, first["find_id"])

    assert editor.get_finds(job_id) == [second]
    assert not (
        editor.JOBS_DIR / job_id / "editor_state.json"
    ).exists()
    assert not (
        editor.JOBS_DIR / job_id / "extraction_output.json"
    ).exists()


def test_delete_find_with_unknown_id_raises_value_error(find_data):
    job_id = editor.create_editor_session("FieldWallProfile")
    editor.add_find(job_id, find_data)

    with pytest.raises(ValueError):
        editor.delete_find(job_id, "missing-find")


def test_sync_finds_without_extraction_output_does_nothing(find_data):
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    stored_find = editor.add_find(job_id, find_data)

    editor.sync_finds_to_output(job_id)

    assert editor.get_finds(job_id) == [stored_find]
    assert not (
        editor.JOBS_DIR / job_id / "extraction_output.json"
    ).exists()


def test_sync_finds_updates_existing_extraction_output(find_data):
    job_id = editor.create_editor_session("FieldWallProfile")
    first = editor.add_find(job_id, find_data)
    second = editor.add_find(
        job_id,
        {**find_data, "face_id": "north", "locus": "1044"},
    )
    output_path = editor.JOBS_DIR / job_id / "extraction_output.json"
    output_path.write_text(json.dumps({"trenchLabel": "T104", "finds": []}))

    editor.sync_finds_to_output(job_id)

    output = json.loads(output_path.read_text())
    assert output["trenchLabel"] == "T104"
    assert output["finds"] == [first, second]
    assert output["finds"] == json.loads(
        (editor.JOBS_DIR / job_id / "finds.json").read_text()
    )


@pytest.mark.parametrize(
    ("model_class", "legacy_output"),
    [
        (
            FieldWallProfile,
            {
                "trenchLabel": None,
                "faceLabel": None,
                "illustrators": None,
                "date": None,
                "northArrowPresent": None,
                "gridSquareCm": None,
                "gridTiePoints": None,
                "loci": None,
                "layers": None,
                "marginalia": None,
            },
        ),
        (
            ArchaeologicalDiagram,
            {
                "metadata": None,
                "trenchProfiles": [],
                "legend": None,
            },
        ),
    ],
)
def test_legacy_output_without_finds_loads_with_empty_list(
    model_class,
    legacy_output,
):
    parsed = model_class.model_validate(legacy_output)

    assert parsed.finds == []
