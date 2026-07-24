# Trench Digitization Pipeline — Web GUI

A browser front end for the numbered pipeline (`01_scans` … `07_visualizer`):
upload a scan, click through each stage, download or carry forward the
outputs, and open the 3D result — instead of running each script by hand.

```
poggio_webapp/
  app.py               Flask API — one route per pipeline stage
  pipeline/            each stage's original logic, adapted into importable
                        functions (preprocess, extract_illustrator,
                        extract_fieldwall, normalizer, validator,
                        convert_coords, build_gempy)
  templates/index.html the wizard shell
  static/app.js         all frontend logic (vanilla JS, no build step)
  static/style.css      styling
  static/visualizer.html  your original 07_visualizer, served as-is
  tools/                standalone helpers NOT wired into the GUI
                        (pixel_picker.html; detectFieldWallMarkers.py is
                        superseded by pipeline/detect_markers.py, which is
                        wired in)
  jobs/                 created at runtime — one folder per session,
                        mirroring 01_scan .. 06_gempy_model
```

`pipeline/` keeps the original scripts' schemas, prompts and defaults; they
were restructured from `argparse` CLI scripts into functions the Flask routes
can call directly. Interface points still match the original CLI byte-for-byte
given the same inputs. Two deliberate departures from the pre-webapp CLI:

- `convert_coords` computes orientation dip from a least-squares fit over all
  boundary points, restoring commit `b01638d` — that improvement was silently
  dropped during the `file organize` commit and the webapp had inherited the
  endpoint-only slope. Interface points are unaffected; only dips change.
- `validator` accepts `FieldWallProfile` JSON instead of rejecting it with
  "no trenchProfiles", and adds the fabrication checks described below.

## Setup

```bash
cd poggio_webapp
python3 -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt --break-system-packages
```

Stage 06 (the GemPy 3D model) needs a heavier, separate install — left out of
`requirements.txt` by default so the rest of the app works without it:

```bash
pip install gempy gempy_viewer --break-system-packages
```

If a scan is a PDF, stage 02 also needs poppler:
```bash
apt install poppler-utils     # macOS: brew install poppler
```

## Running it

```bash
python3 app.py
```
Open **http://localhost:5000**. `PORT` and `FLASK_DEBUG=1` env vars are
respected if you want a different port or the auto-reloading dev server.

## Using it

The first screen offers two workflows. In both, choose the diagram type
before supplying or drawing the geometry:

- **Illustrated trench sheet** produces an `ArchaeologicalDiagram`. Use it
  for archaeological profiles whose layers are described by materials,
  patterns, or shading.
- **Hand-drawn field sheet** produces a `FieldWallProfile`. Use it for a
  graph-paper wall record whose layers are identified by locus numbers and
  Munsell soil colours.

### Upload an existing drawing

1. Select **Use an existing drawing**, then choose the illustrated or
   field-wall type.
2. Upload a PNG, JPEG, TIFF, or PDF. The original file is not modified. The
   screen shows a preview for images or a ready message for PDFs, displays
   dimensions when available, and enables the next step.
3. **Prepare the image** — tune upscale, deskew, and high contrast and inspect
   the cleaned image.
4. **Trace the layers**, or use **Other ways to add data** to import JSON or
   call automatic extraction. A Gemini API key entered for extraction is sent
   only to the local server for that request and is not written to disk.
5. **Clean up the data**, **Check for problems**, and **Place it on the
   site**. Coordinate conversion requires surveyed `originX`, `originY`,
   `surfaceZ`, and `bearing_deg` for every face.
6. **Create the 3D model**, then use **View and download** for the completed
   result.

An upload creates a normal pipeline job when the file is selected. It does
not call `/editor/new` or create a blank-editor draft.

For field-wall uploads, the marker-detection route is the more trustworthy
automatic option: mark the wall's top-left, top-right, and lowest points,
provide the surveyed width, review the detected vertices, and let Gemini
classify only those fixed coordinates. Finalizing that classification does
not make another network call.

### Create a diagram from scratch

1. Select **Create a diagram from scratch**, choose the illustrated or
   field-wall type, and click **Open blank drawing canvas**.
2. Set up and name the profile faces. Archaeological diagrams accept 1–12
   uniquely named faces and show one tab per face. Field-wall diagrams enforce
   a single face; only its name is requested.
