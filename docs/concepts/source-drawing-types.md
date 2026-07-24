---
title: Source drawing types
audience: beginner
status: current
source_files:
  - docs/workflows/01-add-drawing.md
  - docs/workflows/02-prepare-image.md
  - docs/workflows/03-trace-layers.md
  - docs/workflows/03-alternative-import-and-ai.md
verified_against: a8b58f1
---

# Source drawing types

A source drawing type is the kind of input the project is working from, such as an illustrated trench sheet, a hand-drawn field sheet, or an imported data file.

## Why it matters here

The same excavation record can look very different depending on the source. An illustrated sheet often has clearer labels and more polished linework, while a field sheet may rely on hand-written locus numbers and more informal drawing style. The workflow uses this distinction to decide how to trace, name, and later validate the data.

This matters because a beginner should not assume that every drawing is handled the same way. The manual path, the imported-data path, and the AI-assisted path each carry different expectations about review and trust.

## Example

Synthetic documentation example: one drawing is a clean illustrated trench profile with named layers and a second is a field-wall sketch made by hand with locus numbers. The first may be easier to interpret visually, but the second still needs careful tracing and validation because it is based on a different recording convention.

## How the repository represents it

The current application asks the operator to choose the sheet type when a drawing is first added. That choice informs the later tracing and naming workflow. The optional import and AI pages also handle a different kind of source: a pre-existing JSON extraction rather than a scanned drawing.

In practice, the repository treats these as separate starting points:

- Manual tracing from a scan or PDF.
- Importing an existing extraction file.
- Running an automated reading step that produces a new extraction.

The project does not treat imported or AI-generated data as automatically correct just because it is structured. It still needs inspection and comparison with the source drawing.

## Related concepts

- [From archaeology to 3D](archaeology-to-3d.md) explains how these different sources feed the full workflow.
- [Layers and boundaries](layers-and-boundaries.md) explains the structure that is traced inside the drawing.
- [Accuracy and provenance](accuracy-and-provenance.md) explains how to judge the strength of each input.
- Workflows: [Add a drawing](../workflows/01-add-drawing.md), [Prepare the image](../workflows/02-prepare-image.md), [Trace the layers](../workflows/03-trace-layers.md), [Alternative import and AI extraction](../workflows/03-alternative-import-and-ai.md), and the [Glossary](../start-here/glossary.md).
