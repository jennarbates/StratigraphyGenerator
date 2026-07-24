---
title: Data Schemas
audience: developer
status: current
source_files:
  - poggio_webapp/pipeline/extract_fieldwall.py
  - poggio_webapp/pipeline/extract_illustrator.py
  - poggio_webapp/pipeline/assign_markers.py
  - poggio_webapp/backend/routes/manual.py
verified_against: a8b58f1
---

# Data Schemas

This reference documents the Pydantic data models and dataclasses used throughout the application. All schemas validate incoming JSON and represent both user-edited data and extraction results.

## Archaeological Diagram Schemas

These schemas represent a multi-face trench drawing created in Adobe Illustrator or similar tools.

### ArchaeologicalDiagram

Root schema for an illustrator-based extraction or manual edit.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `metadata` | Metadata | optional | Drawing provenance, credits, transcriptions |
| `trenchProfiles` | list[TrenchProfile] | required | One or more faces extracted from the drawing |
| `legend` | list[LegendItem] | optional | Pattern-to-material key |
| `inferred_notes` | list[str] | optional | Internal AI reasoning; not user-facing |
| `rawTranscription` | str | optional | Unstructured text from initial extraction |
| `source` | Literal["extraction", "manual_editor"] | optional | Default "extraction" |
| `finds` | list[dict] | optional | Independent artifact records |

### Metadata

Provenance, attribution, and sheet-level information.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `currentFilePath` | str | optional | Working filename (may differ from uploaded name) |
| `suggestedFilename` | str | optional | Proposed output filename |
| `trenchLabel` | str | optional | Site/trench identifier |
| `scale` | Scale | optional | Metric conversion information |
| `credits` | Credits | optional | Illustrator attribution |
| `marginalia` | list[str] | optional | Handwritten notes from the original sheet |

### Scale

Metric conversion from drawing units (usually grid squares) to real meters.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `unit` | str | optional | "grid squares", "cm", "mm", or unit from drawing |
| `valuesMarked` | list[int] | required | Numeric values found on the scale bar (e.g. [0, 1, 2]) |
| `metricConversionAssumption` | str | optional | Explanation of how valuesMarked map to real meters |
| `confidence` | str | optional | AI confidence level |

### Credits

Author and date information.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `attributions` | list[Attribution] | optional | List of people involved |
| `year` | str | optional | Date drawn or transcribed |

### Attribution

A single person's role.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | str | optional | Person's name |
| `role` | str | optional | "illustrator", "recorder", "field supervisor", etc. |

### TrenchProfile

A single archaeological face (vertical section).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `face` | str | optional | Face label (e.g., "South") |
| `gridLabels` | list[str] | optional | X-axis labels transcribed from grid |
| `gridLabelXMeters` | list[float \\| None] | optional | Computed X-coordinates of grid labels |
| `layers` | list[Layer] | optional | Stratigraphic sequence top to bottom |

### Layer

A single stratigraphic unit within a face.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `layerName` | str | optional | Layer identifier or locus number |
| `inferredMaterial` | str | optional | Material description ("clay", "sand", "stone", etc.) |
| `description` | str | optional | Additional stratigraphic notes |
| `visualPattern` | str | optional | Key to `legend` (e.g., "diagonal_lines", "dots") |
| `featuresInLayer` | list[NotableFeature] | optional | Archaeological finds or disturbances |
| `topBoundary` | list[BoundaryPoint] | optional | Upper edge of this layer (left to right) |
| `bottomBoundary` | list[BoundaryPoint] | optional | Lower edge of this layer (left to right) |

### NotableFeature

An archaeological feature (pit, post hole, artifact concentration, etc.) within a layer.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `feature` | str | optional | Feature type or label |
| `description` | str | optional | Additional context |
| `shapePoints` | list[BoundaryPoint] | optional | Polygon outline (if traced) |
| `approxXMeters` | float | optional | Center X position |
| `approxYMeters` | float | optional | Center or top depth |
| `approxWidthMeters` | float | optional | Horizontal extent |
| `approxHeightMeters` | float | optional | Vertical extent |
| `confidence` | str | optional | AI confidence level |

### LegendItem

A single entry in the pattern key.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `visualPattern` | str | optional | Pattern identifier used in layers |
| `material` | str | optional | Material this pattern represents |

### BoundaryPoint (Illustrator)

A coordinate on a layer or feature boundary.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `xCoordinateMeters` | float | optional | Horizontal distance (left to right on section) |
| `yCoordinateMeters` | float | optional | Vertical distance (depth, positive downward) |
| `confidence` | str | optional | AI confidence level for this point |

---

## Field Wall Schemas

These schemas represent a single-face field-wall drawing with loci and Munsell readings.

### FieldWallProfile

