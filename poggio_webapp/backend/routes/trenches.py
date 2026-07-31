"""Routes for trenches: list them, build one, serve its files.

The grouping and build rules live in backend/services/trench_builder.py. This
module parses requests, maps TrenchBuildError to a 400, and serializes.
"""

from flask import Blueprint, abort, jsonify, request, send_file

from ..services.trench_builder import (
    GempyUnavailableError,
    TrenchBuildError,
    build,
    grouped_members,
    label_variants,
    public_member,
    trench_dir,
)

bp = Blueprint("trenches", __name__)


@bp.route("/api/trenches")
def list_trenches():
    grouped = grouped_members()
    payload = {
        "trenches": {
            label: [public_member(m) for m in members]
            for label, members in grouped.items()
        }
    }
    # Only present for trenches whose jobs were recorded under more than one
    # spelling, so the interface can show that a merge happened.
    variants = {
        label: found
        for label, members in grouped.items()
        if (found := label_variants(members))
    }
    if variants:
        payload["label_variants"] = variants
    return jsonify(payload)


@bp.route("/api/trenches/<label>/build", methods=["POST"])
def build_trench(label):
    body = request.get_json(force=True, silent=True) or {}
    try:
        return jsonify(build(label, body))
    except GempyUnavailableError as error:
        return jsonify({"error": str(error)}), 400
    except TrenchBuildError as error:
        abort(400, description=str(error))


@bp.route("/api/trenches/<label>/file")
def get_trench_file(label):
    """Serve a file from one trench directory, refusing to escape it."""
    rel = request.args.get("path")
    if not rel:
        abort(400, description="missing path")
    base = trench_dir(label).resolve()
    target = (base / rel).resolve()
    if base not in target.parents and target != base:
        abort(400, description="invalid path")
    if not target.is_file():
        abort(404)
    return send_file(target)
