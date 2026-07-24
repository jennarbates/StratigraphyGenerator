---
title: View and download
audience: beginner
status: current
source_files:
  - poggio_webapp/static/visualizer/view.js
  - poggio_webapp/static/app/stages/visualize.js
verified_against: a8b58f1
---

# View and download

Inspect the traced drawing in the interactive visualizer and save the extraction data for later review.

> [!warning]
> Synthetic documentation example only. The visualizer shows a smoke-test extraction and should not be interpreted as a scientific reconstruction.

## Before you start

You should already have a traced extraction or a job that you want to review. The visualizer is a review tool for the current extraction JSON and can also compare two runs side by side.

## Do this

1. Open the interactive view.
   - Action: choose the face you want to inspect.
   - Artifact: a browser view of the drawing and its layers.
2. Use the view controls.
   - Face selection: switch between faces with the face tabs.
   - Overlay: load a source image and align it if the drawing has an image calibration.
   - Alignment: use the alignment controls to place the overlay on top of the drawing.
   - A/B comparison: compare two runs of the same face to see whether the extraction changed.
3. Download the data.
   - Artifact: a JSON download of the traced drawing data.

## What the application creates

- An interactive view of the current extraction.
- A downloaded JSON file containing the traced data for the current job.
- Optional side-by-side comparison views for two runs.

## Check your result

- You can switch between faces and see the layers in the selected face.
- The overlay is aligned well enough for review, or you know why it could not be aligned.
- The download contains the traced data, not the GemPy model file.

## Common problems

- The visualizer shows no drawable points because the extraction has empty or non-numeric coordinates.
- The overlay does not appear because there is no source-image calibration.
- A comparison view is confusing because the two runs are not the same face or the same dataset.

## Under the hood

The visualizer reads the extraction JSON and draws the face-local geometry. It can overlay an image when calibration is available, and it can compare two runs without using the GemPy model as input. The download action saves the traced-data JSON from the current workflow state.

## Next

Use [Log a find](logging-finds.md) if you want to record an artifact independently of the stratigraphic geometry.
