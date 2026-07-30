"""Trench listing and trench build routes (Chunk 6).

The build route is exercised with build_gempy.run_build stubbed out: gempy is
optional in this environment, and the point of these tests is the plumbing
around the build (grouping, merging, registration refusals, file layout), not
GemPy itself.
"""

import csv
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from backend import create_app
from backend.routes import trenches as trenches_routes
from pipeline import build_gempy
from pipeline.merge_walls import merge_extractions, merged_series_order

from fixtures_merge import EAST_WALL, GRID_T900, NORTH_WALL


@pytest.fixture
def client(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    trenches_dir = tmp_path / "trenches"
    trenches_dir.mkdir()
    monkeypatch.setattr(trenches_routes, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(trenches_routes, "TRENCHES_DIR", trenches_dir)

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client(), jobs_dir, trenches_dir


def _write_job(
    jobs_dir,
    job_id,
    *,
    trench_label="T900",
    wall_label=None,
    sheet_type="fieldwall",
    extraction=None,
    normalized=True,
):
    """Create a job directory whose meta mirrors a finalized field sheet."""
    job_directory = jobs_dir / job_id
    (job_directory / "04_normalize_validate").mkdir(parents=True)
    meta = {"job_id": job_id, "sheet_type": sheet_type}
    if trench_label is not None:
        meta["trench_label"] = trench_label
    if wall_label is not None:
        meta["wall_label"] = wall_label
    normalized_path = job_directory / "04_normalize_validate" / "output_clean.json"
    if normalized:
        normalized_path.write_text(json.dumps(extraction or NORTH_WALL))
        meta["normalized_path"] = str(normalized_path)
    (job_directory / "meta.json").write_text(json.dumps(meta))
    return job_directory


def _t900(jobs_dir):
    """The two walls of the A6 fixture, as two jobs of one trench."""
    _write_job(
        jobs_dir,
        "job_north",
        wall_label="north wall",
        extraction=NORTH_WALL,
    )
    _write_job(
        jobs_dir,
        "job_east",
        wall_label="east wall",
        extraction=EAST_WALL,
    )


def _expected_series_order():
    """The order the route should derive. Members are merged in listing order
    (wall_label, then job_id), so the east wall comes first here."""
    merged, _notes = merge_extractions(
        [("east wall", EAST_WALL), ("north wall", NORTH_WALL)])
    order, _order_notes = merged_series_order(merged)
    return order


def test_listing_groups_members_and_skips_unlabelled(client):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)
    _write_job(jobs_dir, "job_orphan", trench_label=None, wall_label="south wall")

    response = http.get("/api/trenches")

    assert response.status_code == 200
    trenches = response.get_json()["trenches"]
    assert list(trenches) == ["T900"]
    members = trenches["T900"]
    assert [m["job_id"] for m in members] == ["job_east", "job_north"]
    assert [m["wall_label"] for m in members] == ["east wall", "north wall"]
    assert all(m["has_normalized"] for m in members)
    assert all(m["sheet_type"] == "fieldwall" for m in members)
    assert all("_normalized_path" not in m for m in members)


def test_listing_skips_unreadable_meta(client):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)
    broken = jobs_dir / "job_broken"
    broken.mkdir()
    (broken / "meta.json").write_text("{not json")

    response = http.get("/api/trenches")

    assert response.status_code == 200
    assert [m["job_id"] for m in response.get_json()["trenches"]["T900"]] == [
        "job_east",
        "job_north",
    ]


def test_listing_reports_missing_normalized_output(client):
    http, jobs_dir, _trenches_dir = client
    _write_job(jobs_dir, "job_north", wall_label="north wall", normalized=False)

    response = http.get("/api/trenches")

    members = response.get_json()["trenches"]["T900"]
    assert members[0]["has_normalized"] is False


def test_build_without_grid_returns_starter_and_starts_no_task(
    client, monkeypatch
):
    http, jobs_dir, trenches_dir = client
    _t900(jobs_dir)

    def fail(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("no build may start before a grid is supplied")

    monkeypatch.setattr(build_gempy, "run_build", fail)

    response = http.post("/api/trenches/T900/build", json={})

    assert response.status_code == 200
    body = response.get_json()
    assert body["needs_grid"] is True
    assert set(body["starter"]["faces"]) == {"north wall", "east wall"}
    assert "task_id" not in body
    assert list(trenches_dir.iterdir()) == []


def test_build_refuses_the_untouched_starter_config(client):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)

    starter = http.post("/api/trenches/T900/build", json={}).get_json()["starter"]
    response = http.post("/api/trenches/T900/build", json={"grid": starter})

    assert response.status_code == 400
    assert "placeholder" in response.get_json()["error"]


def test_build_with_real_grid_starts_task_and_writes_outputs(
    client, monkeypatch
):
    http, jobs_dir, trenches_dir = client
    _t900(jobs_dir)

    calls = []

    def stub_run_build(points_csv, orientations_csv, out_prefix, **kwargs):
        calls.append({
            "points_csv": points_csv,
            "orientations_csv": orientations_csv,
            "out_prefix": out_prefix,
            "kwargs": kwargs,
        })
        return {"series_order": kwargs.get("series_order"), "outputs": {}}

    monkeypatch.setattr(build_gempy, "run_build", stub_run_build)

    response = http.post("/api/trenches/T900/build", json={"grid": GRID_T900})

    assert response.status_code == 200
    body = response.get_json()
    assert body["task_id"]
    assert body["grid_warnings"] == []

    trench_directory = trenches_dir / "T900"
    merged = json.loads((trench_directory / "merged.json").read_text())
    assert [face["face"] for face in merged["trenchProfiles"]] == [
        "east wall",
        "north wall",
    ]
    points_csv = trench_directory / "points.csv"
    orientations_csv = trench_directory / "points_orientations.csv"
    assert points_csv.is_file()
    assert orientations_csv.is_file()
    with points_csv.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert {row["face"] for row in rows} == {"north wall", "east wall"}

    # start_task runs the build on a thread; give it a moment to land.
    for _ in range(200):
        if calls:
            break
        import time

        time.sleep(0.01)
    assert len(calls) == 1
    assert calls[0]["points_csv"] == str(points_csv)
    assert calls[0]["orientations_csv"] == str(orientations_csv)
    assert calls[0]["out_prefix"].startswith(str(trench_directory))
    assert calls[0]["kwargs"]["series_order"] == _expected_series_order()


