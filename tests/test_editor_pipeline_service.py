"""backend/services/editor_pipeline.run_editor_pipeline, actually executed.

Every existing finalize test monkeypatches this function away, so its body was
never run by the suite. A missing ``import storage`` therefore sat in it
undetected: the function raised NameError on the first line for every real
editor finalize while the whole suite stayed green.

These stub only the leaf calls -- the gempy build and the two pipeline stages
that need real extraction data -- so the orchestration itself, its meta.json
writes, and its module-level name resolution all execute for real.
"""

import json

import pytest

import storage
from backend.services import editor_pipeline as service


@pytest.fixture
def prepared_job(monkeypatch):
    """A finalized editor session, ready for the pipeline to pick up."""
    job_id = "abcdef012345"
    directory = storage.JOBS_DIR / job_id
    directory.mkdir()
    (directory / "editor_meta.json").write_text(
        json.dumps({"schema_type": "FieldWallProfile"})
    )
    (directory / "editor_state.json").write_text(json.dumps({}))
    (directory / "extraction_output.json").write_text(json.dumps({}))
    (directory / "meta.json").write_text(json.dumps({"job_id": job_id}))

    monkeypatch.setattr(
        service.normalizer,
        "run_normalize",
        lambda src, dst: ({"normalized": True}, ["normalized"]),
    )
    monkeypatch.setattr(service.validator, "run_validate", lambda path: {"ok": True})
    monkeypatch.setattr(
        service.convert_coords, "make_starter_config", lambda data: {"faces": {}}
    )
    monkeypatch.setattr(
        service.convert_coords,
        "run_convert",
        lambda data, grid, path: {
            "n_points": 3,
            "points_csv": str(storage.JOBS_DIR / "points.csv"),
            "orientations_csv": str(storage.JOBS_DIR / "orientations.csv"),
        },
    )
    monkeypatch.setattr(service, "start_task", lambda *a, **k: "task-1")
    return job_id, directory


def test_run_editor_pipeline_completes_and_records_the_task(prepared_job):
    job_id, directory = prepared_job

    task_id = service.run_editor_pipeline(job_id)

    assert task_id == "task-1"
    meta = json.loads((directory / "meta.json").read_text())
    assert meta["task_id"] == "task-1"
    assert meta["sheet_type"] == "fieldwall"
    assert meta["source"] == "manual_editor"


def test_run_editor_pipeline_creates_every_stage_directory(prepared_job):
    job_id, directory = prepared_job

    service.run_editor_pipeline(job_id)

    for name in service.PIPELINE_SUBDIRECTORIES:
        assert (directory / name).is_dir(), name


def test_run_editor_pipeline_refuses_an_empty_conversion(prepared_job):
    """0 points means the grid config did not line up with the drawing;
    building on it would produce a model of nothing."""
    job_id, _ = prepared_job
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        service.convert_coords,
        "run_convert",
        lambda data, grid, path: {
            "n_points": 0,
            "points_csv": "",
            "orientations_csv": "",
        },
    )
    with pytest.raises(ValueError, match="0 points"):
        service.run_editor_pipeline(job_id)
    monkeypatch.undo()


def test_run_editor_build_records_completion(tmp_path):
    directory = storage.JOBS_DIR / "abcdef012345"
    directory.mkdir()
    (directory / "meta.json").write_text(json.dumps({"status": "building"}))

    result = service.run_editor_build(
        directory,
        lambda log_cb=None: {"outputs": {"model": "trench.gempy"}},
    )

    assert result["outputs"]["model"] == "trench.gempy"
    meta = json.loads((directory / "meta.json").read_text())
    assert meta["status"] == "complete"
    assert meta["model_outputs"] == {"model": "trench.gempy"}


def test_run_editor_build_records_failure_and_reraises(tmp_path):
    directory = storage.JOBS_DIR / "abcdef012345"
    directory.mkdir()
    (directory / "meta.json").write_text(json.dumps({"status": "building"}))

    def boom(log_cb=None):
        raise RuntimeError("gempy exploded")

    with pytest.raises(RuntimeError):
        service.run_editor_build(directory, boom)

    meta = json.loads((directory / "meta.json").read_text())
    assert meta["status"] == "error"
    assert meta["pipeline_error"] == "Model building failed."
