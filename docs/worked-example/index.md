---
title: A trench, end to end
audience: beginner
status: current
source_files:
  - tests/fixtures/t905-2025-layout.json
  - tests/fixtures/t905-2025-loci.json
  - tests/fixtures/t905-2025-special-finds.json
  - tests/test_t905_worked_example.py
verified_against: 13091c9
---

# A trench, end to end

The [workflow pages](../workflows/overview.md) each cover one step. This
section covers one **trench**, from the four numbers that place it on the site
to the 26 findspots inside it, and shows what the application does with a
record that is complete in some places and simply absent in others.

The trench is **T905**. It does not exist.

!!! warning "Synthetic, and deliberately imperfect"

    T905, its personnel, its coordinates, its loci and its finds are invented.
    Nothing here is archaeological evidence and none of it may be used for
    interpretation.

    It is not invented *freely*, though. The [synthetic
    fixtures](../fixtures/README.md) are clean: they show what a well-formed
    input looks like. T905 is the other kind of example. It is modelled on the
    shape of a real season's paperwork — the same sorts of gap, contradiction,
    transposed digit and unrecorded value — because a pipeline demonstrated
    only on tidy input has never been shown to refuse anything.

    Every defect on these pages is deliberate, and every one of them is
    something field records actually do.

![Plan of a five metre square trench showing a cobbled surface and a wall in its northern half, a two by one metre sounding, a corner with no opening elevation, a corner whose height is a spoil heap, and two finds plotted outside the trench](../assets/diagrams/we-trench-plan.svg)

*Everything the worked example turns on is visible in plan, including the three
places where the record runs out.*

## What T905 contains

A 5 m by 5 m trench, opened for one season, with eight
[loci](../archaeology/locus.md):

| Locus | What it is | Excavated? |
|---|---|---|
| 1 | Topsoil, dug together with an old spoil heap | Yes |
| 2 | The deposit between topsoil and the structure | Yes |
| 3 | The building's compacted earthen floor | Exposed, then sounded |
| 4 | A foundation wall, one course preserved | No — drawn and left |
| 5 | A cobbled surface outside the wall | No — drawn and left |
| 6 | A 2 × 1 m sounding through the floor | Yes |
| 7 | The deposit under the floor | Yes |
| 8 | The layer below that | No — out of season |

Two features left standing, one floor sectioned by a small sounding, and a
column of four measured surfaces running down through it. That is an ordinary
season.

## What each page shows

| Page | The question it answers |
|---|---|
| [Registration](registration.md) | Can this trench be placed on the site from its own paperwork? |
| [Stratigraphy](stratigraphy.md) | What does the recording form actually assert, and what does the matrix keep? |
| [The sounding](the-sounding.md) | What does a locus look like as measured geometry rather than prose? |
| [Finds, and what the record cannot support](finds-and-limits.md) | Which of these 26 findspots can be trusted, and how would you know? |

## The short version

Three things are worth taking away before the detail.

**One wall cannot be registered, and that is the correct outcome.** T905's
northeast corner has no opening elevation, because that corner sat inside a
previous season's backfilled trench and there was no undisturbed surface there
to measure. The application will not invent one. Three walls register from
surveyed values; the fourth stops the build. See
[registration](registration.md).

**The record agrees with itself far more often than it disagrees.** Four
vertices are recorded twice on different loci and match exactly. The sounding's
four surfaces chain from one locus to the next without a gap. A stated layer
thickness of "about 20 cm" recomputes to 0.20 m at the corner it was measured
at. Those agreements are what make the disagreements worth noticing.

**Five of the 26 findspots contradict the locus they are filed under**, and no
single check catches all five: two fail on plan position, one fails only on
elevation, one fails on both. A findspot has to be checked in three dimensions
or it is not being checked. See
[finds, and what the record cannot support](finds-and-limits.md).

## Where the numbers live

Everything on these pages comes from three fixtures, and each field in them
records the kind of document it stands for:

```text
tests/fixtures/t905-2025-layout.json          corners, walls, the datum
tests/fixtures/t905-2025-loci.json            eight loci, and the matrix
tests/fixtures/t905-2025-special-finds.json   26 findspots
```

`tests/test_t905_worked_example.py` asserts every claim these pages make. If a
number here is wrong, a test fails — including the counts, which are the
easiest thing to quietly get wrong when a fixture is edited.

## Related

- [Workflow overview](../workflows/overview.md) — the numbered path, one sheet at a time
- [Synthetic fixtures](../fixtures/README.md) — the clean examples, for contrast
- [Glossary](../start-here/glossary.md) — locus, baulk, datum, mAE
