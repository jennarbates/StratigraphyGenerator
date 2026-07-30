import io
import json
from pathlib import Path

import pytest
from PIL import Image


from backend import create_app
from backend import jobs as backend_jobs
from backend.routes import jobs as jobs_routes
from backend.routes import text_metadata


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(backend_jobs, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(jobs_routes, "JOBS_DIR", jobs_dir)

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client(), jobs_dir


def _fake_png():
    image_bytes = io.BytesIO()
    Image.new("RGB", (120, 100), "white").save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes


def _candidate_payload():
    def candidate(raw, proposed, confidence="high"):
        return {
            "raw": raw,
            "proposed": proposed,
            "confidence": confidence,
            "bbox": [100, 100, 300, 200],
            "notes": None,
        }

    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "document": {
            "trenchLabel": candidate("T 104", "T104"),
            "faceLabel": candidate("South baulk", "South baulk"),
            "date": candidate("27 VII 2026", "27 July 2026"),
            "gridSquareCm": candidate("20 cm", 20.0),
            "northArrowPresent": candidate("north arrow", True),
            "illustrators": [candidate("A. Recorder", "A. Recorder")],
            "gridTiePoints": [candidate("194 m", "194 m")],
            "marginalia": [
                candidate(
                    "Section continued on reverse",
                    "Section continued on reverse",
                    "medium",
                )
            ],
            "otherText": [
                candidate("Datum checked 08:30", "Datum checked at 08:30")
            ],
        },
        "loci": [
            {
                "locusNumber": candidate("104Z", "1042", "medium"),
                "munsellRaw": candidate("10 yr 5 / 3", "10YR 5/3", "medium"),
                "description": candidate(
                    "brown silty soil",
                    "brown silty soil",
                ),
            },
            {
                "locusNumber": candidate("1043", "1043"),
                "munsellRaw": candidate("?", None, "low"),
                "description": candidate("compact fill", "compact fill"),
            },
        ],
    }


def _verified_payload():
    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "reviewCompleted": True,
        "document": {
            "trenchLabel": "T104",
            "faceLabel": "South baulk",
            "date": "27 July 2026",
            "gridSquareCm": 20.0,
            "northArrowPresent": True,
            "illustrators": ["A. Recorder"],
            "gridTiePoints": ["194 m"],
            "marginalia": ["Section continued on reverse"],
            "otherText": ["Datum checked at 08:30"],
        },
        "loci": [
            {
                "locusNumber": "1042",
                "munsellRaw": "10YR 5/3",
                "description": "brown silty soil corrected by reviewer",
            },
            {
                "locusNumber": "1043",
                "munsellRaw": None,
                "description": "compact fill",
            },
        ],
        "audit": [
            {
                "fieldPath": "loci.0.locusNumber",
                "raw": "104Z",
                "proposed": "1042",
                "final": "1042",
                "status": "corrected",
                "confidence": "medium",
                "bbox": [100, 100, 300, 200],
            },
            {
                "fieldPath": "loci.1.munsellRaw",
                "raw": "?",
                "proposed": None,
                "final": None,
                "status": "unreadable",
                "confidence": "low",
                "bbox": [100, 100, 300, 200],
            },
        ],
    }


def _manual_payload(verified):
    return {
        "image": "scan",
        "calibration": {
            "origin_px": [10, 10],
            "ref_px": [110, 10],
            "lowest_px": [10, 90],
            "ref_meters": 1,
        },
        "boundaries": [
            {"kind": "top", "name": "1042", "points": [[10, 30], [110, 30]]},
            {"kind": "top", "name": "1043", "points": [[10, 50], [110, 50]]},
            {"kind": "top", "name": "1099", "points": [[10, 70], [110, 70]]},
            {"kind": "base", "name": None, "points": [[10, 90], [110, 90]]},
        ],
        "features": [],
        "trenchLabel": "T104 manual correction",
        "faceLabel": "West face manual correction",
        "square_cm": 25,
        "loci": [
            {
                "locusNumber": "1042",
                "munsellRaw": "7.5YR 4/4",
                "description": None,
            },
            {
                "locusNumber": "1043",
                "munsellRaw": None,
                "description": None,
            },
            {
                "locusNumber": "1099",
                "munsellRaw": "5YR 3/2",
                "description": "missed locus added manually",
            },
        ],
        "verifiedText": {
            "document": verified["document"],
            "loci": verified["loci"],
            "audit": verified["audit"],
        },
    }


