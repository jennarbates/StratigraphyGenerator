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

## Recovering old artifacts

The pre-`webapp` outputs and CLI scripts are all still in git:

```bash
git show d383439^:03_extraction/output_section001.json > output_section001.json
git show d383439^:05_convert_coords/gridConfig.JSON    > gridConfig.JSON
git show d383439^:06_gempy_model/trench23.gempy        > trench23.gempy
git log --oneline --all -- "*convertCoords.py"          # etc.
```
