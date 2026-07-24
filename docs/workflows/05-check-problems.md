---
title: Check for problems
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/validate.js
  - poggio_webapp/backend/routes/processing.py
  - poggio_webapp/pipeline/validator.py
  - tests/test_validator.py
verified_against: a8b58f1
---

# Check for problems

This page explains how the validation step separates hard errors from review warnings and tells you what to inspect for each warning.

## Before you start

Run this step after cleanup and before you register the drawing on site. Errors and warnings are not the same thing: an error means the app treats the geometry as not ready to continue, while a warning means the extraction should be reviewed by a person.

Synthetic documentation example: the simplified JSON below is invented for documentation and is not a real excavation dataset.

```json
{
  "source": "extraction",
  "trenchProfiles": [
    {
      "face": "Synthetic face",
      "layers": [
        {
          "layerName": "Layer A",
          "bottomBoundary": [{"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.30}]
        }
      ]
    }
  ]
}
```

## Do this

1. Input: the cleaned extraction.
   - Action: run validation once. The app shows how many serious problems and how many review items remain.
   - Artifact: an error list and a warning list for the current extraction.
2. Input: the validation report.
   - Action: fix every error before continuing. Review every warning with the source drawing in front of you.
   - Artifact: a clearer understanding of whether the extraction is safe to use.
3. Input: each warning item.
   - Action: use the warning checklist below to decide what to inspect.
   - Artifact: a documented review decision for the warning.

### Warning checklist

- Uniform-spacing warning
  - Trigger: the validator sees boundary vertices spaced at a very regular interval, which can look like mechanically estimated points instead of measured marks.
  - Blocking behavior: this is a warning only; it does not stop the workflow, but it should make you distrust the geometry until you compare it to the source drawing.
  - User inspection step: open the original drawing and compare the marked points to the extracted points. If they look evenly spaced because they were estimated rather than read from the drawing, re-extract or re-trace the boundary.
- Copied-offset boundary warning
  - Trigger: two layer boundaries have nearly the same shape and are shifted by a nearly constant depth, which is a sign of copied geometry.
  - Blocking behavior: this is a warning only; it does not stop the workflow, but it is a reason to review the layer boundaries carefully.
  - User inspection step: inspect the two layers side by side and confirm that each boundary was traced from the drawing rather than copied from the layer above.
- Crossing layers error
  - Trigger: a lower layer boundary sits above the previous layer boundary at the same x-position.
  - Blocking behavior: this is an error and blocks continuation to the next required step.
  - User inspection step: inspect the two boundaries in the drawing and fix the layer order or the boundary points before continuing.
- Implausible depth warning
  - Trigger: a point is deeper than the configured threshold, which defaults to 5.0 metres.
  - Blocking behavior: this is a warning only; it does not block continuation.
  - User inspection step: check whether the point is genuinely deep or whether the coordinate was entered or read incorrectly.
- Feature placement warning
  - Trigger: a feature point lies outside the top and bottom bounds of the layer it is assigned to.
  - Blocking behavior: this is a warning only; it does not block continuation.
  - User inspection step: inspect the feature's placement on the drawing and move or remove it if the layer assignment is wrong.
- Field-wall-specific warning
  - Trigger: the validator sees a field-wall extraction that references a locus number that is missing from `loci[]`, or it sees duplicate locus labels that could confuse the converter.
  - Blocking behavior: this is a warning only; it does not block continuation.
  - User inspection step: review the Munsell/locus list and the layer labels so the field-wall input matches the actual sheet.

## What the application creates

- A validation report with `errors` and `warnings` lists.
- A clear yes/no decision about whether the extraction is ready to continue.
- A record of review items that a person should inspect before the next step.

## Check your result

- Every error is fixed before you continue.
- Every warning is reviewed against the original drawing.
- The validation report is not treated as a science guarantee; it is a human-review aid.

## Common problems

- A warning is ignored because it looks small, but it still points to a line that may be wrong.
- An error is left in place because the user believes the step can continue anyway.
- A passing report with zero errors but one or more warnings still needs a person to inspect the geometry.

## Under the hood

The UI in `poggio_webapp/static/app/stages/validate.js` calls the validation route in `poggio_webapp/backend/routes/processing.py`, which runs `poggio_webapp/pipeline/validator.py`. The validator logic is covered by `tests/test_validator.py`, but the documentation should still treat warnings as review cues rather than proof of correctness.

## Next

Continue to the later registration and coordinate steps when the extraction is ready, or return to [Clean up the data](04-clean-data.md) if you need to revisit the cleanup pass.
