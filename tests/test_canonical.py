"""Parity tests for the canonical section document.

The centrepiece is `test_parity_same_section_both_mediums`: one invented
section, authored twice as the two capture schemas, canonicalizing to the
same identities, geometry, descriptions and features.
"""

import json
from pathlib import Path

import pytest

from pipeline.canonical import (
    CANONICAL_VERSION,
    IGNORED_CAPTURE_KEYS,
    VERBATIM_CAPTURE_KEYS,
    canonicalize,
    capture_keys,
    detect_schema,
    is_canonical,
    surface_id_for,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def field_doc():
    return load("t907-parity-fieldwall.json")


@pytest.fixture
def illustrator_doc():
    return load("t907-parity-illustrator.json")


def only_face(doc):
    canonical, _ = canonicalize(doc)
    return canonical["faces"][0]


def depths(boundary):
    return [p["depthMeters"] for p in boundary]


# 14. detect_schema


def test_detect_schema_reads_both_mediums(field_doc, illustrator_doc):
    assert detect_schema(field_doc) == "FieldWallProfile"
    assert detect_schema(illustrator_doc) == "ArchaeologicalDiagram"


def test_detect_schema_reads_a_field_doc_whose_layers_are_null():
    """The silent-disappearance case: null layers is still a field sheet."""
    assert detect_schema({"faceLabel": "N baulk", "layers": None}) == "FieldWallProfile"


def test_detect_schema_rejects_an_unrecognized_shape():
    with pytest.raises(ValueError, match="schema"):
        detect_schema({"somethingElse": 1})


# 8. surface_id_for


def test_surface_id_for_names_each_medium():
    assert surface_id_for("7", "FieldWallProfile") == "Locus 7"
    assert surface_id_for("Locus 7", "ArchaeologicalDiagram") == "Locus 7"


def test_surface_id_for_rejects_an_empty_label():
    with pytest.raises(ValueError, match="label"):
        surface_id_for("  ", "FieldWallProfile")


def test_surface_id_never_carries_colour(field_doc):
    face = only_face(field_doc)
    assert [layer["surfaceId"] for layer in face["layers"]] == [
        "Locus 1",
        "Locus 2",
        "Locus 3",
    ]
    assert all("10YR" not in layer["surfaceId"] for layer in face["layers"])
    assert face["layers"][0]["displayLabel"] == "Locus 1 (10YR 5/3 brown)"


def test_missing_field_locus_number_falls_back_and_warns():
    doc = {"faceLabel": "N baulk", "layers": [{"locusNumber": None}]}
    canonical, warnings = canonicalize(doc)
    assert canonical["faces"][0]["layers"][0]["surfaceId"] == "layer_0"
    assert any("layer_0" in w for w in warnings)


def test_missing_illustrator_name_falls_back_to_material_then_index():
    doc = {
        "trenchProfiles": [
            {
                "face": "N baulk",
                "layers": [
                    {"layerName": None, "inferredMaterial": "silty clay"},
                    {"layerName": None, "inferredMaterial": None},
                ],
            }
        ]
    }
    canonical, warnings = canonicalize(doc)
    surfaces = [layer["surfaceId"] for layer in canonical["faces"][0]["layers"]]
    assert surfaces == ["silty clay", "layer_1"]
    assert any("layer_1" in w for w in warnings)


# 1. A full field example


def test_field_example_keeps_everything_the_sheet_recorded(field_doc):
    face = only_face(field_doc)
    assert face["face"] == "N baulk"

    first = face["layers"][0]
    assert first["label"] == "1"
    assert first["munsell"] == {
        "raw": "10YR 5/3",
        "colorName": "brown",
        "confidence": "high",
    }
    assert first["description"] == "loose topsoil with modern root disturbance"
    assert depths(first["topBoundary"]) == [0.0, 0.02]
    assert depths(first["bottomBoundary"]) == [0.3, 0.34]
    assert first["bottomBoundary"][0]["uncertaintyCm"] == 2.0
    assert first["features"][0]["feature"] == "stone"
    assert first["features"][0]["approxDepthMeters"] == 0.15
    assert first["material"] is None and first["visualPattern"] is None


def test_field_example_keeps_the_deepest_bottom(field_doc):
    """The real base line, which the old adapter dropped."""
    deepest = only_face(field_doc)["layers"][-1]
    assert depths(deepest["bottomBoundary"]) == [0.8, 0.83]
    assert deepest["bottomBoundaryDerived"] is False


# 2. A full two-face illustrator example


def test_two_face_illustrator_example_canonicalizes():
    doc = {
        "metadata": {
            "trenchLabel": "T908",
            "scale": {"unit": "m", "valuesMarked": [0, 2]},
            "credits": {"attributions": [{"name": "R. Neri", "role": "draughtsman"}]},
        },
        "trenchProfiles": [
            {
                "face": "N baulk",
                "gridLabels": ["A", "B"],
                "gridLabelXMeters": [0.0, 1.0],
                "layers": [
                    {
                        "layerName": "Locus 1",
                        "inferredMaterial": "topsoil",
                        "description": "ploughsoil",
                        "visualPattern": "stipple",
                        "bottomBoundary": [
                            {"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.2}
                        ],
                    }
                ],
            },
            {
                "face": "E baulk",
                "layers": [
                    {
                        "layerName": "Locus 4",
                        "inferredMaterial": "gravel",
                        "description": "gravel spread",
                        "visualPattern": "dots",
                        "bottomBoundary": [
                            {"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.5}
                        ],
                    }
                ],
            },
        ],
        "legend": [{"visualPattern": "stipple", "material": "topsoil"}],
    }
    canonical, _ = canonicalize(doc)

    assert [face["face"] for face in canonical["faces"]] == ["N baulk", "E baulk"]
    north = canonical["faces"][0]
    assert north["gridRefs"] == [
        {"kind": "gridLabel", "rawText": "A", "xMeters": 0.0},
        {"kind": "gridLabel", "rawText": "B", "xMeters": 1.0},
    ]
    layer = north["layers"][0]
    assert layer["material"] == "topsoil"
    assert layer["visualPattern"] == "stipple"
    assert layer["description"] == "ploughsoil"
    assert layer["munsell"] is None
    assert canonical["document"]["legend"] == [
        {"visualPattern": "stipple", "material": "topsoil"}
    ]
    assert canonical["document"]["scale"]["bar"] == {
        "unit": "m",
        "valuesMarked": [0, 2],
    }
    assert canonical["document"]["recorders"] == [
        {"name": "R. Neri", "role": "draughtsman"}
    ]


# 3, 4. Boundary derivation (D1)


def test_null_illustrator_top_comes_from_the_layer_above(illustrator_doc):
    layers = only_face(illustrator_doc)["layers"]

    assert layers[0]["topBoundaryDerived"] is False
    assert layers[1]["topBoundaryDerived"] is True
    assert depths(layers[1]["topBoundary"]) == depths(layers[0]["bottomBoundary"])
    assert layers[2]["topBoundaryDerived"] is True
    assert depths(layers[2]["topBoundary"]) == depths(layers[1]["bottomBoundary"])
    assert depths(layers[2]["bottomBoundary"]) == [0.8, 0.83]


def test_null_field_top_from_the_editor_is_derived_and_warned():
    """E3: the canvas editor emits a null top for every field layer."""
    doc = {
        "faceLabel": "N baulk",
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [{"xMeters": 0.0, "depthMeters": 0.0}],
                "bottomBoundary": [{"xMeters": 0.0, "depthMeters": 0.3}],
            },
            {
                "locusNumber": "2",
                "topBoundary": None,
                "bottomBoundary": [{"xMeters": 0.0, "depthMeters": 0.6}],
            },
        ],
    }
    canonical, warnings = canonicalize(doc)
    second = canonical["faces"][0]["layers"][1]

    assert second["topBoundaryDerived"] is True
    assert depths(second["topBoundary"]) == [0.3]
    assert any("Locus 2" in w and "top" in w for w in warnings)


def test_a_first_layer_without_a_top_stays_empty_and_warns():
    """Nothing above it to derive from, so nothing is invented."""
    doc = {
        "faceLabel": "N baulk",
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": None,
                "bottomBoundary": [{"xMeters": 0.0, "depthMeters": 0.3}],
            }
        ],
    }
    canonical, warnings = canonicalize(doc)
    first = canonical["faces"][0]["layers"][0]

    assert first["topBoundary"] == []
    assert first["topBoundaryDerived"] is False
    assert any("no top boundary" in w for w in warnings)


