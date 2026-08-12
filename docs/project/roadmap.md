---
title: Roadmap
audience: developer
status: current
source_files:
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/assign_markers.py
  - poggio_webapp/pipeline/build_gempy.py
  - poggio_webapp/pipeline/merge_walls.py
  - poggio_webapp/requirements.txt
  - .github/workflows/docs.yml
verified_against: ae2fc1d
---

# Roadmap

Ordered by leverage, not effort. The organizing principle: make the existing
results scientifically valid first, then make the pipeline trustworthy, then
make it general.

Nothing in phases 2–3 matters while the underlying geometry is still invalid.

!!! note

    This roadmap was migrated from the root README and corrected against `d23b842`. Items the README listed as outstanding but which have since shipped are marked **done** rather than deleted, because the reasoning behind them still explains the current design.

## Phase 1 — unblock the science

### 1. Real grid registration

**Partly done.** The binding constraint: get the four registration values per
face from the site records. That path now exists — a surveyed trench layout or
a season's Geospatial Spreadsheet derives the grid config
(`POST /api/trenches/<label>/layout`, `POST /api/trenches/geospatial-sheet`),
and the trenches page prefills a stored derived registration where one exists.

The provenance field this item asked for exists too: the grid config carries
`"source": "surveyed" | "placeholder"`, the starter config declares
`placeholder`, and the multi-wall build refuses that declaration.

What remains is consistency. The [multi-wall trench
build](../workflows/09-multi-wall-trench.md) refuses placeholder registration,
because merged models amplify mis-registration badly enough that the failure
is not survivable. Single-sheet builds still accept it and nothing watermarks
their output, so a placeholder single-sheet model can still be mistaken for a
real one once it leaves the application.

### 2. Wire marker assignment into the interface

**Partly done.** The README claimed `assign_markers.py` defined only
`run_assign`, so the assignment routes threw `AttributeError`. That is no
longer true: the module defines `classify_markers` and `finalize_assignments`
alongside `run_assign`, and the routes call them.

What remains is the wiring. The marker stage is not registered in the live step
list or renderer map, so the whole flow is unreachable from the browser. Once
registered, re-extract T104 through preview → detect → confirm → assign →
finalize and re-check it against the extraction-quality evidence.

See [markers and features](../workflows/03-markers-and-features.md) and
[capability status](capability-status.md).

### 3. Re-extract Trench 23's South and West faces

The evidence so far — the East face genuine in the per-section run, the
all-faces-at-once run fully fabricated — says extract **one face per API
call**. Make per-face extraction the default for illustrator sheets and
validate each face independently.

### 4. Rescan Trench 23 at 300+ DPI

If the original sheet is accessible. Then re-check the five missing legend
materials. This settles resolution-limit versus prompting-problem, which is
currently a hypothesis rather than a finding. See [drawing
guidelines](../reference/drawing-guidelines.md).

## Phase 2 — verification infrastructure

### 5. Tests

**Largely done.** Several hundred Python tests and over two hundred JavaScript
tests now run without a key or network access. The pure functions this item
named — the coordinate transform, `fieldwall_to_profiles`, the fabrication
heuristics — are covered, and the merge layer added 55 more.

CI exists now: `.github/workflows/docs.yml` runs the documentation checkers,
both test suites, a strict site build, and the diagram regeneration check on
every push and pull request. One gap remains: there is still no golden-file
test running a known extraction end-to-end through convert → validate — the
merge-integration and T905 worked-example suites run synthetic records, not a
real extraction.

See [running the tests](../reference/running-the-tests.md) for what is and is
not covered.

### 6. Scan-versus-extraction scoring

Today's A/B check is eyeballing in the visualizer. A cheap objective metric:
rasterize each extracted boundary polyline and measure overlap with ink pixels
in the preprocessed scan. **A boundary that does not lie on ink is fabricated
by definition.**

This upgrades the fabrication checks from statistical signatures to direct
evidence, and can run automatically at validation.

### 7. Hygiene

- **Done:** uploads now pass through `secure_filename` (with a safe fallback
  name); the download routes were already guarded.
- Pin versions in `poggio_webapp/requirements.txt`, which is currently
  unpinned. The documentation requirements are already pinned.
- Add a license. There is none.
- Persist the in-memory task registry to the job folder, or document that a
  server restart orphans running tasks. It is currently
  [documented](../reference/troubleshooting.md) but not fixed.
- Add an age-based sweep for `jobs/`.

## Phase 3 — generalize past these two drawings

### 8. Ensemble extraction as an uncertainty signal

Run extraction twice at different temperatures or against different providers
and diff the geometries. Agreement is cheap evidence of genuine tracing;
divergence flags regions for review. Pairs naturally with putting the Gemini
client behind an interface so other vision models can slot in.

### 9. In-browser boundary editor

Extraction will never be perfect, so the pragmatic endgame is
human-in-the-loop: show the extraction overlaid on the scan and let the user
drag, add, and delete vertices before validation. This turns every "discard and
re-extract" cycle into a five-minute correction.

### 10. Schema unification

`ArchaeologicalDiagram` and `FieldWallProfile` converge via an adapter inside
the coordinate converter. Promote the converged form to a first-class internal
schema with the two extraction formats as input adapters, so the validator,
converter, and builder stop needing dual fallbacks. See [data
schemas](../reference/data-schemas.md).

### 11. Batch mode

Poggio Civitate has decades of trench documentation. Once single-sheet
extraction is trustworthy: a batch queue, persistent job naming, and
site-level aggregation of multiple trenches into one model.

The [multi-wall merge](../workflows/09-multi-wall-trench.md) is the first step
of this — it aggregates walls into a trench. Aggregating trenches into a site
is the same problem one level up. The season-wide [Geospatial Spreadsheet
registration](../archaeology/geospatial-spreadsheet.md) is a second step: it
registers every trench in a season from one file.

### 12. Standards-compliant export

GeoJSON in site coordinates for GIS, and propagation of the per-point
`confidence` fields — captured in the schema, unused downstream — into the
exports.

Harris matrix export, which this item originally included, is **done**. See
[build and review a Harris Matrix](../workflows/harris-matrix.md).

## If effort is limited

Items 6 and 9 deserve to jump the queue. Together they turn the workflow from
*extract, inspect statistically, hope* into *extract, score against the scan,
correct by hand* — the realistic shape of a production digitization tool.

## Related

- [Capability status](capability-status.md) — what works today.
- [Project history](history.md) — how it got here.
- [Accuracy and provenance](../concepts/accuracy-and-provenance.md) — why
  fabrication detection is the recurring theme above.
