# Poggio Civitate Trench Profile Digitization Pipeline

This project converts archival hand-drawn trench profile sheets from the
Poggio Civitate (Murlo, Italy) excavation into structured geological data
suitable for 3D modeling in [GemPy](https://www.gempy.org/). A vision model
reads each scanned drawing into a structured JSON schema, deterministic
scripts clean and validate that data, and a final conversion step places
every point into real site coordinates.

```
scan (.png/.tif)
   │
   ▼
preprocess.py            image cleanup for the vision model
   │
   ▼
renameImages.py           Gemini vision extraction -> extraction JSON
   │
   ▼
normalizer.py             dedupe / null-string cleanup -> *_clean.json
   │
   ▼
validator.py               sanity checks (errors / warnings)
   │
   ▼
convertCoords.py + gridConfig.JSON   face-local -> site (X, Y, Z)
   │
   ▼
points.csv + points_orientations.csv   ready for GemPy
```

`visualizer.html` is a standalone, no-build-step viewer for inspecting an
extraction JSON in the browser. `IllusstratorGuide.md` is a guidelines
document to hand to illustrators producing *new* drawings, so future sheets
digitize cleanly.

## Coordinate conventions

Every drawing is authored in its own **face-local** frame:

- `x` — meters along the face, measured from the face's **left edge**
  (`x = 0`).
- `y` / `depth` — meters **downward** from the ground surface
  (`y = 0` at the surface, positive down, never negative).

This face-local data has no relationship to the site grid until it's
explicitly registered — see **Grid registration**, below.

## Pipeline stages

### 1. `preprocess.py` — scan cleanup
Prepares an archival scan so the vision model can resolve boundary lines
more reliably. Non-destructive: writes new files, never touches the
original.

- Flattens uneven paper tone/background illumination.
- Upscales (default 2x, Lanczos) so thin ink lines survive.
- Applies gentle local contrast (CLAHE) + mild sharpening, while
  **preserving fill hatching** (needed later to identify materials).
- Optional `--deskew` to straighten a rotated scan.
- Optional `--highcontrast` to also emit an aggressively binarized version
  for boundary tracing only — **do not** feed this one to the extraction
  step, since it can wipe out the fill patterns used for material ID.

```bash
python preprocess.py input.png --outdir preprocessed --upscale 2 --deskew --highcontrast
```

Outputs `<name>_clean.png` (use this one downstream) and, optionally,
`<name>_highcontrast.png`.

### 2. `renameImages.py` — vision extraction
Sends a (preprocessed) image to Gemini (`gemini-2.5-flash`) with a detailed
prompt and a strict Pydantic schema (`ArchaeologicalDiagram`), and writes
the raw model output straight to `output_single.json` (a `rawTranscription`
field on the top-level object preserves the model's own free-text reading
of the drawing alongside the structured fields).

Key instructions baked into the prompt:

- Calibrate against the **metric scale bar only** — a capitalized surname
  next to the bar (e.g. "PECK") is a signature, not a unit, and must not be
  used for conversion.
- Trace each layer's boundary independently, following its own drawn shape
  — never copy one boundary's shape and offset it to make another
  ("parallel-izing" layers is a common failure mode this pipeline actively
  guards against).
- Assign each feature to a single, primary layer (no duplicating a feature
  across layers).
- Prefer `null` + a `confidence` note over a plausible-sounding guess for
  any ambiguous point.
- No historical/archaeological interpretation — only what is visibly
  drawn, labeled, or written.

```bash
python renameImages.py path/to/preprocessed/image_clean.png
```

Includes retry-with-backoff for transient API errors (429/500/503).

> `output.json` in this repo predates the current schema (it's missing the
> `rawTranscription` field and uses a slightly different `credits` shape).
> `output_single.json` is the current script's output and reflects the
> live schema — treat it as the reference example going forward.

### 3. `normalizer.py` — JSON cleanup
Idempotent, non-destructive cleanup pass over an extraction JSON before it
reaches validation/GemPy:

- Converts literal `"null"` / `"none"` / `"n/a"` strings to real JSON
  `null`.
- Drops a trench-floor *feature* when it just duplicates the deepest
  layer's `bottomBoundary` (keeps the boundary, removes the redundant
  feature).
- De-duplicates a feature copied into multiple layers, keeping only the
  deepest occurrence.
- Prints a change log; never alters geometry values themselves.

```bash
python normalizer.py output.json output_clean.json
```

### 4. `validator.py` — sanity checks
Schema-tolerant checks (accepts either `yCoordinateMeters` or
`depthMeters`) that catch problems before they corrupt the GemPy model.
Exits `0` if there are no errors (warnings are still printed), `1`
otherwise.

