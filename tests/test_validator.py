import copy

import pytest

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
        "identical boundary shapes" in warning for warning in manual_report.warnings
    )
    assert (
        sum(
            "identical boundary shapes" in warning
            for warning in extraction_report.warnings
        )
        == 1
    )


def test_manual_editor_still_reports_unrelated_bad_geometry(fabricated_geometry):
    fabricated_geometry["source"] = "manual_editor"
    fabricated_geometry["trenchProfiles"][0]["layers"][0]["bottomBoundary"][0][
        "yCoordinateMeters"
    ] = -0.1

    report = validate(fabricated_geometry)

    assert any("negative depth" in error for error in report.errors)


# E4: a field sheet is checked as thoroughly as an illustrator sheet.
#
# The field path used to run through an adapter that kept neither features nor
# the real bottom line, so the feature, continuity and crossing checks had
# nothing to look at and passed in silence. Both mediums go through the
# canonical form now.


@pytest.fixture
def field_sheet_with_a_stray_feature():
    """A stone drawn well below the layer that is said to contain it."""
    return {
        "faceLabel": "N baulk",
        "loci": [{"locusNumber": "1"}, {"locusNumber": "2"}],
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [
                    {"xMeters": 0.0, "depthMeters": 0.0},
                    {"xMeters": 1.0, "depthMeters": 0.03},
                ],
                "bottomBoundary": [
                    {"xMeters": 0.0, "depthMeters": 0.30},
                    {"xMeters": 1.0, "depthMeters": 0.34},
                ],
                "featuresInLayer": [
                    {
                        "feature": "stone",
                        "shapePoints": [{"xMeters": 0.5, "depthMeters": 2.0}],
                    }
                ],
            },
            {
                "locusNumber": "2",
                "topBoundary": [
                    {"xMeters": 0.0, "depthMeters": 0.30},
                    {"xMeters": 1.0, "depthMeters": 0.34},
                ],
                "bottomBoundary": [
                    {"xMeters": 0.0, "depthMeters": 0.55},
                    {"xMeters": 1.0, "depthMeters": 0.58},
                ],
            },
        ],
    }


def test_a_field_feature_outside_its_layer_is_reported(
    field_sheet_with_a_stray_feature,
):
    report = validate(field_sheet_with_a_stray_feature)

    assert any("lies outside layer band" in warning for warning in report.warnings)


def test_a_field_feature_with_only_approximate_coords_is_accepted():
    """The canonical form names the axis approxDepthMeters. Reading only the
    illustrator spelling reported perfectly good geometry as missing."""
    sheet = {
        "faceLabel": "N baulk",
        "loci": [{"locusNumber": "1"}],
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [
                    {"xMeters": 0.0, "depthMeters": 0.0},
                    {"xMeters": 1.0, "depthMeters": 0.02},
                ],
                "bottomBoundary": [
                    {"xMeters": 0.0, "depthMeters": 0.30},
                    {"xMeters": 1.0, "depthMeters": 0.34},
                ],
                "featuresInLayer": [
                    {
                        "feature": "stone",
                        "approxXMeters": 0.4,
                        "approxDepthMeters": 0.15,
                    }
                ],
            }
        ],
    }

    report = validate(sheet)

    assert not any("no shapePoints" in warning for warning in report.warnings)


# E8: registration hints reach both mediums.


def test_an_illustrator_sheet_offers_its_grid_labels_for_registration():
    """A field sheet's gridTiePoints were offered and an illustrator sheet's
    gridLabels were not, though they are the same kind of evidence."""
    from pipeline import convert_coords

    cfg = convert_coords.make_starter_config(
        {
            "trenchProfiles": [
                {
                    "face": "N baulk",
                    "gridLabels": ["190E/53S", "not a label"],
                    "gridLabelXMeters": [0.0, 4.0],
                    "layers": [],
                }
            ]
        }
    )

    assert {"rawText": "190E/53S", "gridX": 190.0, "gridY": -53.0} in (
        cfg["_tiePointsFromSheet"]
    )
    assert {"rawText": "not a label", "gridX": None, "gridY": None} in (
        cfg["_tiePointsFromSheet"]
    )
