---
title: Markers and features
audience: beginner
status: current
source_files:
  - poggio_webapp/backend/routes/markers.py
  - poggio_webapp/backend/routes/features.py
  - poggio_webapp/pipeline/detect_markers.py
  - poggio_webapp/pipeline/detect_features.py
verified_against: a8b58f1
---

# Markers and features

This page explains the current status of marker and feature handling so you can tell the difference between what the app can do today and what remains experimental or backend-only.

## Before you start

The current workflow is built around manual tracing first. The marker and feature modules below are secondary and should not be treated as the default operator path.

Status at a glance:

- Supported UI: manual feature drawing while you trace a layer or locus.
- Experimental UI: automatic AI extraction can create geometry that includes features, but the output still needs human review.
- Backend-only: marker detection and feature detection routes and pipeline modules exist, but they are not exposed as active steps in the live workflow.
- Blocked: the live UI does not register marker-detection or feature-detection stages as clickable workflow steps.

Synthetic documentation example: the feature object below is invented for documentation and uses no real job data.

```json
{
  "feature": "Synthetic pit cut",
  "description": "invented outline for documentation",
  "shapePoints": [
    {"xCoordinateMeters": 0.2, "yCoordinateMeters": 0.15},
    {"xCoordinateMeters": 0.4, "yCoordinateMeters": 0.18},
    {"xCoordinateMeters": 0.3, "yCoordinateMeters": 0.28}
  ]
}
```

## Do this

1. Input: a manual drawing you are already tracing.
   - Action: add features directly while you work on the layer or locus boundaries. This is the supported UI path for drawing a feature shape.
   - Artifact: the saved extraction contains feature geometry and a layer assignment.
2. Input: an AI-assisted extraction or an imported extraction.
   - Action: inspect any feature geometry that arrives with the file. The current UI does not promise that the feature data is accurate, and the later validation step is the place to catch out-of-band positions.
   - Artifact: a saved extraction that may contain feature geometry that still needs review.
3. Input: a backend-only detection workflow.
   - Action: treat marker or feature detection as a developer or specialist path only. The backend routes exist, but the current operator UI does not expose them as a normal next step.
   - Artifact: detection output that remains outside the main documented workflow unless a developer wires it into the UI.

## What the application creates

- Manual feature shapes inside a layer's saved extraction data.
- Optional feature geometry from imported or AI-generated files.
- Backend-only detection output that is not installed as the main operator workflow path.

## Check your result

- Manual features appear in the saved extraction for the correct layer.
- AI-generated or imported features are reviewed, not assumed accurate.
- The validator can flag feature points that sit outside the layer band.

## Common problems

- A feature is drawn but never attached to a layer, so it is hard to interpret later.
- An AI-generated feature looks plausible but sits outside the expected layer range.
- The marker or feature detection route is available in the backend, but the live UI does not present it as a step.

## Under the hood

The backend routes in `poggio_webapp/backend/routes/markers.py` and `poggio_webapp/backend/routes/features.py` implement detection-related work, while the pipeline modules in `poggio_webapp/pipeline/detect_markers.py` and `poggio_webapp/pipeline/detect_features.py` contain the logic. The current live workflow still prioritizes the manual tracing path and leaves these stages as secondary or developer-only capabilities.

## Next

Continue to [Clean up the data](04-clean-data.md) so the extraction is made consistent, or return to [Alternative import and AI extraction](03-alternative-import-and-ai.md) if you still need to source the data.