def test_build_hands_gempy_true_dips_solved_from_both_walls(client, monkeypatch):
    """The payoff of merging: the orientations the model is built from describe
    one plane per surface, not each wall's shallower apparent dip."""
    http, jobs_dir, trenches_dir = client
    _t900(jobs_dir)
    monkeypatch.setattr(build_gempy, "run_build", lambda *a, **k: {})

    response = http.post("/api/trenches/T900/build", json={"grid": GRID_T900})

    assert response.status_code == 200
    with (trenches_dir / "T900" / "points_orientations.csv").open() as handle:
        rows = list(csv.DictReader(handle))

    by_surface = {}
    for row in rows:
        by_surface.setdefault(row["surface"], set()).add(
            (row["dip"], row["azimuth"]))
    assert len(by_surface) == 2
    # Both walls' seeds for a surface now agree, and neither still carries the
    # wall-locked azimuth convert() gave it.
    for values in by_surface.values():
        assert len(values) == 1
        (_dip, azimuth), = values
        assert azimuth not in {"90.0", "180.0"}
    assert any(
        "replaced the per-wall apparent dips" in note
        for note in response.get_json()["notes"]
    )


def test_build_carries_merge_notes_for_munsell_disagreement(client, monkeypatch):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)
    monkeypatch.setattr(build_gempy, "run_build", lambda *a, **k: {})

    response = http.post("/api/trenches/T900/build", json={"grid": GRID_T900})

    notes = response.get_json()["notes"]
    assert any("Munsell disagrees" in note for note in notes)


def test_build_honors_a_supplied_series_order(client, monkeypatch):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)
    supplied = list(reversed(_expected_series_order()))
    calls = []
    monkeypatch.setattr(
        build_gempy,
        "run_build",
        lambda *a, **k: calls.append(k) or {},
    )

    response = http.post(
        "/api/trenches/T900/build",
        json={"grid": GRID_T900, "series_order": supplied},
    )

    assert response.status_code == 200
    for _ in range(200):
        if calls:
            break
        import time

        time.sleep(0.01)
    assert calls[0]["series_order"] == supplied


def test_build_rejects_duplicate_wall_labels(client):
    http, jobs_dir, _trenches_dir = client
    _write_job(jobs_dir, "job_a", wall_label="north wall", extraction=NORTH_WALL)
    _write_job(jobs_dir, "job_b", wall_label="north wall", extraction=EAST_WALL)

    response = http.post("/api/trenches/T900/build", json={"grid": GRID_T900})

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert "job_a" in error
    assert "job_b" in error


def test_build_rejects_member_without_normalized_extraction(client):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)
    _write_job(
        jobs_dir,
        "job_south",
        wall_label="south wall",
        normalized=False,
    )

    response = http.post("/api/trenches/T900/build", json={"grid": GRID_T900})

    assert response.status_code == 400
    assert "job_south" in response.get_json()["error"]


def test_build_rejects_unknown_trench(client):
    http, _jobs_dir, _trenches_dir = client

    response = http.post("/api/trenches/T404/build", json={"grid": GRID_T900})

    assert response.status_code == 400
    assert "T404" in response.get_json()["error"]


def test_build_rejects_grid_missing_a_face(client):
    http, jobs_dir, _trenches_dir = client
    _t900(jobs_dir)
    partial = {"faces": {"north wall": GRID_T900["faces"]["north wall"]}}

    response = http.post("/api/trenches/T900/build", json={"grid": partial})

    assert response.status_code == 400
    assert "east wall" in response.get_json()["error"]


def test_build_derives_a_wall_label_when_missing(client, monkeypatch):
    http, jobs_dir, trenches_dir = client
    _write_job(jobs_dir, "job_north", wall_label="north wall", extraction=NORTH_WALL)
    _write_job(jobs_dir, "job_east", wall_label=None, extraction=EAST_WALL)
    monkeypatch.setattr(build_gempy, "run_build", lambda *a, **k: {})

    response = http.post("/api/trenches/T900/build", json={})

    assert response.status_code == 200
    body = response.get_json()
    assert any("job_east" in note for note in body["notes"])
    assert "fieldwall job_east" in body["starter"]["faces"]


def test_file_route_rejects_escapes(client):
    http, _jobs_dir, trenches_dir = client
    trench_directory = trenches_dir / "T900"
    trench_directory.mkdir()
    (trench_directory / "points.csv").write_text("X,Y,Z,surface,face\n")
    (trenches_dir / "secret.txt").write_text("not yours")

    escape = http.get("/api/trenches/T900/file?path=../secret.txt")
    assert escape.status_code == 400

    missing_path = http.get("/api/trenches/T900/file")
    assert missing_path.status_code == 400

    ok = http.get("/api/trenches/T900/file?path=points.csv")
    assert ok.status_code == 200
