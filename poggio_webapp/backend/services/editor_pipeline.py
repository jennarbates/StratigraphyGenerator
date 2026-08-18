"""Drives a finalized editor session through the model-building pipeline.

Moved verbatim out of app.py during the modularization refactor. The chain is
normalize -> validate -> convert coordinates -> build (async), with meta.json
updated at each step so a browser polling /api/jobs/<id>/status sees progress
even across a server restart.
"""

import json
import threading

import storage
from pipeline import convert_coords, normalizer, validator
from pipeline import editor as editor_pipeline

from ..jobs import STATUS_MESSAGES, read_meta, write_meta
from ..tasks import start_task

EDITOR_PIPELINE_STATUSES = {
    "finalizing",
    "normalizing",
    "validating",
    "converting",
    "building",
    "complete",
    "error",
}
PIPELINE_SUBDIRECTORIES = (
    "01_scan",
    "02_preprocess",
    "03_extraction",
    "04_normalize_validate",
    "05_convert_coords",
    "06_gempy_model",
)

# Serializes the read-decide-write on meta.json in finalize_editor, so two
# concurrent finalize requests cannot both decide the job is idle and start
# the pipeline twice.
FINALIZATION_LOCK = threading.Lock()
META_LOCK = threading.Lock()


def run_editor_build(job_directory, build_fn, *args, log_cb=None):
    try:
        result = build_fn(*args, log_cb=log_cb)
    except Exception:
        with META_LOCK:
            meta = read_meta(job_directory)
            meta.update(
                {
                    "status": "error",
                    "stage": "building",
                    "message": "Model building failed.",
                    "pipeline_error": "Model building failed.",
                }
            )
            write_meta(job_directory, meta)
        raise

    with META_LOCK:
        meta = read_meta(job_directory)
        meta.update(
            {
                "status": "complete",
                "stage": "complete",
                "message": STATUS_MESSAGES["complete"],
            }
        )
        if isinstance(result, dict) and isinstance(result.get("outputs"), dict):
            meta["model_outputs"] = result["outputs"]
        meta.pop("pipeline_error", None)
        write_meta(job_directory, meta)
    return result


def run_editor_pipeline(job_id):
    job_directory = storage.JOBS_DIR / job_id
    for subdirectory in PIPELINE_SUBDIRECTORIES:
        (job_directory / subdirectory).mkdir(exist_ok=True)

    editor_meta = json.loads((job_directory / "editor_meta.json").read_text())
    editor_state = editor_pipeline.load_editor_state(job_id)
    extraction_path = job_directory / "extraction_output.json"
    meta = read_meta(job_directory)
    meta.update(
        {
            "job_id": job_id,
            "sheet_type": (
                "fieldwall"
                if editor_meta["schema_type"] == "FieldWallProfile"
                else "illustrator"
            ),
            "source": "manual_editor",
            "extraction_path": str(extraction_path),
            "status": "normalizing",
            "stage": "normalizing",
            "message": STATUS_MESSAGES["normalizing"],
        }
    )
    write_meta(job_directory, meta)

    normalized_path = job_directory / "04_normalize_validate" / "output_clean.json"
    normalized, normalization_log = normalizer.run_normalize(
        str(extraction_path),
        str(normalized_path),
    )
    meta.update(
        {
            "normalized_path": str(normalized_path),
            "canonical_path": str(normalizer.canonical_path_for(normalized_path)),
            "normalization_log": normalization_log,
            "status": "validating",
            "stage": "validating",
            "message": STATUS_MESSAGES["validating"],
        }
    )
    write_meta(job_directory, meta)

    validation_report = validator.run_validate(str(normalized_path))
    meta.update(
        {
            "validation_report": validation_report,
            "status": "converting",
            "stage": "converting",
            "message": STATUS_MESSAGES["converting"],
        }
    )
    write_meta(job_directory, meta)

    grid_config = editor_state.get("gridConfig")
    if not grid_config:
        grid_config = convert_coords.make_starter_config(normalized)
    points_path = job_directory / "05_convert_coords" / "points.csv"
    conversion = convert_coords.run_convert(
        normalized,
        grid_config,
        str(points_path),
    )
    if conversion["n_points"] == 0:
        raise ValueError("conversion produced 0 points")

    meta.update(
        {
            "points_csv": conversion["points_csv"],
            "orientations_csv": conversion["orientations_csv"],
            "status": "building",
            "stage": "building",
            "message": STATUS_MESSAGES["building"],
        }
    )
    write_meta(job_directory, meta)

    # Imported here rather than at module scope: gempy is an optional extra,
    # and everything above this line must work without it installed.
    from pipeline import build_gempy

    output_prefix = str(job_directory / "06_gempy_model" / "trench_model")
    with META_LOCK:
        task_id = start_task(
            run_editor_build,
            job_directory,
            build_gempy.run_build,
            meta["points_csv"],
            meta["orientations_csv"],
            output_prefix,
        )
        meta = read_meta(job_directory)
        meta.update(
            {
                "task_id": task_id,
                "gempy_task_id": task_id,
            }
        )
        write_meta(job_directory, meta)
    return task_id
