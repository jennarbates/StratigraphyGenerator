"""Filesystem storage for editor sessions."""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path


JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"
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


def create_editor_session(schema_type: str) -> str:
    """
    Create an editor job directory and store its session metadata.

    Raises ValueError when schema_type is not supported.
    """
    if schema_type not in ALLOWED_SCHEMA_TYPES:
        raise ValueError(f"Unsupported schema_type: {schema_type}")

    job_id = uuid.uuid4().hex[:12]
    session_dir = JOBS_DIR / job_id
    session_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "schema_type": schema_type,
        "created_at": created_at,
    }
    (session_dir / "editor_meta.json").write_text(
        json.dumps(metadata, indent=2)
    )
    draft_metadata = {
        "job_id": job_id,
        "schema_type": schema_type,
        "sheet_type": SHEET_TYPES_BY_SCHEMA[schema_type],
        "source": "manual_editor",
        "status": "editing",
        "created_at": created_at,
        "updated_at": created_at,
    }
    (session_dir / "meta.json").write_text(
        json.dumps(draft_metadata, indent=2)
    )
    return job_id


def save_editor_state(job_id: str, state: dict) -> None:
    """Overwrite the saved opaque editor state for an existing job."""
    session_dir = JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    (session_dir / "editor_state.json").write_text(
        json.dumps(state, indent=2)
    )


def load_editor_state(job_id: str) -> dict:
    """Load saved opaque editor state, or return an empty state if unsaved."""
    session_dir = JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    state_path = session_dir / "editor_state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text())


def add_find(job_id: str, find: dict) -> dict:
    """
    Append an artifact find to an existing job and return the stored find.

    A find may be logged independently of any saved or finalized editor state.
    """
    missing_fields = [
        field for field in REQUIRED_FIND_FIELDS if field not in find
    ]
    if missing_fields:
        raise ValueError(
            f'Missing required find field(s): {", ".join(missing_fields)}'
        )

    session_dir = JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    finds_path = session_dir / "finds.json"
    if not finds_path.exists():
        finds_path.write_text(json.dumps([], indent=2))

    finds = json.loads(finds_path.read_text())
    stored_find = dict(find)
    if "find_id" not in stored_find:
        stored_find["find_id"] = uuid.uuid4().hex[:12]
    finds.append(stored_find)
    finds_path.write_text(json.dumps(finds, indent=2))
    return stored_find


def get_finds(job_id: str) -> list[dict]:
    """Return artifact finds for an existing job, or an empty list if unsaved."""
    session_dir = JOBS_DIR / job_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Editor job directory does not exist: {job_id}")

    finds_path = session_dir / "finds.json"
    if not finds_path.exists():
        return []
    return json.loads(finds_path.read_text())


def delete_find(job_id: str, find_id: str) -> None:
    """Delete the artifact find matching find_id from an existing job."""
    finds = get_finds(job_id)
    retained_finds = [
        find for find in finds if find.get("find_id") != find_id
    ]
    if len(retained_finds) == len(finds):
        raise ValueError(f"Find does not exist: {find_id}")

    (JOBS_DIR / job_id / "finds.json").write_text(
        json.dumps(retained_finds, indent=2)
    )


def sync_finds_to_output(job_id: str) -> None:
    """Copy the current artifact finds into an existing finalized output."""
    output_path = JOBS_DIR / job_id / "extraction_output.json"
    if not output_path.exists():
        return

    output = json.loads(output_path.read_text())
    output["finds"] = get_finds(job_id)
    output_path.write_text(json.dumps(output, indent=2))


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


def _point_coordinates(point: dict) -> tuple[float, float] | None:
    x_coordinate = point.get("x")
    y_coordinate = point.get("y")
    if (
        not isinstance(x_coordinate, (int, float))
        or isinstance(x_coordinate, bool)
        or not math.isfinite(x_coordinate)
        or not isinstance(y_coordinate, (int, float))
        or isinstance(y_coordinate, bool)
        or not math.isfinite(y_coordinate)
    ):
        return None
    return float(x_coordinate), float(y_coordinate)


def _direction(start, end, point):
    return (
        (end[0] - start[0]) * (point[1] - start[1])
        - (end[1] - start[1]) * (point[0] - start[0])
    )


def _point_on_segment(point, start, end):
    return (
        _direction(start, end, point) == 0
        and min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def _segments_intersect(first_start, first_end, second_start, second_end):
    first_direction = _direction(first_start, first_end, second_start)
    second_direction = _direction(first_start, first_end, second_end)
    third_direction = _direction(second_start, second_end, first_start)
    fourth_direction = _direction(second_start, second_end, first_end)

    if (
        (first_direction > 0 > second_direction
         or first_direction < 0 < second_direction)
        and (third_direction > 0 > fourth_direction
             or third_direction < 0 < fourth_direction)
    ):
        return True

    return (
        first_direction == 0
        and _point_on_segment(second_start, first_start, first_end)
        or second_direction == 0
        and _point_on_segment(second_end, first_start, first_end)
        or third_direction == 0
        and _point_on_segment(first_start, second_start, second_end)
        or fourth_direction == 0
        and _point_on_segment(first_end, second_start, second_end)
    )


def _polygon_self_intersects(vertices: list[dict]) -> bool:
    points = [_point_coordinates(vertex) for vertex in vertices]
    if any(point is None for point in points):
        return False
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 4:
        return False

    for first_edge in range(len(points)):
        first_edge_end = (first_edge + 1) % len(points)
        for second_edge in range(first_edge + 1, len(points)):
            second_edge_end = (second_edge + 1) % len(points)
            edges_are_adjacent = (
                first_edge_end == second_edge
                or second_edge_end == first_edge
            )
            if edges_are_adjacent:
                continue
            if _segments_intersect(
                points[first_edge],
                points[first_edge_end],
                points[second_edge],
                points[second_edge_end],
            ):
                return True

    return False


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


def finalize_editor_session(job_id: str):
    """
    Validate saved editor state and write the corresponding extraction JSON.

    New editor payloads include structural state and grid registration, which
    are checked before schema validation. Legacy schema-only states remain
    supported for sessions created before the structural envelope existed.
    Pydantic validation errors intentionally propagate.
    """
    from .extract_fieldwall import FieldWallProfile
    from .extract_illustrator import ArchaeologicalDiagram

    session_dir = JOBS_DIR / job_id
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
