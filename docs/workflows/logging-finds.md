---
title: Log a find
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/editor.py
  - poggio_webapp/templates/finds.html
verified_against: a8b58f1
---

# Log a find

Record an artifact without changing the stratigraphic drawing, and later sync the find into the finalized output.

> [!warning]
> Synthetic documentation example only. A logged find is a record of an artifact observation, not a scientific claim about the site sequence.

## Before you start

You need an existing job or a job that has at least enough context for a face name. Finds are stored independently from the stratigraphic geometry, so they can be entered before or after the drawing is finalized.

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
4. Save the find.
   - Artifact: a `finds.json` file stored with the job. When the output is finalized, the find list can be copied into the finalized output payload.

## What the application creates

- A stored find entry with a generated find ID.
- A `finds.json` file for the job.
- A later sync into the finalized `extraction_output.json` when the output is finalized.

## Check your result

- The find is listed under the selected job.
- The location and description are complete enough for review.
- The record is clearly separate from the model geometry and should not be treated as a geological interpretation.

## Common problems

- The find is entered as if it were a layer boundary, which would mix artifact observation with geometry.
- A face name is missing and the entry is not associated with a real face or a placeholder face label.
- Placeholder values are later presented as if they came from a full surveyed record.

## Under the hood

The finds page writes to the job's `finds.json` file, and the editor pipeline can later copy that list into the finalized output. This is separate from the point conversion and model-building pipeline.

## Next

Return to [First model tutorial](../start-here/first-model.md) to follow a complete synthetic example from tracing to model output.
