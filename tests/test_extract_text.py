import json

from poggio_webapp.pipeline import extract_text


def _fieldwall_extraction():
    return {
        "trenchLabel": "T104",
        "faceLabel": "South baulk",
        "illustrators": ["A. Recorder"],
        "date": "27 VII 2026",
        "northArrowPresent": True,
        "gridSquareCm": 20,
        "gridTiePoints": [
            {"rawText": "E 194", "approxXMeters": 0.0},
            {"rawText": None, "approxXMeters": 1.0},
        ],
        "loci": [
            {
                "locusNumber": "1042",
                "munsell": {"raw": "10YR 5/3", "colorName": "brown"},
                "description": "brown silty soil",
                "confidence": "clear",
            },
            {
                "locusNumber": "1043",
                "munsell": None,
                "description": "faded compact fill",
                "confidence": "uncertain handwriting",
            },
        ],
        "layers": [
            {
                "locusNumber": "1042",
                "topBoundary": [
                    {"xMeters": 0, "depthMeters": 0.1, "confidence": "high"}
                ],
                "bottomBoundary": [
                    {"xMeters": 0, "depthMeters": 0.4, "confidence": "high"}
                ],
            }
        ],
        "marginalia": ["Continued on reverse"],
        "source": "extraction",
        "finds": [],
    }


def test_existing_fieldwall_extraction_is_adapted_for_review(tmp_path):
    extraction = _fieldwall_extraction()
    output_path = tmp_path / "nested" / "text_candidates.json"

    result = extract_text.candidates_from_fieldwall_extraction(
        json.dumps(extraction),
        str(output_path),
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result
    assert result["document"]["trenchLabel"] == {
        "raw": "T104",
        "proposed": "T104",
        "confidence": "medium",
        "bbox": None,
        "notes": None,
    }
    assert result["document"]["gridSquareCm"]["proposed"] == 20.0
    assert result["document"]["northArrowPresent"]["proposed"] is True
    assert [row["raw"] for row in result["document"]["gridTiePoints"]] == ["E 194"]
    assert result["loci"][0]["locusNumber"]["confidence"] == "high"
    assert result["loci"][1]["description"]["confidence"] == "low"


def test_embedded_review_candidates_take_precedence_and_bad_box_is_dropped():
    extraction = _fieldwall_extraction()
    extraction["textCandidates"] = {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "document": {
            "trenchLabel": {
                "raw": "T 104",
                "proposed": "T104",
                "confidence": "high",
                "bbox": [300, 100, 100, 200],
            }
        },
        "loci": [],
    }

    result = extract_text.candidates_from_fieldwall_extraction(extraction)

    assert result["document"]["trenchLabel"]["raw"] == "T 104"
    assert result["document"]["trenchLabel"]["proposed"] == "T104"
    assert result["document"]["trenchLabel"]["confidence"] == "high"
    assert result["document"]["trenchLabel"]["bbox"] is None


def test_geometry_from_existing_extraction_is_not_copied_into_text_candidates():
    result = extract_text.candidates_from_fieldwall_extraction(_fieldwall_extraction())
    serialized = json.dumps(result)

    assert "layers" not in result
    assert "topBoundary" not in serialized
    assert "bottomBoundary" not in serialized
    assert "xMeters" not in serialized
    assert all(
        candidate["bbox"] is None for candidate in result["document"]["illustrators"]
    )


def test_missing_and_empty_text_become_empty_review_fields():
    extraction = _fieldwall_extraction()
    extraction["trenchLabel"] = None
    extraction["faceLabel"] = "   "
    extraction["illustrators"] = None
    extraction["gridTiePoints"] = None
    extraction["loci"] = None

    result = extract_text.candidates_from_fieldwall_extraction(extraction)

    assert result["document"]["trenchLabel"] is None
    assert result["document"]["faceLabel"] is None
    assert result["document"]["illustrators"] == []
    assert result["document"]["gridTiePoints"] == []
    assert result["loci"] == []


def test_adapter_rejects_non_object_json():
    try:
        extract_text.candidates_from_fieldwall_extraction("[]")
    except ValueError as error:
        assert "JSON object" in str(error)
    else:
        raise AssertionError("expected a non-object extraction to be rejected")
