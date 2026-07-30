"""The vocabulary of an editor session: allowed schema types, the keys
that mark a structural envelope, and the fields each one requires."""

ALLOWED_SCHEMA_TYPES = {"ArchaeologicalDiagram", "FieldWallProfile"}
SHEET_TYPES_BY_SCHEMA = {
    "ArchaeologicalDiagram": "illustrator",
    "FieldWallProfile": "fieldwall",
}
GRID_REGISTRATION_FIELDS = (
    "originX",
    "originY",
    "surfaceZ",
    "bearing_deg",
)
EDITOR_ENVELOPE_KEYS = {
    "schemaType",
    "finalizeState",
    "gridConfig",
    "editorState",
    "resumeState",
}
REQUIRED_FIND_FIELDS = (
    "face_id",
    "x",
    "y",
    "elevation",
    "locus",
    "description",
)
