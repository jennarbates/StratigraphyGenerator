"""Read-modify-write transactions against a stored Harris Matrix.

The domain work already lives elsewhere -- pipeline/harris_import.py,
pipeline/harris_suggestions.py, backend/harris_store.py. What was still inside
the view functions was the *sequence*: load at an expected revision, transform,
save at that same revision. Both flows are optimistic-concurrency transactions,
and both were spelled out inline where they could not be exercised without an
HTTP request.
"""

import storage

from .. import harris_store
from pipeline.harris_import import import_source_jobs
from pipeline.harris_suggestions import generate_suggestions, review_suggestion


class SuggestionNotFoundError(LookupError):
    """The matrix loaded, but carries no suggestion with that id."""

    def __init__(self, suggestion_id):
        self.suggestion_id = suggestion_id
        super().__init__(f"Suggestion {suggestion_id} was not found.")


def load_at_revision(matrix_id, expected_revision):
    """The stored matrix, or MatrixConflictError if it has moved on."""
    matrix = harris_store.load_matrix(matrix_id)
    if matrix.revision != expected_revision:
        raise harris_store.MatrixConflictError(
            expected_revision,
            matrix.revision,
        )
    return matrix


def import_sources(matrix_id, job_ids, revision):
    """Import jobs into the matrix and regenerate suggestions.

    Returns (saved_matrix, warnings).
    """
    current = load_at_revision(matrix_id, revision)
    imported, warnings = import_source_jobs(current, job_ids, storage.JOBS_DIR)
    with_suggestions = generate_suggestions(imported, storage.JOBS_DIR)
    saved = harris_store.save_matrix(
        matrix_id,
        with_suggestions,
        expected_revision=revision,
    )
    return saved, warnings


def review(matrix_id, suggestion_id, action, revision):
    """Accept or reject one suggestion. Returns the saved matrix."""
    current = load_at_revision(matrix_id, revision)
    if not any(
        suggestion.id == suggestion_id for suggestion in current.suggestions
    ):
        raise SuggestionNotFoundError(suggestion_id)
    reviewed = review_suggestion(current, suggestion_id, action)
    return harris_store.save_matrix(
        matrix_id,
        reviewed,
        expected_revision=revision,
    )
