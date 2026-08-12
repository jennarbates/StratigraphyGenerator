import json
from types import SimpleNamespace

import pytest

import storage
from backend import create_app
from pipeline.extract_fieldwall import FieldWallProfile


@pytest.fixture
def route_context(tmp_path, monkeypatch):
    jobs_dir = storage.JOBS_DIR
    app = create_app()
    app.config.update(TESTING=True)
    return SimpleNamespace(client=app.test_client(), jobs_dir=jobs_dir)


def _create_fieldwall_job(route_context):
    directory = route_context.jobs_dir / "verified-manual-job"
    (directory / "03_extraction").mkdir(parents=True)
    scan_path = directory / "01_scan" / "scan.png"
    scan_path.parent.mkdir()
    scan_path.write_bytes(b"scan")
    (directory / "meta.json").write_text(
        json.dumps(
            {
                "job_id": "verified-manual-job",
                "sheet_type": "fieldwall",
                "scan_path": str(scan_path),
            }
        ),
        encoding="utf-8",
    )
    return directory


def _manual_payload():
    return {
        "image": "scan",
        "calibration": {
            "origin_px": [100, 100],
            "ref_px": [200, 100],
            "lowest_px": [100, 500],
            "ref_meters": 1,
        },
        "boundaries": [
            {"kind": "top", "name": "1042", "points": [[100, 150], [200, 150]]},
            {"kind": "top", "name": "1043", "points": [[100, 250], [200, 250]]},
            {"kind": "top", "name": "1099", "points": [[100, 350], [200, 350]]},
            {"kind": "base", "name": None, "points": [[100, 450], [200, 450]]},
        ],
        "features": [],
        "trenchLabel": "T104 corrected in draw",
        "faceLabel": "West face corrected in draw",
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
                "description": "manually added locus",
            },
        ],
        "verifiedText": {
            "document": {
                "trenchLabel": "T104 proposed",
                "faceLabel": "South face proposed",
                "gridSquareCm": 20,
                "illustrators": ["Lizzy Bruening", "Heather Fusco"],
                "date": "27 July 2026",
                "northArrowPresent": True,
                "gridTiePoints": ["194 m", "190 m"],
                "marginalia": ["Section continued on reverse"],
                "otherText": ["Datum checked at 08:30"],
            },
            "loci": [
                {
                    "locusNumber": "1042",
                    "munsellRaw": "10YR 5/3",
                    "description": "verified upper fill",
                },
                {
                    "locusNumber": "1043",
                    "munsellRaw": "10YR 4/2",
                    "description": None,
                },
            ],
            "audit": [
                {
                    "fieldPath": "loci.0.munsellRaw",
                    "raw": "10 yr 5 / 3",
                    "proposed": "10YR 5/3",
                    "final": "10YR 5/3",
                    "status": "accepted",
                    "confidence": "high",
                    "bbox": [100, 100, 200, 200],
                }
            ],
        },
    }


def test_verified_text_survives_manual_route_and_output_validates(route_context):
    directory = _create_fieldwall_job(route_context)
    response = route_context.client.post(
        "/api/jobs/verified-manual-job/boundaries/manual",
        json=_manual_payload(),
    )

    assert response.status_code == 200
    data = json.loads(response.get_json()["raw_json"])
    assert data["trenchLabel"] == "T104 corrected in draw"
    assert data["faceLabel"] == "West face corrected in draw"
    assert data["gridSquareCm"] == 25
    assert data["illustrators"] == ["Lizzy Bruening", "Heather Fusco"]
    assert data["date"] == "27 July 2026"
    assert data["northArrowPresent"] is True
    assert [tie["rawText"] for tie in data["gridTiePoints"]] == ["194 m", "190 m"]
    assert "Section continued on reverse" in data["marginalia"]
    assert "Other readable text: Datum checked at 08:30" in data["marginalia"]
    assert data["marginalia"][0] == (
        "Boundary and feature geometry was manually traced by a user."
    )

    loci = {locus["locusNumber"]: locus for locus in data["loci"]}
    assert loci["1042"]["munsell"]["raw"] == "7.5YR 4/4"
    assert loci["1042"]["description"] == "verified upper fill"
    assert loci["1042"]["confidence"] == "human-verified"
    assert loci["1043"]["munsell"]["raw"] == "10YR 4/2"
    assert loci["1043"]["description"] is None
    assert loci["1043"]["confidence"] == "human-verified"
    assert loci["1099"] == {
        "locusNumber": "1099",
        "munsell": {"raw": "5YR 3/2", "colorName": None},
        "description": "manually added locus",
        "confidence": "human-entered",
    }

    assert [
        point["sourcePixel"]
        for layer in data["layers"]
        for point in layer["topBoundary"]
    ] == [
        [100.0, 150.0],
        [200.0, 150.0],
        [100.0, 250.0],
        [200.0, 250.0],
        [100.0, 350.0],
        [200.0, 350.0],
    ]
    FieldWallProfile.model_validate(data)

    output_path = directory / "03_extraction" / "field_wall_manual.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == data
