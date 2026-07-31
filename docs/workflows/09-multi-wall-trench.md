---
title: Combine walls into one trench
audience: developer
status: current
source_files:
  - poggio_webapp/backend/routes/trenches.py
  - poggio_webapp/pipeline/merge_walls.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/backend/routes/scans.py
  - poggio_webapp/storage.py
  - poggio_webapp/backend/config.py
verified_against: d23b842
---

# Combine walls into one trench

Merge several single-wall drawings into one document and build a single 3D
model of the whole trench.

!!! note

    **This workflow has a page, but nothing links to it.** Open <http://localhost:5000/trenches> directly. Like the [finds page](logging-finds.md), it works and is tested, but you have to know the address — no control anywhere else in the application will take you there. See [capability status](../project/capability-status.md).

    The page lists every trench, shows which walls are ready, and runs the build with task polling. The HTTP requests documented below are what it calls, and remain the way to script the workflow or read a response in full.

![Four separately drawn walls positioned by their registration to enclose one rectangular pit](../assets/diagrams/w09-walls-to-pit.svg)

*Correct registration is what turns four independent drawings into one trench.*

## Before you start

A trench is not a job. One job holds **one sheet**, and a field sheet records
**one wall**, so a four-walled trench lives across four jobs. Read
[jobs, sheets, and trenches](../concepts/jobs-sheets-and-trenches.md) first if
that split is unfamiliar.

Each wall's job must already have:

- a **trench label**, identical across all the walls you want to combine;
- a **wall label**, different for every wall in that trench;
- a **normalized extraction**, produced by [clean up the data](04-clean-data.md).

Both labels are optional form fields on upload, handled in
`poggio_webapp/backend/routes/scans.py`. A job with no trench label is skipped
silently — most jobs are single sheets that were never assigned to a trench.

