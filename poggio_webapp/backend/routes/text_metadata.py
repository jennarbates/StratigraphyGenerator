"""Routes for extracting and verifying field-wall text metadata."""

import json
from pathlib import Path

from flask import Blueprint, abort, jsonify, request
from pipeline import extract_text as p_extract_text
from pydantic import ValidationError

from ..errors import _friendly_error
from ..jobs import job_dir, load_meta, save_meta
from ..tasks import start_task


bp = Blueprint("text_metadata", __name__)

STATUS_KEY = "text_verification_status"
ERROR_KEY = "text_extraction_error"


def _safe_extraction_error(error: Exception) -> str:
    """Return a useful error without persisting exception or credential data."""
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


def _run_text_extraction_task(
    job_id: str,
    image_path: str,
    api_key: str,
    output_path: str,
    progress_cb=None,
) -> dict:
    """Run extraction and durably record its success or safe failure state."""
    try:
        result = p_extract_text.run_text_extraction(
            image_path,
            api_key,
            output_path,
            progress_cb=progress_cb,
        )
    except Exception as error:
        safe_error = _safe_extraction_error(error)
        meta = load_meta(job_id)
        meta[STATUS_KEY] = "error"
        meta[ERROR_KEY] = safe_error
        save_meta(job_id, meta)
        raise RuntimeError(safe_error) from error

    meta = load_meta(job_id)
    meta["text_candidates_path"] = output_path
    meta[STATUS_KEY] = "ready_for_review"
    meta.pop(ERROR_KEY, None)
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
    api_key = body.get("api_key")
    if not api_key:
        abort(400, description="api_key is required")

    output_path = job_dir(job_id) / "03_extraction" / "text_candidates.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    meta[STATUS_KEY] = "extracting"
    meta.pop(ERROR_KEY, None)
    save_meta(job_id, meta)

    task_id = start_task(
        _run_text_extraction_task,
        job_id,
        image_path,
        api_key,
        str(output_path),
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
