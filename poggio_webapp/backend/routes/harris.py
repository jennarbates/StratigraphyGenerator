"""API routes for Harris Matrix workspaces."""

from typing import Annotated, Literal

from flask import Blueprint, Response, jsonify, render_template, request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)

from pipeline.harris_import import HarrisImportError, discover_source_jobs
from pipeline.harris_suggestions import HarrisSuggestionError
from pipeline.harris_render import HarrisRenderError, render_harris_svg

import storage

from .. import harris_store
from ..services import harris_workspace


bp = Blueprint("harris", __name__)

TrimmedString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, strict=True),
]
JobId = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{12}$", strict=True),
]
Revision = Annotated[int, Field(ge=0, strict=True)]


class _CreateMatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TrimmedString = "Untitled Harris Matrix"
    site: TrimmedString = ""
    trench: TrimmedString = ""


class _ImportSourcesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_ids: Annotated[list[JobId], Field(min_length=1)]
    revision: Revision


class _ReviewSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["accept", "reject"]
    revision: Revision


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


def _export_response(content, mimetype, filename, *, attachment=True):
    disposition = "attachment" if attachment else "inline"
    response = Response(content, mimetype=mimetype)
    response.headers["Content-Disposition"] = (
        f'{disposition}; filename="{filename}"'
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _import_response(matrix, warnings):
    payload = matrix.model_dump(mode="json")
    payload["import_warnings"] = warnings
    return jsonify(payload)


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




@bp.route("/harris")
def harris_index_page():
    return render_template("harris_index.html")


@bp.route("/harris/<matrix_id>")
def harris_editor_page(matrix_id):
    try:
        harris_store.load_matrix(matrix_id)
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)
    return render_template(
        "harris_editor.html",
        matrix_id=matrix_id,
    )


@bp.route("/api/harris-matrices", methods=["GET"])
def list_harris_matrices():
    return jsonify(harris_store.list_matrices())


@bp.route("/api/harris-source-jobs", methods=["GET"])
def list_harris_source_jobs():
    return jsonify(discover_source_jobs(storage.JOBS_DIR))


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


@bp.route("/api/harris-matrices/<matrix_id>/export.json", methods=["GET"])
def export_harris_matrix_json(matrix_id):
    try:
        matrix = harris_store.load_matrix(matrix_id)
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)

    filename = f"harris-matrix-{matrix.matrix_id}.json"
    return _export_response(
        matrix.model_dump_json(indent=2) + "\n",
        "application/json",
        filename,
    )


@bp.route("/api/harris-matrices/<matrix_id>/export.svg", methods=["GET"])
def export_harris_matrix_svg(matrix_id):
    try:
        matrix = harris_store.load_matrix(matrix_id)
        svg = render_harris_svg(matrix)
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)
    except HarrisRenderError as error:
        return _error_response(
            str(error),
            "matrix_render_error",
            400,
        )

    filename = f"harris-matrix-{matrix.matrix_id}.svg"
    return _export_response(
        svg,
        "image/svg+xml",
        filename,
        attachment=request.args.get("inline") != "1",
    )


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


@bp.route(
    "/api/harris-matrices/<matrix_id>/sources",
    methods=["POST"],
)
def import_harris_sources(matrix_id):
    body, error_response = _request_object()
    if error_response is not None:
        return error_response

    try:
        import_request = _ImportSourcesRequest.model_validate(body)
    except ValidationError as error:
        return _invalid_request(error)

    try:
        saved, warnings = harris_workspace.import_sources(
            matrix_id,
            import_request.job_ids,
            import_request.revision,
        )
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.MatrixConflictError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)
    except HarrisImportError as error:
        return _error_response(
            str(error),
            "source_import_error",
            400,
        )
    except HarrisSuggestionError as error:
        return _error_response(
            str(error),
            "suggestion_generation_error",
            400,
        )
    return _import_response(saved, warnings)


@bp.route(
    (
        "/api/harris-matrices/<matrix_id>/suggestions/"
        "<suggestion_id>"
    ),
    methods=["POST"],
)
def review_harris_suggestion(matrix_id, suggestion_id):
    body, error_response = _request_object()
    if error_response is not None:
        return error_response

    try:
        review_request = _ReviewSuggestionRequest.model_validate(body)
    except ValidationError as error:
        return _invalid_request(error)

    try:
        saved = harris_workspace.review(
            matrix_id,
            suggestion_id,
            review_request.action,
            review_request.revision,
        )
    except harris_workspace.SuggestionNotFoundError as error:
        return _error_response(str(error), "suggestion_not_found", 404)
    except (
        harris_store.InvalidMatrixIdError,
        harris_store.MatrixNotFoundError,
        harris_store.MatrixConflictError,
        harris_store.InvalidMatrixError,
    ) as error:
        return _store_error_response(error)
    except HarrisSuggestionError as error:
        return _error_response(
            str(error),
            "suggestion_review_error",
            400,
        )
    return _matrix_response(saved)
