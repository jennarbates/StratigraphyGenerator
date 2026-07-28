"""Safe, durable filesystem storage for Harris Matrix workspaces."""

import os
import re
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import ValidationError

from . import config

if __package__ == "backend":
    from pipeline.harris_matrix import HarrisMatrix, validate_matrix_graph
else:
    from ..pipeline.harris_matrix import (
        HarrisMatrix,
        validate_matrix_graph,
    )


_MATRIX_ID = re.compile(r"[0-9a-f]{12}")
_SAFE_INITIAL_FIELDS = ("title", "site", "trench")
_DEFAULT_MATRICES_DIR = config.MATRICES_DIR
MATRICES_DIR = _DEFAULT_MATRICES_DIR


class HarrisStoreError(Exception):
    """Base class for expected matrix storage errors."""


class InvalidMatrixIdError(HarrisStoreError, ValueError):
    """Raised before filesystem access when a matrix ID is unsafe."""


class MatrixNotFoundError(HarrisStoreError, FileNotFoundError):
    """Raised when a valid matrix ID has no stored matrix."""


class MatrixConflictError(HarrisStoreError):
    """Raised when an optimistic revision check fails."""

    def __init__(self, expected_revision: int, actual_revision: int):
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        super().__init__(
            "Matrix revision conflict: expected "
            f"{expected_revision}, found {actual_revision}."
        )


class InvalidMatrixError(HarrisStoreError, ValueError):
    """Raised when matrix schema or graph validation fails."""

    def __init__(self, message: str, *, error_codes=()):
        self.error_codes = tuple(error_codes)
        super().__init__(message)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_matrix_id(matrix_id: str) -> str:
    if not isinstance(matrix_id, str) or _MATRIX_ID.fullmatch(matrix_id) is None:
        raise InvalidMatrixIdError(
            "Matrix ID must be exactly 12 lowercase hexadecimal characters."
        )
    return matrix_id


def _matrices_root() -> Path:
    if MATRICES_DIR != _DEFAULT_MATRICES_DIR:
        return MATRICES_DIR
    return config.MATRICES_DIR


def _matrix_directory(matrix_id: str) -> Path:
    return _matrices_root() / matrix_id


def _matrix_path(matrix_id: str) -> Path:
    return _matrix_directory(matrix_id) / "matrix.json"


def _validate_candidate(candidate) -> HarrisMatrix:
    try:
        matrix = HarrisMatrix.model_validate(candidate)
    except ValidationError as error:
        raise InvalidMatrixError("Matrix schema is invalid.") from error

    report = validate_matrix_graph(matrix)
    if not report["ok"]:
        error_codes = sorted({
            issue["code"]
            for issue in report["errors"]
        })
        raise InvalidMatrixError(
            "Matrix graph is invalid: " + ", ".join(error_codes) + ".",
            error_codes=error_codes,
        )
    return matrix


def _atomic_write(matrix: HarrisMatrix, destination: Path) -> None:
    serialized = matrix.model_dump_json(indent=2) + "\n"
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=".matrix-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def create_matrix(initial_fields: dict | None = None) -> HarrisMatrix:
    """Create and persist an empty version 1 matrix."""
    if initial_fields is None:
        initial_fields = {}
    if not isinstance(initial_fields, dict):
        raise InvalidMatrixError("Initial matrix fields must be an object.")

    safe_fields = {
        field: initial_fields[field]
        for field in _SAFE_INITIAL_FIELDS
        if field in initial_fields
    }
    _matrices_root().mkdir(exist_ok=True)

    for _attempt in range(100):
        matrix_id = secrets.token_hex(6)
        matrix_directory = _matrix_directory(matrix_id)
        if matrix_directory.exists():
            continue

        timestamp = _utc_now()
        matrix = _validate_candidate(
            {
                "schema_version": 1,
                "matrix_id": matrix_id,
                "revision": 0,
                "title": safe_fields.get("title", "Untitled Harris Matrix"),
                "site": safe_fields.get("site", ""),
                "trench": safe_fields.get("trench", ""),
                "notes": "",
                "source_job_ids": [],
                "units": [],
                "relations": [],
                "correlations": [],
                "suggestions": [],
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

        try:
            matrix_directory.mkdir()
        except FileExistsError:
            continue
        _atomic_write(matrix, matrix_directory / "matrix.json")
        return matrix

    raise HarrisStoreError("Could not allocate a unique matrix ID.")


def load_matrix(matrix_id: str) -> HarrisMatrix:
    """Load and validate one stored matrix."""
    matrix_id = _validate_matrix_id(matrix_id)
    path = _matrix_path(matrix_id)
    try:
        serialized = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise MatrixNotFoundError(
            f"Matrix {matrix_id} was not found."
        ) from error

    try:
        matrix = HarrisMatrix.model_validate_json(serialized)
    except ValidationError as error:
        raise InvalidMatrixError(
            f"Stored matrix {matrix_id} is invalid."
        ) from error

    if matrix.matrix_id != matrix_id:
        raise InvalidMatrixError(
            f"Stored matrix {matrix_id} has a mismatched matrix ID."
        )
    return _validate_candidate(matrix)


def save_matrix(
    matrix_id: str,
    candidate: dict | HarrisMatrix,
    expected_revision: int,
) -> HarrisMatrix:
    """Validate and atomically save a matrix using optimistic concurrency."""
    matrix_id = _validate_matrix_id(matrix_id)
    current = load_matrix(matrix_id)
    if expected_revision != current.revision:
        raise MatrixConflictError(expected_revision, current.revision)

    if isinstance(candidate, HarrisMatrix):
        candidate_data = candidate.model_dump(mode="python")
    elif isinstance(candidate, dict):
        candidate_data = dict(candidate)
    else:
        raise InvalidMatrixError("Matrix candidate must be an object.")

    updated_at = _utc_now()
    if updated_at <= current.updated_at:
        updated_at = current.updated_at + timedelta(microseconds=1)
    candidate_data.update(
        {
            "matrix_id": current.matrix_id,
            "revision": current.revision + 1,
            "created_at": current.created_at,
            "updated_at": updated_at,
        }
    )
    matrix = _validate_candidate(candidate_data)
    _atomic_write(matrix, _matrix_path(matrix_id))
    return matrix


def _summary(matrix: HarrisMatrix) -> dict:
    return {
        "matrix_id": matrix.matrix_id,
        "title": matrix.title,
        "site": matrix.site,
        "trench": matrix.trench,
        "revision": matrix.revision,
        "updated_at": matrix.updated_at.isoformat(),
        "unit_count": len(matrix.units),
        "relation_count": len(matrix.relations),
    }


def list_matrices() -> list[dict]:
    """Return valid stored matrices, newest first, without server paths."""
    matrices_root = _matrices_root()
    if not matrices_root.exists():
        return []

    stored = []
    for matrix_directory in sorted(
        matrices_root.iterdir(),
        key=lambda path: path.name,
    ):
        if (
            not matrix_directory.is_dir()
            or _MATRIX_ID.fullmatch(matrix_directory.name) is None
        ):
            continue
        try:
            matrix = load_matrix(matrix_directory.name)
        except (InvalidMatrixError, MatrixNotFoundError):
            continue
        stored.append(matrix)

    stored.sort(key=lambda matrix: matrix.matrix_id)
    stored.sort(key=lambda matrix: matrix.updated_at, reverse=True)
    return [_summary(matrix) for matrix in stored]
