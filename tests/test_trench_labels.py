"""Trench/wall label metadata on scan uploads and editor creation (Chunk 5)."""

import io
import json

import pytest
from PIL import Image

import storage
from backend import create_app
from pipeline import editor


@pytest.fixture
def scan_client(tmp_path, monkeypatch):
    jobs_dir = storage.JOBS_DIR

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client(), jobs_dir


@pytest.fixture
def editor_client(tmp_path, monkeypatch):
    jobs_dir = storage.JOBS_DIR

    import app as app_module

    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client(), jobs_dir


@pytest.fixture
def editor_jobs_dir(tmp_path, monkeypatch):
    jobs_dir = storage.JOBS_DIR
    return jobs_dir


def _fake_png():
    image_bytes = io.BytesIO()
    Image.new("RGB", (120, 100), "white").save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes


def _create_job(client):
    response = client.post("/api/jobs")
    assert response.status_code == 200
    return response.get_json()["job_id"]


def _upload(client, job_id, **extra):
    data = {"sheet_type": "fieldwall", "file": (_fake_png(), "wall.png")}
    data.update(extra)
    return client.post(
        f"/api/jobs/{job_id}/scan",
        data=data,
        content_type="multipart/form-data",
    )


def _read_meta(jobs_dir, job_id):
    return json.loads((jobs_dir / job_id / "meta.json").read_text())


def test_upload_with_both_labels_echoes_and_persists(scan_client):
    client, jobs_dir = scan_client
    job_id = _create_job(client)

    response = _upload(client, job_id, trench_label="T900", wall_label="north wall")

    assert response.status_code == 200
    body = response.get_json()
    assert body["trench_label"] == "T900"
    assert body["wall_label"] == "north wall"

    meta = _read_meta(jobs_dir, job_id)
    assert meta["trench_label"] == "T900"
    assert meta["wall_label"] == "north wall"
    assert meta["sheet_type"] == "fieldwall"


def test_upload_without_labels_omits_keys(scan_client):
    client, jobs_dir = scan_client
    job_id = _create_job(client)

    response = _upload(client, job_id)

    assert response.status_code == 200
    body = response.get_json()
    assert "trench_label" not in body
    assert "wall_label" not in body

    meta = _read_meta(jobs_dir, job_id)
    assert "trench_label" not in meta
    assert "wall_label" not in meta


def test_upload_with_blank_labels_omits_keys(scan_client):
    client, jobs_dir = scan_client
    job_id = _create_job(client)

    response = _upload(client, job_id, trench_label="   ", wall_label="")

    assert response.status_code == 200
    meta = _read_meta(jobs_dir, job_id)
    assert "trench_label" not in meta
    assert "wall_label" not in meta


def test_upload_strips_surrounding_whitespace(scan_client):
    client, jobs_dir = scan_client
    job_id = _create_job(client)

    response = _upload(
        client,
        job_id,
        trench_label="  T900  ",
        wall_label="\teast wall\n",
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["trench_label"] == "T900"
    assert body["wall_label"] == "east wall"

    meta = _read_meta(jobs_dir, job_id)
    assert meta["trench_label"] == "T900"
    assert meta["wall_label"] == "east wall"


def test_create_editor_session_records_labels(editor_jobs_dir):
    job_id = editor.create_editor_session(
        "FieldWallProfile",
        trench_label="  T900 ",
        wall_label=" north wall ",
    )

    meta = _read_meta(editor_jobs_dir, job_id)
    assert meta["trench_label"] == "T900"
    assert meta["wall_label"] == "north wall"


def test_create_editor_session_omits_blank_labels(editor_jobs_dir):
    job_id = editor.create_editor_session(
        "FieldWallProfile",
        trench_label="   ",
        wall_label=None,
    )

    meta = _read_meta(editor_jobs_dir, job_id)
    assert "trench_label" not in meta
    assert "wall_label" not in meta


def test_editor_creation_persists_labels(editor_client):
    client, jobs_dir = editor_client

    response = client.post(
        "/editor/new",
        json={
            "schema_type": "FieldWallProfile",
            "trench_label": "  T900 ",
            "wall_label": " north wall ",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["trench_label"] == "T900"
    assert body["wall_label"] == "north wall"

    meta = _read_meta(jobs_dir, body["job_id"])
    assert meta["trench_label"] == "T900"
    assert meta["wall_label"] == "north wall"
    assert meta["status"] == "editing"


def test_editor_creation_without_labels_omits_keys(editor_client):
    client, jobs_dir = editor_client

    response = client.post("/editor/new", json={"schema_type": "FieldWallProfile"})

    assert response.status_code == 200
    body = response.get_json()
    assert "trench_label" not in body
    assert "wall_label" not in body

    meta = _read_meta(jobs_dir, body["job_id"])
    assert "trench_label" not in meta
    assert "wall_label" not in meta
