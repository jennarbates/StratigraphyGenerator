"""Editor sessions: storage, structural validation, finalization.

Split out of a single 660-line module during the modularization refactor.
Every name that module exported is re-exported here, so ``from pipeline import
editor`` and ``from pipeline.editor import X`` keep working unchanged.
"""

from .errors import (
    DuplicateFaceNameError,
    EditorSchemaMismatchError,
    EditorStateStructureError,
    EditorStructuralValidationError,
    EmptyEditorError,
    FaceNameError,
    FacePolygonError,
    FieldWallFaceCountError,
    IncompleteGridRegistrationError,
    PolygonMetadataError,
    PolygonStackingError,
    SelfIntersectingPolygonError,
    UnclosedPolygonError,
    ZeroUsableLayersError,
)
from .finalize import finalize_editor_session
from .finds import (
    add_find,
    delete_find,
    get_finds,
    sync_finds_to_output,
)
from .schema import (
    ALLOWED_SCHEMA_TYPES,
    EDITOR_ENVELOPE_KEYS,
    GRID_REGISTRATION_FIELDS,
    REQUIRED_FIND_FIELDS,
    SHEET_TYPES_BY_SCHEMA,
)
from .session import (
    create_editor_session,
    load_editor_state,
    save_editor_state,
)

__all__ = [
    "ALLOWED_SCHEMA_TYPES",
    "EDITOR_ENVELOPE_KEYS",
    "GRID_REGISTRATION_FIELDS",
    "REQUIRED_FIND_FIELDS",
    "SHEET_TYPES_BY_SCHEMA",
    "DuplicateFaceNameError",
    "EditorSchemaMismatchError",
    "EditorStateStructureError",
    "EditorStructuralValidationError",
    "EmptyEditorError",
    "FaceNameError",
    "FacePolygonError",
    "FieldWallFaceCountError",
    "IncompleteGridRegistrationError",
    "PolygonMetadataError",
    "PolygonStackingError",
    "SelfIntersectingPolygonError",
    "UnclosedPolygonError",
    "ZeroUsableLayersError",
    "add_find",
    "create_editor_session",
    "delete_find",
    "finalize_editor_session",
    "get_finds",
    "load_editor_state",
    "save_editor_state",
    "sync_finds_to_output",
]
