import copy
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline.validator import validate


@pytest.fixture
def fabricated_geometry():
    x_coordinates = [0.0, 0.25, 0.5, 0.75, 1.0]
    upper_depths = [0.4, 0.45, 0.42, 0.48, 0.44]
    lower_depths = [depth + 0.4 for depth in upper_depths]

    def boundary(depths):
        return [
            {
                "xCoordinateMeters": x,
                "yCoordinateMeters": depth,
                "confidence": "certain",
            }
            for x, depth in zip(x_coordinates, depths)
        ]

    return {
        "source": "extraction",
        "trenchProfiles": [
            {
                "face": "T104 field wall",
                "layers": [
                    {
                        "layerName": "Layer 1",
                        "topBoundary": boundary([0.0] * len(x_coordinates)),
                        "bottomBoundary": boundary(upper_depths),
                    },
                    {
                        "layerName": "Layer 2",
                        "topBoundary": boundary(upper_depths),
                        "bottomBoundary": boundary(lower_depths),
                    },
                ],
            }
        ],
    }


def test_manual_editor_skips_evenly_spaced_vertices_warning(fabricated_geometry):
    fabricated_geometry["source"] = "manual_editor"

    report = validate(fabricated_geometry)

    assert not any("evenly spaced" in warning for warning in report.warnings)


def test_extraction_still_warns_about_evenly_spaced_vertices(fabricated_geometry):
    report = validate(fabricated_geometry)

    spacing_warnings = [
        warning for warning in report.warnings if "evenly spaced" in warning
    ]
    assert len(spacing_warnings) == 2


def test_copy_pasted_layers_warning_depends_on_source(fabricated_geometry):
    manual_geometry = copy.deepcopy(fabricated_geometry)
    manual_geometry["source"] = "manual_editor"

    manual_report = validate(manual_geometry)
    extraction_report = validate(fabricated_geometry)

    assert not any(
        "identical boundary shapes" in warning
        for warning in manual_report.warnings
    )
    assert sum(
        "identical boundary shapes" in warning
        for warning in extraction_report.warnings
    ) == 1


def test_manual_editor_still_reports_unrelated_bad_geometry(fabricated_geometry):
    fabricated_geometry["source"] = "manual_editor"
    fabricated_geometry["trenchProfiles"][0]["layers"][0]["bottomBoundary"][0][
        "yCoordinateMeters"
    ] = -0.1

    report = validate(fabricated_geometry)

    assert any("negative depth" in error for error in report.errors)