3. Draw on the fixed **3 m wide × 2 m deep** metric canvas. Grid lines are
   spaced every **0.25 m**. Snap-to-grid starts enabled but can be turned off.
4. Click or tap the canvas to place vertices. A polygon needs at least three
   vertices before **Close shape** will work. The editor automatically numbers
   polygons, keeps their stacking order, and opens the metadata form when a
   shape closes.
5. Correct a shape as needed:
   - drag an existing vertex;
   - select an edge midpoint to insert a vertex;
   - select a vertex and use **Delete selected vertex** (or modifier-click a
     vertex);
   - use **Undo last vertex** or **Cancel current shape** while drawing; or
   - delete a closed polygon from the polygon list.

   A self-intersecting polygon receives a dashed warning stroke and cannot be
   finalized.
6. Add polygon metadata. Archaeological polygons require a **Material** and
   may include a note; the material is the polygon's label in the list.
   Field-wall polygons require a **Locus number** and **Munsell notation**,
   for example `10YR 5/3`, and may include a note. Select a polygon in the
   sidebar to revise its metadata.
7. Optionally add drawing-level context such as trench label, recorder or
   illustrator, date, and a general note. Field-wall drawings also accept a
   face label and north-arrow status.
8. Register every face to the surveyed site grid:
   - `originX` and `originY`: site coordinates of the face's local x=0 edge;
   - `surfaceZ`: ground-surface elevation at that edge; and
   - `bearing_deg`: clockwise-from-north bearing of the face's local +x axis,
     from 0 through 360.

   All four values are required for every face. Use survey data, not
   placeholders.
9. Changes autosave about two seconds after editing; initial face setup is
   saved immediately. **All changes saved** confirms persistence. If saving
   fails, the editor shows **Couldn’t save**, retains the current state on
   screen, and offers **Retry save**.
10. Refreshing the editor restores saved faces, polygons, metadata, active
    face, and registration. Drafts are also listed on the home page under
    **Previous work** as **Created from scratch — Work in progress**; select
    one there to resume it.
11. **Finalize** is enabled only after every face contains at least one
    closed, non-self-intersecting polygon, every polygon has the metadata
    required by its diagram type, and every face has complete grid
    registration. The editor first saves final changes, then assembles the
    schema and starts normalization, validation, coordinate conversion, and
    GemPy model building.
12. The results page shows **Creating 3D model** while it polls the saved job
    status. It reloads to **Your 3D model is ready** when building finishes.
    If processing fails, it reports that the drawing is still saved and links
    back to the editor for review.

## Regression tests

Run from the repository root:

```bash
.venv/bin/python -m pytest -q
node poggio_webapp/static/canvas/grid.test.mjs
node poggio_webapp/static/app/stages/start-options.test.mjs
git diff --check
git status --short
```

If `.venv/bin/python` does not exist, substitute `python3 -m pytest -q`.

## Notes / known limits

- **Grid registration is still placeholder data.** This is the single biggest
  limiter on model quality — see the open items in the top-level README.
- **The validator now flags fabricated geometry** (vertices on a perfectly
  regular interval; layers whose boundaries are one shape copied down). These
  are warnings rather than errors — strong signals, not proof. Every
  extraction produced so far trips at least one of them; read stage 5's
  warnings before trusting a model.
- **CV-based marker detection is currently broken past the "confirm" step.**
  `pipeline/detect_markers.py` (preview/detect/confirm) works. But
  `app.py`'s `/markers/assign` and `/markers/finalize` routes call
  `pipeline.assign_markers.classify_markers` /
  `.finalize_assignments` — function names that don't exist in
  `assign_markers.py` (it only defines the older `run_assign`). Clicking
  "assign" in step 3 above will 400/error until that mismatch is fixed. See
  the top-level README's *How it works* and *Known open items* sections for
  the full detail.
- Each job's working files live under `jobs/<job_id>/` on this server and
  are not cleaned up automatically — delete old job folders periodically if
  disk space matters.
- The blank editor draws polygons, not freehand paint or brush strokes.
- Blank canvases have fixed 3 m × 2 m dimensions and 0.25 m grid spacing.
- Editing is single-user; collaborative editing and merge/conflict handling
  are not implemented.
- Completed models support viewing and downloading, not arbitrary reopening
  for edits. Failed model processing does retain an editor recovery path.
