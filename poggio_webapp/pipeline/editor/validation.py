"""Structural checks on saved editor state, before schema validation.

These run first because a Pydantic error on a half-drawn polygon reads as
a schema mismatch when the real problem is that the drawing is not
finished. Each check raises its own error from .errors.
"""

import math

from .errors import (
    DuplicateFaceNameError,
    EmptyEditorError,
    EditorSchemaMismatchError,
    EditorStateStructureError,
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
from .geometry import _point_coordinates, _polygon_self_intersects
from .schema import EDITOR_ENVELOPE_KEYS, GRID_REGISTRATION_FIELDS


def _drawable_polygons(face: dict) -> list[dict]:
    polygons = face.get("polygons", [])
    if not isinstance(polygons, list):
        raise EditorStateStructureError(
            f'Face "{face.get("name", "<unnamed>")}" polygons must be a list.'
        )
    return [
        polygon
        for polygon in polygons
        if isinstance(polygon, dict) and polygon.get("vertices")
    ]


def _validate_polygon_stacking(face_name: str, polygons: list[dict]) -> None:
    polygon_ids = set()

    for polygon in polygons:
        polygon_id = polygon.get("id")
        if not isinstance(polygon_id, (int, str)) or isinstance(
            polygon_id,
            bool,
        ):
            raise PolygonStackingError(
                f'Face "{face_name}" has a polygon without a valid id.'
            )
        if polygon_id in polygon_ids:
            raise PolygonStackingError(
                f'Face "{face_name}" has duplicate polygon id {polygon_id}; '
                "stacking order is ambiguous."
            )
        polygon_ids.add(polygon_id)

    order_keys = ("stackOrder", "zOrder", "zIndex")
    explicit_orders = []
    has_explicit_order = False
    for polygon in polygons:
        order = None
        for order_key in order_keys:
            if order_key in polygon:
                order = polygon[order_key]
                has_explicit_order = True
                break
        explicit_orders.append(order)

    if has_explicit_order and explicit_orders != list(range(len(polygons))):
        raise PolygonStackingError(
            f'Face "{face_name}" polygon stack order must be unique, '
            "contiguous, and match the saved polygon order."
        )


def _validate_face_names(faces: list[dict]) -> None:
    normalized_names = set()
    for face_index, face in enumerate(faces):
        if not isinstance(face, dict):
            raise EditorStateStructureError(
                f"Face {face_index + 1} must be an object."
            )

        face_name = face.get("name")
        if not isinstance(face_name, str) or not face_name.strip():
            raise FaceNameError(f"Face {face_index + 1} needs a name.")

        normalized_name = face_name.strip().lower()
        if normalized_name in normalized_names:
            raise DuplicateFaceNameError(
                f'Duplicate face name "{face_name.strip()}"; '
                "face names must be unique."
            )
        normalized_names.add(normalized_name)


def _distinct_valid_vertex_count(vertices: list[dict]) -> int:
    return len({
        coordinates
        for vertex in vertices
        if isinstance(vertex, dict)
        and (coordinates := _point_coordinates(vertex)) is not None
    })


def _validate_polygons(
    state: dict,
    editor_state: dict,
    schema_type: str,
) -> None:
    resume_state = state.get("resumeState")
    resume_faces = (
        resume_state.get("faces")
        if isinstance(resume_state, dict)
        else None
    )

    for face_index, face in enumerate(editor_state["faces"]):
        face_name = face.get("name", "<unnamed>")
        polygons = _drawable_polygons(face)
        _validate_polygon_stacking(face_name, polygons)

        if not polygons:
            raise FacePolygonError(
                f'Face "{face_name}" needs at least one completed polygon.'
            )

        metadata_face = face
        if (
            isinstance(resume_faces, list)
            and face_index < len(resume_faces)
            and isinstance(resume_faces[face_index], dict)
        ):
            metadata_face = resume_faces[face_index]
        metadata_by_polygon_id = metadata_face.get(
            "metadataByPolygonId",
            metadata_face.get("polygonMetadata", {}),
        )
        if not isinstance(metadata_by_polygon_id, dict):
            metadata_by_polygon_id = {}

        for polygon in polygons:
            polygon_id = polygon.get("id")
            vertices = polygon.get("vertices", [])
            if (
                polygon.get("closed") is not True
                or not isinstance(vertices, list)
                or _distinct_valid_vertex_count(vertices) < 3
            ):
                raise UnclosedPolygonError(
                    f'Face "{face_name}" polygon {polygon_id} is not closed '
                    "with at least three distinct vertices."
                )
            if _polygon_self_intersects(vertices):
                raise SelfIntersectingPolygonError(
                    f'Face "{face_name}" polygon {polygon_id} '
                    "self-intersects."
                )

            metadata = metadata_by_polygon_id.get(polygon_id)
            if metadata is None:
                metadata = metadata_by_polygon_id.get(str(polygon_id))
            if not isinstance(metadata, dict):
                raise PolygonMetadataError(
                    f'Face "{face_name}" polygon {polygon_id} needs metadata.'
                )

            if schema_type == "FieldWallProfile":
                if not _has_required_text(metadata.get("locus")):
                    raise PolygonMetadataError(
                        f'Face "{face_name}" polygon {polygon_id} '
                        "needs a locus."
                    )
                if not _has_required_text(metadata.get("munsell")):
                    raise PolygonMetadataError(
                        f'Face "{face_name}" polygon {polygon_id} '
                        "needs Munsell notation."
                    )
            elif not (
                _has_required_text(metadata.get("material"))
                or _has_required_text(metadata.get("inferredMaterial"))
            ):
                raise PolygonMetadataError(
                    f'Face "{face_name}" polygon {polygon_id} '
                    "needs a material."
                )


def _is_finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _has_required_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_grid_registration(
    editor_state: dict,
    grid_config: dict,
) -> None:
    faces = editor_state.get("faces")
    if not faces:
        raise IncompleteGridRegistrationError(
            "Grid registration is incomplete because the editor has no faces."
        )

    registered_faces = (
        grid_config.get("faces", {})
        if isinstance(grid_config, dict)
        else {}
    )
    if not isinstance(registered_faces, dict):
        registered_faces = {}
    for face in faces:
        face_name = face.get("name", "<unnamed>")
        registration = registered_faces.get(face_name, {})
        if not isinstance(registration, dict):
            registration = {}
        missing_fields = [
            field
            for field in GRID_REGISTRATION_FIELDS
            if not _is_finite_number(registration.get(field))
        ]
        bearing = registration.get("bearing_deg")
        if (
            "bearing_deg" not in missing_fields
            and not 0 <= bearing <= 360
        ):
            missing_fields.append("bearing_deg")

        if missing_fields:
            raise IncompleteGridRegistrationError(
                f'Face "{face_name}" grid registration is incomplete: '
                f'{", ".join(missing_fields)}.'
            )


def _validate_usable_layers(
    finalize_state: dict,
    schema_type: str,
) -> None:
    if schema_type == "FieldWallProfile":
        layers = finalize_state.get("layers")
        usable_layers = (
            [layer for layer in layers if isinstance(layer, dict)]
            if isinstance(layers, list)
            else []
        )
    else:
        profiles = finalize_state.get("trenchProfiles")
        usable_layers = []
        if isinstance(profiles, list):
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue
                layers = profile.get("layers")
                if isinstance(layers, list):
                    usable_layers.extend(
                        layer for layer in layers if isinstance(layer, dict)
                    )

    if not usable_layers:
        raise ZeroUsableLayersError(
            "Assembled editor state must produce at least one usable layer."
        )


def _validate_editor_structure(
    state: dict,
    schema_type: str,
) -> dict:
    if not isinstance(state, dict):
        raise EditorStateStructureError(
            "Assembled editor state must be an object."
        )

    finalize_state = state.get("finalizeState")
    editor_state = state.get("editorState")
    saved_schema_type = state.get("schemaType")
    if saved_schema_type != schema_type:
        raise EditorSchemaMismatchError(
            f'Saved schemaType "{saved_schema_type}" conflicts with '
            f'session schema "{schema_type}".'
        )
    if not isinstance(finalize_state, dict):
        raise EditorStateStructureError(
            "Assembled editor state must include a finalizeState object."
        )
    if not isinstance(editor_state, dict):
        raise EditorStateStructureError(
            "Assembled editor state must include an editorState structural "
            "snapshot."
        )

    faces = editor_state.get("faces")
    if not isinstance(faces, list) or not faces:
        raise EmptyEditorError(
            "Set up at least one face before finalizing."
        )
    if schema_type == "FieldWallProfile" and len(faces) != 1:
        raise FieldWallFaceCountError(
            "A FieldWallProfile must have exactly one face."
        )

    _validate_face_names(faces)
    _validate_polygons(state, editor_state, schema_type)
    _validate_grid_registration(editor_state, state.get("gridConfig"))
    _validate_usable_layers(finalize_state, schema_type)
    return finalize_state


def _is_editor_envelope(state) -> bool:
    return (
        isinstance(state, dict)
        and bool(EDITOR_ENVELOPE_KEYS.intersection(state))
    )
