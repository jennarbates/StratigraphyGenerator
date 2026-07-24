---
title: Accuracy and provenance
audience: beginner
status: current
source_files:
  - docs/workflows/03-alternative-import-and-ai.md
  - docs/workflows/05-check-problems.md
  - docs/workflows/06-place-on-site.md
  - docs/workflows/07-create-model.md
  - docs/project/capability-status.md
verified_against: a8b58f1
---

# Accuracy and provenance

Provenance is the story of where a value came from, and accuracy is how much confidence that value deserves. In this project, those two ideas are closely linked.

## Why it matters here

A result can look polished and still be weak. A visually attractive model is not proof that the geometry is trustworthy, and a completed extraction is not automatically a scientifically verified one. The project uses provenance to keep that distinction clear.

This is especially important when different kinds of evidence are mixed: manual tracing, imported files, computer-vision detections, AI output, placeholders, and surveyed values each carry different strengths and weaknesses.

## Example

Synthetic documentation example: a boundary traced by hand from a cleaned scan and a registration value taken from real field survey are much stronger than a placeholder origin value or an AI-generated extraction that has not been checked against the drawing.

## How the repository represents it

The repository separates several provenance types, and the current documentation should treat them differently:

| Provenance type | What it means | How cautious to be |
|---|---|---|
| Manual tracing | A person traced or recorded the feature directly from the drawing. | Usually the most straightforward starting point, but still needs validation and review. |
| Imported data | An existing extraction file was supplied to the workflow. | Useful when a dataset already exists, but the import step is not a guarantee of correctness. |
| Computer-vision detection | An automated detector proposed candidates from the image. | Promising for support, but still reviewable and not equivalent to verified geometry. |
| AI classification or transcription | An automated reading step generated or labelled an extraction. | Experimental and should be checked against the source drawing before being trusted. |
| Placeholder values | Generated defaults used for smoke tests or documentation exercises. | Not a scientific result and should not be treated as surveyed data. |
| Surveyed values | Real measurements or coordinates from the site. | Appropriate for scientific use when they are recorded and documented properly. |

The app also uses labels such as supported, experimental, and backend-only to describe current capability. Those labels are a practical way to communicate confidence, but they are not a substitute for human review.

## Related concepts

- [From archaeology to 3D](archaeology-to-3d.md) explains why provenance matters for the final model.
- [Source drawing types](source-drawing-types.md) explains the different input paths that carry different provenance.
- [Coordinate spaces](coordinate-spaces.md) explains why coordinate conversion needs careful input values.
- Workflows: [Alternative import and AI extraction](../workflows/03-alternative-import-and-ai.md), [Check for problems](../workflows/05-check-problems.md), [Place on site](../workflows/06-place-on-site.md), [Create the model](../workflows/07-create-model.md), and the [Glossary](../start-here/glossary.md).