def test_a_null_bottom_comes_from_the_layer_below():
    doc = {
        "faceLabel": "N baulk",
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [{"xMeters": 0.0, "depthMeters": 0.0}],
                "bottomBoundary": None,
            },
            {
                "locusNumber": "2",
                "topBoundary": [{"xMeters": 0.0, "depthMeters": 0.3}],
                "bottomBoundary": [{"xMeters": 0.0, "depthMeters": 0.6}],
            },
        ],
    }
    canonical, _ = canonicalize(doc)
    first = canonical["faces"][0]["layers"][0]

    assert first["bottomBoundaryDerived"] is True
    assert depths(first["bottomBoundary"]) == [0.3]


# 5, 6. Points


def test_point_keys_unify_including_a_mixed_legacy_pair():
    doc = {
        "trenchProfiles": [
            {
                "face": "N baulk",
                "layers": [
                    {
                        "layerName": "Locus 1",
                        "bottomBoundary": [
                            {"xCoordinateMeters": 0.4, "depthMeters": 0.7}
                        ],
                    }
                ],
            }
        ]
    }
    point = only_face(doc)["layers"][0]["bottomBoundary"][0]

    assert point["xMeters"] == 0.4
    assert point["depthMeters"] == 0.7
    assert "xCoordinateMeters" not in point
    assert "yCoordinateMeters" not in point


