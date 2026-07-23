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

1. **Scan** — pick illustrator-sheet or field-recording-sheet, upload the
   image/PDF.
2. **Preprocess** — tune upscale/deskew/high-contrast, see the cleaned image.
3. **Mark vertices** (field sheets only; illustrator sheets skip straight to
   Extraction) — the no-network half of the CV path. Pick the photo rotation,
   confirm the bold-grid-square size in cm by hand, click the wall's
   top-left/top-right/lowest point and give the real width between the top
   corners; CV finds the recorder's circle-marked vertices (a marker can't be
   fabricated the way a traced boundary can). Review/toggle/add candidates,
   then confirm. No API key needed here.
4. **Extraction** — paste a Gemini API key (only sent to your own local
   server for that request; never written to disk by this app — get one at
   https://aistudio.google.com/apikey if you don't have one). This is
   the one stage that calls out to the network and can take a bit — progress
   streams into a log box. Three paths:
   - **Confirmed CV markers (recommended for field sheets)**: Gemini only
     *classifies* each point confirmed in Mark vertices (surface / bottom of
     locus N / noise) and reads the sheet's labels — it never touches
     coordinates. Review the proposed classification, then Finalize assembles
     it with the untouched CV coordinates, with no further network call.
   - **Gemini tracing**: full extraction from the preprocessed image (the
     only path for illustrator sheets).
   - **Upload a previous extraction JSON**: no network call at all.
5. **Normalize** — one click, shows the change log.
6. **Validate** — adjust tolerances if needed, see errors (would corrupt the
   model) vs. warnings (worth a look).
7. **Convert coordinates** — edit the grid-registration table (originX/Y,
   surfaceZ, bearing_deg per face). *Real survey values, not the smoke-test
   placeholders, are what make the absolute coordinates trustworthy* — same
   caveat as the original `gridConfig.JSON`. Works for both sheet types: a
   field sheet is adapted to the same single-face shape, with surfaces named
   `Locus N (munsell)`, and any tie-in labels transcribed off the drawing are
   listed under `_tiePointsFromSheet` for reference — verbatim, not
   interpreted.
8. **3D model** — set resolution/section direction/vertical exaggeration,
   optionally override the stratigraphic order, build. Renders the same
   cross-section + zoomed-middle-layers PNGs as the CLI, plus downloadable
   `.gempy`/mesh/lith-block files.
9. **Visualize** — opens the original `visualizer.html` in a new tab (its own
   file pickers still drive it — A/B compare two extraction runs against the
   scan).

## Notes / known limits

- **Grid registration is still placeholder data.** This is the single biggest
  limiter on model quality — see the open items in the top-level README.
- **The validator now flags fabricated geometry** (vertices on a perfectly
  regular interval; layers whose boundaries are one shape copied down). These
  are warnings rather than errors — strong signals, not proof. Every
  extraction produced so far trips at least one of them; read stage 5's
  warnings before trusting a model.
- **The CV marker flow's classify step is two-phase by design.**
  `assign_markers.classify_markers` (network call, returns a reviewable
  proposal) and `assign_markers.finalize_assignments` (no network,
  assembles the reviewed proposal with the untouched CV coordinates) back
  the `/markers/assign` and `/markers/finalize` routes; the older one-shot
  `run_assign` remains as a wrapper for script use.
- **`pipeline/detect_features.py` is not wired into the GUI yet.** It
  proposes closed-contour feature candidates (stones, cuts, lenses) for
  human review, but no `app.py` route or frontend step calls it.
- Each job's working files live under `jobs/<job_id>/` on this server and
  are not cleaned up automatically — delete old job folders periodically if
  disk space matters.