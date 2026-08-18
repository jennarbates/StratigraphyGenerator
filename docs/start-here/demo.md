---
title: Run the demo
audience: beginner
status: current
source_files:
  - poggio_webapp/demo/datasets.py
  - poggio_webapp/demo/seed.py
  - poggio_webapp/demo/walls.py
  - poggio_webapp/demo/run.py
  - poggio_webapp/backend/routes/demo.py
  - poggio_webapp/static/app/demo-mode.mjs
  - tests/test_demo.py
  - tests/test_demo_routes.py
  - Makefile
verified_against: ae2fc1d
---

# Run the demo

A whole excavated trench, taken to a model: no drawing to trace, no survey to
type in, no API key.

## From the application

Start it with `make run` and open <http://localhost:5000>. In the sidebar:

> **Never used this before?** Load a demonstration trench. No drawing needed.
> **[See it refuse]** · **[See it build]**

Each button seeds one trench. Then open the trenches page and press **Build the
combined model**. The registration is already filled in from the trench's
surveyed records, so there is nothing to type.

Pressing Build yourself is the point. The two trenches end differently, and
watching that happen is the demonstration.

"Remove the demonstration" takes both back out again.

## From the command line

```bash
make demo
```

```bash
make demo-run
```

The first seeds both trenches; the second builds them and reports where each
one lands.

## Why there are two

The demonstration is a pair, and neither half means much alone.

| Trench | What it has | Where it ends |
|---|---|---|
| **T905** | Four wall drawings, three surveyed corners | The build **refuses**, naming the east wall |
| **T906** | The same four drawings, all four corners | Merges, registers, converts, **builds** |

They differ by one number: an opening elevation at the northeast corner. That
corner sat inside a previous season's backfilled trench, so there was no
undisturbed surface there to measure and nobody measured one.

Everything else about the two trenches is identical. The same 8 loci, the same
stratigraphy, the same 26 findspots, the same four sections. One number decides
whether there is a model.

That is the whole argument for the refusal. An application that filled the gap
in would produce a model from T905 too, and it would look exactly as convincing
as T906's.

## What you get

```
T905: REFUSED. The record does not support a model

  these faces have no surfaceZ in the grid config: 'east wall'. surfaceZ is
  the ground surface each wall's depths are measured down from, so without it
  those depths convert to no elevation at all. This is usually a corner whose
  opening elevation was never recorded -- supply it, or build the walls that
  are registered as their own trench
```

T905 does not fail early. It loads four wall sheets, normalizes each one,
merges them into a trench, checks the site grid, checks the vertical frame, and
*then* refuses, because the refusal is about registration, and registration is
the last thing checked before conversion. Getting that far is the point.

T906 goes on through conversion and into a model:

```
T906: BUILT. The model is on disk

  3 surface mesh(es): Locus_1, Locus_2, Locus_3
  extent 148.0-157.0 E, -27.0--18.0 N, 22.95-25.70 mAE
  order Locus 1 over Locus 2 over Locus 3  (harris-matrix)
```

132 interface points across three surfaces, orientations solved from *pairs* of
walls rather than single ones (so each surface carries one true dip instead of
four disagreeing apparent ones), and a stratigraphic order taken from the
Harris matrix rather than guessed from elevation.

!!! note "The last stage needs GemPy"

    Without it you get `MODEL-READY` instead of `BUILT`: every stage ran and
    only the mesh is missing. Install it with
    `pip install gempy gempy_viewer`. It is an optional extra, and heavy. See
    [create the model](../workflows/07-create-model.md).

The section drawing GemPy writes beside the meshes is worth a look. The three
deposits stack in the order the matrix gives, and the western end rides half a
metre high, which is the corner standing on the old spoil heap, showing up in
the model because the record says it is there.

Both trenches stay in the application afterwards. Open
<http://localhost:5000/trenches> after `make run` and they are there, alongside
their Harris matrices and the season's findspots.

## Where the numbers come from

`make demo-list` shows the record sets available:

```
T905     Synthetic demonstration data: T905 2025
```

T905 is the [worked example](../worked-example/index.md), a synthetic trench
built to have the gaps, contradictions and transcription slips that real
paperwork has. `poggio_webapp/demo/datasets.py` finds it in `tests/fixtures/`,
which is why a fresh clone can run the demo with nothing installed but the core
dependencies.

It also looks in `local/fixtures/`. Anything there is real excavation data, is
never committed, and is labelled **Real excavation records** everywhere it
appears. If you have put a season's records there, they show up in
`make demo-list` too.

## The wall drawings are invented, and say so

The fixtures record a trench's corners, loci and finds. They do not record its
four drawn sections, and neither does `scans/`, so the demo draws them, in
`poggio_webapp/demo/walls.py`.

Each locus boundary sits at the mean closing elevation the record gives for
that locus; the undulation between those readings is invented. Every generated
point is marked `"confidence": "synthetic"` and every sheet carries a
marginal note saying it was not drawn in the field.

`poggio_webapp/demo/seed.py` **refuses to generate sections for a real record
set**. Invented geometry does not go under a real trench's label, and a
demonstration is not a good enough reason to make the exception.

## What it writes, and how to undo it

Everything lands in `poggio_webapp/jobs/`, `poggio_webapp/trenches/` and
`poggio_webapp/matrices/`, the same three gitignored directories the
application already uses for your own work. Nothing is written into the
repository and nothing is copied out of `local/`.

Seeded jobs are named `demo-t905-north-wall` and so on, and every one carries a
provenance badge wherever it appears (in the drawing list and on the trenches
page), so a demonstration trench is never mistaken for your own work.

Re-seeding removes the previous run's demo trenches first, so the
demonstration always opens on a known state and leaves everything else alone.
"Remove the demonstration" in the sidebar, or `DELETE /api/demo`, takes both
trenches back out.

## Related

- [A trench, end to end](../worked-example/index.md): the record these numbers come from, page by page
- [Combine walls into one trench](../workflows/09-multi-wall-trench.md): the workflow the demo automates
- [Place on site](../workflows/06-place-on-site.md): what registration is, and why a corner elevation decides it
- [Quickstart](quickstart.md): installing enough to run this
