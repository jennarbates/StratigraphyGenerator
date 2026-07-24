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


def _create_editor(client, schema_type="FieldWallProfile"):
    response = client.post("/editor/new", json={"schema_type": schema_type})
    assert response.status_code == 200
    return response.get_json()["job_id"]


def _write_job_meta(
    tmp_path,
    job_id,
    *,
    status,
    source="extraction",
    created_at=None,
    updated_at=None,
):
    job_dir = tmp_path / "jobs" / job_id
    job_dir.mkdir()
    meta = {
        "job_id": job_id,
        "source": source,
        "status": status,
    }
    if created_at is not None:
        meta["created_at"] = created_at
    if updated_at is not None:
        meta["updated_at"] = updated_at
    (job_dir / "meta.json").write_text(json.dumps(meta))


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


def _invalid_structural_field_wall_envelope():
    return {
        "schemaType": "FieldWallProfile",
        "finalizeState": _valid_field_wall_state(),
        "gridConfig": {"faces": {}},
        "editorState": {"faces": []},
        "resumeState": {"faces": []},
    }


def _read_job_meta(job_id):
    return json.loads(
        (editor.JOBS_DIR / job_id / "meta.json").read_text()
    )


def _mock_pipeline_start(monkeypatch, task_id="editor-task-123"):
    calls = []

    def fake_run_editor_pipeline(job_id):
        calls.append({
            "job_id": job_id,
            "meta": _read_job_meta(job_id),
        })
        return task_id

    monkeypatch.setattr(
        app_module,
        "_run_editor_pipeline",
        fake_run_editor_pipeline,
    )
    return calls


def _expected_finalized_output(state):
    return {
        **state,
        "finds": [],
        "source": "manual_editor",
    }


