"""Wall traces in the viewer manifest (Chunk 8, part 1).

A merged trench model interpolates across the whole extent, including the
empty air between two walls. The traces are the points that were actually
drawn on each wall, so a reader can see which parts of the model are data.

The manifest is built through the same seam tests/test_gempy_viewer_manifest.py
uses -- run_build with a stand-in gempy module -- over CSVs the real converter
produced from the A6 fixture trench.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from fixtures_merge import (
    EAST_WALL,
    GRID_T900,
    NORTH_WALL,
    SURFACE_L1,
    SURFACE_L2,
)
from test_gempy_viewer_manifest import fake_gempy

import storage
from pipeline import convert_coords
from pipeline.build_gempy import run_build, wall_traces
from pipeline.merge_walls import merge_extractions


@pytest.fixture
def manifest(tmp_path, monkeypatch):
    """The manifest for the merged T900 trench: two walls, two surfaces."""
    merged, _notes = merge_extractions(
        [("north wall", NORTH_WALL), ("east wall", EAST_WALL)]
    )
    conversion = convert_coords.run_convert(
        merged, GRID_T900, str(tmp_path / "points.csv")
    )

    model_dir = tmp_path / "06_gempy_model"
    model_dir.mkdir()
    monkeypatch.setitem(sys.modules, "gempy", fake_gempy())
    result = run_build(
        conversion["points_csv"],
        conversion["orientations_csv"],
        model_dir / "trench_model",
        resolution=(2, 2, 1),
        extent=[0, 4, 0, 3, 99, 100],
        make_plot=False,
        make_meshes=False,
        save_model=False,
    )
    return json.loads(Path(result["outputs"]["viewer_manifest"]).read_text())


def test_manifest_carries_one_trace_per_face_and_surface(manifest):
    traces = manifest["wallTraces"]

    assert len(traces) == 4
    assert {(trace["face"], trace["surface"]) for trace in traces} == {
        (face, surface)
        for face in ("north wall", "east wall")
        for surface in (SURFACE_L1, SURFACE_L2)
    }
    for trace in traces:
        assert len(trace["points"]) == 5
        assert all(len(point) == 3 for point in trace["points"])
        assert all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for point in trace["points"]
            for value in point
        )


def test_north_wall_traces_sit_on_the_north_wall(manifest):
    """Bearing 90 from origin (0, 3): the north wall runs east at Y = 3."""
    north = [trace for trace in manifest["wallTraces"] if trace["face"] == "north wall"]

    assert len(north) == 2
    for trace in north:
        assert all(point[1] == pytest.approx(3.0) for point in trace["points"])
        assert all(0.0 <= point[0] <= 4.0 for point in trace["points"])


def test_east_wall_traces_are_ordered_along_the_wall(manifest):
    """The east wall runs south at X = 4, so X cannot order it -- the trace
    has to be monotone in Y."""
    east = [trace for trace in manifest["wallTraces"] if trace["face"] == "east wall"]

    assert len(east) == 2
    for trace in east:
        ys = [point[1] for point in trace["points"]]
        assert ys == sorted(ys)
        assert all(point[0] == pytest.approx(4.0) for point in trace["points"])


def test_traces_are_monotone_along_the_wall_for_both_faces(manifest):
    for trace in manifest["wallTraces"]:
        xs = [point[0] for point in trace["points"]]
        ys = [point[1] for point in trace["points"]]
        along = xs if (max(xs) - min(xs)) > (max(ys) - min(ys)) else ys
        assert along == sorted(along)


def test_wall_traces_orders_a_shuffled_group_along_its_own_axis():
    """The grouping helper on its own: a north-south wall is ordered by Y even
    when the rows arrive out of order."""
    points = pd.DataFrame(
        [
            {"X": 4.0, "Y": 1.5, "Z": 99.5, "surface": SURFACE_L1, "face": "east"},
            {"X": 4.0, "Y": 0.5, "Z": 99.4, "surface": SURFACE_L1, "face": "east"},
            {"X": 4.0, "Y": 2.5, "Z": 99.6, "surface": SURFACE_L1, "face": "east"},
        ]
    )

    traces = wall_traces(points)

    assert len(traces) == 1
    assert [point[1] for point in traces[0]["points"]] == [0.5, 1.5, 2.5]
    assert traces[0] == {
        "face": "east",
        "surface": SURFACE_L1,
        "points": [
            [4.0, 0.5, 99.4],
            [4.0, 1.5, 99.5],
            [4.0, 2.5, 99.6],
        ],
    }


def test_wall_traces_without_a_face_column_is_empty():
    """Older CSVs predate the face column; they get no traces rather than a
    crash or a made-up face name."""
    points = pd.DataFrame(
        [
            {"X": 0.0, "Y": 0.0, "Z": 99.0, "surface": SURFACE_L1},
        ]
    )

    assert wall_traces(points) == []


TRACE = {
    "face": "north wall",
    "surface": SURFACE_L1,
    "points": [[0.0, 3.0, 99.98], [2.0, 3.0, 99.97], [4.0, 3.0, 99.96]],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app import app

    jobs_dir = storage.JOBS_DIR
    app.config.update(TESTING=True)
    return app.test_client(), jobs_dir


def _job_with_traces(jobs_dir, wall_traces):
    """A finished job whose manifest carries the given wallTraces value."""
    job_id = "traced-job"
    model_dir = jobs_dir / job_id / "06_gempy_model"
    (model_dir / "trench_model_meshes").mkdir(parents=True)
    (model_dir / "trench_model_meshes" / "L1.obj").write_bytes(b"o mesh")
    (model_dir / "trench_model_lith_block.npz").write_bytes(b"block")
    manifest = {
        "schema_version": 1,
        "kind": "gempy-surface-model",
        "coordinate_system": {"units": "m", "up_axis": "Z"},
        "extent": [0, 4, 0, 3, 99, 100],
        "resolution": [50, 50, 30],
        "series_order": [SURFACE_L1],
        "single_face_note": None,
        "surfaces": [
            {
                "name": SURFACE_L1,
                "mesh_path": "trench_model_meshes/L1.obj",
            }
        ],
        "lith_block_path": "trench_model_lith_block.npz",
    }
    if wall_traces is not None:
        manifest["wallTraces"] = wall_traces
    (model_dir / "trench_model_viewer.json").write_text(json.dumps(manifest))
    (jobs_dir / job_id / "meta.json").write_text(json.dumps({}))
    return job_id


def test_visualizer_files_route_serves_wall_traces(client):
    """The manifest key the viewer needs survives the job payload's whitelist."""
    http, jobs_dir = client
    job_id = _job_with_traces(jobs_dir, [TRACE])

    payload = http.get(f"/api/jobs/{job_id}/visualizer-files").get_json()

    assert payload["model3d"]["wall_traces"] == [TRACE]
    assert payload["model3d"]["warnings"] == []


