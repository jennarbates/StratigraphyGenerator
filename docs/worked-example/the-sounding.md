---
title: The sounding as measured geometry
audience: user
status: current
source_files:
  - tests/fixtures/t905-2025-loci.json
  - tests/test_t905_worked_example.py
  - poggio_webapp/pipeline/site_elevation.py
verified_against: ae2fc1d
---

# The sounding as measured geometry

Most of a locus record is prose. The part this application can actually build
from is four corners and an elevation at each, recorded twice — once when the
locus opened and once when it closed.

T905's sounding is the cleanest example in the trench: a 2 × 1 m box, dug
through the floor in three stages, with the same four coordinates measured at
every stage. Eight readings per locus, twenty-four in total, and they form one
continuous column.

![A section down the western edge of a two metre sounding showing three recorded surfaces bounding two excavated layers above an unexcavated one, each surface labelled with its elevation at both ends](../assets/diagrams/we-sounding-section.svg)

*Each locus closes on the surface the next one opens on, so the four elevations
describe one continuous column.*

## The readings

The sounding sits at 153–154E by 22–24S. All three loci use the same four
corners.

| Surface | NW | NE | SE | SW |
|---|---|---|---|---|
| Locus 6 opening — the floor | 23.99 | 23.98 | 23.91 | 23.87 |
| Locus 6 closing = Locus 7 opening | 23.79 | 23.77 | 23.74 | 23.74 |
| Locus 7 closing = Locus 8 opening | 23.62 | 23.58 | 23.51 | 23.51 |
| Locus 8 closing | 23.62 | 23.58 | 23.51 | 23.51 |

All values mAE, on the corrected 25.23 datum.

Three properties of that table are worth naming, because each is a check you
can run on any locus record:

**The column closes.** Locus 6's closing surface *is* Locus 7's opening
surface, at all four corners, and Locus 7's closing *is* Locus 8's opening. Not
"within a centimetre" — identically. A locus is opened on the surface the
previous one was closed on, so where those two readings disagree, one of them
was taken on a different day, at a different point, or after further digging
that nobody wrote down.

**Every surface descends.** No corner of any locus is higher at closing than at
opening. That sounds too obvious to check until you meet a record where it
fails, which usually means an opening and closing column got swapped.

**Locus 8 has zero thickness.** Its opening and closing elevations are
identical at all four corners, because it was defined and left unexcavated at
the end of the season. An unexcavated locus should look exactly like this, and
one that does not has been dug into without being recorded as such.

## What the elevations say that the prose does not

The season describes the floor as "approximately 20 cm" thick, and the SU
form's elevation field says `20.0 cm deep`. Subtract Locus 6's two surfaces:

| Corner | Opening | Closing | Thickness |
|---|---|---|---|
| NW | 23.99 | 23.79 | **0.20 m** |
| NE | 23.98 | 23.77 | 0.21 m |
| SE | 23.91 | 23.74 | 0.17 m |
| SW | 23.87 | 23.74 | 0.13 m |

The stated figure is exactly right — at one corner. Across the box the layer
runs from 13 cm to 21 cm, and the southwest corner is barely two thirds the
thickness of the northwest.

This is the general case, not a flaw in this particular record. **A single
stated thickness is a measurement of a place, not a property of a layer.** A
model that extrudes 0.20 m uniformly across the sounding is 7 cm wrong at one
corner, which is more than the 6 cm repeatability of the instruments that
produced the numbers in the first place.

The same reasoning applies to the depth of a find below a surface, and there it
bites harder — see [finds, and what the record cannot
support](finds-and-limits.md).

## How precise are these numbers?

The record answers this itself, without anyone having to run an experiment.

Locus 1's closing surface and Locus 2's opening surface are the same physical
ground, read at the same eight points a day apart. Comparing them:

| Point | Locus 1 closing | Locus 2 opening | Difference |
|---|---|---|---|
| 150E/20S | 24.14 | 24.15 | **+0.01** |
| 151E/20S | 24.19 | 24.17 | −0.02 |
| 151E/22S | 24.17 | 24.15 | −0.02 |
| 154E/22S | 24.12 | 24.08 | −0.04 |
| 154E/23S | 24.04 | 24.10 | **+0.06** |
| 155E/23S | 24.04 | 24.06 | **+0.02** |
| 155E/25S | 24.04 | 24.03 | −0.01 |
| 150E/25S | 24.12 | 24.07 | −0.05 |

Three of the eight **rise**. Ground that has been excavated between two
readings cannot rise, so those three are pure measurement error, and the
largest is 6 cm.

That is the number to carry into everything else on these pages: a plumb bob, a
line level and a tape repeat to roughly ±6 cm on a cut soil surface, and better
than that only in ideal conditions. A 2 cm difference between two elevations in
this record is not a finding. A 30 cm difference is.

Locus 4, the stone wall, gives the same answer from the other direction. It was
never excavated, so its opening and closing readings are the same stone tops
measured twice, two weeks apart. Three of its corners fall, by 9 cm, 2 cm and
2 cm; the fourth **rises by 5 cm**. On an irregular stone surface the tape
simply lands somewhere slightly different.

## Two loci recorded once, from two directions

Loci 3, 4 and 5 were opened on the same morning and closed on the same morning,
and their boundaries touch. Four vertices therefore appear on two locus records
each:

| Point | On | Opening | Closing |
|---|---|---|---|
| 153.20E/20S | Loci 3 and 4 | 24.05 | 24.03 |
| 152.84E/20S | Loci 4 and 5 | 24.13 | 24.04 |
| 152.65E/21.36S | Loci 3 and 5 | 24.00 | 24.00 |
| 150E/21.82S | Loci 3 and 5 | 24.02 | 24.02 |

All four agree **exactly**, in both phases. Given that the same instruments
scatter by up to 6 cm when re-measuring a soil surface a day later, eight exact
matches are not eight lucky readings — they are one reading written onto two
forms, which is the sensible thing to do when two loci share an edge.

That is worth knowing in both directions. It is a strong check that the
boundaries between the three loci were drawn consistently. It is *not*
independent corroboration of the elevation itself, and treating it as such
would be double-counting a single measurement.

## What this feeds

The four-surface column is what the [model builder](../workflows/07-create-model.md)
consumes: each surface becomes a set of points, and the model interpolates
between them. Three things follow from the table above.

- **The interpolation is a hypothesis.** Four corners per surface is four
  points. What happens between them is the model's guess, constrained by
  nothing.
- **The surfaces are not parallel.** Locus 6 is 0.20 m thick at one corner and
  0.13 m at another, so a model that assumes constant thickness will diverge
  from the readings by more than their own uncertainty.
- **Locus 8 has a top and no bottom.** It was never dug. Any surface drawn
  beneath it is invention, and should be labelled as such rather than rendered
  in the same style as a measured one.

## Related

- [Create the model](../workflows/07-create-model.md) — what happens to these surfaces
- [Layers and boundaries](../concepts/layers-and-boundaries.md)
- [Elevation](../archaeology/elevation.md) and [locus](../archaeology/locus.md)
- [Accuracy and provenance](../concepts/accuracy-and-provenance.md)
