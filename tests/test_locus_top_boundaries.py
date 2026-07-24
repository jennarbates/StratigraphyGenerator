import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from backend.routes.manual import Calibration, _build_fieldwall
from pipeline.assign_markers import _assemble
from pipeline.convert_coords import fieldwall_to_profiles


@pytest.fixture
def calibration():
    return Calibration(
        origin_x=0,
        origin_y=0,
        ux=1,
        uy=0,
        vx=0,
        vy=1,
        px_per_m=10,
        ref_x=10,
        ref_y=0,
    )


def _manual_payload(include_base=True):
    boundaries = [
        # Deliberately submitted out of vertical order: the backend must sort
        # locus tops by their geometry without changing which locus owns one.
        {"kind": "top", "name": "2", "points": [[0, 20], [10, 20]]},
        {"kind": "top", "name": "1", "points": [[0, 10], [10, 10]]},
    ]
    if include_base:
        boundaries.append(
            {"kind": "base", "name": None, "points": [[0, 30], [10, 30]]}
        )
    return {
        "boundaries": boundaries,
        "loci": [
            {"locusNumber": "1", "munsellRaw": "10YR 5/3"},
            {"locusNumber": "2", "munsellRaw": "10YR 4/2"},
        ],
        "features": [],
        "square_cm": 20,
        "trenchLabel": "T104",
        "faceLabel": "south",
    }


def test_manual_fieldwall_uses_each_named_line_as_that_locus_top(calibration):
    data, warnings = _build_fieldwall(_manual_payload(), calibration, None)

    assert [layer["locusNumber"] for layer in data["layers"]] == ["1", "2"]
    locus_1, locus_2 = data["layers"]

    assert [point["depthMeters"] for point in locus_1["topBoundary"]] == [1.0, 1.0]
    assert locus_1["bottomBoundary"] == locus_2["topBoundary"]
    assert [point["depthMeters"] for point in locus_2["topBoundary"]] == [2.0, 2.0]
    assert [point["depthMeters"] for point in locus_2["bottomBoundary"]] == [3.0, 3.0]
    assert "Locus top boundaries were reordered" in " ".join(warnings)


def test_manual_fieldwall_requires_a_final_base(calibration):
    with pytest.raises(ValueError, match="final bottom line"):
        _build_fieldwall(_manual_payload(include_base=False), calibration, None)


def test_marker_assembly_does_not_shift_locus_names_down_one_line():
    markers = [
        {"id": 0, "x_m": 0.0, "depth_m": 1.0},
        {"id": 1, "x_m": 1.0, "depth_m": 1.0},
        {"id": 2, "x_m": 0.0, "depth_m": 2.0},
        {"id": 3, "x_m": 1.0, "depth_m": 2.0},
        {"id": 4, "x_m": 0.0, "depth_m": 3.0},
        {"id": 5, "x_m": 1.0, "depth_m": 3.0},
    ]
    result = {
        "loci": [
            {"locusNumber": "1", "munsell": None},
            {"locusNumber": "2", "munsell": None},
        ],
        "assignments": [
            {"markerId": 0, "kind": "top", "locusNumber": "1"},
            {"markerId": 1, "kind": "top", "locusNumber": "1"},
            {"markerId": 2, "kind": "top", "locusNumber": "2"},
            {"markerId": 3, "kind": "top", "locusNumber": "2"},
            {"markerId": 4, "kind": "base", "locusNumber": None},
            {"markerId": 5, "kind": "base", "locusNumber": None},
        ],
    }

    profile, warnings = _assemble(markers, result)

    assert not warnings
    locus_1, locus_2 = profile["layers"]
    assert locus_1["topBoundary"][0]["depthMeters"] == 1.0
    assert locus_1["bottomBoundary"] == locus_2["topBoundary"]
    assert locus_2["bottomBoundary"][0]["depthMeters"] == 3.0


def test_fieldwall_conversion_models_the_locus_top_not_its_bottom(calibration):
    data, _ = _build_fieldwall(_manual_payload(), calibration, None)

    adapted, notes = fieldwall_to_profiles(data)

    assert not notes
    layers = adapted["trenchProfiles"][0]["layers"]
    assert layers[0]["bottomBoundary"][0]["depthMeters"] == 1.0
    assert layers[1]["bottomBoundary"][0]["depthMeters"] == 2.0
