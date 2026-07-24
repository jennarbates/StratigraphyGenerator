---
title: Trace the layers
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/draw.js
  - poggio_webapp/backend/routes/manual.py
verified_against: 077f108
---

# Trace the layers

This page covers the manual tracing path from a prepared image to a saved extraction JSON.

## Before you start

Use the prepared image from the previous step. You should also know whether you are working from an illustrated trench sheet or a hand-drawn field sheet, because the tracing instructions differ slightly.

Synthetic documentation example: the generated example images in [docs/fixtures/README.md](../fixtures/README.md) show the kinds of lines you might trace in practice.

## Do this

1. Input: the prepared image and a sheet type.
   - Action: open the drawing and, if needed, rotate it so it is upright. For non-PDF uploads, the app offers a rotation choice before the tracing workspace opens.
   - Artifact: the drawing is displayed in the tracing workspace.
2. Input: the drawing and the real width of a known distance on it.
   - Action: click the three calibration points in order: the top-left reference point, the top-right reference point, and the lowest point. Enter the real distance between the first two clicks in metres.
   - Artifact: the app stores calibration values that convert pixels into metres.
3. Input: the calibrated drawing.
   - Action: for an illustrated sheet, start the surface line, then add the lower soil lines and names. For a field sheet, start the top of each locus, then add the final bottom line below the deepest locus. Add optional internal features when you have them.
   - Artifact: the app records boundary points, feature shapes, and optional layer or locus metadata.
4. Input: the traced boundaries and any notes.
   - Action: enter the trench name, the face name, and the per-layer or per-locus metadata, then save the drawing.
   - Artifact: the app builds a manual extraction JSON file and reports any warnings.

<!-- SCREENSHOT: 03-trace-calibration.png
State: synthetic field-wall fixture, calibration complete
Callouts: top-left, top-right, lowest point, real width
-->

## What the application creates

- Calibration metadata that records the three click locations and the real distance used for scaling.
- Boundary polylines for the surface or locus tops and the lower boundaries.
- Optional feature polygons and descriptive metadata.
- A manual extraction file in the extraction folder, such as an illustrator or field-wall JSON artifact.

## Check your result

- The three calibration clicks are complete and the real width has been entered.
- At least one lower boundary or locus top is present, and the final bottom line is present for field sheets.
- The save step completes and reports a success banner with the saved boundary and feature counts.

## Common problems

- The calibration points are too close together and the app refuses to continue.
- The surface or lower boundary line is not long enough, so the save step reports an error.
- A field-wall drawing is missing the final bottom line below the deepest locus.
- A feature shape has fewer than three points, so the app asks you to finish or delete it.

## Under the hood

The tracing editor in [poggio_webapp/static/app/stages/draw.js](../../poggio_webapp/static/app/stages/draw.js) lets you click on the image, collect calibration points, and build boundary and feature shapes. The server route in [poggio_webapp/backend/routes/manual.py](../../poggio_webapp/backend/routes/manual.py) converts those pixel points into metres and writes the extraction JSON.

## Next

Return to [Workflow overview](overview.md) if you want to review the full path, or continue to the later cleanup and validation steps in the broader documentation set.
