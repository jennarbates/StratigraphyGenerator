# Trench Digitization Pipeline

Turns a trench-profile drawing — archival illustrator sheet or modern field
recording sheet — into a 3D GemPy geological model. Folders are numbered in
the order the pipeline actually runs — each stage's output feeds the next
stage's input. Two source drawings are in here so far:

- **Trench 23** (Poggio Civitate, 1980) — illustrator sheet, hatch-pattern
  legend, three faces (East/South/West).
- **T104, southern baulk wall** (2025 field sheet, Lizzy Browning/Heather
  Fusco) — hand-drawn on graph paper, Locus number + Munsell color instead
  of a hatch legend, one wall only.

These two use **different extraction scripts** (see 03 below) because they
record material differently, but feed the same downstream shape.

```
00_docs                  reference material (not code)
01_scans                 raw drawings: qwertyTest.png (Trench 23),
                         T104_southern_baulk_wall.jpeg (T104)
02_preprocess            image cleanup before vision extraction
03_extraction            vision model -> structured JSON
04_normalize_validate    clean + sanity-check that JSON
05_convert_coords        face-local (x, depth) -> site-wide (X, Y, Z)
06_gempy_model           build & compute the GemPy model, render sections
07_visualizer            standalone HTML viewer
```

## Pipeline, in order

### 00_docs — `IllusstratorGuide.md`
Guidelines for whoever *draws* the trench profiles (scale bars, line
weight, labeling). Upstream of all code — read this before a new drawing
is made, so the scan below is actually digitizable.

### 01_scans — `qwertyTest.png`, `T104_southern_baulk_wall.jpeg`
Raw source drawings. `qwertyTest.png` is the Trench 23 illustrator sheet
(scanned well below the 300 DPI `IllusstratorGuide.md` recommends — see the
open item on this in section 03). `T104_southern_baulk_wall.jpeg` is a
modern phone photo of a graph-paper field sheet, much higher resolution
(4284×5712) but a different recording convention entirely (Locus + Munsell,
no printed scale bar — see 03).

