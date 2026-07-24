---
title: What this project does
audience: beginner
status: current
source_files:
  - README.md
  - poggio_webapp/static/app/core/state.js
  - poggio_webapp/pipeline/build_gempy.py
verified_against: eac1f51
---

# What this project does

Poggio Civitate turns a drawing of a vertical trench wall into structured
information that can be checked, placed in a site coordinate system, and
optionally used to build a 3D geological model.

## Why it matters here

An archaeological drawing contains several kinds of information at once:
layer boundaries, recording labels, measurements, and sometimes features
inside a layer. The application helps a person separate those parts and
record their positions as data.

The drawing remains the source evidence. The application does not decide
whether an archaeological interpretation is correct, and a successful check
does not make placeholder coordinates or uncertain geometry scientifically
trustworthy. A person must compare the result with the drawing and use real
survey information before interpreting its site position.

The [current capability status](../project/capability-status.md) distinguishes
the dependable, experimental, backend-only, blocked, and historical parts of
the project.

## Example

**Synthetic documentation example:** imagine a trench-profile drawing with
two named layers and a stone drawn inside the lower layer. A person can trace
the layer boundaries and the stone, add the drawing's labels, check the
resulting data, and enter surveyed coordinates for that wall. These invented
details explain the workflow only; they are not archaeological evidence.

Safe example files are available in the
[synthetic fixtures](../fixtures/README.md).

## How the repository represents it

The application recognizes two broad drawing styles:

- An **illustrated trench sheet** uses faces, named layers, patterns, and
  material descriptions.
- A **hand-drawn field sheet** represents one wall with locus numbers,
  Munsell soil-colour notes, and boundaries drawn on graph paper.

Both styles become structured JSON data. The application can normalize small
formatting differences, validate the data for detectable problems, and
convert local drawing measurements into site coordinates. GemPy support is an
optional, experimental final step that interpolates a model from those
converted points; it is not installed with the core application.

The supported beginner path is to upload a drawing and trace it manually.
Automatic reading is experimental, and some other paths are not available in
the live interface. Use [Choose your path](choose-your-path.md) before
starting.

## Related concepts

- [Glossary](glossary.md) defines the vocabulary used throughout this guide.
- [Geometric normalization](../concepts/geometric-normalization.md) explains
  how a rotated image and local measurements are related.
- [Markers, features, and finds](../concepts/markers-features-and-finds.md)
  separates three easily confused kinds of evidence.
- [Drawing guidelines](../reference/drawing-guidelines.md) explains what
  makes a source drawing easier to interpret.