You also need real surveyed registration for every wall. This workflow will
refuse to build without it, and that refusal is deliberate: see
[Why placeholders are fatal here](#why-placeholders-are-fatal-here).

```mermaid
flowchart TD
  A[North wall job] --> An[normalized extraction]
  B[East wall job] --> Bn[normalized extraction]
  C[South wall job] --> Cn[normalized extraction]
  An --> M[merge_walls.merge_extractions]
  Bn --> M
  Cn --> M
  M --> D[merged.json, one multi-face document]
  D --> V[convert_coords.run_convert]
  V --> G[build_gempy.run_build]
  M -.->|canonicalizes Munsell per locus| D
```

*The merge runs before coordinate conversion, because everything after extraction is already multi-face.*

## Do this

### 1. See how the jobs are grouped

```bash
curl http://localhost:5000/api/trenches
```

The response maps each trench label to its member jobs, with `has_normalized`
telling you which walls are ready:

```json
{
  "trenches": {
    "DEMO-TRENCH": [
      {"job_id": "…", "wall_label": "North", "sheet_type": "fieldwall", "has_normalized": true},
      {"job_id": "…", "wall_label": "South", "sheet_type": "fieldwall", "has_normalized": true}
    ]
  }
}
```

### 2. Ask for a starter configuration

Post a build with no `grid` key. Nothing is written; you get a starter config
and the merge notes back.

```bash
curl -X POST http://localhost:5000/api/trenches/DEMO-TRENCH/build \
  -H 'Content-Type: application/json' -d '{}'
```

The response has `"needs_grid": true`, a `starter` config with one entry per
face, and a `notes` list. **Read the notes.** They record every judgement the
merge made — derived wall labels, disagreeing Munsell readings, and inferred
layer ordering.

### 3. Replace every placeholder value

For each face, set `originX`, `originY`, `surfaceZ`, and `bearing_deg` from
your site records, exactly as in [place on site](06-place-on-site.md).

A starter config only becomes a trench if adjacent walls actually share their
corner coordinates. A per-sheet starter cannot know that, which is why the
starter's own `_comment` says so.

### 4. Build

```bash
curl -X POST http://localhost:5000/api/trenches/DEMO-TRENCH/build \
  -H 'Content-Type: application/json' \
  -d '{"grid": {"faces": {"North": {"originX": 0, "originY": 0, "surfaceZ": 100, "bearing_deg": 90}}}}'
```

A successful response returns a `task_id`, the accumulated `notes`, and
`grid_warnings`. Poll the task as described in
[asynchronous tasks](../architecture/asynchronous-tasks.md).

`grid_warnings` are non-fatal geometry observations — walls that do not meet at
a corner, for instance. The repository's convention is to report rather than
guess, so judging them is yours.

### 5. Retrieve the outputs

```bash
curl 'http://localhost:5000/api/trenches/DEMO-TRENCH/file?path=merged.json'
```

## What the application creates

Under `poggio_webapp/trenches/<safe-label>/`:

| Path | Contents |
|---|---|
| `merged.json` | One multi-face `trenchProfiles` document combining every wall |
| `points.csv` | Interface points in site coordinates |
| `points_orientations.csv` | Orientation rows for the same points |
| `06_gempy_model/` | The built model and its exports |

The label is made filesystem-safe by replacing every character outside
`A-Za-z0-9_.-` with an underscore, so `T104 South` becomes `T104_South`.

Nothing under `jobs/` is modified. The merge reads each wall's normalized
extraction and never mutates its input.

## Check your result

- Every wall you expected appears in `merged.json` under `trenchProfiles`.
- The notes list contains no surprises — particularly no derived wall labels
  you did not intend and no Munsell disagreements you have not reviewed.
- The face count in `points.csv` matches the number of walls.

## Common problems

Each of these is a deliberate refusal with a specific message, not a crash.

| Message | Cause | Fix |
|---|---|---|
| `no jobs are labelled trench …` | No job's `meta.json` carries that trench label | Set a trench label on each wall's job |
| `these jobs have no normalized extraction yet` | A wall stopped before normalization | Run [clean up the data](04-clean-data.md) on that job |
| `two or more sheets claim the same wall` | Duplicate wall labels, compared case-insensitively | Give each job a distinct wall label |
| `these faces still carry the starter placeholder registration` | Step 3 was skipped | Enter real survey values |
| `the grid config has no entry for these faces` | A face would be silently dropped | Add the missing face to the config |
| `conversion produced no interface points` | The walls' layers have no boundary points | Check the tracing on each wall |
| `gempy import failed` | GemPy is not installed | `pip install gempy gempy_viewer` |

A contradiction between walls raises a different error. If wall A puts locus 3
above locus 5 and wall B puts 5 above 3, the ordering has a cycle and the build
stops, naming the surfaces actually on the cycle. It does not guess an order.

### Why placeholders are fatal here

A single-sheet build tolerates the starter values `0, 0, 100, 90` because one
face has no neighbours to be wrong about. Merged models amplify
mis-registration instead: identical placeholders lay every wall along the same
bearing, producing a row of parallel walls roughly 10 m apart rather than four
walls around a pit. The result looks like a confident model and is a model of
nothing, so the build refuses rather than producing it.

![The same four walls laid out in a parallel row because every face shares the placeholder bearing](../assets/diagrams/w09-placeholder-failure.svg)

*Why placeholder registration is fatal for a merged build: a confident-looking model of nothing.*

## Under the hood

`pipeline/merge_walls.py` exists because everything downstream of extraction —
grid config, conversion, and the GemPy build — is already multi-face, while a
`FieldWallProfile` sheet is single-wall. The merge has to happen *before*
coordinate conversion.

One rule shapes the whole module: **GemPy fuses interface points into a
surface by exact string match on the surface name.** The same locus recorded on
two walls is one deposit and must receive one identical name; two different
deposits must never collide.

That is harder than it sounds, because surface names for field sheets are built
as `Locus N (munsell)`, and Munsell readings of the same locus routinely differ
slightly between sheets. So the merge canonicalizes the Munsell label per locus
number across the whole trench — first usable reading wins, disagreements
become notes — and feeds the canonical values into the existing adapter. It
never builds surface strings itself.

When the same deposit was recorded under *different* locus numbers on different
walls, pass a `correlation` map of `"wall:locus"` to the canonical number.

Series order is derived rather than assumed. Each face's layers are already
top-to-bottom, so every adjacent pair is an ordering constraint; the
constraints from all faces are merged and topologically sorted, with ties
broken by first-seen order so the result is deterministic.

### A known limitation of merged orientations

Coordinate conversion gives every orientation seed the azimuth of the wall it
was measured on, and the dip measured *along* that wall. On one wall that is
all anyone can know. On a merged trench it is wrong in a systematic way: one
surface arrives with a seed dipping toward the north wall's bearing and another
toward the east wall's, and an apparent dip is always shallower than the true
dip — so the model fits a compromise plane matching neither drawing.

`poggio_webapp/pipeline/true_dip.py` solves the real problem: two walls that
are not parallel pin a plane down exactly, giving one true dip and dip azimuth
per surface. It is covered by `tests/test_true_dip.py` but **wired into no
pipeline**, so nothing in this workflow calls it yet.

Where a solve is not available — a surface drawn on only one wall, or two walls
too nearly parallel — it emits nothing and says why, rather than inventing an
orientation that would look like an improvement.

## Next

- [Create the model](07-create-model.md) for what the GemPy build does with
  these CSV exports.
- [Coordinate spaces](../concepts/coordinate-spaces.md) for the registration
  formula the merge relies on.
- [Running the tests](../reference/running-the-tests.md) — the merge layer has
  the densest test coverage in the repository.
