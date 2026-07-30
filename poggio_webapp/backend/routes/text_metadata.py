"""Routes for extracting and verifying field-wall text metadata."""

import json
import os
from pathlib import Path

from flask import Blueprint, abort, jsonify, request
from pydantic import ValidationError

from pipeline import extract_fieldwall as p_extract_fieldwall
from pipeline import extract_text as p_extract_text

from ..errors import _friendly_error
from ..jobs import job_dir, load_meta, save_meta
from ..tasks import start_task

bp = Blueprint("text_metadata", __name__)

STATUS_KEY = "text_verification_status"
ERROR_KEY = "text_extraction_error"


def _safe_extraction_error(error: Exception) -> str:
    """Return a useful error without persisting exception or credential data."""
    if (
        getattr(error, "code", None) == 400
        and "response_schema" in str(error)
        and "Invalid JSON payload" in str(error)
    ):
        return (
            "Gemini rejected the structured-output schema. "
            "This is a server configuration error, not an API-key error."
        )
    if getattr(error, "code", None) in {
        400,
        401,
        403,
        429,
        500,
        502,
        503,
        504,
    }:
        return _friendly_error(error)
    if isinstance(error, ValueError):
        return "Text extraction returned invalid structured output."
    return "Text extraction failed. Please try again."


def _run_fieldwall_extraction_task(
    job_id: str,
    image_path: str,
    square_cm: float,
    api_key: str,
    extraction_path: str,
    candidates_path: str,
    max_output_tokens: int = 65_536,
    progress_cb=None,
) -> dict:
    """Run the established field-wall extraction and expose its text for review."""
    try:
        raw_json, warning = p_extract_fieldwall.run_extraction(
            image_path,
            square_cm,
            extraction_path,
            api_key,
            max_output_tokens=max_output_tokens,
            progress_cb=progress_cb,
        )
        if warning:
            raise ValueError(warning)
        result = p_extract_text.candidates_from_fieldwall_extraction(
            raw_json,
            candidates_path,
        )
    except Exception as error:
        safe_error = _safe_extraction_error(error)
        meta = load_meta(job_id)
        meta[STATUS_KEY] = "error"
        meta[ERROR_KEY] = safe_error
        save_meta(job_id, meta)
        raise RuntimeError(safe_error) from error

    meta = load_meta(job_id)
    meta["extraction_path"] = extraction_path
    meta["text_candidates_path"] = candidates_path
    meta[STATUS_KEY] = "ready_for_review"
    meta.pop(ERROR_KEY, None)
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)
    return result


@bp.route("/api/jobs/<job_id>/text-extraction", methods=["POST"])
def start_text_extraction(job_id):
    meta = load_meta(job_id)
    if meta.get("sheet_type") != "fieldwall":
        abort(400, description="text extraction is only available for field-wall jobs")

    image_path = meta.get("clean_image_path") or meta.get("scan_path")
    if not image_path:
        abort(400, description="upload a scan first")
    if not Path(image_path).is_file():
        abort(400, description="the job's uploaded image is missing on disk")

    body = request.get_json(force=True, silent=True) or {}
    api_key = body.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        abort(400, description="api_key is required")

    try:
        square_cm = float(body.get("square_cm"))
    except (TypeError, ValueError):
        square_cm = 0
    if square_cm <= 0:
        abort(400, description="square_cm is required for field-wall sheets")

    max_output_tokens = int(body.get("max_output_tokens", 65_536))
    extraction_dir = job_dir(job_id) / "03_extraction"
    extraction_path = extraction_dir / "field_wall.json"
    candidates_path = extraction_dir / "text_candidates.json"
    extraction_dir.mkdir(parents=True, exist_ok=True)

    meta[STATUS_KEY] = "extracting"
    meta.pop(ERROR_KEY, None)
    save_meta(job_id, meta)

    task_id = start_task(
        _run_fieldwall_extraction_task,
        job_id,
        image_path,
        square_cm,
        api_key,
        str(extraction_path),
        str(candidates_path),
        max_output_tokens,
    )

    # Reload so a very fast task cannot have ready_for_review/error replaced
    # by the earlier extracting snapshot.
    meta = load_meta(job_id)
    meta["text_extraction_task_id"] = task_id
    save_meta(job_id, meta)
    return jsonify({"task_id": task_id})


def _load_json_file(path_value):
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@bp.route("/api/jobs/<job_id>/text-extraction", methods=["GET"])
def get_text_extraction(job_id):
    meta = load_meta(job_id)
    payload = {
        "status": meta.get(STATUS_KEY, "not_started"),
    }

    candidates = _load_json_file(meta.get("text_candidates_path"))
    if candidates is not None:
        payload["candidates"] = candidates

    verified_text = _load_json_file(meta.get("verified_text_path"))
    if verified_text is not None:
        payload["verified_text"] = verified_text

    if meta.get(ERROR_KEY):
        payload["error"] = meta[ERROR_KEY]

    return jsonify(payload)


@bp.route("/api/jobs/<job_id>/text-verification", methods=["POST"])
def save_text_verification(job_id):
    meta = load_meta(job_id)
    body = request.get_json(force=True, silent=True)
    try:
        verified = p_extract_text.VerifiedFieldWallText.model_validate(body)
    except ValidationError as error:
        return jsonify({"error": f"invalid verified text: {error}"}), 400

    if verified.reviewCompleted is not True:
        abort(400, description="reviewCompleted must be true")

    saved = verified.model_dump(mode="json")
    output_path = job_dir(job_id) / "03_extraction" / "verified_text.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(saved, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    meta["verified_text_path"] = str(output_path)
    meta[STATUS_KEY] = "verified"
    meta.pop(ERROR_KEY, None)
    save_meta(job_id, meta)
    return jsonify(saved)


@bp.route("/api/jobs/<job_id>/text-verification/skip", methods=["POST"])
def skip_text_verification(job_id):
    meta = load_meta(job_id)
    meta[STATUS_KEY] = "skipped"
    meta.pop(ERROR_KEY, None)
    save_meta(job_id, meta)
    return jsonify({"status": "skipped"})
