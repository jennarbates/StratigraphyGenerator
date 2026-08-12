---
title: Project history
audience: developer
status: current
source_files:
  - poggio_webapp/pipeline/__init__.py
  - poggio_webapp/app.py
verified_against: ae2fc1d
---

# Project history

How the repository reached its current shape, and how to recover what came
before.

## The numbered-folder era

The pipeline began as a series of numbered directories, each holding a
standalone CLI script and its outputs:

```
02_preprocess  03_extraction  04_normalize_validate
05_convert_coords  06_gempy_model  07_visualizer
```

You ran them in order, by hand, passing files between stages.

Those folders were retired in the `webapp` commit. Each stage's logic became an
importable module under `poggio_webapp/pipeline/`, and the web application
became the way to run them. The stage boundaries survived the move — the
numbered folders map almost one-to-one onto today's pipeline modules — which is
why the workflow documentation is still numbered.

## What that means now

`scans/` remains, holding raw drawings; it was `01_scans/` until commit
`0b2edf9`. `00_docs/`, which held reference material for whoever draws the
profiles, was retired in that same commit — recover it the way the section
below recovers everything else. Everything else moved.

The application writes into three directories, all created on import and none
of them tracked by git:

- `poggio_webapp/jobs/` — one folder per sheet
- `poggio_webapp/trenches/` — merged multi-wall output
- `poggio_webapp/matrices/` — Harris matrices

A fresh clone therefore has no jobs, no models, and no matrices. That is
expected. See [jobs, sheets, and
trenches](../concepts/jobs-sheets-and-trenches.md) for how those directories
relate.

## Recovering old artifacts

The pre-`webapp` outputs and CLI scripts are all still in git history.

Retrieve a specific artifact by naming its path at the commit before the
migration:

```bash
git show d383439^:03_extraction/output_section001.json > output_section001.json
```

```bash
git show d383439^:05_convert_coords/gridConfig.JSON > gridConfig.JSON
```

```bash
git show d383439^:06_gempy_model/trench23.gempy > trench23.gempy
```

Find a retired script wherever it lived across the whole history:

```bash
git log --oneline --all -- "*convertCoords.py"
```

List everything that existed at that commit:

```bash
git ls-tree -r --name-only d383439^
```

## Why the old extractions are still useful

The history holds both known-genuine and known-fabricated extractions of the
same source drawing. That makes them ready-made fixtures for testing the
fabrication heuristics — a test that cannot tell the two apart is not testing
anything.

[Accuracy and provenance](../concepts/accuracy-and-provenance.md) explains what
distinguishes them, and the [roadmap](roadmap.md) lists this as a concrete
verification task.

## Related

- [Capability status](capability-status.md) — the present state.
- [Roadmap](roadmap.md) — where it is going.
- [Pipeline](../architecture/pipeline.md) — the modules the numbered folders
  became.
