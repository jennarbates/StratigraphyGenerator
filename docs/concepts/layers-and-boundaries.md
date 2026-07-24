---
title: Layers and boundaries
audience: beginner
status: current
source_files:
  - docs/workflows/03-trace-layers.md
  - docs/workflows/04-clean-data.md
  - docs/workflows/05-check-problems.md
  - docs/start-here/glossary.md
verified_against: a8b58f1
---

# Layers and boundaries

A layer is the stratigraphic unit that occupies a part of the trench profile, and a boundary is the line that separates one unit from another.

## Why it matters here

This distinction is central to the tracing workflow. A beginner may be tempted to draw only the obvious outlines, but the application needs the boundaries to define each unit clearly. If the boundaries are weak, the later model and the later interpretation will also be weak.

In this project, a layer and a boundary belong together: the boundary often represents the top or bottom of a unit, and matching those lines carefully is an important part of making the extraction consistent.

## Example

Synthetic documentation example: one layer sits above another, and the line between them is traced as the boundary between the units. If the boundary is missing or misplaced, the layer inventory becomes harder to understand even if the drawing still looks visually reasonable.

## How the repository represents it

The tracing workflow asks the operator to create boundaries and then attach them to the layer or locus structure. In field-sheet work, the top of a locus and the final base line are important parts of the geometry. In illustrated work, the layers are named and the boundaries define their upper and lower limits.

The project later uses validation to check whether the boundaries and the layer data are consistent enough to continue. This is not the same as saying the interpretation is confirmed; it means the extraction is coherent enough to review.

## Related concepts

- [From archaeology to 3D](archaeology-to-3d.md) shows how these units become part of the later model.
- [Markers, features, and finds](markers-features-and-finds.md) distinguishes boundaries from other evidence like markers and features.
- [Accuracy and provenance](accuracy-and-provenance.md) explains how to judge whether the boundaries should be trusted.
- Workflows: [Trace the layers](../workflows/03-trace-layers.md), [Clean up the data](../workflows/04-clean-data.md), [Check for problems](../workflows/05-check-problems.md), and the [Glossary](../start-here/glossary.md).
