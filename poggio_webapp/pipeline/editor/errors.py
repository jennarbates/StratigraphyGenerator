"""Structural problems in saved editor state.

One class per rule, so a caller can catch the family or a single case, and
so the message lives with the rule rather than at the raise site.
"""


class EditorStructuralValidationError(ValueError):
    """Base class for editor-only structural validation failures."""


class EditorStateStructureError(EditorStructuralValidationError):
    """Raised when an assembled editor payload lacks its structural snapshot."""


class EditorSchemaMismatchError(EditorStructuralValidationError):
    """Raised when saved and session schema types do not agree."""


class EmptyEditorError(EditorStructuralValidationError):
    """Raised when an editor has no faces."""


class FieldWallFaceCountError(EditorStructuralValidationError):
    """Raised when a field-wall editor does not have exactly one face."""


class FaceNameError(EditorStructuralValidationError):
    """Raised when an editor face has no usable name."""


class DuplicateFaceNameError(EditorStructuralValidationError):
    """Raised when editor face names are not unique."""


class FacePolygonError(EditorStructuralValidationError):
    """Raised when an editor face has no usable completed polygon."""


class UnclosedPolygonError(EditorStructuralValidationError):
    """Raised when a drawn polygon is not closed."""


class SelfIntersectingPolygonError(EditorStructuralValidationError):
    """Raised when a polygon crosses itself."""


class PolygonStackingError(EditorStructuralValidationError):
    """Raised when polygon stacking order is ambiguous."""


class IncompleteGridRegistrationError(EditorStructuralValidationError):
    """Raised when any editor face lacks a complete grid registration."""


class PolygonMetadataError(EditorStructuralValidationError):
    """Raised when a completed polygon lacks required metadata."""


class ZeroUsableLayersError(EditorStructuralValidationError):
    """Raised when an assembled model contains no usable layers."""
