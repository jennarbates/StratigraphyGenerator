import json
import subprocess
import sys
from pathlib import Path

import pytest
from google import genai
from google.genai import _transformers
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline.extract_fieldwall import FieldWallProfile
from pipeline.extract_illustrator import ArchaeologicalDiagram


def _field_wall_data():
    return {
        "trenchLabel": None,
        "faceLabel": None,
        "illustrators": None,
        "date": None,
        "northArrowPresent": None,
        "gridSquareCm": None,
        "gridTiePoints": None,
        "loci": None,
        "layers": None,
        "marginalia": None,
    }


def test_existing_output_defaults_to_extraction():
    raw_json = subprocess.check_output(
        [
            "git",
            "show",
            "d383439^:03_extraction/output_section001.json",
        ],
        cwd=REPO_ROOT,
        text=True,
    )

    diagram = ArchaeologicalDiagram(**json.loads(raw_json))

    assert diagram.source == "extraction"


def test_manual_editor_source_is_accepted():
    diagram = ArchaeologicalDiagram(
        metadata=None,
        trenchProfiles=[],
        legend=None,
        source="manual_editor",
    )
    field_wall = FieldWallProfile(
        **_field_wall_data(),
        source="manual_editor",
    )

    assert diagram.source == "manual_editor"
    assert field_wall.source == "manual_editor"


def test_fieldwall_schema_requests_review_candidates_without_reserializing_them():
    schema = FieldWallProfile.model_json_schema()
    payload = {
        **_field_wall_data(),
        "textCandidates": {
            "schemaVersion": 1,
            "sheetType": "fieldwall",
            "document": {},
            "loci": [],
        },
    }

    field_wall = FieldWallProfile.model_validate(payload)

    assert "textCandidates" in schema["properties"]
    assert "finds" not in schema["properties"]
    assert field_wall.textCandidates is not None
    assert "textCandidates" not in field_wall.model_dump()
    assert field_wall.model_dump()["finds"] == []


def test_fieldwall_schema_is_accepted_by_gemini_converter():
    client = genai.Client(api_key="not-a-real-key")
    try:
        converted = _transformers.t_schema(
            client._api_client,
            FieldWallProfile,
        )
    finally:
        client.close()

    assert "textCandidates" in converted.properties
    serialized = json.dumps(
        converted.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
    )
    assert "additional_properties" not in serialized
    assert "additionalProperties" not in serialized


def test_invalid_source_is_rejected():
    with pytest.raises(ValidationError):
        ArchaeologicalDiagram(
            metadata=None,
            trenchProfiles=[],
            legend=None,
            source="bogus",
        )

    with pytest.raises(ValidationError):
        FieldWallProfile(
            **_field_wall_data(),
            source="bogus",
        )