def test_confidence_uncertainty_and_source_pixel_survive():
    doc = {
        "faceLabel": "N baulk",
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [
                    {
                        "xMeters": 0.0,
                        "depthMeters": 0.1,
                        "confidence": "low",
                        "uncertaintyCm": 4.5,
                        "sourcePixel": [120, 340],
                    }
                ],
                "bottomBoundary": [],
            }
        ],
    }
    point = only_face(doc)["layers"][0]["topBoundary"][0]

    assert point["confidence"] == "low"
    assert point["uncertaintyCm"] == 4.5
    assert point["sourcePixel"] == [120, 340]


# 7. Duplicate loci


def test_duplicate_locus_numbers_keep_the_first_reading():
    doc = {
        "faceLabel": "N baulk",
        "loci": [
            {"locusNumber": "5", "munsell": {"raw": "10YR 5/3", "colorName": "brown"}},
            {"locusNumber": "5", "munsell": {"raw": "7.5YR 4/4", "colorName": "dark"}},
        ],
        "layers": [{"locusNumber": "5"}],
    }
    canonical, warnings = canonicalize(doc)

    assert canonical["faces"][0]["layers"][0]["munsell"]["raw"] == "10YR 5/3"
    assert any("more than once" in w for w in warnings)


def test_a_locus_with_no_layer_is_reported():
    doc = {
        "faceLabel": "N baulk",
        "loci": [{"locusNumber": "9", "description": "orphan"}],
        "layers": [{"locusNumber": "1"}],
    }
    _, warnings = canonicalize(doc)
    assert any("9" in w and "no layer" in w for w in warnings)


# 9. Metadata union


def test_field_document_metadata_round_trips(field_doc):
    canonical, _ = canonicalize(field_doc)
    document = canonical["document"]

    assert canonical["sourceSchema"] == "FieldWallProfile"
    assert canonical["source"] == "extraction"
    assert document["trenchLabel"] == "T907"
    assert document["recorders"] == [{"name": "A. Fabbri", "role": None}]
    assert document["date"] == "7/7/2015"
    assert document["marginalia"] == ["NR. 7/80"]
    assert document["northArrowPresent"] is True
    assert document["scale"] == {"gridSquareCm": 10.0, "bar": None}
    assert document["legend"] == []
    assert document["rawTranscription"] is None
    assert document["inferredNotes"] == []
    assert canonical["faces"][0]["gridRefs"] == [
        {"kind": "tiePoint", "rawText": "155.80", "xMeters": 0.0}
    ]


def test_illustrator_document_metadata_round_trips(illustrator_doc):
    canonical, _ = canonicalize(illustrator_doc)
    document = canonical["document"]

    assert canonical["sourceSchema"] == "ArchaeologicalDiagram"
    assert document["trenchLabel"] == "T907"
    assert document["recorders"] == [{"name": "A. Fabbri", "role": "illustrator"}]
    assert document["date"] == "7/7/2015"
    assert document["marginalia"] == ["NR. 7/80"]
    assert document["northArrowPresent"] is None
    assert document["scale"]["gridSquareCm"] is None
    assert document["scale"]["bar"]["unit"] == "m"
    assert len(document["legend"]) == 3
    assert document["rawTranscription"].startswith("North baulk of T907")
    assert document["inferredNotes"] == [
        "scale bar calibrated from the printed 1 m mark"
    ]


# 10. Finds


def test_finds_pass_through_verbatim(field_doc, illustrator_doc):
    for doc in (field_doc, illustrator_doc):
        canonical, _ = canonicalize(doc)
        assert canonical["finds"] == doc["finds"]


def test_finds_default_to_an_empty_list():
    canonical, _ = canonicalize({"faceLabel": "N baulk", "layers": []})
    assert canonical["finds"] == []


# 11. Parity centrepiece

NEUTRAL_LAYER_KEYS = (
    "surfaceId",
    "description",
    "topBoundary",
    "bottomBoundary",
    "features",
)