def test_visualizer_files_route_drops_malformed_traces_with_a_warning(client):
    """A bad overlay entry must not cost the reader the whole 3D model."""
    http, jobs_dir = client
    job_id = _job_with_traces(
        jobs_dir,
        [
            TRACE,
            "not a trace",
            {"face": "east wall", "surface": SURFACE_L1, "points": []},
            {"face": "", "surface": SURFACE_L1, "points": TRACE["points"]},
            {
                "face": "east wall",
                "surface": SURFACE_L1,
                "points": [[0.0, 3.0], [1.0, 3.0, 99.0]],
            },
        ],
    )

    payload = http.get(f"/api/jobs/{job_id}/visualizer-files").get_json()
    model3d = payload["model3d"]

    assert model3d["wall_traces"] == [TRACE]
    assert any("wall trace" in warning for warning in model3d["warnings"])
    assert len(model3d["surfaces"]) == 1


def test_visualizer_files_route_omits_wall_traces_when_absent(client):
    """Models built before this feature keep their exact payload shape."""
    http, jobs_dir = client
    job_id = _job_with_traces(jobs_dir, None)

    model3d = http.get(f"/api/jobs/{job_id}/visualizer-files").get_json()["model3d"]

    assert "wall_traces" not in model3d
    assert model3d["warnings"] == []


def test_existing_manifest_keys_are_untouched(manifest):
    """Additive only: the keys the viewer already reads keep their shape."""
    assert manifest["schema_version"] == 2
    assert manifest["kind"] == "gempy-surface-model"
    assert manifest["coordinate_system"] == {"units": "m", "up_axis": "Z"}
    assert manifest["surfaces"] == []
    assert manifest["lith_block_path"] == "trench_model_lith_block.npz"
    assert manifest["volume"]["shape"] == [2, 2, 1]
    assert manifest["single_face_note"] is None
