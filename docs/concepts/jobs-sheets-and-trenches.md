---
title: Jobs, sheets, and trenches
audience: beginner
status: current
source_files:
  - poggio_webapp/backend/jobs.py
  - poggio_webapp/backend/config.py
  - poggio_webapp/backend/routes/scans.py
  - poggio_webapp/backend/routes/trenches.py
verified_against: d23b842
---

# Jobs, sheets, and trenches

A **job** is one working session over one drawing. A **sheet** is that drawing.
A **trench** is the real hole in the ground, which usually takes several sheets
to record.

These three are easy to blur together, and blurring them is the single most
common source of confusion about why the application is shaped the way it is.

## Why it matters here

The rule is: **one job holds one sheet.**

A job is a folder under `poggio_webapp/jobs/`, containing that sheet's scan,
its extraction, and a `meta.json`. Every workflow step from
[add a drawing](../workflows/01-add-drawing.md) through
[view and download](../workflows/08-view-and-download.md) operates on exactly
one job.

But a trench has walls, and how many sheets that takes depends on which kind of
drawing you have:

- An **illustrated trench sheet** may already record several faces on one
  sheet. Its `ArchaeologicalDiagram` document carries a list of faces under
  `trenchProfiles`, so one job can cover a whole trench.
- A **hand-drawn field sheet** records exactly one wall. Its
  `FieldWallProfile` document describes that single wall through `loci` and
  `layers`. A four-walled trench needs four sheets, so four jobs.

See [source drawing types](source-drawing-types.md) for why the two formats
differ.

That asymmetry is why [combining walls into one
trench](../workflows/09-multi-wall-trench.md) exists at all. For illustrator
sheets, the multi-face document arrives ready-made. For field sheets, it has to
be assembled from several jobs first.

## Example

Three field sheets recording the north, south, and west walls of trench T104
produce three independent jobs:

```
poggio_webapp/jobs/
  <job-1>/   meta.json → trench_label: "T104", wall_label: "North"
  <job-2>/   meta.json → trench_label: "T104", wall_label: "South"
  <job-3>/   meta.json → trench_label: "T104", wall_label: "West"
```

Nothing links them except the shared `trench_label`. There is no trench record,
no database row, and no parent folder. The grouping is derived by reading every
job's `meta.json` on demand.

A fourth job uploaded without a trench label simply does not participate. It is
not an error — most jobs are single sheets that were never assigned to a
trench, so unlabelled jobs are skipped silently.

## How the repository represents it

### The job

`poggio_webapp/backend/jobs.py` is the whole of it — five short helpers over a
directory:

- `job_dir()` resolves the folder and returns `404` for an unknown id.
- `load_meta()` / `save_meta()` read and write `meta.json`.
- `rel_url()` builds the `/api/jobs/<id>/file?path=…` URL for a file inside
  the job.
- `safe_job_path()` resolves a relative path under the job directory and
  refuses to escape it.

There is no job model, no ORM, and no index. A job is a folder, and its
`meta.json` is the only state.

### The labels

Both labels are optional form fields on upload, cleaned by `clean_label()` and
written into `meta.json` only when non-empty:

| Field | Meaning | Set at |
|---|---|---|
| `trench_label` | Which trench this sheet belongs to | Upload, or editor creation |
| `wall_label` | Which wall of that trench this sheet records | Upload, or editor creation |
| `sheet_type` | `illustrator` or `fieldwall` | Upload |
| `normalized_path` | Where the cleaned extraction landed | Normalization |

Wall labels matter more than they look. They become **face names**, and GemPy
fuses faces by exact name — so two walls sharing a label would collide into
one surface. The build treats duplicates as fatal rather than guessing, and
derives a label from the sheet type and job id when one is missing, recording
that in its notes.

### The trench

`poggio_webapp/trenches/<safe-label>/` holds merged output only. It is created
by the build, not by any upload, and its contents are derived: delete it and
the next build recreates it from the jobs. The jobs remain the source of truth.

The three top-level directories, all defined in
`poggio_webapp/backend/config.py` and created on import:

| Directory | Holds | Source of truth? |
|---|---|---|
| `jobs/` | One folder per sheet | Yes |
| `trenches/` | Merged multi-wall output | No — derived |
| `matrices/` | Harris matrices | Yes |

## Related concepts

- [Source drawing types](source-drawing-types.md) — why one format is
  multi-face and the other is not.
- [Coordinate spaces](coordinate-spaces.md) — what a face name is registered
  against.
- [Files and artifacts](../architecture/files-and-artifacts.md) — what each
  stage writes into a job folder.
- [Combine walls into one trench](../workflows/09-multi-wall-trench.md) — the
  workflow this model exists to support.
