import json
import subprocess
import sys
from pathlib import Path

import pytest
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
