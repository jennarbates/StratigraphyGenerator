---
title: First model tutorial
audience: beginner
status: current
source_files:
  - docs/workflows/06-place-on-site.md
  - docs/workflows/07-create-model.md
  - docs/workflows/08-view-and-download.md
  - docs/workflows/logging-finds.md
verified_against: a8b58f1
---

# First model tutorial

Follow a complete synthetic example that moves from a cleaned tracing to a placeholder model, then review the outputs.

> [!warning]
> Synthetic documentation example only. This tutorial uses placeholder values for a smoke test. It does not produce or validate a real scientific model.

## Before you start

Use this tutorial after you have completed the earlier workflow pages. The path below is the intended beginner sequence:

1. [Add a drawing](../workflows/01-add-drawing.md)
2. [Prepare the image](../workflows/02-prepare-image.md)
3. [Trace the layers](../workflows/03-trace-layers.md)
4. [Alternative import and AI extraction](../workflows/03-alternative-import-and-ai.md)
5. [Markers and features](../workflows/03-markers-and-features.md)
6. [Clean up the data](../workflows/04-clean-data.md)
7. [Check for problems](../workflows/05-check-problems.md)
8. [Place on site](../workflows/06-place-on-site.md)
9. [Create the model](../workflows/07-create-model.md)
10. [View and download](../workflows/08-view-and-download.md)
11. [Log a find](../workflows/logging-finds.md)

## Do this

1. Start with the synthetic example from [Place on site](../workflows/06-place-on-site.md).
   - Example registration values: `originX = 0.0`, `originY = 0.0`, `surfaceZ = 100.0`, `bearing_deg = 90.0`.
   - Artifact: the conversion step writes `points.csv` and `points_orientations.csv`.
2. Build a placeholder model from those CSVs in [Create the model](../workflows/07-create-model.md).
   - Artifact: a `.gempy` model file, section image, and mesh outputs.
3. Open the output in [View and download](../workflows/08-view-and-download.md).
   - Artifact: a review view of the traced drawing and a downloaded JSON of the traced data.
4. Record a synthetic find in [Log a find](../workflows/logging-finds.md).
   - Artifact: a stored find entry and a later sync into the finalized output.

## What the application creates

- A smoke-test registration and conversion set.
- A placeholder GemPy model and visualization outputs.
- A find record that is independent from the stratigraphic geometry.

## Check your result

- Every stage has a concrete output artifact.
- The tutorial clearly labels the example as synthetic and non-scientific.
- The model and the visualization are treated as placeholders, not as archaeological conclusions.

## Common problems

- The tutorial is read as a real excavation result because the synthetic example is not clearly labeled.
- The model is expected to be scientifically verified because it has a file extension and a section image.
- The find is confused with the layer geometry because the two are stored separately but are presented as the same thing.

## Under the hood

This walkthrough uses the same steps as the repository workflow: registration feeds the converter, the converter writes CSVs, the model builder uses those CSVs, and the visualizer and finds pages consume the resulting work products. The tutorial uses documentation-only placeholder values rather than real survey data.

## Next

Return to [Place on site](../workflows/06-place-on-site.md) if you want to repeat the registration step, or continue to [View and download](../workflows/08-view-and-download.md) for a review pass.