### 02_preprocess — `preprocess.py`
```
python preprocess.py 01_scans/your_scan.png --outdir 02_preprocess/out
```
Grayscale, background-flatten, upscale, CLAHE-sharpen a raw scan so the
vision model can resolve boundary lines. Outputs `*_clean.png` (feed this
forward) and, optionally, `*_highcontrast.png` (boundary-tracing only —
don't feed this to material ID).

### 03_extraction — two scripts, for two kinds of source drawing

**`renameImages.py` → `output.json`, `output_single.json`** (Trench 23,
illustrator sheet)
```
python renameImages.py 02_preprocess/out/your_scan_clean.png
```
Calls Gemini with a structured schema (`ArchaeologicalDiagram`) to
transcribe the drawing: layers matched to a drawn hatch-pattern legend,
boundary points, features, scale, credits. `output.json` and
`output_single.json` look like two runs of the same single-agent extraction
over the same drawing — worth diffing if you're not sure which is
authoritative, since they already disagree slightly (e.g.
`gridLabelXMeters` and the scale's `metricConversionAssumption` differ
between the two). Separately: cross-checking `output.json` against the
scan turned up **5 of the legend's 14 materials never appearing as a layer
or feature anywhere** in the extraction (Light, Pink-Yellow with Carbon and
Plaster, Yellow, Gray-Yellow with Carbon, Traces of Carbon) — most likely
folded into the neighboring "Dark Gray"/"Buff-Gray" calls rather than
genuinely absent, and likely a resolution limit of the scan (well under
300 DPI) rather than a prompting problem. Worth a rescan if the original
artifact is available; `preprocess.py`'s upscaling won't recover what
isn't there.

**`extractFieldWall.py` → e.g. `field_wall_t104.json`** (T104, modern field
sheet)
```
python extractFieldWall.py 01_scans/T104_southern_baulk_wall.jpeg \
    --square-cm 20 --out field_wall_t104.json
```
Separate schema (`FieldWallProfile`) built for graph-paper field sheets
recorded with **Locus number + Munsell soil color** rather than a hatch
legend — forcing this drawing through `renameImages.py`'s
`inferredMaterial`/`visualPattern` fields would mean inventing a fill
pattern that was never drawn. `--square-cm` is a required, human-confirmed
number (T104's bold squares measure 20cm, minor squares 2cm — verified
computationally from the grid spacing in the photo, not just read off by
eye) rather than something the model re-derives from the image each time.
Any coordinate-looking labels along the top of the wall are transcribed
verbatim into `gridTiePoints` but deliberately **not interpreted** — what
they mean (northing/easting/elevation/something else) is still an open
question, see below.

**Not yet built:** a `convertCoords.py`-equivalent step for
`FieldWallProfile` JSON — the illustrator-sheet converter expects
`ArchaeologicalDiagram`'s shape (layers/surface/face), not
`loci`/Locus-number shape. Needs writing once a real `extractFieldWall.py`
run has been reviewed.

### 04_normalize_validate — `normalizer.py`, `validator.py`
```
python normalizer.py 03_extraction/output.json 04_normalize_validate/output_clean.json
python validator.py  04_normalize_validate/output_clean.json
```
`normalizer.py` fixes literal `"null"` strings and de-duplicates
floor/cross-layer features — non-destructive, logs every change.
`validator.py` then sanity-checks the cleaned JSON (monotonic layer
stacking, depth plausibility, feature containment) and exits non-zero on
error. Run validator **after** normalizer, and again after
`convertCoords.py` if you touch the grid config.

### 05_convert_coords — `convertCoords.py`, `gridConfig.JSON`, `gridConfigConnected.JSON` → `points.csv`, `points_orientations.csv`
```
python convertCoords.py 04_normalize_validate/output_clean.json \
    --grid gridConfig.JSON --out points.csv
```
Converts each face's local (x, depth) into site-wide (X, Y, Z) using a
grid-registration config that must come from real survey data.

**Careful — `gridConfig.JSON` is a placeholder.** Its own `_comment`
says the three faces are lined up end-to-end on one straight line "for a
pipeline smoke-test" and do NOT reflect real corners.
`gridConfigConnected.JSON` is a second, explicitly **hypothetical** test
config modeling a U-shaped pit with faces meeting at real corners — also
not survey data. The `points.csv` / `points_orientations.csv` in this
folder were generated from one of these placeholders, not from a
surveyed grid — treat the resulting model's absolute coordinates and
inter-face geometry as illustrative, not final, until real
`originX/originY/surfaceZ/bearing_deg` values replace them.

### 06_gempy_model — `buildGempyModel.py` → `trench23.gempy` + section PNGs
```
python buildGempyModel.py 05_convert_coords/points.csv \
    05_convert_coords/points_orientations.csv --out-prefix trench23
```
Builds the GemPy model (one conformable series, order inferred from
mean Z per surface), computes it, and writes:
- `trench23.gempy` — native save file
- `trench23_section_y.png` — full cross-section
- `trench23_section_y_zoom.png` — cropped/exaggerated view of the thin
  middle layers
- `test_section_y.png` — looks like an earlier/test run of the same
  section plot (same content, different render pass) — worth confirming
  whether it's still needed or safe to drop once `trench23_section_y.png`
  is trusted.

### 07_visualizer — `visualizer.html`
Standalone HTML viewer (Poggio Civitate themed) for inspecting the
digitized profile. No build step — open directly in a browser.

## Known open items across the pipeline

**Trench 23**
1. **Grid registration is still placeholder data** (see 05 above) — the
   single biggest thing standing between this and a real site model.
2. **`output.json` vs `output_single.json`** — confirm which extraction
   run is authoritative before it becomes the source of truth downstream.
3. **5 of 14 legend materials are missing from the extraction** (see 03
   above) — likely a scan-resolution limit, worth a rescan.
4. **`test_section_y.png`** in 06 — likely safe to archive/delete once
   confirmed superseded by `trench23_section_y.png`.

**T104**
5. **Is the southern baulk wall a cut feature** (pit/posthole/ditch/wall-
   trench fill) rather than flat stratigraphy? The locus boundaries in the
   photo read as steep/near-vertical wedges, not horizontal bands — if so,
   `buildGempyModel.py`'s one-conformable-series assumption is the wrong
   model for it (it needs a fault/unconformity relationship instead), and
   `extractFieldWall.py`'s top/bottom-boundary convention may need
   rethinking too. Unconfirmed as of this writing.
6. **What do the coordinate-looking labels along the top of the T104
   drawing mean?** (northing/easting, elevation, stake ID — unclear.)
   Transcribed verbatim by `extractFieldWall.py` but not interpreted.
   Confirming this could mean skipping manual grid-registration guesswork
   entirely for this wall, unlike Trench 23.
7. **No `points.csv` yet for T104** — `extractFieldWall.py` hasn't been run
   for real (no network path to the Gemini API from this environment), and
   its JSON output shape doesn't have a `convertCoords.py` equivalent yet.