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
  jobs/                 created at runtime — one folder per session,
                        mirroring 01_scan .. 06_gempy_model
```

Nothing in `pipeline/` changes the original scripts' behavior — same schemas,
same prompts, same math, same defaults. They were only restructured from
`argparse` CLI scripts into functions the Flask routes can call directly, so
results should match the original CLI byte-for-byte given the same inputs.

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
3. **Extraction** — paste a Gemini API key (only sent to your own local
   server for that request; never written to disk by this app — get one at
   https://aistudio.google.com/apikey if you don't have one). For field
   sheets, confirm the bold-grid-square size in cm by hand first. This is
   the one stage that calls out to the network and can take a bit — progress
   streams into a log box.
4. **Normalize** — one click, shows the change log.
5. **Validate** — adjust tolerances if needed, see errors (would corrupt the
   model) vs. warnings (worth a look).
6. **Convert coordinates** — edit the grid-registration table (originX/Y,
   surfaceZ, bearing_deg per face). *Real survey values, not the smoke-test
   placeholders, are what make the absolute coordinates trustworthy* — same
   caveat as the original `gridConfig.JSON`. Illustrator-sheet extractions
   only for now (matches the open item on `FieldWallProfile` conversion in
   the original README).
7. **3D model** — set resolution/section direction/vertical exaggeration,
   optionally override the stratigraphic order, build. Renders the same
   cross-section + zoomed-middle-layers PNGs as the CLI, plus downloadable
   `.gempy`/mesh/lith-block files.
8. **Visualize** — opens the original `visualizer.html` in a new tab (its own
   file pickers still drive it — A/B compare two extraction runs against the
   scan).

## Notes / known limits carried over from the original pipeline

- Field-wall (`FieldWallProfile`) JSON has no coordinate-conversion step yet
  — same open item as the CLI README.
- `detectFieldWallMarkers.py` (CV-based marker detection for T104-style
  photos) isn't wired into this GUI; it's a standalone pre-step you'd still
  run by hand before extraction if you need it.
- Each job's working files live under `jobs/<job_id>/` on this server and
  are not cleaned up automatically — delete old job folders periodically if
  disk space matters.
