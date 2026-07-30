"""Turning validated editor state into the extraction document."""

import json

import storage

from .finds import sync_finds_to_output
from .validation import _is_editor_envelope, _validate_editor_structure


def finalize_editor_session(job_id: str):
    """
    Validate saved editor state and write the corresponding extraction JSON.

    New editor payloads include structural state and grid registration, which
    are checked before schema validation. Legacy schema-only states remain
    supported for sessions created before the structural envelope existed.
    Pydantic validation errors intentionally propagate.
    """
    # Imported inside the function: these pull in the pydantic schema
    # modules, and importing them at package import time would make
    # pipeline.editor depend on them just to save a session.
    from ..extract_fieldwall import FieldWallProfile
    from ..extract_illustrator import ArchaeologicalDiagram

    session_dir = storage.JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    metadata = json.loads((session_dir / "editor_meta.json").read_text())
    state = json.loads((session_dir / "editor_state.json").read_text())
    schema_type = metadata["schema_type"]
    model_state = (
        _validate_editor_structure(state, schema_type)
        if _is_editor_envelope(state)
        else state
    )
    schema_models = {
        "ArchaeologicalDiagram": ArchaeologicalDiagram,
        "FieldWallProfile": FieldWallProfile,
    }
    model_class = schema_models[schema_type]
    validated = model_class(**{**model_state, "source": "manual_editor"})

    (session_dir / "extraction_output.json").write_text(
        validated.model_dump_json(indent=2)
    )
    sync_finds_to_output(job_id)
    return validated