def test_text_autofill_to_manual_fieldwall_json_is_network_free(
    workflow,
    monkeypatch,
):
    client, jobs_dir = workflow
    candidates = _candidate_payload()
    verified = _verified_payload()
    api_key = "test-key-that-must-never-reach-job-files"

    create_response = client.post("/api/jobs")
    assert create_response.status_code == 200
    job_id = create_response.get_json()["job_id"]
    job_dir = jobs_dir / job_id

    upload_response = client.post(
        f"/api/jobs/{job_id}/scan",
        data={
            "sheet_type": "fieldwall",
            "file": (_fake_png(), "field-wall.png"),
        },
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 200
    assert (job_dir / "01_scan" / "field-wall.png").is_file()

    def fake_run_fieldwall_extraction(
        image_path,
        square_cm,
        output_path,
        supplied_api_key,
        max_output_tokens=65_536,
        progress_cb=None,
    ):
        assert Path(image_path) == job_dir / "01_scan" / "field-wall.png"
        assert square_cm == 20
        assert supplied_api_key == api_key
        raw_json = json.dumps({"gridSquareCm": square_cm, "layers": []})
        Path(output_path).write_text(
            raw_json,
            encoding="utf-8",
        )
        return raw_json, None

    def fake_candidates_from_extraction(raw_json, output_path):
        assert json.loads(raw_json)["gridSquareCm"] == 20
        Path(output_path).write_text(
            json.dumps(candidates, indent=2),
            encoding="utf-8",
        )
        return candidates

    def run_synchronously(function, *args, **kwargs):
        function(*args, **kwargs)
        return "network-free-text-task"

    monkeypatch.setattr(
        text_metadata.p_extract_fieldwall,
        "run_extraction",
        fake_run_fieldwall_extraction,
    )
    monkeypatch.setattr(
        text_metadata.p_extract_text,
        "candidates_from_fieldwall_extraction",
        fake_candidates_from_extraction,
    )
    monkeypatch.setattr(text_metadata, "start_task", run_synchronously)

    extraction_response = client.post(
        f"/api/jobs/{job_id}/text-extraction",
        json={"api_key": api_key, "square_cm": 20},
    )
    assert extraction_response.status_code == 200
    assert extraction_response.get_json() == {
        "task_id": "network-free-text-task"
    }

    candidates_path = job_dir / "03_extraction" / "text_candidates.json"
    assert json.loads(candidates_path.read_text(encoding="utf-8")) == candidates

    verification_response = client.post(
        f"/api/jobs/{job_id}/text-verification",
        json=verified,
    )
    assert verification_response.status_code == 200
    assert verification_response.get_json() == verified

    verified_path = job_dir / "03_extraction" / "verified_text.json"
    assert candidates_path != verified_path
    assert json.loads(candidates_path.read_text(encoding="utf-8")) == candidates
    assert json.loads(verified_path.read_text(encoding="utf-8")) == verified

    manual_response = client.post(
        f"/api/jobs/{job_id}/boundaries/manual",
        json=_manual_payload(verified),
    )
    assert manual_response.status_code == 200

    fieldwall_path = job_dir / "03_extraction" / "field_wall_manual.json"
    fieldwall = json.loads(fieldwall_path.read_text(encoding="utf-8"))

    assert fieldwall["trenchLabel"] == "T104 manual correction"
    assert fieldwall["faceLabel"] == "West face manual correction"
    assert fieldwall["gridSquareCm"] == 25
    assert fieldwall["illustrators"] == ["A. Recorder"]
    assert fieldwall["date"] == "27 July 2026"
    assert fieldwall["northArrowPresent"] is True
    assert fieldwall["gridTiePoints"] == [
        {"rawText": "194 m", "approxXMeters": None}
    ]
    assert "Section continued on reverse" in fieldwall["marginalia"]
    assert "Other readable text: Datum checked at 08:30" in fieldwall["marginalia"]

    loci = {locus["locusNumber"]: locus for locus in fieldwall["loci"]}
    assert loci["1042"] == {
        "locusNumber": "1042",
        "munsell": {"raw": "7.5YR 4/4", "colorName": None},
        "description": "brown silty soil corrected by reviewer",
        "confidence": "human-verified",
    }
    assert loci["1043"] == {
        "locusNumber": "1043",
        "munsell": None,
        "description": "compact fill",
        "confidence": "human-verified",
    }
    assert loci["1099"] == {
        "locusNumber": "1099",
        "munsell": {"raw": "5YR 3/2", "colorName": None},
        "description": "missed locus added manually",
        "confidence": "human-entered",
    }

    source_pixels = [
        point["sourcePixel"]
        for layer in fieldwall["layers"]
        for point in layer["topBoundary"]
    ]
    assert source_pixels == [
        [10.0, 30.0],
        [110.0, 30.0],
        [10.0, 50.0],
        [110.0, 50.0],
        [10.0, 70.0],
        [110.0, 70.0],
    ]
    assert [
        point["sourcePixel"]
        for point in fieldwall["layers"][-1]["bottomBoundary"]
    ] == [[10.0, 90.0], [110.0, 90.0]]
    assert [
        [point["xMeters"], point["depthMeters"]]
        for point in fieldwall["layers"][0]["topBoundary"]
    ] == [[0.0, 0.2], [1.0, 0.2]]

    assert candidates_path.is_file()
    assert verified_path.is_file()
    assert fieldwall_path.is_file()
    assert candidates_path.read_bytes() != verified_path.read_bytes()
    assert all(
        api_key not in path.read_text(encoding="utf-8")
        for path in job_dir.rglob("*")
        if path.is_file() and path.suffix in {".json", ".txt"}
    )
