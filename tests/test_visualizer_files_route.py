import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

import backend.jobs as jobs
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(jobs, "JOBS_DIR", jobs_dir)
    app.config.update(TESTING=True)
    return app.test_client()


def _manual_calibration():
    return {
        "kind": "manual",
        "origin_px": [100.25, 200.5],
        "ref_px": [200.25, 200.5],
        "lowest_px": [100.25, 300.5],
        "ref_meters": 1.0,
        "px_per_m": 100.0,
    }


def _marker_calibration():
    return {
        "kind": "manual",
        "origin_px": [100, 200],
        "ref_px": [500, 195],
        "lowest_px": [100, 650.0],
        "ref_meters": 4.0,
        "px_per_m": 100.5,
    }


def _write_meta(job_dir, meta):
    (job_dir / "meta.json").write_text(json.dumps(meta))


def test_manual_calibration_surfaced_under_calibration_key(client):
    job_id = "manual-calibration"
    job_dir = jobs.JOBS_DIR / job_id
    job_dir.mkdir()
    image_path = job_dir / "manual.png"
    image_path.write_bytes(b"image")
    calibration = _manual_calibration()
    _write_meta(job_dir, {
        "manual_calibration": calibration,
        "manual_image_path": str(image_path),
    })

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["calibration"] == calibration
    assert "marker_calib" not in payload
    assert (
        payload["image_url"]
        == f"/api/jobs/{job_id}/file?path=manual.png"
    )


def test_manual_calibration_omitted_without_matching_image(client):
    job_id = "missing-manual-image"
    job_dir = jobs.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_meta(job_dir, {
        "manual_calibration": _manual_calibration(),
        "manual_image_path": str(job_dir / "missing.png"),
    })

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert "calibration" not in payload
    assert "image_url" not in payload


def test_no_calibration_at_all_still_serves_image(client):
    job_id = "scan-without-calibration"
    job_dir = jobs.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = job_dir / "scan.png"
    scan_path.write_bytes(b"scan")
    _write_meta(job_dir, {"scan_path": str(scan_path)})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert (
        payload["image_url"]
        == f"/api/jobs/{job_id}/file?path=scan.png"
    )
    assert "calibration" not in payload


def test_marker_calib_surfaced_under_calibration_key(client):
    job_id = "marker-calibration"
    job_dir = jobs.JOBS_DIR / job_id
    extraction_dir = job_dir / "03_extraction"
    extraction_dir.mkdir(parents=True)
    rotated_path = extraction_dir / "marker_source_rotated.png"
    rotated_path.write_bytes(b"image")
    calibration = _marker_calibration()
    _write_meta(job_dir, {"marker_calib": calibration})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["calibration"] == calibration
    assert "marker_calib" not in payload
    assert (
        payload["image_url"]
        == f"/api/jobs/{job_id}/file?"
        "path=03_extraction/marker_source_rotated.png"
    )


def test_marker_calib_ignored_without_rotated_image(client):
    job_id = "marker-calibration-without-rotated-image"
    job_dir = jobs.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = job_dir / "scan.png"
    scan_path.write_bytes(b"scan")
    _write_meta(job_dir, {
        "marker_calib": _marker_calibration(),
        "scan_path": str(scan_path),
    })

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert (
        payload["image_url"]
        == f"/api/jobs/{job_id}/file?path=scan.png"
    )
    assert "calibration" not in payload
    assert "marker_calib" not in payload
