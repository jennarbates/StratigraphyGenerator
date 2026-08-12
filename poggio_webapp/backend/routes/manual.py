"""Manual tracing route.

Parses the request, calls pipeline.manual_extraction, writes the result into
the job directory. The conversion itself lives in the pipeline layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, abort, jsonify, request

from pipeline.manual_extraction import (
    build_fieldwall,
    build_illustrator,
    make_calibration,
)

from ..jobs import job_dir, load_meta, rel_url, save_meta

bp = Blueprint("manual", __name__)


@bp.route("/api/jobs/<job_id>/boundaries/manual", methods=["POST"])
def build_manual_extraction(job_id):
    meta = load_meta(job_id)
    if not meta.get("scan_path"):
        abort(400, description="upload a scan first")

    payload = request.get_json(force=True, silent=True) or {}
    try:
        calib = make_calibration(payload)
        fieldwall = meta.get("sheet_type") == "fieldwall"
        image_kind = payload.get("image")
        if image_kind == "clean" and meta.get("clean_image_path"):
            source_path = meta["clean_image_path"]
        elif image_kind == "rotated":
            rotated = job_dir(job_id) / "03_extraction" / "marker_source_rotated.png"
            source_path = str(rotated) if rotated.exists() else meta.get("scan_path")
        else:
            source_path = meta.get("scan_path")
        if fieldwall:
            data, warnings = build_fieldwall(payload, calib, source_path)
            filename = "field_wall_manual.json"
        else:
            data, warnings = build_illustrator(payload, calib, source_path)
            filename = "illustrator_manual.json"
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    out_dir = job_dir(job_id) / "03_extraction"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    raw = json.dumps(data, indent=2)
    out_path.write_text(raw)

    meta["extraction_path"] = str(out_path)
    meta["manual_image_path"] = source_path
    meta["manual_calibration"] = {
        "kind": "manual",
        "origin_px": payload["calibration"]["origin_px"],
        "ref_px": payload["calibration"]["ref_px"],
        "lowest_px": payload["calibration"]["lowest_px"],
        "ref_meters": payload["calibration"]["ref_meters"],
        "px_per_m": round(calib.px_per_m, 6),
    }
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)

    return jsonify(
        {
            "raw_json": raw,
            "warnings": warnings,
            "file_url": rel_url(job_id, Path(out_path)),
            "px_per_m": round(calib.px_per_m, 3),
            "n_boundaries": len(payload.get("boundaries") or []),
            "n_features": len(payload.get("features") or []),
        }
    )
