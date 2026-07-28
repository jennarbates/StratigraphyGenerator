"""CRUD API routes for Harris Matrix workspaces."""

from typing import Annotated

from flask import Blueprint, jsonify, request
from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
)

from .. import harris_store


bp = Blueprint("harris", __name__)

TrimmedString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True),
]


class _CreateMatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TrimmedString = "Untitled Harris Matrix"
    site: TrimmedString = ""
    trench: TrimmedString = ""


def _error_response(message, code, status, *, details=None):
    payload = {
        "error": message,
        "code": code,
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status


def _invalid_request(error: ValidationError):
    issues = [
        {
            "field": ".".join(str(part) for part in issue["loc"]),
            "code": issue["type"],
            "message": issue["msg"],
        }
        for issue in error.errors(include_url=False)
    ]
    return _error_response(
        "Request body is invalid.",
        "invalid_request",
        400,
        details={"issues": issues},
    )


def _request_object():
    body = request.get_json(silent=True)
    if body is None:
        if request.get_data(cache=True).strip():
            return None, _error_response(
                "Request body must be valid JSON.",
                "invalid_request",
                400,
            )
        return {}, None
    if not isinstance(body, dict):
        return None, _error_response(
            "Request body must be a JSON object.",
            "invalid_request",
            400,
        )
    return body, None


def _matrix_response(matrix, status=200):
    return jsonify(matrix.model_dump(mode="json")), status


def _store_error_response(error):
    if isinstance(error, harris_store.InvalidMatrixIdError):
        return _error_response(
            str(error),
            "invalid_matrix_id",
            400,
        )
    if isinstance(error, harris_store.MatrixNotFoundError):
        return _error_response(
            str(error),
            "matrix_not_found",
            404,
        )
    if isinstance(error, harris_store.MatrixConflictError):
        return _error_response(
            "Matrix revision conflict.",
            "revision_conflict",
            409,
            details={
                "expected_revision": error.expected_revision,
                "actual_revision": error.actual_revision,
            },
        )
    if isinstance(error, harris_store.InvalidMatrixError):
        return _error_response(
            str(error),
            "invalid_matrix",
            400,
            details={"error_codes": list(error.error_codes)},
        )
    raise error


@bp.route("/api/harris-matrices", methods=["GET"])
def list_harris_matrices():
    return jsonify(harris_store.list_matrices())


@bp.route("/api/harris-matrices", methods=["POST"])
def create_harris_matrix():
    body, error_response = _request_object()
    if error_response is not None:
        return error_response

    try:
        initial_fields = _CreateMatrixRequest.model_validate(body)
    except ValidationError as error:
        return _invalid_request(error)

    try:
        matrix = harris_store.create_matrix(
            initial_fields.model_dump(mode="python")
        )
    except harris_store.InvalidMatrixError as error:
        return _store_error_response(error)
    return _matrix_response(matrix, 201)


@bp.route("/api/harris-matrices/<matrix_id>", methods=["GET"])
def get_harris_matrix(matrix_id):
    try:
        matrix = harris_store.load_matrix(matrix_id)
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)
    return _matrix_response(matrix)


@bp.route("/api/harris-matrices/<matrix_id>", methods=["PUT"])
def update_harris_matrix(matrix_id):
    body, error_response = _request_object()
    if error_response is not None:
        return error_response

    candidate_matrix_id = body.get("matrix_id")
    if candidate_matrix_id is not None and candidate_matrix_id != matrix_id:
        return _error_response(
            "Matrix ID in the request body must match the URL.",
            "matrix_id_mismatch",
            400,
        )

    expected_revision = body.get("revision")
    if (
        type(expected_revision) is not int
        or expected_revision < 0
    ):
        return _error_response(
            "Matrix revision must be a non-negative integer.",
            "invalid_matrix",
            400,
            details={"error_codes": []},
        )

    try:
        matrix = harris_store.save_matrix(
            matrix_id,
            body,
            expected_revision=expected_revision,
        )
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.MatrixConflictError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)
    return _matrix_response(matrix)
