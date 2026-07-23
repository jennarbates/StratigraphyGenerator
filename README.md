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
                         normalizer, validator, convert_coords, build_gempy
  tools/                 standalone helpers not wired into the GUI
  static/, templates/    frontend
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

For T104 the fix is `poggio_webapp/tools/detectFieldWallMarkers.py` — the
recorder marks each measured vertex with a small circle, so finding them is a
computer-vision problem, and CV cannot invent a marker that isn't there. It
is restored to the tree but **not yet wired into the GUI**, and it does not
yet assign markers to loci.

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
2. **Wire `detectFieldWallMarkers.py` into the GUI and close the
   marker→locus gap** (open item 2). Either auto-assign markers to the
   nearest boundary with a confidence score, or — probably better — overlay
   the detected markers on the scan in the browser and click-assign the
   ambiguous ones. Then re-extract T104 constrained to those markers: pass
   the detected coordinates into the prompt as ground truth, or snap output
   vertices to the nearest marker and flag boundaries that needed big snaps.
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