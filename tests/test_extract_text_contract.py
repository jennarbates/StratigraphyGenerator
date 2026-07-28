import pytest
from pydantic import ValidationError

from poggio_webapp.pipeline.extract_text import (
    FieldWallTextCandidates,
    TextCandidate,
    VerifiedFieldWallText,
    normalize_munsell,
)


def _candidate_payload():
    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "document": {
            "trenchLabel": {
                "raw": "T 104",
                "proposed": "T104",
                "confidence": "high",
                "bbox": [120, 310, 290, 360],
                "notes": None,
            },
            "faceLabel": None,
            "date": None,
            "gridSquareCm": {
                "raw": "20 cm",
                "proposed": 20.0,
                "confidence": "high",
                "bbox": [120, 370, 290, 420],
                "notes": None,
            },
            "northArrowPresent": {
                "raw": "north arrow visible",
                "proposed": True,
                "confidence": "medium",
                "bbox": [800, 50, 900, 180],
                "notes": None,
            },
            "illustrators": [],
            "gridTiePoints": [],
            "marginalia": [],
            "otherText": [],
        },
        "loci": [
            {
                "locusNumber": {
                    "raw": "1042",
                    "proposed": "1042",
                    "confidence": "high",
                    "bbox": [120, 430, 180, 470],
                    "notes": None,
                },
                "munsellRaw": {
                    "raw": "10 yr 5 / 3",
                    "proposed": "10YR 5/3",
                    "confidence": "medium",
                    "bbox": [190, 430, 310, 470],
                    "notes": None,
                },
                "description": {
                    "raw": "brown silty soil",
                    "proposed": "brown silty soil",
                    "confidence": "low",
                    "bbox": [320, 430, 560, 470],
                    "notes": "last word is difficult to read",
                },
            }
        ],
    }


def _verified_payload():
    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "reviewCompleted": True,
        "document": {
            "trenchLabel": "T104",
            "faceLabel": "Southern baulk",
            "date": "2025",
            "gridSquareCm": 20.0,
            "northArrowPresent": True,
            "illustrators": ["Lizzy Bruening", "Heather Fusco"],
            "gridTiePoints": ["194 m", "190 m"],
            "marginalia": ["Section continued on reverse"],
            "otherText": [],
        },
        "loci": [
            {
                "locusNumber": "1042",
                "munsellRaw": "10YR 5/3",
                "description": "brown silty soil",
            }
        ],
        "audit": [
            {
                "fieldPath": "document.trenchLabel",
                "raw": "T 104",
                "proposed": "T104",
                "final": "T104",
                "status": "accepted",
                "confidence": "high",
                "bbox": [120, 310, 290, 360],
            }
        ],
    }


def test_candidate_json_round_trips_through_pydantic():
    payload = _candidate_payload()

    parsed = FieldWallTextCandidates.model_validate(payload)

    assert parsed.model_dump(mode="json") == payload


def test_candidate_nullable_values_may_be_omitted():
    payload = _candidate_payload()
    del payload["document"]["trenchLabel"]["proposed"]
    del payload["document"]["trenchLabel"]["bbox"]

    parsed = FieldWallTextCandidates.model_validate(payload)
    trench_label = parsed.model_dump(mode="json")["document"]["trenchLabel"]

    assert trench_label["proposed"] is None
    assert trench_label["bbox"] is None


@pytest.mark.parametrize("schema_version", [0, 2, 1.0, "1"])
def test_candidate_schema_version_accepts_only_integer_one(schema_version):
    payload = _candidate_payload()
    payload["schemaVersion"] = schema_version

    with pytest.raises(ValidationError):
        FieldWallTextCandidates.model_validate(payload)


def test_verified_json_round_trips_through_pydantic():
    payload = _verified_payload()

    parsed = VerifiedFieldWallText.model_validate(payload)

    assert parsed.model_dump(mode="json") == payload


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValidationError):
        TextCandidate(
            raw="T 104",
            proposed="T104",
            confidence="certain",
            bbox=None,
            notes=None,
        )


@pytest.mark.parametrize(
    "bbox",
    [
        [-1, 100, 200, 300],
        [100, 100, 1001, 300],
        [200, 100, 200, 300],
        [250, 100, 200, 300],
        [100, 300, 200, 300],
        [100, 350, 200, 300],
    ],
    ids=[
        "below-zero",
        "above-1000",
        "x-min-equals-x-max",
        "x-min-above-x-max",
        "y-min-equals-y-max",
        "y-min-above-y-max",
    ],
)
def test_invalid_bounding_boxes_are_rejected(bbox):
    with pytest.raises(ValidationError):
        TextCandidate(
            raw="T 104",
            proposed="T104",
            confidence="high",
            bbox=bbox,
            notes=None,
        )


def test_munsell_spacing_and_hue_are_normalized():
    assert normalize_munsell("10 yr 5 / 3") == ("10YR 5/3", True)


def test_already_valid_munsell_is_unchanged():
    assert normalize_munsell("10YR 5/3") == ("10YR 5/3", True)


def test_malformed_munsell_is_preserved_and_marked_invalid():
    assert normalize_munsell("unreadable value") == ("unreadable value", False)


def test_none_munsell_remains_none():
    assert normalize_munsell(None) == (None, False)


@pytest.mark.parametrize("raw", ["", "   "])
def test_empty_munsell_does_not_become_an_invented_value(raw):
    assert normalize_munsell(raw) == ("", False)


def test_candidate_schema_contains_no_geometry_fields():
    schema = FieldWallTextCandidates.model_json_schema()
    property_names = set()

    def collect_properties(value):
        if isinstance(value, dict):
            property_names.update(value.get("properties", {}))
            for nested in value.values():
                collect_properties(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_properties(nested)

    collect_properties(schema)

    assert property_names.isdisjoint(
        {
            "layers",
            "topBoundary",
            "bottomBoundary",
            "shapePoints",
            "xMeters",
            "depthMeters",
            "approxXMeters",
            "approxDepthMeters",
            "approxWidthMeters",
            "approxHeightMeters",
            "markerPositions",
            "features",
        }
    )