Root schema for a field-wall extraction or manual edit.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `trenchLabel` | str | optional | Trench or section identifier |
| `faceLabel` | str | optional | Face or wall direction |
| `illustrators` | list[str] | optional | People who recorded this wall |
| `date` | str | optional | Recording date |
| `northArrowPresent` | bool | optional | Whether a north arrow appeared on the drawing |
| `gridSquareCm` | float | optional | Side length of grid squares in centimeters |
| `gridTiePoints` | list[GridTiePoint] | optional | Reference grid cells for scale verification |
| `loci` | list[Locus] | optional | Stratigraphic units with color readings |
| `layers` | list[LocusLayer] | optional | Same units organized by depth order |
| `marginalia` | list[str] | optional | Handwritten notes |
| `source` | Literal["extraction", "manual_editor"] | optional | Default "extraction" |

### Locus

A stratigraphic unit with Munsell soil color.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `locusNumber` | str | optional | Locus identifier (unique within face) |
| `munsell` | MunsellColor | optional | Soil color reading |
| `description` | str | optional | Additional stratigraphic context |
| `confidence` | str | optional | AI confidence level |

### MunsellColor

A Munsell soil color reading.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `raw` | str | optional | Original text transcribed from field notes |
| `colorName` | str | optional | Normalized color (e.g., "10YR 4/3") |

### LocusLayer

A locus positioned within the stratigraphic sequence.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `locusNumber` | str | optional | Locus identifier |
| `topBoundary` | list[BoundaryPoint] | optional | Upper edge (left to right) |
| `bottomBoundary` | list[BoundaryPoint] | optional | Lower edge (left to right) |
| `featuresInLayer` | list[FieldFeature] | optional | Archaeological features within this locus |

### FieldFeature

An archaeological feature (pit, post hole, find, etc.) within a field-wall layer.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `feature` | str | optional | Feature type or identifier |
| `description` | str | optional | Context and interpretation |
| `shapePoints` | list[BoundaryPoint] | optional | Feature boundary (if traced) |
| `approxXMeters` | float | optional | Center X position on wall |
| `approxDepthMeters` | float | optional | Center or top depth |
| `approxWidthMeters` | float | optional | Horizontal extent |
| `approxHeightMeters` | float | optional | Vertical extent |
| `confidence` | str | optional | AI confidence level |

### GridTiePoint

A reference to a grid cell for scale verification.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `rawText` | str | optional | Grid label transcribed from drawing |
| `approxXMeters` | float | optional | Computed X-coordinate of this grid cell |

### BoundaryPoint (Field Wall)

A coordinate on a field-wall layer or feature boundary.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `xMeters` | float | optional | Horizontal distance on the wall |
| `depthMeters` | float | optional | Vertical distance (positive downward) |
| `confidence` | str | optional | AI confidence level for this point |

---

## Marker Detection Schemas

These schemas represent marker-detection results and assignments.

### MarkerAssignment

A single marker's assigned role.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `markerId` | int | required | Unique marker identifier from detection |
| `kind` | str | required | "top", "base", or "noise" |
| `locusNumber` | str | optional | Locus this marker belongs to (if kind is "top" or "base") |

| Assignment Kind | Meaning |
|---|---|
| `"top"` | Top boundary of a locus |
| `"base"` | Final boundary below the deepest locus |
| `"noise"` | Not a boundary (stone, hatch mark, stray dot) |

### MarkerAssignmentResult

The complete output of marker assignment.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `trenchLabel` | str | optional | Trench identifier |
| `faceLabel` | str | optional | Face identifier |
| `illustrators` | list[str] | optional | Recorder names |

---

## Coordinate Transformation Schemas

### Calibration (Manual Editor)

Three-point calibration used to transform pixel coordinates to section meters.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `origin_x` | float | required | X-coordinate of first calibration point (section meters) |
| `origin_y` | float | required | Y-coordinate of first calibration point (section meters) |
| `ux` | float | required | X-coordinate of second calibration point |
| `uy` | float | required | Y-coordinate of second calibration point |
| `vx` | float | required | X-coordinate of third calibration point |

---

## Shared Field Patterns

### Field Naming Conventions

The application uses two related coordinate systems within sections:

- **Illustrator diagrams** use `xCoordinateMeters` and `yCoordinateMeters`
- **Field-wall diagrams** use `xMeters` and `depthMeters` (synonym for y)

Both represent the same conceptual space; the application converter handles both naming conventions.

### Confidence Fields

When AI extractions are involved, confidence fields may contain:

- `"high"`
- `"medium"`
- `"low"`
- `null` or empty (unknown or manual)

### Null Strings

The validator scans all fields for literal strings like `"null"`, `"None"`, or `"n/a"`. These are reported as warnings because they typically indicate data trapped in text rather than proper JSON nulls.

---

## Validation and Conversion

After a user completes an extraction or manual edit, the data flows through:

1. **JSON-Schema validation** — Pydantic checks required fields and types
2. **Custom validation** — `validator.py` checks geometric plausibility
3. **Normalization** — Empty fields are pruned and references are resolved
4. **Coordinate conversion** — Section-local coordinates become site-wide

All Pydantic models use the Python `|` union syntax (Python 3.10+) for optional field types.

---

## Under the Hood

All schemas are defined using Python `pydantic.BaseModel`. Extraction schemas (AI-generated) and manual-editor schemas coexist in the same data structures, distinguished by the `source` field.

The application converts between naming conventions and coordinate systems programmatically; documentation always uses the naming from the user's chosen workflow.
