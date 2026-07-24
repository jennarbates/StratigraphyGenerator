# Trench Digitization Pipeline

Turns a trench-profile drawing — archival illustrator sheet or modern field
recording sheet — into a 3D GemPy geological model.

Everything runs through the web GUI in `poggio_webapp/`. The old numbered
folders (`02_preprocess` … `07_visualizer`) were retired in the `webapp`
commit; each stage's logic now lives as an importable module in
`poggio_webapp/pipeline/`, and the old CLI scripts plus every previously
produced output are recoverable from git history (see *Recovering old
artifacts* below).

```
00_docs                  reference material for whoever draws the profiles
01_scans                 raw drawings
poggio_webapp/           the pipeline + browser GUI  <- start here
  app.py                 Flask API, one route per stage
  pipeline/              preprocess, extract_illustrator, extract_fieldwall,
                         normalizer, validator, convert_coords, build_gempy,
                         detect_markers + assign_markers (CV marker
                         detection/classification for field-wall sheets)
  tools/                 standalone helpers not wired into the GUI
                         (pixel_picker.html; detectFieldWallMarkers.py is now
                         superseded by pipeline/detect_markers.py)
  static/, templates/    frontend (static/visualizer.html is the A/B viewer)
  jobs/                  created at runtime, one folder per session
```

Setup and per-stage usage: see **`poggio_webapp/README.md`**.

## The two source drawings

- **Trench 23** (Poggio Civitate, 1980) — illustrator sheet, hatch-pattern
  legend, three faces (East/South/West). Scanned well below the 300 DPI
  `00_docs/IllusstratorGuide.md` recommends.
- **T104, southern baulk wall** (2025 field sheet, Lizzy Bruening / Heather
  Fusco) — hand-drawn on graph paper, Locus number + Munsell color instead of
  a hatch legend, one wall only, 4284×5712 phone photo.

They use different extraction schemas (`ArchaeologicalDiagram` vs
`FieldWallProfile`) because they record material differently, but both now
feed the same coordinate conversion and model build.

## Browser workflows

Open `http://localhost:5000` after starting the web app. The first screen
supports two independent ways to begin.

### Upload an existing drawing

1. Select **Use an existing drawing**.
2. Choose **Illustrated trench sheet** for an archaeological diagram whose
   layers are identified by materials, patterns, or shading, or choose
   **Hand-drawn field sheet** for a field-wall record whose layers use locus
   numbers and Munsell soil colours.
3. Upload a PNG, JPEG, TIFF, or PDF. The app keeps the original unchanged,
   shows an image preview (or a PDF-ready message), reports image dimensions
   when available, and unlocks **Prepare the image**.
4. Continue through preprocess, trace/extract, normalize, validate, surveyed
   coordinate conversion, model building, and results as described below.

Uploading creates an ordinary pipeline job only after a file is selected. It
does not create a blank-editor session.

### Create a diagram from scratch

1. Select **Create a diagram from scratch**, choose the diagram type, and
   click **Open blank drawing canvas**.
2. The editor uses a fixed **3 m × 2 m** metric canvas for every face, with
   **0.25 m** grid spacing. Snap-to-grid is on initially and may be turned
   off.
3. For an archaeological diagram, choose 1–12 faces and give each a unique
   name before drawing. Use the face tabs to move between them. A field-wall
   diagram always has exactly one named face.
4. Click or tap to place polygon vertices, then use **Close shape** after at
   least three vertices. Correct geometry by dragging vertices, selecting an
   edge midpoint to insert a vertex, selecting and deleting a vertex, undoing
   the last vertex of the open polygon, cancelling the open polygon, or
   deleting a closed polygon. Self-intersections are shown with a dashed
   stroke and must be corrected before finalization.
5. Label every archaeological polygon with a material; an optional note can
   record additional context. For a field wall, every polygon instead
   requires a locus number and Munsell notation such as `10YR 5/3`, with an
   optional note. The polygon list reopens saved metadata for correction.
6. Enter surveyed registration separately for every face: `originX`,
   `originY`, `surfaceZ`, and `bearing_deg`. These are real site coordinates
   for the face's local x=0 point, its ground-surface elevation, and the
   clockwise-from-north direction of local +x. Placeholder values should not
   be used.
7. Changes autosave after about two seconds. **All changes saved** confirms
   persistence; **Couldn’t save** leaves the drawing in place and offers
   **Retry save**. Drafts appear under **Previous work** as **Work in
   progress** and reopen in the editor with their faces, polygons, metadata,
   active face, and registration restored.
8. **Finalize** becomes available only when every face has at least one
   closed, non-self-intersecting polygon with the required metadata and
   complete registration. Finalization saves once more, assembles the chosen
   schema, then runs normalization, validation, coordinate conversion, and
   GemPy model building.
9. The results page reports **Creating 3D model** while it polls durable job
   status and changes to **3D model ready** when the build completes. If model
   processing fails, the saved draft remains available from the recovery link
   and **Previous work**.

### Workflow limitations

- Drawing is polygon-based; there is no freehand paint or brush tool.
- Every face uses the fixed 3 m × 2 m canvas and 0.25 m grid.
- Editing is single-user; there is no collaborative editing or conflict
  resolution.
