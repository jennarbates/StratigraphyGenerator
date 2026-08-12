import json

import pytest

import storage
from app import app
from pipeline.manual_extraction import (
    Calibration,
    _converted_points,
    build_fieldwall,
    build_illustrator,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def calibration():
    return Calibration(
        origin_x=100.25,
        origin_y=200.5,
        ux=1.0,
        uy=0.0,
        vx=0.0,
        vy=1.0,
        px_per_m=100.0,
        ref_x=200.25,
        ref_y=200.5,
    )


def _fieldwall_payload():
    return {
        "boundaries": [
            {
                "kind": "top",
                "name": "1042",
                "points": [[180.25, 210.5], [100.25, 210.5]],
            },
            {
                "kind": "base",
                "points": [[180.25, 300.5], [100.25, 300.5]],
            },
        ],
        "loci": [{"locusNumber": "1042"}],
        "features": [
            {
                "feature_type": "stone",
                "points": [
                    [140.125, 250.625],
                    [120.25, 240.5],
                    [160.75, 245.875],
                ],
            }
        ],
    }


def _illustrator_payload(include_surface=True):
    boundaries = [
        {
            "kind": "bottom",
            "name": "soil",
            "points": [[180.25, 300.5], [100.25, 300.5]],
        }
    ]
    if include_surface:
        boundaries.insert(
            0,
            {
                "kind": "surface",
                "points": [[180.25, 210.5], [100.25, 210.5]],
            },
        )
    return {
        "boundaries": boundaries,
        "features": [
            {
                "feature_type": "stone",
                "points": [
                    [140.125, 250.625],
                    [120.25, 240.5],
                    [160.75, 245.875],
                ],
            }
        ],
    }


def _manual_route_payload():
    return {
        **_illustrator_payload(),
        "calibration": {
            "origin_px": [100.25, 200.5],
            "ref_px": [200.25, 200.5],
            "lowest_px": [100.25, 300.5],
            "ref_meters": 1.0,
        },
    }


def test_manual_calibration_includes_kind(client):
    job_id = "manual-calibration-kind"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = job_dir / "scan.png"
    scan_path.write_bytes(b"scan")
    (job_dir / "meta.json").write_text(
        json.dumps(
            {
                "scan_path": str(scan_path),
                "sheet_type": "illustrator",
            }
        )
    )

    response = client.post(
        f"/api/jobs/{job_id}/boundaries/manual",
        json=_manual_route_payload(),
    )

    assert response.status_code == 200
    meta = json.loads((job_dir / "meta.json").read_text())
    assert meta["manual_calibration"]["kind"] == "manual"


def test_fieldwall_bottom_boundary_contains_matching_source_pixels(calibration):
    data, _ = build_fieldwall(_fieldwall_payload(), calibration, None)

    assert [point["sourcePixel"] for point in data["layers"][0]["bottomBoundary"]] == [
        [100.25, 300.5],
        [180.25, 300.5],
    ]


def test_fieldwall_top_boundary_contains_matching_source_pixels(calibration):
    data, _ = build_fieldwall(_fieldwall_payload(), calibration, None)

    assert [point["sourcePixel"] for point in data["layers"][0]["topBoundary"]] == [
        [100.25, 210.5],
        [180.25, 210.5],
    ]


def test_illustrator_bottom_boundary_contains_matching_source_pixels(calibration):
    data, _ = build_illustrator(_illustrator_payload(), calibration, None)

    boundary = data["trenchProfiles"][0]["layers"][0]["bottomBoundary"]
    assert [point["sourcePixel"] for point in boundary] == [
        [100.25, 300.5],
        [180.25, 300.5],
    ]


def test_illustrator_top_boundary_contains_matching_source_pixels(calibration):
    data, _ = build_illustrator(_illustrator_payload(), calibration, None)

    boundary = data["trenchProfiles"][0]["layers"][0]["topBoundary"]
    assert [point["sourcePixel"] for point in boundary] == [
        [100.25, 210.5],
        [180.25, 210.5],
    ]


def test_fieldwall_feature_preserves_source_pixel_order(calibration):
    payload = _fieldwall_payload()
    data, _ = build_fieldwall(payload, calibration, None)

    feature = data["layers"][0]["featuresInLayer"][0]
    assert [point["sourcePixel"] for point in feature["shapePoints"]] == (
        payload["features"][0]["points"]
    )


def test_illustrator_feature_preserves_source_pixel_order(calibration):
    payload = _illustrator_payload()
    data, _ = build_illustrator(payload, calibration, None)

    feature = data["trenchProfiles"][0]["layers"][0]["featuresInLayer"][0]
    assert [point["sourcePixel"] for point in feature["shapePoints"]] == (
        payload["features"][0]["points"]
    )


def test_sorted_boundary_keeps_source_pixel_attached_to_metre_point(calibration):
    converted = _converted_points(
        calibration,
        [[180.25, 240.5], [120.25, 260.5]],
        fieldwall=False,
    )

    assert converted == [
        {
            "xCoordinateMeters": 0.2,
            "yCoordinateMeters": 0.6,
            "confidence": "human-traced",
            "sourcePixel": [120.25, 260.5],
        },
        {
            "xCoordinateMeters": 0.8,
            "yCoordinateMeters": 0.4,
            "confidence": "human-traced",
            "sourcePixel": [180.25, 240.5],
        },
    ]


def test_fallback_surface_stores_origin_and_reference_source_pixels(calibration):
    data, warnings = build_illustrator(
        _illustrator_payload(include_surface=False),
        calibration,
        None,
    )

    surface = data["trenchProfiles"][0]["layers"][0]["topBoundary"]
    assert [point["sourcePixel"] for point in surface] == [
        [calibration.origin_x, calibration.origin_y],
        [calibration.ref_x, calibration.ref_y],
    ]
    assert "top calibration edge was used" in " ".join(warnings)


def test_existing_expected_metre_coordinates_do_not_change():
    calibration = Calibration(
        origin_x=1053.6,
        origin_y=1468.8,
        ux=1.0,
        uy=0.0,
        vx=0.0,
        vy=1.0,
        px_per_m=1000.0,
        ref_x=2053.6,
        ref_y=1468.8,
    )

    fieldwall = _converted_points(calibration, [[2250, 1900]], fieldwall=True)
    illustrator = _converted_points(calibration, [[2250, 1900]], fieldwall=False)

    assert (fieldwall[0]["xMeters"], fieldwall[0]["depthMeters"]) == (1.1964, 0.4312)
    assert (
        illustrator[0]["xCoordinateMeters"],
        illustrator[0]["yCoordinateMeters"],
    ) == (1.1964, 0.4312)


def test_serialized_json_round_trips_source_pixel(calibration):
    data, _ = build_fieldwall(_fieldwall_payload(), calibration, None)

    restored = json.loads(json.dumps(data))

    assert restored["layers"][0]["topBoundary"][0]["sourcePixel"] == [100.25, 210.5]
    assert restored["layers"][0]["featuresInLayer"][0]["shapePoints"][0][
        "sourcePixel"
    ] == [140.125, 250.625]


def test_verified_text_is_merged_without_replacing_manual_draw_values(calibration):
    payload = _fieldwall_payload()
    payload.update(
        {
            "trenchLabel": "Manual trench",
            "faceLabel": "Manual face",
            "square_cm": 25,
            "loci": [
                {
                    "locusNumber": "1042",
                    "munsellRaw": "7.5YR 4/4",
                    "description": None,
                }
            ],
            "verifiedText": {
                "document": {
                    "trenchLabel": "Verified trench",
                    "faceLabel": "Verified face",
                    "gridSquareCm": 20,
                    "illustrators": ["A. Recorder", "B. Illustrator"],
                    "date": "15 July 2026",
                    "northArrowPresent": False,
                    "gridTiePoints": ["E 194", "E 190"],
                    "marginalia": ["Continued on reverse"],
                    "otherText": ["Scale checked by JB"],
                },
                "loci": [
                    {
                        "locusNumber": "1042",
                        "munsellRaw": "10YR 5/3",
                        "description": "brown silty soil",
                    }
                ],
                "audit": [],
            },
        }
    )

    data, _ = build_fieldwall(payload, calibration, None)

    assert data["trenchLabel"] == "Manual trench"
    assert data["faceLabel"] == "Manual face"
    assert data["gridSquareCm"] == 25
    assert data["illustrators"] == ["A. Recorder", "B. Illustrator"]
    assert data["date"] == "15 July 2026"
    assert data["northArrowPresent"] is False
    assert data["gridTiePoints"] == [
        {"rawText": "E 194", "approxXMeters": None},
        {"rawText": "E 190", "approxXMeters": None},
    ]
    assert data["loci"][0] == {
        "locusNumber": "1042",
        "munsell": {"raw": "7.5YR 4/4", "colorName": None},
        "description": "brown silty soil",
        "confidence": "human-verified",
    }
    assert "Continued on reverse" in data["marginalia"]
    assert "Other readable text: Scale checked by JB" in data["marginalia"]
    assert data["marginalia"][0] == (
        "Boundary and feature geometry was manually traced by a user."
    )


def test_manual_locus_not_present_in_verified_text_remains_human_entered(calibration):
    payload = _fieldwall_payload()
    payload["verifiedText"] = {
        "document": {},
        "loci": [
            {
                "locusNumber": "9999",
                "munsellRaw": "10YR 5/3",
                "description": None,
            }
        ],
        "audit": [],
    }

    data, _ = build_fieldwall(payload, calibration, None)

    assert data["loci"][0]["confidence"] == "human-entered"
    assert data["loci"][0]["munsell"] is None


def test_verified_draw_fields_are_used_when_manual_values_are_empty(calibration):
    payload = _fieldwall_payload()
    payload.update(
        {
            "trenchLabel": None,
            "faceLabel": "",
            "square_cm": None,
            "verifiedText": {
                "document": {
                    "trenchLabel": "Verified trench",
                    "faceLabel": "Verified face",
                    "gridSquareCm": 20,
                },
                "loci": [],
                "audit": [],
            },
        }
    )

    data, _ = build_fieldwall(payload, calibration, None)

    assert data["trenchLabel"] == "Verified trench"
    assert data["faceLabel"] == "Verified face"
    assert data["gridSquareCm"] == 20