def test_create_editor_with_valid_schema_type_returns_session_details(client):
    response = client.post(
        "/editor/new",
        json={"schema_type": "FieldWallProfile"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    job_id = payload["job_id"]
    assert payload == {
        "job_id": job_id,
        "schema_type": "FieldWallProfile",
        "status": "editing",
        "editor_url": f"/editor/{job_id}",
    }


def test_create_editor_with_invalid_schema_type_returns_400(client):
    response = client.post(
        "/editor/new",
        json={"schema_type": "bogus"},
    )

    assert response.status_code == 400
    assert "Unsupported schema_type" in response.get_json()["error"]


def test_get_editor_page_for_valid_job_returns_200(client):
    job_id = _create_editor(client)

    response = client.get(f"/editor/{job_id}")

    assert response.status_code == 200


def test_new_editor_draft_appears_as_resumable_previous_work(client):
    job_id = _create_editor(client)

    response = client.get("/")

    assert response.status_code == 200
    assert f'href="/editor/{job_id}"'.encode() in response.data
    assert b"Work in progress" in response.data
    assert b"Created from scratch" in response.data
    assert b"Creating 3D model" not in response.data


@pytest.mark.parametrize("status", ["building", "complete"])
def test_non_editing_job_keeps_results_link(client, tmp_path, status):
    job_id = f"{status}-job"
    _write_job_meta(tmp_path, job_id, status=status)

    response = client.get("/")

    assert f'href="/jobs/{job_id}"'.encode() in response.data


def test_results_route_for_editor_draft_redirects_to_editor(client):
    job_id = _create_editor(client)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/editor/{job_id}")


def test_previous_work_sorts_by_updated_at_then_created_at(client, tmp_path):
    _write_job_meta(
        tmp_path,
        "z-old-update",
        status="complete",
        created_at="2026-07-24T12:00:00+00:00",
        updated_at="2026-07-24T12:00:00+00:00",
    )
    _write_job_meta(
        tmp_path,
        "z-old-created",
        status="complete",
        created_at="2026-07-24T13:00:00+00:00",
        updated_at="2026-07-24T14:00:00+00:00",
    )
    _write_job_meta(
        tmp_path,
        "a-new-created",
        status="complete",
        created_at="2026-07-24T13:30:00+00:00",
        updated_at="2026-07-24T14:00:00+00:00",
    )

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert (
        html.index("/jobs/a-new-created")
        < html.index("/jobs/z-old-created")
        < html.index("/jobs/z-old-update")
    )


def test_legacy_job_without_timestamps_remains_listable(client, tmp_path):
    job_id = "legacy-job"
    _write_job_meta(tmp_path, job_id, status="complete")

    response = client.get("/")

    assert response.status_code == 200
    assert f'href="/jobs/{job_id}"'.encode() in response.data


def test_editor_page_contains_job_id_data_attribute(client):
    job_id = _create_editor(client)

    response = client.get(f"/editor/{job_id}")

    assert f'data-job-id="{job_id}"'.encode() in response.data


def test_archaeological_diagram_editor_page_contains_schema_data_attribute(
    client,
):
    job_id = _create_editor(client, "ArchaeologicalDiagram")

    response = client.get(
        f"/editor/{job_id}?schema_type=FieldWallProfile",
    )

    assert (
        b'data-schema-type="ArchaeologicalDiagram"'
        in response.data
    )


def test_field_wall_profile_editor_page_contains_schema_data_attribute(client):
    job_id = _create_editor(client, "FieldWallProfile")

    response = client.get(
        f"/editor/{job_id}?schema_type=ArchaeologicalDiagram",
    )

    assert b'data-schema-type="FieldWallProfile"' in response.data


def test_get_editor_page_for_unknown_session_returns_404(client):
    response = client.get("/editor/never-created")

    assert response.status_code == 404
    assert b'id="editor-app"' not in response.data


@pytest.mark.parametrize(
    "editor_meta",
    [
        None,
        "{not valid json",
        json.dumps({}),
        json.dumps({"schema_type": "UnsupportedSchema"}),
    ],
    ids=[
        "missing",
        "malformed",
        "missing-schema",
        "unsupported-schema",
    ],
)
def test_editor_page_with_invalid_metadata_is_not_usable(
    client,
    tmp_path,
    editor_meta,
):
    job_id = "invalid-metadata"
    session_dir = tmp_path / "jobs" / job_id
    session_dir.mkdir()
    if editor_meta is not None:
        (session_dir / "editor_meta.json").write_text(editor_meta)

    response = client.get(f"/editor/{job_id}")

    assert response.status_code != 200
    assert b'id="editor-app"' not in response.data


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


def test_finalize_valid_saved_state_returns_lifecycle_fields(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch)
    job_id = _create_editor(client)
    state = _valid_field_wall_state()
    save_response = client.post(f"/editor/{job_id}/save", json=state)

    response = client.post(f"/editor/{job_id}/finalize")

    assert save_response.status_code == 200
    assert response.status_code == 202
    assert response.get_json() == {
        "job_id": job_id,
        "status": "building",
        "task_id": "editor-task-123",
        "results_url": f"/jobs/{job_id}",
        "visualizer_url": f"/visualizer?job={job_id}",
        "output": _expected_finalized_output(state),
    }
    assert [call["job_id"] for call in calls] == [job_id]


def test_finalize_changes_status_from_editing_to_finalizing_before_pipeline(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch)
    job_id = _create_editor(client)
    client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )
    editing_updated_at = _read_job_meta(job_id)["updated_at"]

    response = client.post(f"/editor/{job_id}/finalize")

    assert response.status_code == 202
    finalizing_meta = calls[0]["meta"]
    assert finalizing_meta["status"] == "finalizing"
    assert finalizing_meta["updated_at"] != editing_updated_at


def test_finalize_sets_building_status_and_stores_task_id_after_pipeline_start(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch, task_id="build-task-456")
    job_id = _create_editor(client)
    client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )

    response = client.post(f"/editor/{job_id}/finalize")

    metadata = _read_job_meta(job_id)
    assert response.status_code == 202
    assert len(calls) == 1
    assert metadata["status"] == "building"
    assert metadata["task_id"] == "build-task-456"
    assert metadata["gempy_task_id"] == "build-task-456"
    assert metadata["updated_at"] != calls[0]["meta"]["updated_at"]


def test_finalize_invalid_saved_state_returns_400_and_leaves_status_editing(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch)
    job_id = _create_editor(client)
    save_response = client.post(
        f"/editor/{job_id}/save",
        json={"trenchLabel": "T104"},
    )

    response = client.post(f"/editor/{job_id}/finalize")

    assert save_response.status_code == 200
    assert response.status_code == 400
    assert "error" in response.get_json()
    assert _read_job_meta(job_id)["status"] == "editing"
    assert calls == []


