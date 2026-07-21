# Poggio Civitate — Trench Drawing Digitization

An LLM-based tool for digitizing hand-drawn trench profile drawings from **Poggio Civitate** (Murlo, Italy) into structured, measurable data suitable for 3D geological modeling in **GemPy**.

The tool transcribes scanned trench profile drawings into structured JSON: layer boundaries as point lists, feature geometry, scale, grid labels, and legend — extracted with careful attention to measurement accuracy and honest uncertainty.

---

## Table of contents

- [Overview](#overview)
- [How it works](#how-it-works)
- [Drawing digitization (`renameImages.py`)](#drawing-digitization-renameimagespy)
- [Data schema](#data-schema)
- [GemPy integration](#gempy-integration)
- [Setup](#setup)
- [Known constraints and gotchas](#known-constraints-and-gotchas)
- [Roadmap](#roadmap)

---

## Overview

Poggio Civitate is an Etruscan site excavated over many decades, with a large archive of hand-drawn trench profile drawings from earlier seasons. This project brings those archival profiles into a digital pipeline so that stratigraphic boundaries can be modeled in 3D.

GemPy does not ingest raw data directly; it needs interface points (where a layer boundary sits in space) and orientation data (dip/strike). This tool extracts boundary points directly from the archival drawings, measured against each drawing's own scale bar and grid.

---

## How it works

```
  Hand-drawn profile drawings
              │
              ▼
      renameImages.py
      (LLM extraction)
              │
              ▼
  Structured boundary points
  (face-local x, depth)
              │
              ▼
  grid-to-site coordinate
  conversion (deterministic)
              │
              ▼
     Site-wide X / Y / Z
              │
              ▼
          GemPy
  (3D geological model)
```

---

## Drawing digitization (`renameImages.py`)

An LLM-based tool that transcribes scanned hand-drawn trench profile drawings into structured JSON suitable for GemPy. It uses Google's `google-genai` SDK (Gemini 2.5 Flash) with Pydantic schemas for structured output.

### Two-agent design

1. **Vision agent** — sees the image. It measures against the drawn scale bar and grid labels, traces layer boundaries as point lists, records feature geometry, and owns all uncertainty judgments and methodological notes. It is given the output schema as a **completeness checklist** so its transcription supplies every field the structuring step needs.
2. **Structuring agent** — does **not** see the image. It faithfully transcribes the vision agent's description into the fixed schema and is forbidden from inventing values, coordinates, or interpretation.

This split is deliberate: because the structuring agent has no image, it cannot confabulate archaeological interpretation. All measurement and judgment happen in one place (the vision agent), so any error has a single source.

> A single-agent variant (one call that sees the image and emits the schema directly, with an embedded raw-transcription field) is a reasonable alternative worth benchmarking — it removes the lossy text handoff. See [Roadmap](#roadmap).

### Design principles baked into the prompts

- **Null beats a guess.** Faded, obscured, or ambiguous readings are left null and flagged in a `confidence` field rather than interpolated into plausible-looking numbers.
- **Boundaries are point lists, not single depths.** Real boundaries undulate (U-shaped cuts, irregular bottoms). Point density follows the line's actual complexity — flat boundaries get 2–3 points, complex ones get many.
- **No interpretation beyond what is drawn.** The model must not infer chronology, period, or links to known events, buildings, or destruction layers. Site background is provided only to help read labels correctly, never as license to add interpretation.
- **Verbatim transcription.** Unclear text, abbreviations, and units are copied exactly, not expanded or guessed.
- **Methodological notes only.** `inferred_notes` captures how a measurement was estimated, what was unreadable, and which metadata was missing — never historical interpretation.

### Running it

```bash
python renameImages.py
```

The entry point processes a single image path (currently `./images/qwertyTest.png`). It prints the vision agent's description, then the structured JSON, and returns the parsed `ArchaeologicalDiagram` object.

---

## Data schema

Structured output conforms to the `ArchaeologicalDiagram` Pydantic model. Key elements:

### Coordinate convention

- **x** — horizontal position *along the face*, in meters, measured from the left edge of the drawn profile (`x = 0` at the leftmost point).
- **depth** — vertical distance *downward* from the ground surface, in meters, **positive downward** (`depth = 0` at the top of the topsoil).

These are **face-local** coordinates. Converting them to site-wide X/Y/Z is a separate deterministic step (see below) — the LLM never does it.

### Structure

- **`metadata`** — file path, suggested filename, trench label, scale (with an explicit `metricConversionAssumption` field for non-metric scales), credits, and marginalia.
- **`trenchProfiles`** — one per face (East, South, West, …). Each carries its grid labels and their x-positions in meters (`gridLabelXMeters`), plus its layers.
- **`layers`** — each with material, visual pattern, features, and `topBoundary` / `bottomBoundary` as point lists. `topBoundary` is null when a layer's top is simply the bottom of the layer above (the downstream converter stitches these).
- **`BoundaryPoint`** — `xCoordinateMeters`, `depthMeters`, and an optional per-point `confidence` flag.
- **`NotableFeature`** — features carry structured `shapePoints` (for traced outlines like U-shaped carbon lenses) or `approx*` fields (for discrete objects like a single stone), keeping geometry out of prose.
- **`legend`** — visual pattern → material mapping.
- **`inferred_notes`** — methodological/readability notes only.

---

## GemPy integration

GemPy needs two inputs:

1. **Interface / surface points** — X/Y/Z where a layer boundary sits.
2. **Orientation data** — dip/strike.

The boundary point lists from the drawing tool feed the interface points. The remaining gap is a **coordinate conversion step**: face-local `(x, depth)` coordinates must be converted to true site-wide X/Y/Z using the site grid-to-coordinate lookup. This is a deterministic script/math step, not something the LLM extraction can infer — and it is the natural next piece of work before anything reaches GemPy.

---

## Setup

### Requirements

- Python 3 with a project-local virtual environment
- `google-genai`, `pillow`, `pydantic`
- A Google Gemini API key

### API key

The Gemini API key must persist across terminal sessions. `export` alone only lasts for the current shell — add it to `~/.zshrc` and reload:

```bash
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Virtual environment hygiene

- Keep a `.venv` **inside each project folder** with consistent naming.
- Check which environment is active with `which python3` before running — a `ModuleNotFoundError: No module named 'google'` usually means the wrong venv (or global Python) is active, not a missing install.
- Consider `direnv` for automatic per-project activation.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install google-genai pillow pydantic
```

### Version control

This repo is initialized locally. To publish it, create an empty repository on GitHub (no README/.gitignore, to avoid a first-push conflict), then:

```bash
git remote add origin https://github.com/<username>/PoggioCivitate.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

Suggested `.gitignore`:

```
.DS_Store
.env
.venv/
__pycache__/
images/
```

> Do not commit API keys or `.env` files. Once a secret is committed and pushed, it lives in history even after deletion.

---

## Known constraints and gotchas

- **`sips` paths.** Use correct relative vs. absolute paths — a stray leading slash or typo yields "not a valid file" errors.
- **Fabricated interpretation.** Earlier output invented archaeological claims (links to named events, site zones) in `inferred_notes`. The current prompts strip this: the structuring agent cannot see the image and is barred from adding interpretation. Spot-check new output to confirm notes stay methodological.
- **Checklist padding.** A long completeness checklist can tempt the vision agent to invent evenly-spaced points where a boundary was actually faded. Watch first runs for suspiciously uniform points; strengthen the "null beats a guess" rule rather than cutting the checklist if it appears.
- **Coordinate conventions.** Depth is positive-downward and face-local. Keep this consistent everywhere — ambiguity here surfaces during the site-coordinate conversion.

---

## Roadmap

- [ ] **Coordinate conversion script** — face-local `(x, depth)` → site-wide X/Y/Z using the site grid lookup.
- [ ] **Validator** — check boundary monotonicity (each layer's bottom ≥ the one above) and top/bottom continuity before data reaches GemPy.
- [ ] **Feature-geometry extraction** — confirm traced outlines (U-shaped carbon lenses) land in structured `shapePoints`, not prose.
- [ ] **Single-agent benchmark** — compare a one-call image→schema variant against the two-agent design for measurement accuracy.
- [ ] **Batch processing** — extend `renameImages.py` beyond a single hard-coded image to a directory of drawings.
