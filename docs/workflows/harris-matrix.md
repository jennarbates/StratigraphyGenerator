---
title: Build and review a Harris Matrix
audience: user
status: current
source_files:
  - poggio_webapp/backend/routes/harris.py
  - poggio_webapp/backend/harris_store.py
  - poggio_webapp/pipeline/harris_matrix.py
  - poggio_webapp/pipeline/harris_import.py
  - poggio_webapp/pipeline/harris_suggestions.py
  - poggio_webapp/pipeline/harris_render.py
  - poggio_webapp/static/harris/dashboard.js
  - poggio_webapp/static/harris/editor.js
verified_against: 2267711
---

# Build and review a Harris Matrix

A Harris Matrix records an archaeologist's interpretation of stratigraphic
sequence. Each node is a unit. Each ordering relationship states that one
unit is chronologically younger than another. The matrix is a review tool,
not an automatically true or scientifically verified account.

Open **Harris matrices** from the main application. A matrix is a separate,
trench-level workspace, outside the numbered drawing-to-3D steps. It can be
created blank, or it can import units from multiple drawing jobs for the same
trench. A saved drawing with usable extraction data offers **Create or add to
a Harris Matrix**, which opens the dashboard with that source preselected.
Opening this link does not create, import, or modify anything.

## Direction and relationship meaning

Every chronological edge is stored as:

```text
younger unit -> older unit
```

The diagram renders youngest units at the top and oldest units at the bottom.
Relationship kinds add archaeological meaning without changing that
direction:

- `above`
- `cuts`
- `fills`
- `precedes`
- `other`

Correlation is different. It says that two or more imported observations are
interpreted as parts of the same stratigraphic unit. A correlation is not a
chronological edge. Correlated units collapse into one display node during
validation and rendering.

## Create or reopen a matrix

1. Open `/harris`.
2. Enter a title and, when known, the site and trench.
3. Optionally select one or more usable drawing jobs.
4. Choose **Create matrix**. This explicit action creates the workspace and
   imports the selected sources.
5. To add selected sources to an existing matrix instead, use the explicit
   add action under that matrix.

A blank matrix does not require a drawing job. Matrices persist on disk and
can be reopened after the Flask process restarts.

## Import and review source units

The importer supports:

- `FieldWallProfile`, using `layers[].locusNumber`;
- `ArchaeologicalDiagram`, using
  `trenchProfiles[].layers[].layerName`.

For each unit, the editor shows the source job, face, zero-based layer index,
and original label. Generic labels such as `Polygon 1` and missing labels are
flagged for correction. Editing an imported unit's matrix label does not
change its deterministic identity or any source file.

Import is idempotent: importing the same source again does not duplicate its
units. The importer reads the first usable artifact in this order:

1. `meta.json` `normalized_path`;
2. `04_normalize_validate/output_clean.json`;
3. `meta.json` `extraction_path`;
4. `extraction_output.json`.

Resolved source paths must remain inside the source job directory. Matrix
creation, import, editing, and export never write to source `meta.json`,
extraction or normalized JSON, editor state, finds, converted coordinates, or
GemPy output. Matrix JSON stores provenance references, not server paths.

## Add interpretations

Use **Relationships** to choose an explicitly labelled younger unit and older
unit, relationship kind, and optional evidence or notes. The save is rejected
if it would introduce a chronological cycle, reference a missing unit, create
a duplicate edge, or order units within the same correlation.

Use **Correlations** only when there is archaeological support for treating
the selected observations as the same stratigraphic unit. Equal labels are
never merged automatically. Overlapping correlation edits are normalized
into one group.

## Review suggestions

Suggestions are conservative proposals, not facts:

- an `above` proposal may be generated for consecutive source layers whose
  recorded shared boundary matches within the configured tolerance;
- a correlation proposal may be generated when the same normalized label
  occurs in different jobs or faces.

Every proposal begins `pending`. Review each proposal individually with
**Accept** or **Reject**. Only acceptance changes relationships or
correlations. Rejected suggestions remain recorded as `rejected`, so
regeneration does not silently restore them. The application does not infer
chronology from finds, material, colour, dates, AI, OCR, or external sources.

## Validation, diagram, and exports

Graph errors prevent saving or rendering. Stable error codes include:

| Code | Meaning |
|---|---|
| `missing-unit` | A relationship or correlation references an absent unit. |
| `self-relation` | A relationship connects a unit to itself. |
| `duplicate-relation` | More than one saved edge has the same direction. |
| `overlapping-correlation` | Stored correlation groups overlap instead of being normalized. |
| `relation-within-correlation` | A chronological edge connects correlated units. |
| `cycle` | Younger-to-older relationships form a chronological cycle. |

Warnings do not invalidate the saved assertions:

| Code | Meaning |
|---|---|
| `redundant-relation` | The edge follows from a longer path. It stays in JSON but is omitted from the diagram. |
| `isolated-unit` | A display node has no chronological relationship. |
| `generic-label` | An imported label still appears generic. |

The SVG renderer first collapses correlations, validates the graph, and
applies a deterministic transitive reduction. Consequently, the display
shows immediate relationships without silently deleting redundant assertions
from the versioned JSON.

Use **Download JSON** for the complete version 1 record and **Download SVG**
for a scalable diagram. **Print / Save as PDF** uses the browser's print
dialog; there is no server-side PDF generator.

## Current limitations

- No AI or OCR chronology inference.
- No phase or period grouping.
- No multi-user collaboration, authentication, or database.
- No automatic correlation from equal labels.
- No arbitrary node positioning.
- No server-generated PDF.
- Matrices are designed for at most 250 imported units.
- A matrix covers one trench-level interpretation, not site-wide merging.

## Exact release test commands

Run from the repository root:

```bash
PYTHON=.venv/bin/python
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

"$PYTHON" -m pytest -q
node poggio_webapp/static/harris/core.test.mjs
node poggio_webapp/static/canvas/grid.test.mjs
node poggio_webapp/static/app/stages/start-options.test.mjs
node poggio_webapp/static/app/text-metadata.test.mjs
node poggio_webapp/static/app/stages/verify-text-navigation.test.mjs
node poggio_webapp/static/visualizer/viewbox.test.mjs
node poggio_webapp/static/visualizer/alignment-policy.test.mjs
node poggio_webapp/static/visualizer/schema-core.test.mjs
node poggio_webapp/static/visualizer/coordinates.test.mjs
"$PYTHON" tools/docs/check_docs.py
git diff --check
git status --short
```

Run the Harris groups explicitly:

```bash
"$PYTHON" -m pytest -q \
  tests/test_harris_schema.py \
  tests/test_harris_graph.py \
  tests/test_harris_store.py \
  tests/test_harris_import.py \
  tests/test_harris_suggestions.py \
  tests/test_harris_routes.py \
  tests/test_harris_pages.py \
  tests/test_harris_render.py
```
