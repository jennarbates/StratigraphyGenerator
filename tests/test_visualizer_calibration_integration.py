# Manual verification checklist:
# 1. Load a job calibrated via manual tracing in the browser visualizer.
#    Confirm "Align overlay to drawing" is disabled and the hint reads
#    "Exact source-image alignment is active."
# 2. Load a job calibrated via CV marker detection. Confirm the same disabled
#    align control and exact-calibration hint.
# 3. Load a job with no calibration. Confirm the align control is enabled,
#    drag a box over the drawing, and verify that the overlay sits flush with
#    every side of the dragged box, with no visible inset gap.

import json

import pytest


import backend.jobs as jobs
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(jobs, "JOBS_DIR", jobs_dir)
    app.config.update(TESTING=True)
    return app.test_client()


def _write_meta(job_dir, meta):
    (job_dir / "meta.json").write_text(json.dumps(meta))


def test_manual_route_calibration_flows_to_visualizer(client):
    job_id = "manual-calibration-integration"
    job_dir = jobs.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = job_dir / "scan.png"
    scan_path.write_bytes(b"scan")
    _write_meta(job_dir, {
        "scan_path": str(scan_path),
        "sheet_type": "illustrator",
    })

    manual_response = client.post(
        f"/api/jobs/{job_id}/boundaries/manual",
        json={
            "boundaries": [
                {
                    "kind": "surface",
                    "points": [[100.25, 210.5], [180.25, 210.5]],
                },
                {
                    "kind": "bottom",
                    "name": "soil",
                    "points": [[100.25, 300.5], [180.25, 300.5]],
                },
            ],
            "features": [],
            "calibration": {
                "origin_px": [100.25, 200.5],
                "ref_px": [200.25, 200.5],
                "lowest_px": [100.25, 300.5],
                "ref_meters": 1.0,
            },
        },
    )

    assert manual_response.status_code == 200

    visualizer_response = client.get(
        f"/api/jobs/{job_id}/visualizer-files",
    )

    assert visualizer_response.status_code == 200
    assert visualizer_response.get_json()["calibration"]["kind"] == "manual"


def test_marker_calibration_flows_to_visualizer(client):
    job_id = "marker-calibration-integration"
    job_dir = jobs.JOBS_DIR / job_id
    extraction_dir = job_dir / "03_extraction"
    extraction_dir.mkdir(parents=True)
    rotated_path = extraction_dir / "marker_source_rotated.png"
    rotated_path.write_bytes(b"image")
    _write_meta(job_dir, {
        "marker_calib": {
            "kind": "manual",
            "origin_px": [100, 200],
            "ref_px": [500, 195],
            "lowest_px": [100, 650.0],
            "ref_meters": 4.0,
            "px_per_m": 100.5,
        },
    })

    visualizer_response = client.get(
        f"/api/jobs/{job_id}/visualizer-files",
    )

    assert visualizer_response.status_code == 200
    assert visualizer_response.get_json()["calibration"]["kind"] == "manual"
