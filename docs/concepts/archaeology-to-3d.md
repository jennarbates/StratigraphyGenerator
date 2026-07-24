---
title: From archaeology to 3D
audience: beginner
status: current
source_files:
  - docs/workflows/01-add-drawing.md
  - docs/workflows/02-prepare-image.md
  - docs/workflows/03-trace-layers.md
  - docs/workflows/06-place-on-site.md
  - docs/workflows/07-create-model.md
verified_against: a8b58f1
---

# From archaeology to 3D

This concept is the big picture: a trench drawing becomes structured drawing data, then site coordinates, and finally a 3D model.

## Why it matters here

The project is not only about drawing lines. It is about turning a paper record into information that can be checked, compared, and placed in a wider site context. Each step in the workflow adds a kind of certainty or uncertainty, so the later model should be read as a visualization of the available evidence, not as automatic proof of the archaeology.

A model can look convincing and still be weak if the input geometry is uncertain, the registration values are placeholders, or the evidence came from an experimental path. The safest way to read the result is to treat each stage as a question of how much evidence was captured and how clearly its provenance is known.

## Example

Synthetic documentation example: a hand-drawn trench profile is uploaded, cleaned, traced into boundaries, and then registered with placeholder site coordinates for a smoke test. The result is a simple 3D model that helps show the workflow, but it should not be read as a scientific reconstruction.

## How the repository represents it

The application breaks the journey into a sequence of user-facing steps:

1. Add a drawing and choose the sheet type.
2. Prepare the image so the drawing is easier to read.
3. Trace the layers to create structured boundaries and features.
4. Clean up and validate the extraction.
5. Place the face on site by entering registration values.
6. Create the model from the converted coordinates.
7. View and download the outputs.

The repository stores each result as job artifacts, so the workflow is meant to be reviewed step by step. The later model step depends on earlier stages being careful, consistent, and clearly labeled when they are not yet scientifically verified.

## Related concepts

- [Source drawing types](source-drawing-types.md) explains the different kinds of source sheets and imports.
- [Layers and boundaries](layers-and-boundaries.md) explains the structure inside the drawing.
- [Coordinate spaces](coordinate-spaces.md) explains how the drawing moves from pixels to site coordinates.
- [Accuracy and provenance](accuracy-and-provenance.md) explains how much trust to place in each input.
- Workflows: [Add a drawing](../workflows/01-add-drawing.md), [Prepare the image](../workflows/02-prepare-image.md), [Place on site](../workflows/06-place-on-site.md), [Create the model](../workflows/07-create-model.md), and the [Glossary](../start-here/glossary.md).