def test_synchronous_pipeline_failure_sets_error_and_preserves_editor_data(
    client,
    monkeypatch,
):
    calls = []

    def fail_pipeline(job_id):
        calls.append(_read_job_meta(job_id))
        raise RuntimeError("sensitive internal pipeline detail")

    monkeypatch.setattr(app_module, "_run_editor_pipeline", fail_pipeline)
    job_id = _create_editor(client)
    state = _valid_field_wall_state()
    client.post(f"/editor/{job_id}/save", json=state)
    state_path = editor.JOBS_DIR / job_id / "editor_state.json"
    original_editor_state = state_path.read_text()

    response = client.post(f"/editor/{job_id}/finalize")

    metadata = _read_job_meta(job_id)
    output = json.loads(
        (editor.JOBS_DIR / job_id / "extraction_output.json").read_text()
    )
    assert response.status_code == 500
    assert calls[0]["status"] == "finalizing"
    assert metadata["status"] == "error"
    assert metadata["updated_at"] != calls[0]["updated_at"]
    assert state_path.read_text() == original_editor_state
    assert output == _expected_finalized_output(state)


def test_pipeline_failure_returns_non_2xx_with_user_safe_error(
    client,
    monkeypatch,
):
    def fail_pipeline(job_id):
        raise RuntimeError("database password was rejected")

    monkeypatch.setattr(app_module, "_run_editor_pipeline", fail_pipeline)
    job_id = _create_editor(client)
    client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )

    response = client.post(f"/editor/{job_id}/finalize")

    assert not 200 <= response.status_code < 300
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["error"] == "Model processing could not be started."
    assert "password" not in response.get_data(as_text=True)


def test_second_finalize_while_finalizing_does_not_start_pipeline_again(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch, task_id=None)
    job_id = _create_editor(client)
    client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )

    first_response = client.post(f"/editor/{job_id}/finalize")
    second_response = client.post(f"/editor/{job_id}/finalize")

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.get_json()["status"] == "finalizing"
    assert len(calls) == 1


def test_second_finalize_while_building_does_not_start_pipeline_again(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch)
    job_id = _create_editor(client)
    client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )

    first_response = client.post(f"/editor/{job_id}/finalize")
    second_response = client.post(f"/editor/{job_id}/finalize")

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.get_json()["status"] == "building"
    assert second_response.get_json()["task_id"] == "editor-task-123"
    assert len(calls) == 1


def test_finalize_after_completion_returns_existing_lifecycle_information(
    client,
    monkeypatch,
):
    calls = _mock_pipeline_start(monkeypatch)
    job_id = _create_editor(client)
    state = _valid_field_wall_state()
    client.post(f"/editor/{job_id}/save", json=state)
    first_response = client.post(f"/editor/{job_id}/finalize")
    metadata = _read_job_meta(job_id)
    metadata["status"] = "complete"
    app_module._save_meta(editor.JOBS_DIR / job_id, metadata)

    second_response = client.post(f"/editor/{job_id}/finalize")

    assert first_response.status_code == 202
    assert second_response.status_code == 200
    assert second_response.get_json() == {
        "job_id": job_id,
        "status": "complete",
        "task_id": "editor-task-123",
        "results_url": f"/jobs/{job_id}",
        "visualizer_url": f"/visualizer?job={job_id}",
        "output": _expected_finalized_output(state),
    }
    assert len(calls) == 1


def test_finalize_lifecycle_urls_point_to_job_results_and_visualizer(
    client,
    monkeypatch,
):
    _mock_pipeline_start(monkeypatch)
    job_id = _create_editor(client)
    client.post(
        f"/editor/{job_id}/save",
        json=_valid_field_wall_state(),
    )

    response = client.post(f"/editor/{job_id}/finalize")

    payload = response.get_json()
    assert payload["results_url"] == f"/jobs/{job_id}"
    assert payload["visualizer_url"] == f"/visualizer?job={job_id}"


def test_finalize_structural_error_returns_4xx_json(client):
    job_id = _create_editor(client)
    save_response = client.post(
        f"/editor/{job_id}/save",
        json=_invalid_structural_field_wall_envelope(),
    )

    response = client.post(f"/editor/{job_id}/finalize")

    assert save_response.status_code == 200
    assert response.status_code == 400
    assert response.is_json
    assert "at least one face" in response.get_json()["error"]
