---
title: Asynchronous tasks
audience: developer
status: current
source_files:
  - poggio_webapp/backend/tasks.py
  - poggio_webapp/backend/routes/extraction.py
  - poggio_webapp/backend/routes/markers.py
  - poggio_webapp/backend/routes/gempy.py
  - poggio_webapp/backend/routes/task_status.py
verified_against: a8b58f1
---

# Asynchronous tasks

Some steps are run in a background thread so the browser can continue working while the server processes data.

## Responsibilities

- Create a task record with status, log, and timing information for each background job.
- Start a thread for long-running work such as extraction, marker assignment, and GemPy model builds.
- Expose task status through a GET endpoint so the UI can poll for completion.

## Inputs

- A callable function plus its arguments from the route layer.
- Optional progress callbacks when the called function expects them.
- The task identifier returned to the client.

## Outputs

- A task entry stored in the in-memory task registry.
- A status payload with log lines and either a result or an error.
- A task identifier that the frontend can use to poll.

## Main source files

- `poggio_webapp/backend/tasks.py`
- `poggio_webapp/backend/routes/extraction.py`
- `poggio_webapp/backend/routes/markers.py`
- `poggio_webapp/backend/routes/gempy.py`
- `poggio_webapp/backend/routes/task_status.py`

## Failure boundaries

- The task registry lives in memory and is not persisted to disk, so a restart loses the task state.
- If a task raises an exception, the task record is marked as error and the error is stored in the task entry.
- The polling endpoint returns 404 for unknown task identifiers, which means a stale or lost task cannot be inspected after a restart.
- The async model is separate from the durable job metadata and should not be treated as a full job persistence layer.

## Related tests

- `tests/test_editor_status.py`

## Related workflow pages

- [Alternative import and AI extraction](../workflows/03-alternative-import-and-ai.md)
- [Create the model](../workflows/07-create-model.md)

## Under the hood

The task helper in `poggio_webapp/backend/tasks.py` uses a daemon thread to run the supplied callable and updates a shared dictionary with the current status. The route modules call that helper when a workflow step needs a background operation, but the task store remains process-local. This is sufficient for the current local-development workflow, but it is an important limitation for restart resilience and for any future multi-process deployment.
