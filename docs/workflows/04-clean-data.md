---
title: Clean up the data
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/normalize.js
  - poggio_webapp/backend/routes/processing.py
  - poggio_webapp/pipeline/normalizer.py
verified_against: a8b58f1
---

# Clean up the data

This page covers the cleanup step that standardizes extraction JSON before the validator checks it.

## Before you start

Have a saved extraction from manual tracing, import, or AI extraction. Cleanup is a formatting pass, not a geometry rescue step. It can remove obvious duplicates and null-like strings, but it cannot remeasure a line or replace a missing boundary.

Synthetic documentation example: the JSON below is invented for documentation and shows the kinds of issues cleanup removes.

```json
{
  "source": "extraction",
  "trenchProfiles": [
    {
      "face": "Synthetic face",
      "layers": [
        {
          "layerName": "Layer A",
          "description": "null",
          "featuresInLayer": [
            {
              "feature": "Floor",
              "shapePoints": [{"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.25}]
            },
            {
              "feature": "Floor",
              "shapePoints": [{"xCoordinateMeters": 0.0, "yCoordinateMeters": 0.25}]
            }
          ]
        }
      ]
    }
  ]
}
```

## Do this

1. Input: a saved extraction.
   - Action: run the cleanup step once after the extraction exists and before validation. The app does not need extra settings.
   - Artifact: a cleaned JSON file written to the job's normalize folder.
2. Input: the cleaned file.
   - Action: inspect the output if the app reports changes. The cleaner removes null-like strings such as `null` or `n/a`, removes duplicate floor features, and removes duplicate cross-layer features when the same feature shape appears in more than one layer.
   - Artifact: a normalized file that is easier to validate.

## What the application creates

- A cleaned extraction JSON file.
- A short change log that says what the cleaner removed or normalized.
- A later input file for the validation step.

## Check your result

- The cleaned file is written successfully.
- The change log describes the cleanup actions plainly.
- The geometry itself is still the same drawing, just represented more cleanly.

## Common problems

- You expected cleanup to fix a bad boundary shape; it will not.
- The cleaner reports no changes because the file did not contain the kinds of duplicates or null strings it knows how to remove.
- A later validation step still warns about geometry because cleanup did not change the line positions.

## Under the hood

The UI in `poggio_webapp/static/app/stages/normalize.js` calls the normalize route in `poggio_webapp/backend/routes/processing.py`. The cleaner in `poggio_webapp/pipeline/normalizer.py` performs the null-string cleanup and duplicate-feature removal.

## Next

Continue to [Check for problems](05-check-problems.md) so the cleaned extraction is reviewed before you move on.
