import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from backend.routes.manual import (
    Calibration,
    _build_fieldwall,
    _build_illustrator,
    _converted_points,
)


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


def test_fieldwall_bottom_boundary_contains_matching_source_pixels(calibration):
    data, _ = _build_fieldwall(_fieldwall_payload(), calibration, None)

    assert [point["sourcePixel"] for point in data["layers"][0]["bottomBoundary"]] == [
        [100.25, 300.5],
        [180.25, 300.5],
    ]


def test_fieldwall_top_boundary_contains_matching_source_pixels(calibration):
    data, _ = _build_fieldwall(_fieldwall_payload(), calibration, None)

    assert [point["sourcePixel"] for point in data["layers"][0]["topBoundary"]] == [
        [100.25, 210.5],
        [180.25, 210.5],
    ]


def test_illustrator_bottom_boundary_contains_matching_source_pixels(calibration):
    data, _ = _build_illustrator(_illustrator_payload(), calibration, None)

    boundary = data["trenchProfiles"][0]["layers"][0]["bottomBoundary"]
    assert [point["sourcePixel"] for point in boundary] == [
        [100.25, 300.5],
        [180.25, 300.5],
    ]


def test_illustrator_top_boundary_contains_matching_source_pixels(calibration):
    data, _ = _build_illustrator(_illustrator_payload(), calibration, None)

    boundary = data["trenchProfiles"][0]["layers"][0]["topBoundary"]
    assert [point["sourcePixel"] for point in boundary] == [
        [100.25, 210.5],
        [180.25, 210.5],
    ]


def test_fieldwall_feature_preserves_source_pixel_order(calibration):
    payload = _fieldwall_payload()
    data, _ = _build_fieldwall(payload, calibration, None)

    feature = data["layers"][0]["featuresInLayer"][0]
    assert [point["sourcePixel"] for point in feature["shapePoints"]] == (
        payload["features"][0]["points"]
    )


def test_illustrator_feature_preserves_source_pixel_order(calibration):
    payload = _illustrator_payload()
    data, _ = _build_illustrator(payload, calibration, None)

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
    data, warnings = _build_illustrator(
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
    data, _ = _build_fieldwall(_fieldwall_payload(), calibration, None)

    restored = json.loads(json.dumps(data))

    assert restored["layers"][0]["topBoundary"][0]["sourcePixel"] == [100.25, 210.5]
    assert (
        restored["layers"][0]["featuresInLayer"][0]["shapePoints"][0]["sourcePixel"]
        == [140.125, 250.625]
    )