Checks include:

- **Errors**: null coordinates with no `confidence` explanation, negative
  depths, layers whose boundaries cross (a lower layer rising above the
  layer above it, beyond a small hand-drawn-line tolerance), missing
  `trenchProfiles`.
- **Warnings**: implausible depths (>5 m by default), non-left-to-right
  `x` sequences, large gaps between an independently-drawn top boundary
  and the layer above's bottom, mismatched `gridLabels`/
  `gridLabelXMeters` lengths, features whose points fall outside their
  layer's vertical band, leftover literal `"null"` strings.

```bash
python validator.py output_clean.json
```

Tunable thresholds live at the top of the file (`MONOTONIC_TOLERANCE_M`,
`TOP_CONTINUITY_TOLERANCE_M`, `MAX_PLAUSIBLE_DEPTH_M`).

### 5. `convertCoords.py` — face-local → site coordinates
Turns cleaned, validated face-local points into real site coordinates
`(X, Y, Z)` for GemPy, using a **grid config** that records where each
face physically sits on site (this comes from site records, not the
drawing itself, and cannot be inferred by the model).

Per-point math, given a face's origin `(X0, Y0)`, surface elevation `Z0`,
and compass bearing `θ` (degrees clockwise from north, the direction the
face's local `+x` points):

```
X = X0 + x * sin(θ)
Y = Y0 + x * cos(θ)
Z = Z0 - depth
```

```bash
# generate a starter grid config with placeholder values to fill in:
python convertCoords.py output_clean.json --make-config gridConfig.JSON

# once gridConfig.JSON has real site values:
python convertCoords.py output_clean.json --grid gridConfig.JSON --out points.csv
```

Writes two files:

- `points.csv` — one row per interface (boundary) point:
  `X, Y, Z, surface, face`.
- `points_orientations.csv` — one crude orientation seed per boundary
  (dip estimated from the average slope of depth vs. x, azimuth from the
  face bearing, polarity fixed at 1) for GemPy's orientation input.

Faces missing from the grid config are skipped with a warning, not
silently dropped.

> **Note:** `buildGempy.py` was an exact duplicate of `convertCoords.py`
> and has been removed — `convertCoords.py` is the single canonical
> version of this step going forward.

### `gridConfig.JSON` — site registration
Maps each face name to its site registration:

| field | meaning |
|---|---|
| `originX` / `originY` | site coordinates of the face's `x = 0` edge |
| `surfaceZ` | ground-surface elevation at that edge |
| `bearing_deg` | compass bearing (clockwise from north) the face's local `+x` axis points |

This file **must be filled in with real surveyed values** before running
the final conversion — the checked-in copy uses placeholder values
(`bearing_deg: 90.0` for every face, origins spread 10 m apart) and will
produce geometrically wrong output if used as-is.

## Supporting files

- **`visualizer.html`** — a self-contained, dependency-free HTML page for
  loading and inspecting an extraction JSON (drag-and-drop) in the
  browser: profiles, layers, features, legend. Useful for spot-checking
  a `renameImages.py` / `normalizer.py` output before it goes through
  coordinate conversion.
- **`IllusstratorGuide.md`** — drawing guidelines for illustrators
  producing new trench profile sheets, covering scale bars, origin/
  orientation marking, boundary-line conventions, fill patterns and
  legends, feature labeling, metadata placement, and scan settings. Follow
  this for new drawings and extraction accuracy improves substantially
  (e.g. it explains why a signature like "PECK" next to a scale bar can
  get misread as a unit, and how to avoid it).

## Typical end-to-end run

```bash
python preprocess.py raw_scans/trench23_1980.png --outdir preprocessed --deskew

python renameImages.py preprocessed/trench23_1980_clean.png
# -> output_single.json

python normalizer.py output_single.json output_clean.json

python validator.py output_clean.json
# fix any [ERROR] lines before continuing

python convertCoords.py output_clean.json --grid gridConfig.JSON --out points.csv
# -> points.csv, points_orientations.csv, ready for GemPy
```

## Requirements

- Python 3.10+ (uses `X | None` type unions)
- `google-genai`, `pillow`, `pydantic` (for `renameImages.py`)
- `opencv-python`, `numpy` (for `preprocess.py`)
- A `GEMINI_API_KEY` (or equivalent client credentials) configured for the
  `google.genai` client
- GemPy (downstream of this pipeline, not included here) to consume
  `points.csv` / `points_orientations.csv`