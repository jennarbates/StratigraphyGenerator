import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

import app as app_module
from app import app
from backend.tasks import TASKS
from pipeline import editor


@pytest.fixture
def client(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(editor, "JOBS_DIR", jobs_dir)
    TASKS.clear()
    app.config.update(TESTING=True)
    yield app.test_client()
    TASKS.clear()


def _write_meta(
    job_directory,
    *,
    job_id="status-job",
    status,
    stage=None,
    message=None,
    **extra,
):
    job_directory.mkdir()
    meta = {
        "job_id": job_id,
        "status": status,
        **extra,
    }
    if stage is not None:
        meta["stage"] = stage
    if message is not None:
        meta["message"] = message
    (job_directory / "meta.json").write_text(json.dumps(meta))
    return meta


@pytest.mark.parametrize(
    ("status", "stage", "message"),
    [
        ("editing", "editing", "Continue editing the drawing."),
        (
            "finalizing",
            "finalizing",
            "Preparing the drawing for model processing.",
        ),
        ("building", "building", "Building the 3D model."),
        ("complete", "complete", "The 3D model is ready."),
        (
            "error",
            "building",
            "The 3D model could not be built.",
        ),
    ],
)
def test_job_status_reads_lifecycle_from_meta(
    client,
    status,
    stage,
    message,
):
    job_id = f"{status}-job"
    job_directory = editor.JOBS_DIR / job_id
    _write_meta(
        job_directory,
        job_id=job_id,
        status=status,
        stage=stage,
        message=message,
    )

    response = client.get(f"/api/jobs/{job_id}/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "job_id": job_id,
        "status": status,
        "stage": stage,
        "message": message,
        "results_url": f"/jobs/{job_id}",
    }


def test_unknown_job_status_returns_404(client):
    response = client.get("/api/jobs/unknown-job/status")

    assert response.status_code == 404


def test_job_status_does_not_require_live_task(client):
    job_id = "durable-building-job"
    _write_meta(
        editor.JOBS_DIR / job_id,
        job_id=job_id,
        status="building",
        task_id="lost-task",
    )
    TASKS.clear()

    response = client.get(f"/api/jobs/{job_id}/status")

    assert response.status_code == 200
    assert response.get_json()["status"] == "building"
    assert response.get_json()["stage"] == "building"


def test_complete_status_provides_results_url(client):
    job_id = "complete-results-job"
    _write_meta(
        editor.JOBS_DIR / job_id,
        job_id=job_id,
        status="complete",
    )

    response = client.get(f"/api/jobs/{job_id}/status")

    assert response.status_code == 200
    assert response.get_json()["results_url"] == f"/jobs/{job_id}"


def test_successful_editor_build_persists_complete_status_and_outputs(
    tmp_path,
):
    job_directory = tmp_path / "successful-build"
    points_path = job_directory / "05_convert_coords" / "points.csv"
    orientations_path = (
        job_directory / "05_convert_coords" / "orientations.csv"
    )
    model_path = job_directory / "06_gempy_model" / "trench_model.gempy"
    _write_meta(
        job_directory,
        status="building",
        stage="building",
        points_csv=str(points_path),
        orientations_csv=str(orientations_path),
    )
    build_result = {
        "outputs": {
            "model": str(model_path),
            "meshes": [
                str(
                    job_directory
                    / "06_gempy_model"
                    / "trench_model_meshes"
                    / "layer.obj"
                ),
            ],
        },
    }

    def fake_build(*args, log_cb=None):
        return build_result

    result = app_module._run_editor_build(
        job_directory,
        fake_build,
        "points.csv",
        "orientations.csv",
        "output-prefix",
    )

    meta = json.loads((job_directory / "meta.json").read_text())
    assert result == build_result
    assert meta["status"] == "complete"
    assert meta["stage"] == "complete"
    assert meta["message"] == "The 3D model is ready."
    assert meta["model_outputs"] == build_result["outputs"]
    assert meta["points_csv"] == str(points_path)
    assert meta["orientations_csv"] == str(orientations_path)


def test_failed_editor_build_persists_safe_error_and_preserves_source_state(
    tmp_path,
):
    job_directory = tmp_path / "failed-build"
    _write_meta(
        job_directory,
        status="building",
        stage="building",
    )
    editor_state_path = job_directory / "editor_state.json"
    editor_state_path.write_text('{"faces": [{"id": "source-face"}]}')
    original_editor_state = editor_state_path.read_text()

    def fail_build(*args, log_cb=None):
        raise RuntimeError("secret database password")

    with pytest.raises(RuntimeError, match="secret database password"):
        app_module._run_editor_build(
            job_directory,
            fail_build,
            "points.csv",
            "orientations.csv",
            "output-prefix",
        )

    meta = json.loads((job_directory / "meta.json").read_text())
    assert meta["status"] == "error"
    assert meta["stage"] == "building"
    assert meta["message"] == "Model building failed."
    assert meta["pipeline_error"] == "Model building failed."
    assert "password" not in json.dumps(meta)
    assert editor_state_path.read_text() == original_editor_state
