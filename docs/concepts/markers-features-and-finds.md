---
title: Markers, features, and finds
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/detect_markers.py
  - poggio_webapp/pipeline/assign_markers.py
  - poggio_webapp/pipeline/detect_features.py
  - poggio_webapp/backend/routes/manual.py
  - poggio_webapp/pipeline/editor.py
  - poggio_webapp/app.py
  - poggio_webapp/static/app/index.js
verified_against: c702617
---

# Markers, features, and finds

A **marker** is a measured boundary point, a **feature** is a drawn object
within a stratigraphic layer, and a **find** is a recovered artifact recorded
at a location.

## Why it matters here

Markers and features are similar-looking concepts handled by two
different detectors. They are not interchangeable, and confusing them breaks
the anti-fabrication guarantees of the field-sheet path. This note defines
each, states where it lives in the code, and explains how the two detectors
avoid stepping on each other.

Their current availability also differs. Automated marker detection and
assignment and automated feature detection are `backend-only`: their route and
stage modules exist, but they are not registered in the live workflow. Manual
feature tracing in **Trace the layers** is `supported`. Find logging is
`experimental` at the direct `/finds` page and has no link from the main
application or editor.

## Example

On a field sheet, a filled dot marking a surveyed boundary vertex is a marker.
An outlined stone or cut inside a layer is a feature. An artifact recovered
during excavation and logged with its face, locus, position, elevation, and
description is a find.

Removing the marker changes the boundary geometry. Removing the feature leaves
the boundary in place but changes the layer inventory. A find is recorded
separately and does not define either boundary or feature geometry.

## How the repository represents it

### Definitions

**A marker is a measurement point.** It is the small filled pencil dot (usually
circled) that the field recorder drew on the recording sheet at a vertex they
physically measured on the trench wall. Markers carry no meaning on their
own; each one is a vertex of a named locus top or of the final line below
the deepest locus. The next locus's top also closes the locus above it.
Collectively, the markers *are* the boundary geometry of the section.

**A feature is an object.** It is a discrete thing drawn *within* a layer:
a stone, a cut, a lens, a void. Features are inventory attached to a layer,
not boundary geometry. Deleting every feature from an extraction leaves the
stratigraphic model geometrically intact; deleting a marker removes a real
measured point from a boundary.

**A find is a recovered artifact record.** The current find logger associates
it with a job and requires a face, local `x` and `y` position, elevation,
locus, and description. A find can be logged before stratigraphy is started or
finalized, so it is not a boundary point or a feature shape.

| | Marker | Feature | Find |
|---|---|---|---|
| What it represents | Deliberate pencil dot at a measured boundary vertex | Drawn outline or symbol of an object inside a layer | Recovered artifact logged independently of the drawing |
| What it becomes in JSON | A `BoundaryPoint` on a locus's `topBoundary` / `bottomBoundary` | A `featuresInLayer` entry (name, `approx*` box, or `shapePoints` outline) | An entry in job-level `finds`, with `face_id`, `x`, `y`, `elevation`, `locus`, `description`, and `find_id` |
| Where it applies | Field recording sheets | Both sheet types | Any existing job, even without saved stratigraphy |
| How geometry is recorded | Computer-vision candidates retain fixed coordinates through backend classification | Human tracing is supported; AI tracing is experimental; CV proposals are backend-only | A person marks a point on the find logger's reference canvas and enters its elevation |
| Current availability | `backend-only` automated flow | `supported` manual tracing; `backend-only` automated detection | `experimental` direct `/finds` page |
| Main implementation | `pipeline/detect_markers.py` and `pipeline/assign_markers.py` | `pipeline/detect_features.py`, extraction schemas, and the manual route | `pipeline/editor.py`, application find routes, and the finds page |

### Markers

