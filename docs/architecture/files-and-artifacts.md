---
title: Files and artifacts
audience: developer
status: current
source_files:
  - poggio_webapp/backend/routes/jobs.py
  - poggio_webapp/backend/routes/pages.py
  - poggio_webapp/backend/routes/scans.py
  - poggio_webapp/backend/routes/preprocess.py
  - poggio_webapp/backend/routes/processing.py
  - poggio_webapp/backend/routes/manual.py
  - poggio_webapp/app.py
verified_against: a8b58f1
---

# Files and artifacts

The repository stores job artifacts in numbered subfolders so each stage leaves a visible trail of intermediate files.

## Responsibilities

- Keep uploaded and generated files inside the job directory instead of in an unrelated temporary location.
- Preserve stage-specific artifacts such as scans, preprocessed images, extraction JSON, validation output, converted CSVs, and model files.
- Make the current job's artifacts reachable through the backend's file-serving routes.

## Inputs

- File uploads from users.
- Outputs from the preprocessing, extraction, normalization, conversion, and model-building steps.
- Existing job identifiers that the server uses to resolve the correct folder.

## Outputs

- Job folders with subfolders such as 01_scan, 02_preprocess, 03_extraction, 04_normalize_validate, 05_convert_coords, and 06_gempy_model.
- File URLs that the browser can load or download.
- Metadata entries in meta.json that reference the current files.

## Main source files

- `poggio_webapp/backend/routes/jobs.py`
- `poggio_webapp/backend/routes/scans.py`
- `poggio_webapp/backend/routes/preprocess.py`
- `poggio_webapp/backend/routes/processing.py`
- `poggio_webapp/backend/routes/manual.py`
- `poggio_webapp/backend/routes/pages.py`
- `poggio_webapp/app.py`

## Failure boundaries

- If an expected artifact is missing, later steps can fail with a clear 400 error or an empty result rather than silently proceeding.
- The file-serving route refuses paths that escape the job directory, so the server does not expose unrelated files.
- The metadata file can point to a file that no longer exists, which is an important limitation of the current storage model.
- The editor flow uses a separate set of files and does not automatically mirror all upload-based artifacts.

## Related tests

- `tests/test_editor_routes.py`
- `tests/test_editor_status.py`
- `tests/test_finds_routes.py`

## Related workflow pages

- [Prepare the image](../workflows/02-prepare-image.md)
- [View and download](../workflows/08-view-and-download.md)

## Under the hood

The directory layout is created when a new job is created in `poggio_webapp/backend/routes/jobs.py` and later reused by the route modules that write outputs. The file-serving endpoint in `poggio_webapp/backend/routes/jobs.py` resolves a requested path relative to the job folder and rejects escape attempts. That gives the system a simple and auditable artifact model, even though it is not a general-purpose distributed storage layer.

The numbered folders are a useful map for developers even when the current workflow is not fully linear. Some steps produce artifacts for later review, while others only create a working copy for the next step.
