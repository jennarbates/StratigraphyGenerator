import json
import subprocess
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


def _editor_state_envelope():
    return {
        "finalizeState": _archaeological_diagram_state(),
        "gridConfig": {
            "faces": {
                "south": {
                    "originX": 123.5,
                    "originY": 456.25,
                    "surfaceZ": 287.8,
                    "bearing_deg": 90.0,
                }
            }
        },
        "editorState": {
            "faces": [
                {
                    "name": "south",
                    "polygons": [
                        {
                            "id": 1,
                            "closed": True,
                            "stackOrder": 0,
                            "vertices": [
                                {"x": 0.0, "y": 0.0},
                                {"x": 100.0, "y": 0.0},
                                {"x": 100.0, "y": 100.0},
                                {"x": 0.0, "y": 100.0},
                            ],
                        }
                    ],
                }
            ]
        },
    }


def _output_path(job_id):
    return editor.JOBS_DIR / job_id / "extraction_output.json"


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


def test_finalize_unclosed_polygon_raises_specific_error_without_output():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = _editor_state_envelope()
    state["editorState"]["faces"][0]["polygons"][0]["closed"] = False
    editor.save_editor_state(job_id, state)

    with pytest.raises(
        editor.UnclosedPolygonError,
        match=r'Face "south" polygon 1 is not closed',
    ):
        editor.finalize_editor_session(job_id)

    assert not _output_path(job_id).exists()


def test_finalize_self_intersecting_polygon_raises_specific_error_without_output():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = _editor_state_envelope()
    state["editorState"]["faces"][0]["polygons"][0]["vertices"] = [
        {"x": 0.0, "y": 0.0},
        {"x": 100.0, "y": 100.0},
        {"x": 0.0, "y": 100.0},
        {"x": 100.0, "y": 0.0},
    ]
    editor.save_editor_state(job_id, state)

    with pytest.raises(
        editor.SelfIntersectingPolygonError,
        match=r'Face "south" polygon 1 self-intersects',
    ):
        editor.finalize_editor_session(job_id)

    assert not _output_path(job_id).exists()


def test_finalize_incomplete_face_grid_raises_specific_error_without_output():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = _editor_state_envelope()
    del state["gridConfig"]["faces"]["south"]["surfaceZ"]
    editor.save_editor_state(job_id, state)

    with pytest.raises(
        editor.IncompleteGridRegistrationError,
        match=r'Face "south" grid registration is incomplete: surfaceZ',
    ):
        editor.finalize_editor_session(job_id)

    assert not _output_path(job_id).exists()


def test_finalize_ambiguous_polygon_stacking_raises_specific_error():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = _editor_state_envelope()
    state["editorState"]["faces"][0]["polygons"][0]["stackOrder"] = 1
    editor.save_editor_state(job_id, state)

    with pytest.raises(
        editor.PolygonStackingError,
        match=r'Face "south" polygon stack order must be unique',
    ):
        editor.finalize_editor_session(job_id)

    assert not _output_path(job_id).exists()


def test_finalize_structurally_valid_editor_envelope_succeeds():
    job_id = editor.create_editor_session("ArchaeologicalDiagram")
    state = _editor_state_envelope()
    editor.save_editor_state(job_id, state)

    result = editor.finalize_editor_session(job_id)

    assert isinstance(result, ArchaeologicalDiagram)
    assert result.source == "manual_editor"
    assert result.model_dump(exclude={"source"}) == state["finalizeState"]
    assert _output_path(job_id).exists()


def test_client_finalize_control_blocks_invalid_states_and_enables_clean_state():
    grid_module = (
        REPO_ROOT / "poggio_webapp" / "static" / "canvas" / "grid.mjs"
    )
    canvas_html = (
        REPO_ROOT / "poggio_webapp" / "static" / "canvas.html"
    ).read_text()
    canvas_javascript = (
        REPO_ROOT / "poggio_webapp" / "static" / "canvas" / "index.js"
    ).read_text()
    script = f"""
import assert from "node:assert/strict";
import {{ updateFinalizeControl }} from "{grid_module.as_uri()}";

const validState = {{
  faces: [{{
    name: "south",
    gridRegistration: {{
      originX: 123.5,
      originY: 456.25,
      surfaceZ: 287.8,
      bearing_deg: 90,
    }},
    polygons: [{{
      id: 1,
      closed: true,
      vertices: [
        {{ x: 0, y: 0 }},
        {{ x: 100, y: 0 }},
        {{ x: 100, y: 100 }},
        {{ x: 0, y: 100 }},
      ],
    }}],
  }}],
}};

function assertBlocked(mutator, messagePattern) {{
  const state = structuredClone(validState);
  mutator(state);
  const button = {{ disabled: false }};
  const status = {{ textContent: "" }};
  const result = updateFinalizeControl(button, status, state);
  assert.equal(result.canFinalize, false);
  assert.equal(button.disabled, true);
  assert.match(status.textContent, messagePattern);
}}

assertBlocked(
  (state) => {{ state.faces[0].polygons[0].closed = false; }},
  /not closed/,
);
assertBlocked(
  (state) => {{
    state.faces[0].polygons[0].vertices = [
      {{ x: 0, y: 0 }},
      {{ x: 100, y: 100 }},
      {{ x: 0, y: 100 }},
      {{ x: 100, y: 0 }},
    ];
  }},
  /self-intersects/,
);
assertBlocked(
  (state) => {{ state.faces[0].gridRegistration.surfaceZ = ""; }},
  /incomplete grid registration/,
);
assertBlocked(
  (state) => {{
    state.faces[0].polygons.push(
      structuredClone(state.faces[0].polygons[0]),
    );
  }},
  /duplicate polygon id/,
);
assertBlocked(
  (state) => {{ state.faces[0].polygons[0].stackOrder = 1; }},
  /stack order/,
);

const button = {{ disabled: true }};
const status = {{ textContent: "" }};
const result = updateFinalizeControl(button, status, validState);
assert.equal(result.canFinalize, true);
assert.equal(button.disabled, false);
assert.match(status.textContent, /ready to finalize/i);
"""

    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert 'id="finalize-editor"' in canvas_html
    assert 'id="finalize-status"' in canvas_html
    assert "updateFinalizeControl" in canvas_javascript
