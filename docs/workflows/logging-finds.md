---
title: Log a find
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/editor/finds.py
  - poggio_webapp/backend/routes/finds.py
  - poggio_webapp/static/finds/index.js
  - poggio_webapp/templates/finds.html
verified_against: ae2fc1d
---

# Log a find

Record an artifact without changing the stratigraphic drawing, and later sync the find into the finalized output.

!!! warning

    Synthetic documentation example only. A logged find is a record of an artifact observation, not a scientific claim about the site sequence.

## Before you start

You need an existing job or a job that has at least enough context for a face name. Finds are stored independently from the stratigraphic geometry, so they can be entered before or after the drawing is finalized.

The finds page is reachable only by address: open <http://localhost:5000/finds> directly. No control elsewhere in the application links to it. See [capability status](../project/capability-status.md).

## Do this

1. Open the finds page.
   - Action: choose the job you want to annotate.
   - Artifact: a new find entry for that job.
2. Mark the find location.
   - Action: select a face or enter one manually, then click the reference canvas once.
   - Artifact: an $x$, $y$, and elevation location for the find.
3. Describe the find.
   - Action: enter locus, elevation, and a short description.
   - Artifact: a stored find record.
4. Choose **Log find**.
   - Artifact: a `finds.json` file stored with the job. The find list is copied into the finalized `extraction_output.json` whenever one exists, and again when the output is finalized.

## What the application creates

- A stored find entry with a generated find ID.
- A `finds.json` file for the job.
- A sync into the finalized `extraction_output.json`, run when a find is logged or deleted after finalization and again when the output is finalized.

## Check your result

- The find is listed under the selected job.
- The location and description are complete enough for review.
- The record is clearly separate from the model geometry and should not be treated as a geological interpretation.

## Common problems

- The find is entered as if it were a layer boundary, which would mix artifact observation with geometry.
- A face name is missing and the entry is not associated with a real face or a placeholder face label.
- Placeholder values are later presented as if they came from a full surveyed record.

## Under the hood

The finds page posts to the routes in `poggio_webapp/backend/routes/finds.py`, which store the record in the job's `finds.json` through `poggio_webapp/pipeline/editor/finds.py` and re-sync the list into `extraction_output.json` whenever that finalized output exists. This is separate from the point conversion and model-building pipeline.

## Next

Return to [First model tutorial](../start-here/first-model.md) to follow a complete synthetic example from tracing to model output.