def neutral(layer):
    return {key: layer[key] for key in NEUTRAL_LAYER_KEYS}


def test_parity_same_section_both_mediums(field_doc, illustrator_doc):
    """The same drawn section, recorded twice, canonicalizes the same.

    What is allowed to differ is the medium's own written label text, its
    observation fields, and whether a shared line was drawn once or twice.
    """
    field, _ = canonicalize(field_doc)
    illustrator, _ = canonicalize(illustrator_doc)

    field_face = field["faces"][0]
    illustrator_face = illustrator["faces"][0]

    assert field_face["face"] == illustrator_face["face"]
    assert (
        field_face["gridRefs"][0]["xMeters"]
        == (illustrator_face["gridRefs"][0]["xMeters"])
    )
    assert len(field_face["layers"]) == len(illustrator_face["layers"])

    for recorded, drawn in zip(field_face["layers"], illustrator_face["layers"]):
        assert neutral(recorded) == neutral(drawn)

    assert field["document"]["trenchLabel"] == illustrator["document"]["trenchLabel"]
    assert field["document"]["date"] == illustrator["document"]["date"]
    assert field["document"]["marginalia"] == illustrator["document"]["marginalia"]
    assert (
        field["document"]["recorders"][0]["name"]
        == (illustrator["document"]["recorders"][0]["name"])
    )


def test_parity_keeps_the_medium_specific_observations(field_doc, illustrator_doc):
    field_layer = only_face(field_doc)["layers"][0]
    illustrator_layer = only_face(illustrator_doc)["layers"][0]

    assert field_layer["munsell"]["raw"] == "10YR 5/3"
    assert field_layer["material"] is None
    assert illustrator_layer["munsell"] is None
    assert illustrator_layer["material"] == "topsoil"
    assert illustrator_layer["visualPattern"] == "stipple"

    assert field_layer["label"] == "1"
    assert illustrator_layer["label"] == "Locus 1"
    assert field_layer["provenance"]["schemaType"] == "FieldWallProfile"
    assert illustrator_layer["provenance"]["schemaType"] == "ArchaeologicalDiagram"
    assert illustrator_layer["provenance"]["sourceFace"] == "N baulk"
    assert illustrator_layer["provenance"]["sourceLayerIndex"] == 0
    assert illustrator_layer["provenance"]["sourceLabel"] == "Locus 1"


# 12. Lossless inventory


def walk_keys(value, prefix=""):
    """Every dotted key path in a capture document, lists collapsed to []."""
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path
            yield from walk_keys(child, path)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item, f"{prefix}[]")


@pytest.mark.parametrize(
    "fixture,schema_type",
    [
        ("t907-parity-fieldwall.json", "FieldWallProfile"),
        ("t907-parity-illustrator.json", "ArchaeologicalDiagram"),
    ],
)
def test_every_capture_key_is_mapped_or_ignored(fixture, schema_type):
    handled = capture_keys(schema_type)
    unaccounted = set()
    for path in walk_keys(load(fixture)):
        if path in handled or path in IGNORED_CAPTURE_KEYS:
            continue
        if any(
            path == root or path.startswith(f"{root}.") or path.startswith(f"{root}[]")
            for root in VERBATIM_CAPTURE_KEYS
        ):
            continue
        unaccounted.add(path)
    assert unaccounted == set()


def test_an_unexpected_capture_key_fails_the_inventory():
    """The guard itself has to bite, or it guards nothing."""
    handled = capture_keys("FieldWallProfile")
    assert "layers[].inventedKey" not in handled
    assert "layers[].inventedKey" not in IGNORED_CAPTURE_KEYS


# 13. Determinism and idempotence


def test_canonicalize_is_deterministic(field_doc, illustrator_doc):
    for doc in (field_doc, illustrator_doc):
        first, first_warnings = canonicalize(doc)
        second, second_warnings = canonicalize(doc)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        assert first_warnings == second_warnings


def test_canonicalize_is_idempotent(field_doc, illustrator_doc):
    for doc in (field_doc, illustrator_doc):
        once, _ = canonicalize(doc)
        twice, warnings = canonicalize(once)
        assert twice == once
        assert warnings == []


def test_is_canonical_recognizes_its_own_output(field_doc):
    canonical, _ = canonicalize(field_doc)
    assert is_canonical(canonical) is True
    assert canonical["canonicalVersion"] == CANONICAL_VERSION
    assert is_canonical(field_doc) is False


def test_canonicalize_does_not_mutate_its_input(field_doc):
    before = json.dumps(field_doc, sort_keys=True)
    canonicalize(field_doc)
    assert json.dumps(field_doc, sort_keys=True) == before
