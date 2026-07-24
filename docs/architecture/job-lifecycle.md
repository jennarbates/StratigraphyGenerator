---
title: Job lifecycle
audience: developer
status: current
source_files:
  - poggio_webapp/app.py
  - poggio_webapp/backend/jobs.py
  - poggio_webapp/backend/routes/jobs.py
  - poggio_webapp/pipeline/editor.py
verified_against: a8b58f1
---

# Job lifecycle

The repository stores each attempt as a job directory with metadata that evolves as the workflow progresses.

## Responsibilities

- Create a job folder and initial metadata for a new attempt.
- Track status, stage, message, and task identifiers in meta.json.
- Support both the older upload-based workflow and the newer editor workflow without merging them into one code path.

## Inputs

- A new job request from the browser.
- Existing job identifiers and the current contents of the job directory.
- Editor state snapshots and finalized output data for the editor-specific path.

## Outputs

- A job folder under the repository job workspace.
- A meta.json file that records the job's current state.
- Editor-specific files such as editor_meta.json, editor_state.json, and finds.json when the manual editor flow is used.

## Main source files

- `poggio_webapp/backend/routes/jobs.py`
- `poggio_webapp/backend/jobs.py`
- `poggio_webapp/app.py`
- `poggio_webapp/pipeline/editor.py`

## Failure boundaries

- If the job folder is missing, the server treats the job as unknown and returns a 404.
- If the metadata file is missing or malformed, status endpoints can no longer describe the job accurately.
- The editor flow stores a separate editor_meta.json file, so a partially completed editor session does not automatically become a completed upload-based job.
- Task identifiers are stored in metadata, but the actual in-memory task registry is not durable across a restart.

## Related tests

- `tests/test_editor_routes.py`
- `tests/test_editor_status.py`
- `tests/test_finds_routes.py`

## Related workflow pages

- [Add a drawing](../workflows/01-add-drawing.md)
- [Trace the layers](../workflows/03-trace-layers.md)
- [Create the model](../workflows/07-create-model.md)

## Under the hood

The upload-based route in `poggio_webapp/backend/routes/jobs.py` creates a job folder and writes a minimal meta.json with the job identifier and sheet type. The newer editor workflow in `poggio_webapp/app.py` and `poggio_webapp/pipeline/editor.py` uses the same job workspace but adds editor-specific files and later writes finalized output into the same directory.

In both paths, the repository treats meta.json as the main state record for the job even though the editor flow also creates editor_meta.json and editor_state.json. That means the documentation should regard job lifecycle as a shared folder-based concept, while remembering that the editor path has its own session metadata.
