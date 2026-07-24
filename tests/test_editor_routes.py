import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from app import app
from pipeline import editor


@pytest.fixture
def client(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(editor, "JOBS_DIR", jobs_dir)
    app.config.update(TESTING=True)
    return app.test_client()


def _create_editor(client, schema_type="FieldWallProfile"):
    response = client.post("/editor/new", json={"schema_type": schema_type})
    assert response.status_code == 200
    return response.get_json()["job_id"]


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


def test_create_editor_with_valid_schema_type_returns_job_id(client):
    response = client.post(
        "/editor/new",
        json={"schema_type": "FieldWallProfile"},
    )

    assert response.status_code == 200
    assert response.get_json()["job_id"]


def test_create_editor_with_invalid_schema_type_returns_400(client):
    response = client.post(
        "/editor/new",
        json={"schema_type": "bogus"},
    )

    assert response.status_code == 400
    assert "Unsupported schema_type" in response.get_json()["error"]


def test_save_then_load_state_round_trips_over_http(client):
    job_id = _create_editor(client)
    state = {
        "features": [{"id": 1, "coordinates": [12.5, 8.25]}],
        "settings": {"snap": True},
    }

    save_response = client.post(f"/editor/{job_id}/save", json=state)
    load_response = client.get(f"/editor/{job_id}/state")

    assert save_response.status_code == 200
    assert save_response.get_json() == {"ok": True}
    assert load_response.status_code == 200
    assert load_response.get_json() == state


def test_get_state_without_saved_state_returns_empty_object(client):
    job_id = _create_editor(client)

    response = client.get(f"/editor/{job_id}/state")

    assert response.status_code == 200
    assert response.get_json() == {}


def test_get_state_for_unknown_job_returns_404(client):
    response = client.get("/editor/never-created/state")

    assert response.status_code == 404
    assert "does not exist" in response.get_json()["error"]


def test_finalize_valid_saved_state_returns_finalized_object(client):
    job_id = _create_editor(client)
    state = _valid_field_wall_state()
    save_response = client.post(f"/editor/{job_id}/save", json=state)

    response = client.post(f"/editor/{job_id}/finalize")

    assert save_response.status_code == 200
    assert response.status_code == 200
    assert response.get_json() == {**state, "source": "manual_editor"}


def test_finalize_invalid_saved_state_returns_400(client):
    job_id = _create_editor(client)
    save_response = client.post(
        f"/editor/{job_id}/save",
        json={"trenchLabel": "T104"},
    )

    response = client.post(f"/editor/{job_id}/finalize")

    assert save_response.status_code == 200
    assert response.status_code == 400
    assert "error" in response.get_json()