- `pipeline/detect_markers.py` finds candidate dots with CV: adaptive
  thresholding, morphological opening, then a circle hunt restricted to the
  user-clicked wall box, with solidity and fill filters. Size limits are
  given in paper millimeters and converted through the grid-square size.
- `pipeline/assign_markers.py` closes the loop. Gemini receives the fixed
  marker list and only *classifies* each point: `top` of a named locus,
  final `base`, or `noise`. Coordinates pass through verbatim; the final
  `FieldWallProfile` is assembled deterministically in Python. There is no
  code path by which the model can invent a coordinate or move one; it may
  classify a candidate as `noise`.
- The backend flow includes a human review stage where candidates can be
  toggled or added before classification. Its frontend module exists, but
  the live `STEPS` and `RENDERERS` omit it, so this review flow is not
  currently reachable from the application.

The point of all this is anti-fabrication. Gemini tracing on T104-style
sheets kept producing boundaries with perfectly even spacing and layers
copied down with a constant offset. A marker cannot be fabricated the way a
traced boundary can: either the dot is on the paper or it is not.

### Features

- The extraction schemas (`NotableFeature` in `extract_illustrator.py`,
  `FieldFeature` in `extract_fieldwall.py`) define a feature as a name plus
  either an approximate bounding box (`approxXMeters`, `approxWidthMeters`,
  ...) for compact objects like stones, or a `shapePoints` outline for
  traced shapes like cuts and lenses.
- `pipeline/normalizer.py` drops a trench-floor "feature" that merely
  duplicates the deepest layer's bottom boundary, and removes features
  duplicated across layers.
- `pipeline/validator.py` (`check_features`) warns when a feature's
  geometry falls outside its layer's top and bottom boundaries.
- `pipeline/detect_features.py` proposes compact closed contours (Canny
  edges, then area, aspect, solidity, extent, and circularity filters, with
  IoU dedupe) as *reviewable candidates*. It deliberately does not claim any
  contour is a stone; a person approves, rejects, and labels each proposal.
  This automated review stage is `backend-only` because it is not registered
  in the live workflow.
- In the supported primary workflow, an operator can manually trace feature
  shapes in **Trace the layers**. The experimental Gemini extraction path can
  also produce features.

### Finds

- `pipeline/editor.py` stores each job's find records in `finds.json` and
  gives a new record a 12-character `find_id` when it does not already have
  one.
- Adding or deleting a find also copies the current list into
  `extraction_output.json` when that finalized output exists. If it does not
  exist, find logging still works independently.
- The `/finds` page lists existing jobs, accepts a point on a read-only
  reference canvas, and records its face, local position, elevation, locus,
  and description. This page is `experimental` because users must know its
  direct URL.

### How the detectors avoid each other's targets

The two target classes overlap visually (both are compact ink blobs), so
each detector explicitly filters out the other's:

- `detect_markers.py` rejects stone outlines with its solidity and fill
  filters (a marker is a small *filled* disk; a stone is a *hollow* traced
  outline), and `assign_markers` classifies anything that slipped through
  (stones, hatch marks, stray dots) as `noise`, which excludes it from every
  boundary.
- `detect_features.py` rejects marker-sized blobs with its minimum bounding
  box (10 px per side) and minimum area fraction, and its extent and
  solidity floors are tuned for outlined shapes rather than dots.

If you extend either detector, preserve this separation: a proposal that
could plausibly be a vertex dot must not become a feature candidate, and
nothing hollow or outline-like should survive marker detection.

## Related concepts

If removing it would change *where a boundary is*, it is a marker.
If removing it would change *what is inside a layer*, it is a feature.
If it is a recovered artifact logged at a location, it is a find.

- [Geometric normalization](geometric-normalization.md) explains how the
  source image is straightened before later processing.
- [Drawing guidelines](../reference/drawing-guidelines.md) explains how to
  make markers, boundaries, and feature labels legible.
- [Current capability status](../project/capability-status.md) records which
  paths are supported, experimental, backend-only, or blocked.
