import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

import app as app_module
from app import app
from pipeline import editor


@pytest.fixture
def client(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(editor, "JOBS_DIR", jobs_dir)
    app.config.update(TESTING=True)
    return app.test_client()


def _create_editor(client):
    response = client.post(
        "/editor/new",
        json={"schema_type": "FieldWallProfile"},
    )
    assert response.status_code == 200
    return response.get_json()["job_id"]


def _find_data(**overrides):
    return {
        "face_id": "south",
        "x": 1.25,
        "y": 0.45,
        "elevation": 287.35,
        "locus": "1042",
        "description": "Bronze fragment",
        **overrides,
    }


def _valid_field_wall_state():
    return {
        "trenchLabel": "T104",
        "faceLabel": "Southern baulk",
        "illustrators": ["A. Recorder"],
        "date": "2026-07-24",
        "northArrowPresent": True,
        "gridSquareCm": 20.0,
        "gridTiePoints": [],
        "loci": [],
        "layers": [],
        "marginalia": [],
    }


def test_post_find_without_stratigraphy_succeeds(client):
    job_id = _create_editor(client)

    response = client.post(f"/finds/{job_id}/new", json=_find_data())

    assert response.status_code == 200
    stored = response.get_json()
    assert stored["find_id"]
    assert stored["locus"] == "1042"
    assert not (editor.JOBS_DIR / job_id / "editor_state.json").exists()


def test_post_find_missing_required_field_returns_clear_4xx(client):
    job_id = _create_editor(client)
    find_data = _find_data()
    del find_data["elevation"]

    response = client.post(f"/finds/{job_id}/new", json=find_data)

    assert 400 <= response.status_code < 500
    assert "elevation" in response.get_json()["error"]


def test_get_finds_returns_both_added_finds(client):
    job_id = _create_editor(client)
    first = client.post(f"/finds/{job_id}/new", json=_find_data()).get_json()
    second = client.post(
        f"/finds/{job_id}/new",
        json=_find_data(face_id="north", locus="1043"),
    ).get_json()

    response = client.get(f"/finds/{job_id}")

    assert response.status_code == 200
    assert response.get_json() == [first, second]


def test_delete_find_removes_it_from_subsequent_get(client):
    job_id = _create_editor(client)
    first = client.post(f"/finds/{job_id}/new", json=_find_data()).get_json()
    second = client.post(
        f"/finds/{job_id}/new",
        json=_find_data(locus="1043"),
    ).get_json()

    delete_response = client.delete(
        f"/finds/{job_id}/{first['find_id']}",
    )
    get_response = client.get(f"/finds/{job_id}")

    assert delete_response.status_code == 200
    assert delete_response.get_json() == {"ok": True}
    assert get_response.get_json() == [second]


def test_delete_unknown_find_returns_4xx(client):
    job_id = _create_editor(client)

    response = client.delete(f"/finds/{job_id}/missing-find")

    assert 400 <= response.status_code < 500
    assert "missing-find" in response.get_json()["error"]


def test_post_find_syncs_existing_extraction_output(client):
    job_id = _create_editor(client)
    output_path = editor.JOBS_DIR / job_id / "extraction_output.json"
    output_path.write_text(json.dumps({"trenchLabel": "T104", "finds": []}))

    response = client.post(f"/finds/{job_id}/new", json=_find_data())

    assert response.status_code == 200
    assert json.loads(output_path.read_text())["finds"] == [
        response.get_json(),
    ]


def test_find_added_before_finalize_is_synced_into_output(
    client,
    monkeypatch,
):
    job_id = _create_editor(client)
    pipeline_calls = []

    def fake_run_editor_pipeline(requested_job_id):
        pipeline_calls.append(requested_job_id)
        return "find-sync-build-task"

    monkeypatch.setattr(
        app_module,
        "_run_editor_pipeline",
        fake_run_editor_pipeline,
    )
    stored_find = client.post(
        f"/finds/{job_id}/new",
        json=_find_data(),
    ).get_json()
    save_response = client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )

    finalize_response = client.post(f"/editor/{job_id}/finalize")

    assert save_response.status_code == 200
    assert finalize_response.status_code == 202
    assert pipeline_calls == [job_id]
    output_path = editor.JOBS_DIR / job_id / "extraction_output.json"
    assert json.loads(output_path.read_text())["finds"] == [stored_find]
