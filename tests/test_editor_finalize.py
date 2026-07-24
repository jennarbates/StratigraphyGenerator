import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline import editor
from pipeline.extract_fieldwall import FieldWallProfile
from pipeline.extract_illustrator import ArchaeologicalDiagram


@pytest.fixture(autouse=True)
def isolate_jobs_dir(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(editor, "JOBS_DIR", jobs_dir)


def _field_wall_state():
    return {
        "trenchLabel": "T104",
        "faceLabel": "Southern baulk",
        "illustrators": ["A. Recorder"],
        "date": "2026-07-24",
        "northArrowPresent": True,
        "gridSquareCm": 20.0,
        "gridTiePoints": [
            {
                "rawText": "194m",
                "approxXMeters": 0.0,
            }
        ],
        "loci": [
            {
                "locusNumber": "1",
                "munsell": {
                    "raw": "10YR 5/3",
                    "colorName": "brown",
                },
                "description": "Brown soil",
                "confidence": "certain",
            }
        ],
        "layers": [
            {
                "locusNumber": "1",
                "topBoundary": [
                    {
                        "xMeters": 0.0,
                        "depthMeters": 0.0,
                        "confidence": "human-traced",
                    }
                ],
                "bottomBoundary": [
                    {
                        "xMeters": 0.0,
                        "depthMeters": 0.4,
                        "confidence": "human-traced",
                    }
                ],
                "featuresInLayer": [],
            }
        ],
        "marginalia": ["Example note"],
    }


def _archaeological_diagram_state():
    return {
        "metadata": {
            "currentFilePath": "manual-editor",
            "suggestedFilename": "trench_104_2026",
            "trenchLabel": "T104",
            "scale": {
                "unit": "m",
                "valuesMarked": [0, 1],
                "metricConversionAssumption": None,
                "confidence": "certain",
            },
            "credits": {
                "attributions": [
                    {
                        "name": "A. Recorder",
                        "role": "illustrator",
                    }
                ],
                "year": "2026",
            },
            "marginalia": [],
        },
        "trenchProfiles": [
            {
                "face": "south",
                "gridLabels": ["A"],
                "gridLabelXMeters": [0.0],
                "layers": [
                    {
                        "layerName": "Layer 1",
                        "inferredMaterial": "soil",
                        "description": "Brown soil",
                        "visualPattern": "dots",
                        "featuresInLayer": [],
                        "topBoundary": [
                            {
                                "xCoordinateMeters": 0.0,
                                "yCoordinateMeters": 0.0,
                                "confidence": "human-traced",
                            }
                        ],
                        "bottomBoundary": [
                            {
                                "xCoordinateMeters": 0.0,
                                "yCoordinateMeters": 0.4,
                                "confidence": "human-traced",
                            }
                        ],
                    }
                ],
            }
        ],
        "legend": [
            {
                "visualPattern": "dots",
                "material": "soil",
            }
        ],
        "inferred_notes": [],
        "rawTranscription": "Manual editor example",
    }


def test_finalize_field_wall_profile_sets_source_and_preserves_fields():
    job_id = editor.create_editor_session("FieldWallProfile")
    state = _field_wall_state()
    editor.save_editor_state(job_id, state)

    result = editor.finalize_editor_session(job_id)

    assert isinstance(result, FieldWallProfile)
    assert result.source == "manual_editor"
    assert result.model_dump(exclude={"source"}) == state


def test_finalize_archaeological_diagram_sets_source_and_preserves_fields():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = _archaeological_diagram_state()
    editor.save_editor_state(job_id, state)

    result = editor.finalize_editor_session(job_id)

    assert isinstance(result, ArchaeologicalDiagram)
    assert result.source == "manual_editor"
    assert result.model_dump(exclude={"source"}) == state


def test_finalize_validation_error_leaves_no_output_file():
    job_id = editor.create_editor_session("FieldWallProfile")
    state = _field_wall_state()
    del state["trenchLabel"]
    editor.save_editor_state(job_id, state)
    output_path = editor.JOBS_DIR / job_id / "extraction_output.json"

    with pytest.raises(ValidationError):
        editor.finalize_editor_session(job_id)

    assert not output_path.exists()


def test_finalize_output_round_trips_through_json_file():
    job_id = editor.create_editor_session("FieldWallProfile")
    editor.save_editor_state(job_id, _field_wall_state())

    result = editor.finalize_editor_session(job_id)

    output_path = editor.JOBS_DIR / job_id / "extraction_output.json"
    assert output_path.exists()
    output_data = json.loads(output_path.read_text())
    reparsed = FieldWallProfile.model_validate(output_data)
    assert reparsed == result
    assert reparsed.model_dump() == result.model_dump()


def test_finalize_nonexistent_job_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        editor.finalize_editor_session("missing-job")
