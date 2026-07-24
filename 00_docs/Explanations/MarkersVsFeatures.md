# Markers vs. Features

Two similar-sounding concepts run through the pipeline and are handled by two
different detectors. They are not interchangeable, and confusing them breaks
the anti-fabrication guarantees of the field-sheet path. This note defines
each, states where it lives in the code, and explains how the two detectors
avoid stepping on each other.

---

## Definitions

**A marker is a measurement.** It is the small filled pencil dot (usually
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

| | Marker | Feature |
|---|---|---|
| What it is on paper | Deliberate pencil dot at a measured vertex | Drawn outline or symbol of a physical object |
| What it becomes in JSON | A `BoundaryPoint` on a locus's `topBoundary` / `bottomBoundary` | A `featuresInLayer` entry (name, `approx*` box or `shapePoints` outline) |
| Which sheets have it | Field recording sheets only | Both sheet types |
| Who fixes its coordinates | Computer vision, immutable thereafter | Gemini tracing (or, once wired in, human-reviewed CV proposals) |
| May the LLM touch its geometry? | Never (classification only) | Yes, currently |
| Detector | `pipeline/detect_markers.py` | `pipeline/detect_features.py` |

---

## Where each lives in the code

### Markers

- `pipeline/detect_markers.py` finds candidate dots with CV: adaptive
  thresholding, morphological opening, then a circle hunt restricted to the
  user-clicked wall box, with solidity and fill filters. Size limits are
  given in paper millimeters and converted through the grid-square size.
- `pipeline/assign_markers.py` closes the loop. Gemini receives the fixed
  marker list and only *classifies* each point: `top` of a named locus,
  final `base`, or `noise`. Coordinates pass through verbatim; the final
  `FieldWallProfile` is assembled deterministically in Python. There is no
  code path by which the model can invent, move, or drop a vertex.
- The GUI's "Mark vertices" step (field sheets only) is the human review
  gate: toggle or add candidates before anything is classified.

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
  **It is not wired into the GUI yet**, so in the current app features come
  only from Gemini tracing.

---

## How the detectors avoid each other's targets

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

---

## Rule of thumb

If removing it would change *where a boundary is*, it is a marker.
If removing it would change *what is inside a layer*, it is a feature.