- Completed models can be viewed and downloaded, but cannot be arbitrarily
  reopened for editing. The editor recovery link is provided for failed model
  processing.

### Regression test commands

From the repository root:

```bash
.venv/bin/python -m pytest -q
node poggio_webapp/static/canvas/grid.test.mjs
node poggio_webapp/static/app/stages/start-options.test.mjs
git diff --check
git status --short
```

If `.venv/bin/python` is unavailable, use `python3 -m pytest -q`.

## How it works

Everything is a Flask route in `app.py` calling one function in
`pipeline/`. There is no ORM and no database — each job is a folder under
`jobs/<job_id>/` holding a `meta.json` (a flat dict of "what path is this
job's current X") plus the numbered subfolders `01_scan` … `06_gempy_model`
that mirror the original CLI script names. Two kinds of stage exist:

- **Synchronous** (preprocess, normalize, validate, convert, marker
  detect/confirm/finalize): the route runs the function inline and returns
  the result in one HTTP response.
- **Asynchronous** (extraction, marker assign, GemPy build): these call an
  external API (Gemini) or take real compute time, so the route calls
  `start_task()`, which spawns a **daemon thread**, hands back a `task_id`
  immediately, and the browser polls `GET /api/tasks/<task_id>` until
  `status` flips from `"running"` to `"done"`/`"error"`. `TASKS` is a plain
  in-memory Python dict — restart the server and every in-flight task
  (and its log lines) is gone; nothing is persisted to disk. Each async
  function can optionally accept a `progress_cb`/`log_cb` keyword (detected
  by inspecting `fn.__code__.co_varnames`), which `start_task` wires up to
  append strings into that task's `log` list — that's the scrolling log box
  the UI shows during extraction/GemPy runs.

### Stage 0 — job creation & upload

`POST /api/jobs` mints a 12-hex-character job id (`uuid4().hex[:12]`),
creates the six numbered subfolders, and writes an empty `meta.json`.
`POST /api/jobs/<id>/scan` accepts one file (`.png/.jpg/.jpeg/.pdf/.tif/
.tiff`) plus a `sheet_type` (`illustrator` or `fieldwall`), saves it
byte-for-byte into `01_scan/` under its original filename, and — for
non-PDF images — calls `preprocess.probe_dimensions()` (a PIL open, no
full decode) to report width/height and get an upscale recommendation
back before the person even clicks "preprocess". All later downloads go
through `GET /api/jobs/<id>/file?path=...`, which resolves the requested
path via `safe_job_path()` — this joins the path onto the job directory,
resolves both to absolute paths, and rejects anything whose resolved
target isn't inside the job directory, so a `path=../../etc/passwd` style
request 400s instead of escaping the sandbox. Note this guard is only used
by the *download* route today — see roadmap item 7 about the *upload*
route trusting the raw client filename.

### Stage 1 — preprocess (`pipeline/preprocess.py`)

Goal: make thin, faded boundary ink resolvable by a vision model without
destroying the fill patterns that identify each layer. Runs entirely in
OpenCV/NumPy, no network call.

1. **Load.** PDFs are rasterized via `pdf2image.convert_from_path` at a
   configurable `pdf_dpi` (default 300) and page number; everything else
   goes through `cv2.imread`. Converted to grayscale immediately.
2. **Optional deskew** (`deskew_flag`). Runs Canny edge detection, then a
   Hough line transform (`cv2.HoughLines`, threshold=200) over the first
   200 detected lines. For each line's `theta`, converts to a "degrees off
   horizontal" value and keeps only those within ±15°, then takes the
   **median** (not mean — median resists a few outlier near-vertical
   lines) as the estimated skew angle and applies a single
   `cv2.warpAffine` rotation around the image center with cubic
   interpolation and edge-replicated borders. If no lines survive the ±15°
   filter, skew is reported as 0.0 and the image passes through unrotated.
3. **Flatten background** (`flatten_background`, always applied). Computes
   a heavily Gaussian-blurred version of the image (`sigmaX=25`) as an
   estimate of the large-scale illumination/paper-tone gradient, then
   divides the original by that blur and rescales — this is a classic
   "divide out the background" illumination-correction trick, so a scan
   that's darker in one corner from uneven lighting or foxed paper doesn't
   throw off later thresholding.
4. **`clean()`** — the default output (`<name>_clean.png`): flatten →
   optional Lanczos upscale (`fx=fy=upscale`, default 2.0) → CLAHE
   (contrast-limited adaptive histogram equalization, clip limit 2.0,
   8×8 tiles — boosts local contrast without blowing out the whole image
   like a global histogram stretch would) → a mild unsharp-mask sharpen
   (`addWeighted(eq, 1.5, blurred, -0.5, 0)`, i.e. `1.5×original -
   0.5×blurred`).
5. **`high_contrast()`** — optional second output (`highcontrast=true`):
   flatten → upscale → `cv2.adaptiveThreshold` (Gaussian-weighted local
   mean, block size 25, C=10) to pure binary black/white. Explicitly
   documented as "boundary tracing only" — it destroys the fill
   hatching/texture that distinguishes one material from another, so it's
   an alternative reference image, not a replacement for `clean`.
6. **Upscale recommendation** (`recommend_upscale`) — a pure heuristic
   with no image analysis beyond width/height: target the longest side at
   ~3000px, clamp the resulting factor to `[1.0, 4.0]`, round to the
   nearest 0.5. The reasoning baked into its returned message: extraction
   caps whatever you send to at most 3072px on the longest side anyway
   (`MAX_SEND_DIMENSION` in the extraction modules), so recommending an
   upscale that lands near that same number means preprocessing's upscale
   isn't doing work that gets thrown away one step later — while a
   genuinely low-DPI scan still gets real help keeping thin lines from
   disappearing.

Whichever output is produced, `clean_image_path` in `meta.json` is what
every later stage (extraction, the visualizer's auto-loaded image) reads.

### Stage 2 — extraction (`pipeline/extract_illustrator.py` /
`extract_fieldwall.py`)

Both call `google.genai` with `model="gemini-2.5-flash"`,
`response_mime_type="application/json"`, a Pydantic `response_schema` (so
Gemini's structured-output mode enforces the shape server-side),
`temperature=0.1` (low — this is transcription, not creative generation),
and `thinking_config=types.ThinkingConfig(thinking_budget=1024)`. That
budget is deliberately small: 2.5-flash thinks before writing any JSON by
default, and on a dense, many-layer sheet that reasoning alone was pushing
requests past Google's server-side deadline into a 504.

Before sending, the image is opened with `Image.MAX_IMAGE_PIXELS = None`
(these are the app's own preprocessed output, not an untrusted upload, so
PIL's decompression-bomb guard is deliberately disabled) and then capped
to at most `MAX_SEND_DIMENSION = 3072`px on the longest side
(`_cap_for_sending`, Lanczos resize) — independent of whatever
upscale factor preprocessing used, so a big upscaled scan or a raw
4284×5712 field photo doesn't turn into a slow, oversized base64 payload
with no accuracy benefit.

The call itself goes through `_extract_common.generate_with_retry`: up to
5 attempts, exponential backoff (`2**attempt` seconds), retrying only on
status codes `{429, 500, 502, 503, 504}` (429 = quota, 5xx = server-side),
capped by a 600-second wall-clock budget for the whole retry loop so a
Google-side outage can't silently burn five attempts' worth of image
tokens chasing a request that's going to keep failing. After the response
comes back, `_extract_common.check_response` inspects
`response.candidates[0].finish_reason` for a `MAX_TOKENS` cutoff *and*
independently attempts to `json.loads` the raw text — belt and suspenders,
since a response can also get truncated by a plain network cutoff that
`finish_reason` won't report. Either failure mode returns a warning string
telling the person to raise `max_output_tokens` and re-run, rather than
letting a truncated file fail three stages later as a cryptic
`JSONDecodeError` inside the normalizer.

**Illustrator-sheet prompt** (`extract_illustrator.PROMPT_TEMPLATE`) walks
Gemini through six numbered steps: (1) calibrate against the metric scale
bar specifically — the prompt explicitly warns that a capitalized surname
next to a year (a signature) is not a unit, and instructs those into
`credits.attributions` instead of inventing a unit conversion for them;
(2) list grid labels and estimate their x-positions as a *reference*, not
as mandatory sample points; (3) **trace each layer's boundary
independently** — this is flagged as the most important instruction, with
three explicit named warning signs of doing it wrong (two boundaries
sharing the same up/down pattern shifted by a constant depth; every layer
having the same point count at the same x-positions; a constant vertical
gap between layers across the whole face) and an instruction to go back
and re-read each line separately if any of those show up; (4) inventory
every distinct layer per face against the legend, without merging visually
distinct bands; (5) capture discrete features either as a traced
`shapePoints` outline or an `approx*` box, assigned to exactly one layer
even if it visually spans two; (6) mark uncertain coordinates `null` with
a `confidence` string explaining why, per-point rather than globally. A
final section explicitly forbids historical/chronological interpretation
— the model is told to transcribe only what's drawn, labeled, or written,
even in `inferred_notes` (methodology only).

**Field-wall prompt** (`extract_fieldwall.build_prompt`, parameterized by
the user-supplied `square_cm`) differs in three structural ways from the
illustrator prompt: scale comes from **counting minor grid lines within a
known bold-square size** the recorder already gave, not a printed scale
bar; material is a **Locus number + Munsell soil-color notation**
transcribed verbatim, not a hatch-pattern legend; and coordinate labels at
the sheet's edges are transcribed into `gridTiePoints[].rawText` **without
interpreting** whether they're northings, eastings, or elevations — that's
explicitly deferred to a human checking site records. The boundary-tracing
instruction is reframed around the sheet's own convention: the recorder
marks each *measured* vertex with a small circle and connects the dots
with straight segments, so the model's job is to find and report each
visible circle marker's position, not to resample the curve's shape at
its own chosen intervals — with the same "if your spacing comes out even,
you're estimating, not reading markers" warning as the illustrator prompt.

`upload_extraction` (`POST /api/jobs/<id>/extract/upload`) is the
escape hatch around all of the above: paste in a `.json` file (e.g. one
recovered from git history, or a hand-corrected extraction) and the route
sniffs which of the two schemas it matches (`trenchProfiles` key present →
illustrator; `convert_coords.is_field_wall()` → field-wall) and installs
it as this job's extraction, skipping Gemini entirely. Every later stage
reads whichever `extraction_path` is currently in `meta.json`, so it can't
tell the difference between a freshly-called extraction and an uploaded
one.

### Stage 2 alternative — CV marker detection (field-wall sheets only)

Built specifically because Gemini free-tracing kept producing
geometrically fabricated boundaries on T104-style sheets (see *Known open
items* below). Division of labor: **coordinates come from computer
vision and are never touched by Gemini**; Gemini only classifies which
boundary each CV-found point belongs to and reads the sheet's printed
text. Five HTTP round-trips, each backed by one pipeline function:

1. **`/markers/preview`** → `detect_markers.write_rotated_preview` reads
   the scan with `cv2.IMREAD_IGNORE_ORIENTATION` (so EXIF auto-rotation
   metadata from a phone camera can't silently flip the image differently
   on different machines), applies one of the four `rotate ∈ {0, 90, 180,
   270}` clockwise rotations the user picks, and writes that fixed working
   frame to disk. **Every pixel coordinate from this point forward — the
   user's clicks, the CV detections — is in this rotated frame.**
2. **`/markers/detect`** → `detect_markers.run_detect`. The user clicks
   three points on the *preview* image (wall's top-left corner = the
   origin, top-right corner, and the wall's lowest point) and supplies the
   real-world distance between the two top corners (read off the sheet's
   own tie labels, e.g. two tie labels "194 m" and "190 m" 4m apart). From
   that: `px_per_m = pixel_distance(top-left, top-right) / ref_meters`,
   and `mm_px = px_per_m * square_cm / 1000` converts the marker
   size limits (given in *paper millimeters* — how big the recorder's
   pencil dot is on the sheet — assuming one bold grid square is 1cm of
   paper, standard mm graph paper) into pixels. The actual detector:
   - **Ink mask**: adaptive mean threshold (`cv2.ADAPTIVE_THRESH_MEAN_C`,
     block size scaled to `~2mm` of paper) on the grayscale image, ANDed
     with a "not red" mask (`redness = R - (G+B)/2 < 25`) — the adaptive
     threshold alone survives uneven phone-photo lighting and faint
     pencil that a single fixed gray cutoff would fragment; the redness
     filter exists so red pen/ink annotations don't get treated as marker
     candidates.
   - **Morphological opening** with an elliptical kernel sized to
     `~0.35mm` of paper — this is what lets a vertex dot that visually
     touches its boundary line survive as its own blob, rather than
     merging into one large non-circular contour and disappearing from
     the circle hunt entirely.
   - **Candidate restriction to a "wall box"**: the two corner clicks plus
     a margin (`box_margin_paper_mm`, default 2mm) define left/right/top
     bounds, and the third click (lowest point) sets the bottom bound —
     this alone drops handwriting, the Munsell legend, and any table in
     the photo from consideration before circularity is even checked.
   - **Per-contour filters**: diameter must fall between
     `min_marker_paper_mm`/`max_marker_paper_mm` (defaults 0.5–2.5mm,
     converted via `mm_px`); circularity `4π·area/perimeter² ≥ 0.65`;
     solidity (area / convex-hull area) `≥ 0.9`; fill (area / enclosing
     circle's area) `≥ 0.5`. Dots are small, solid, filled disks — stone
     outlines and nested-contour duplicates fail one or more of these.
   - **Dedupe**: candidates are sorted largest-first, and any candidate
     within half a minimum-diameter of an already-kept point is dropped —
     this collapses nested/duplicate contours from the same physical dot
     down to one.
   - Every surviving marker gets `x_m = (pixel_x - origin_x) / px_per_m`
     and `depth_m = (pixel_y - origin_y) / px_per_m`, plus a debug PNG
     (green circles = accepted, red = rejected-but-in-box, magenta box =
     search region, magenta/orange crosses = the two corner clicks) and a
     CSV, both written into the job's `03_extraction/` folder.
3. **`/markers/confirm`** — the person reviews the candidate list (toggle
   off false positives, add any the CV missed by hand), and this route
   installs that reviewed list as `markers_confirmed.json`, **always
   recomputing `x_m`/`depth_m` from the submitted pixel coordinates
   server-side** rather than trusting client-submitted meter values — so
   a manually-added point and a CV-detected point are calibrated
   identically. This step is optional: `/markers/assign` will run on the
   raw CV output (`markers.json`) if a person skips straight past review.
4. **`/markers/assign`** — sends the confirmed markers' `(x_m, depth_m)`
   list as plain text (not as image annotations) alongside the rotated
   photo, and asks Gemini for exactly two things: (a) verbatim transcription
   of the sheet's text fields (trench/face labels, date, tie points, loci +
   Munsell colors, marginalia), and (b) for every single marker id, a
   classification into `"top"` with a `locusNumber` (that locus's named
   upper boundary), `"base"` (the final line below the deepest locus), or
   `"noise"` (stray dot, hatch mark, stone — not a boundary vertex at
   all). The prompt is explicit that these coordinates are fixed and the
   model must not invent, move, or report new ones.
5. **`/markers/finalize`** — deterministic, no network call: assembles the
   classified markers plus the immutable CV coordinates into a
   `FieldWallProfile` JSON. Per-locus top boundaries are built by
   grouping markers with the same `locusNumber` and sorting by `x_m`; loci
   are ordered top-to-bottom by the mean depth of their assigned top
   markers; each layer's `bottomBoundary` is the *next* locus's top markers,
   or the `"base"`-classified markers for the deepest locus. Thus the
   shallowest named line remains the top of Locus 1 instead of shifting all
   locus names down one line.
   Along the way it collects warnings for anything Gemini did
   inconsistently — an assignment referencing an unknown marker id, the
   same marker id assigned twice, a locus with fewer than 2 boundary
   markers (too few to draw a line), a locus named in the legend that got
   no boundary markers at all — and appends a `[provenance]` line to
   `marginalia` recording exactly how many markers ended up boundary vs.
   noise, so that provenance travels with the file even after
   it's downloaded.

  **Known bug as of the last commit**: the `/markers/assign` and
  `/markers/finalize` routes in `app.py` call
  `pipeline.assign_markers.classify_markers` and
  `.finalize_assignments` — names that do not exist in
  `assign_markers.py`. That file currently only defines `run_assign`
  (the older, single-function version: classify *and* write the output
  file in one call) plus its `build_prompt`/`_assemble` helpers. The
  `app.py` side of a two-step classify/finalize split landed in the
  latest commit; the corresponding split in `assign_markers.py` did not.
  **Calling either route today raises `AttributeError`.** Fix is either
  to add `classify_markers`/`finalize_assignments` wrapper functions
  around the existing `_assemble`/`run_assign` logic, or to revert
  `app.py`'s two routes back to calling `run_assign` directly.

### Stage 3 — normalize (`pipeline/normalizer.py`)

Two structural cleanup passes over the raw extraction JSON, run in this
order, both logging every change into a flat list of human-readable
strings returned alongside the cleaned data:

1. **`clean_null_strings`** — recursively walks every dict/list and turns
   any string value that (after `.strip().lower()`) equals `"null"`,
   `"none"`, `"n/a"`, or `""` into an actual JSON `null`. This exists
   because Gemini sometimes writes the literal word "null" as a string
   instead of leaving the field absent, which downstream code that checks
   `is not None` would otherwise treat as a present value.
2. **`dedupe_floor`** — per face, checks whether the deepest layer's
   `featuresInLayer` contains something named with "floor" in it whose
   `shapePoints` are geometrically identical (compared via rounding each
   coordinate to 3 decimal places) to that same layer's `bottomBoundary`
   — i.e. the trench floor got traced once as a boundary and a second time
   as a redundant "feature." Drops the duplicate feature entry.
3. **`dedupe_cross_layer_features`** — per face, builds a signature (lowercased
   feature name + rounded shape-point tuple) for every feature across every
   layer, keeping only the *last* layer a given signature appears in — this
   catches the same physical feature (e.g. a stone outline near a layer
   boundary) getting attributed to two adjacent layers by the model.

### Stage 4 — validate (`pipeline/validator.py`)

Returns `{errors: [...], warnings: [...], ok: bool}` — `ok` is `len(errors)
== 0`; warnings never block anything downstream. If the extraction is a
`FieldWallProfile` (no `trenchProfiles` key), it's adapted through
`convert_coords.fieldwall_to_profiles()` first so every check below runs
against the same face/layer shape either way. Per face:

- **`check_uniform_spacing`** (the primary fabrication check) — takes
  consecutive x-gaps along a boundary's vertices, computes their
  coefficient of variation (`stdev/mean`), and warns if `cv < 0.02` — real
  hand-traced or marker-derived boundaries land around 0.20; a boundary
  sampled at a fixed interval instead of actually read comes out at
  ~0.00.
- **`check_parallel_layers`** — compares every pair of layers' bottom
  boundaries that share identical x-stations and point counts; if the
  depth differences between the two are all within 5mm of each other
  (`spread ≤ PARALLEL_OFFSET_TOLERANCE_M`), warns that one boundary is
  almost certainly a copy of the other offset by a constant, not two
  independently-traced lines.
- **`check_boundary`** (per top/bottom boundary) — errors on any point
  with a null x or y that has no `confidence` note explaining why; errors
  on any negative depth (the convention is positive-down); warns on
  depths beyond `max_plausible_depth_m` (default 5.0m); warns if x-values
  aren't monotonically left-to-right.
- **Cross-layer checks** — for consecutive layers (top-to-bottom order as
  listed in the JSON), interpolates the previous layer's bottom boundary
  at each x-station of the current layer's top (`depth_at_x`, simple
  piecewise-linear interpolation, clamped at the ends) and warns if the
  gap between "previous bottom" and "this top" exceeds
  `top_continuity_tolerance_m` (default 0.10m, "possible void/overlap");
  separately, **errors** (not warns) if the current layer's *bottom* comes
  out shallower than the previous layer's bottom by more than
  `monotonic_tolerance_m` (default 0.02m) — that means the layers
  literally cross, which is geometrically invalid for a conformable
  stratigraphic sequence.
- **`check_features`** — warns if a feature has neither `shapePoints` nor
  any `approx*` field (geometry might be trapped only in the free-text
  `description`); if it does have `shapePoints`, warns on any point whose
  depth falls outside `[layer's top-boundary min, layer's bottom-boundary
  max]` by more than the monotonic tolerance.
- **Field-wall-only checks** (`_check_field_wall_extras`) — warns if a
  layer references a locus number absent from `loci[]` (no Munsell
  reading for it); warns if the same locus number appears more than once
  in `loci[]` (the converter will silently use the first); cross-checks
  the numeric values embedded in `gridTiePoints[].rawText` (e.g. "194 m")
  against how far apart those same tie points were placed in the drawing
  — if the ratio of "label span" to "drawn span" is off by more than 1.5×
  in either direction, warns that the extracted scale is probably wrong.

All three tolerances (`monotonic_tolerance`, `top_continuity_tolerance`,
`max_depth`) are exposed as request-body overrides on `POST
/api/jobs/<id>/validate`, not hardcoded.

### Stage 5 — convert coordinates (`pipeline/convert_coords.py`)

Turns each face's local `(x along face, depth down from surface)` points
into site-wide `(X, Y, Z)` using one rigid transform per face, defined by
four numbers a person supplies per face (`GET
/api/jobs/<id>/gridconfig/starter` returns a placeholder starter config —
`originX/Y = 0, 0`, `surfaceZ = 100`, `bearing_deg = 90`, offset by 10m
per face index — that's a smoke-test shape, not real survey data):

```
X = originX + x · sin(bearing_deg in radians)
Y = originY + x · cos(bearing_deg in radians)
Z = surfaceZ − depth
```

`bearing_deg` is the compass direction (clockwise from north) that the
face's local +x axis points in site coordinates; `originX/Y` is where that
face's local x=0 sits; `surfaceZ` is the ground-surface elevation at that
same point, so `depth` (positive-down, local) becomes `Z` (absolute
elevation) by simple subtraction.

Alongside every boundary's points, `convert()` also writes exactly one
**orientation seed** (a `dip`/`azimuth`/`polarity` row GemPy uses to
constrain the surface's local tilt) per boundary, computed via
`least_squares_slope`: an ordinary least-squares fit of depth against x
over **every point on that boundary**, not just its two endpoints. This
matters on a wavy, hand-drawn boundary where the first and last point
alone could suggest a slope the middle of the line doesn't actually have
— note in the code explicitly calls out that this least-squares approach
was accidentally dropped during a file-reorganization commit and had to
be restored, since the webapp had silently inherited the weaker
endpoint-only version. The seed point itself is placed at the boundary's
*middle* point (`xs[len(xs)//2]`), converted to site coordinates the same
way as any other point.

`fieldwall_to_profiles()` is the adapter that lets a `FieldWallProfile`
(one wall, `loci[]` + `layers[]`, Locus-number-and-Munsell material) flow
through this same `trenchProfiles`-shaped code path: it produces exactly
one synthetic face, names each surface `"Locus N (munsell)"` by joining
each layer's locus number to its looked-up Munsell reading (falling back
to `"Locus N"` with a note if no Munsell entry exists, and noting —
rather than silently overwriting — when the same locus number appears
twice in `loci[]`), and uses that locus's `topBoundary` as its named model
surface. The temporary generic adapter stores that interface in the
`bottomBoundary` slot that `convert()` reads; other raw field-wall geometry
is still served intact to the visualizer. `make_starter_config` also surfaces the
sheet's transcribed `gridTiePoints[].rawText` verbatim under
`_tiePointsFromSheet` in the returned config for a human to cross-check
against site records — it does not attempt to interpret which axis they
represent.

`run_convert()` writes both `points.csv` (`X, Y, Z, surface, face`) and
`points_orientations.csv` (adds `dip, azimuth, polarity`) into
`05_convert_coords/`, and reports any face named in the extraction that
had no matching entry in the submitted grid config (`missing_faces`) —
if that leaves zero total points, the route 400s with an explicit
explanation rather than handing GemPy an empty CSV.

### Stage 6 — GemPy model (`pipeline/build_gempy.py`)

Optional heavy dependency (`pip install gempy gempy_viewer`), imported
lazily so the rest of the app works without it. Given the two CSVs:

- **Extent**: if not explicitly supplied, `infer_extent` takes each axis's
  min/max across all points and pads by `max(10% of that axis's span, a
  minimum padding value)` — `padding_xy` (default 2.0m) and `padding_z`
  (default 1.0m) set the minimums so a single-face model (near-zero span
  on one axis) still gets a sane box instead of a zero-width extent.
- **Stratigraphic order**: if not explicitly supplied via `series_order`,
  `infer_series_order` groups all points by `surface` name, averages each
  surface's `Z`, and sorts descending — i.e. it assumes shallower average
  elevation means younger/higher in the pile, which is the ordinary
  reading of an undisturbed conformable sequence but would be wrong for
  a genuinely inverted or faulted one.
- **Single-face-surface warning**: before building, checks whether any
  surface's points come from only one face (`coverage.groupby(...)`) and
  logs (and returns in the result dict as `single_face_note`) that such a
  surface will still get interpolated across the *entire* model extent —
  worth knowing before trusting the shape of a boundary far from the face
  that actually constrains it.
- Builds via `gp.create_geomodel` + `gp.map_stack_to_surfaces` (a single
  `"Strat_Series"` stack — i.e. this assumes one continuous conformable
  sequence, not multiple unconformity-bounded series) + `gp.compute_model`.
- **Outputs**: the `.gempy` project file (`save_model=True` by default);
  a `.npz` of the raw lithology block array plus its resolution/extent (so
  the voxel grid can be reloaded without recomputing); one `.obj` mesh per
  surface (`export_meshes`, vertex/face arrays from
  `solution.raw_arrays`, filenames sanitized via `safe_filename` — any
  character outside `[A-Za-z0-9_.-]` becomes `_`); and, if plotting
  succeeds, a 2D cross-section PNG at the requested
  `vertical_exaggeration` plus an optional **zoomed** second PNG. The zoom
  range (`middle_zoom_range`) defaults to just the *middle* surfaces
  (dropping the shallowest and deepest, which tend to be much thicker/less
  interesting) and pads their combined Z-span by 25% (or a 5cm floor),
  rendered at 3× the main plot's vertical exaggeration by default — this
  is the plot meant to actually show thin-layer detail that the full-depth
  section compresses into a sliver. Plotting failures are caught and
  logged as a warning rather than failing the whole build — the model
  itself is still saved even if matplotlib/gempy_viewer chokes on
  rendering it.

## Known open items

### 1. Grid registration is still placeholder — this is the binding constraint

`convertCoords`' per-face registration (`originX`, `originY`, `surfaceZ`,
`bearing_deg`) has never been real survey data. With the old smoke-test
placeholder, all points land on Y=0 and the three Trench 23 faces sit
end-to-end across 31 m, so GemPy builds one long section extruded sideways,
not a trench. The hypothetical `gridConfigConnected` values (faces meeting at
real corners) produce a proper 2.8 × 5.8 m pit from the same code — so the
only thing missing for a legitimate Trench 23 model is four real numbers per
face from the site records.

### 2. Boundary geometry is partly fabricated in BOTH extractions

The validator now checks for this automatically (see *Fabrication checks*).
Current status of the existing extraction runs:

| extraction | copy-pasted layer pairs | verdict |
|---|---|---|
| `output_section001.json` | 26 (East 1, South 10, West 15) | **use this one** — East face is genuinely traced |
| `output_single_section001.json` | 63 (21 per face = every possible pair) | discard — every layer is one shape copied down |
| `field_wall_t104.json` | 6 pairs + all vertices on a fixed 0.08 m interval | discard — geometry invented, scale ~5× off |

This resolves the old "the two extractions disagree and there's no way to
pick" item: pick `output_section001.json`, and treat only its East face
geometry as trustworthy. South and West need re-extraction.

For T104 the fix is CV marker detection — the recorder marks each measured
vertex with a small circle, so finding them is a computer-vision problem, and
CV cannot invent a marker that isn't there. This is now wired into the GUI as
a five-step flow (`poggio_webapp/pipeline/detect_markers.py` +
`assign_markers.py`, routes `/markers/preview` → `/markers/detect` →
`/markers/confirm` → `/markers/assign` → `/markers/finalize`):

1. **preview** — rotate the scan into a working frame
2. **detect** — click the wall's top-left/top-right/lowest point, give the
   real width between the top corners, get CV-detected marker candidates
3. **confirm** — user reviews/toggles candidates, adds any missed by hand
4. **assign** — Gemini *classifies* each confirmed marker (top of locus N /
   final base / noise) and reads the sheet's labels — it does not touch
   coordinates
5. **finalize** — the (possibly user-corrected) classification is combined
   with the immutable CV coordinates into the extraction JSON, no network
   call

The marker→locus gap is closed in design: geometry can no longer be
fabricated because Gemini is restricted to labeling fixed, CV-found points
rather than tracing boundaries. `tools/detectFieldWallMarkers.py`, the
original CLI version, is superseded by this and kept only for reference.
**However, the assign/finalize half is currently broken** — see *How it
works → Stage 2 alternative* above for the exact function-name mismatch —
so nothing has actually been run end-to-end through this new path yet, and
that has to happen (and be re-checked against the extraction-quality table
below) before this item can be called done.

### 3. Scan resolution (Trench 23)

Cross-checking against the scan turned up 5 of the legend's 14 materials never
appearing as a layer or feature anywhere (Light; Pink-Yellow with Carbon and
Plaster; Yellow; Gray-Yellow with Carbon; Traces of Carbon) — most likely
folded into neighboring "Dark Gray"/"Buff-Gray" calls. Probably a resolution
limit rather than a prompting problem; `preprocess.py`'s upscaling won't
recover what isn't there. Worth a rescan if the original artifact is
available.

### 4. Settled questions

- The T104 southern baulk wall is an ordinary trench wall, not a cut feature —
  the one-conformable-series approach applies as-is.
- The coordinate labels along the top of the T104 sheet are relative to the
  site's overall grid. Their *values* still need confirming against site
  records; `make_starter_config` now surfaces them verbatim under
  `_tiePointsFromSheet` without interpreting them.

## Fabrication checks

`pipeline/validator.py` flags the two failure modes seen so far:

- **evenly spaced vertices** — real traced boundaries have irregular vertex
  spacing (Trench 23 sits around cv 0.20); fabricated ones come out at cv 0.00.
- **identical boundary shapes offset by a constant** — one boundary copied
  down rather than several traced.

Both are warnings, not errors: they are strong signals, not proof.

## Roadmap

Ordered by leverage, not effort. The organizing principle: make the existing
results scientifically valid first, then make the pipeline trustworthy, then
make it general. Phase 1 restates the open items above as a sequence; nothing
in phases 2–3 matters while the underlying geometry is still invalid.

### Phase 1 — unblock the science

1. **Real grid registration** (open item 1). Get the four numbers per face
   from the site records. Also add a provenance field to the grid config
   (`"source": "surveyed" | "placeholder"`) and have `build_gempy` refuse —
   or at least watermark its output PNGs — when building from placeholders.
   Right now nothing stops a placeholder model from being mistaken for a real
   one once it leaves the app.
2. **Fix the broken `assign_markers` wiring, then run T104 through it.**
   `app.py`'s `/markers/assign` and `/markers/finalize` routes call
   `pipeline.assign_markers.classify_markers` /
   `.finalize_assignments`, but `assign_markers.py` only defines
   `run_assign` (the older single-call design) — calling either route
   throws `AttributeError` right now. Either split `run_assign` into the
   two named functions `app.py` expects, or point `app.py` back at
   `run_assign`. Only once that's fixed does ~~wire
   `detectFieldWallMarkers.py` into the GUI and close the marker→locus
   gap~~ (open item 2) actually become **done**: re-extract T104 through
   preview → detect → confirm → assign → finalize, then re-check it
   against the extraction-quality table above.
3. **Re-extract Trench 23 South and West faces.** The evidence so far (East
   genuine in the per-section run, the all-faces-at-once run fully
   fabricated) says extract one face per API call. Make per-face extraction
   the default for illustrator sheets and validate each face independently.
4. **Rescan Trench 23 at 300+ DPI** if the original sheet is accessible
   (open item 3), then re-check the five missing legend materials. That
   settles resolution-limit vs. prompting-problem — currently a hypothesis.

### Phase 2 — verification infrastructure

5. **Tests.** The highest-value targets are all pure functions:
   `least_squares_slope`, the coordinate transform,
   `fieldwall_to_profiles`, and the two fabrication heuristics — which can
   be fed the known-fabricated and known-genuine extractions already sitting
   in git history as fixtures. Add a golden-file test running
   `output_section001.json` through convert → validate, then CI.
6. **Scan-vs-extraction scoring.** Today's A/B check is eyeballing in
   `visualizer.html`. Cheap objective metric: rasterize each extracted
   boundary polyline and measure overlap with ink pixels in the preprocessed
   scan. A boundary that doesn't lie on ink is fabricated by definition —
   this upgrades the fabrication checks from statistical signatures to
   direct evidence, and can run automatically at stage 5.
7. **Hygiene.** Route uploads through `safe_job_path`/`secure_filename`
   (the download route is guarded; the upload route saves the raw client
   filename). Pin versions in `requirements.txt`. Add a license. Persist the
   in-memory task registry to the job folder, or document that a server
   restart orphans running tasks. Age-based sweep for `jobs/`.

### Phase 3 — generalize past these two drawings

8. **Ensemble extraction as an uncertainty signal.** Run extraction twice
   (different temperature or provider) and diff the geometries: agreement is
   cheap evidence of genuine tracing, divergence flags regions for review.
   Pairs naturally with putting the Gemini client behind an interface so
   other vision models can slot in.
9. **In-browser boundary editor.** Extraction will never be perfect, so the
   pragmatic endgame is human-in-the-loop: show the extraction overlaid on
   the scan, drag/add/delete vertices before validation. Turns every
   "discard and re-extract" cycle into a five-minute correction — probably
   the single biggest usability win available.
10. **Schema unification.** `ArchaeologicalDiagram` and `FieldWallProfile`
    currently converge via an adapter inside `convert_coords`. Promote the
    converged form to a first-class internal schema with the two extraction
    formats as input adapters, so validator/converter/builder stop needing
    the dual `get_x`/`get_y` fallbacks.
11. **Batch mode.** Poggio Civitate has decades of trench documentation.
    Once single-sheet extraction is trustworthy: a batch queue (the async
    task registry already half-exists), persistent job naming, and
    site-level aggregation of multiple trenches into one GemPy model.
12. **Standards-compliant export.** Harris matrix from the stratigraphic
    order, GeoJSON in site coordinates for GIS, and propagate the per-point
    `confidence` fields (captured in the schema, unused downstream) into
    the exports.

If effort is limited, items 6 and 9 deserve to jump the queue: together they
turn the workflow from "extract, inspect statistically, hope" into "extract,
score against the scan, correct by hand" — the realistic shape of a
production digitization tool.

## Recovering old artifacts

The pre-`webapp` outputs and CLI scripts are all still in git:

```bash
git show d383439^:03_extraction/output_section001.json > output_section001.json
git show d383439^:05_convert_coords/gridConfig.JSON    > gridConfig.JSON
git show d383439^:06_gempy_model/trench23.gempy        > trench23.gempy
git log --oneline --all -- "*convertCoords.py"          # etc.
```
