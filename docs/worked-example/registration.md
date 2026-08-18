---
title: Registering T905
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/trench_layout.py
  - poggio_webapp/pipeline/site_grid.py
  - poggio_webapp/pipeline/site_elevation.py
  - tests/fixtures/t905-2025-layout.json
  - tests/test_t905_worked_example.py
verified_against: ae2fc1d
---

# Registering T905

[Place on site](../workflows/06-place-on-site.md) asks for four numbers per
wall: an origin easting, an origin northing, a surface elevation, and a
bearing. Working those out by hand is slow and easy to get wrong, and (this is
the dangerous part) **a model built on the starter placeholders looks exactly
like a model built on real values**.

The numbers usually already exist. A trench's corners are staked by total
station and written into the season's spreadsheet; its elevations are in the
trench book. Give the application the corners and the wall names and it derives
each wall's registration:

- its **origin** is the corner it starts at,
- its **bearing** is the direction to the next corner, clockwise from Grid North,
- its **surfaceZ** is the opening elevation measured at that corner.

Wall names come from the corner labels: two corners sharing a cardinal letter
name the wall between them, so `NW` to `NE` is the north wall.

![Plan of a five metre square trench showing a cobbled surface and a wall in its northern half, a two by one metre sounding, a corner with no opening elevation, a corner whose height is a spoil heap, and two finds plotted outside the trench](../assets/diagrams/we-trench-plan.svg)

*Everything the worked example turns on is visible in plan, including the three
places where the record runs out.*

## The corners

Straight out of the season spreadsheet, with the elevations from the trench
book's opening entry:

| Corner | Grid | Opening elevation |
|---|---|---|
| NW | 150, −20 | 24.28 mAE |
| NE | 155, −20 | **not recorded** |
| SE | 155, −25 | 24.16 mAE |
| SW | 150, −25 | 24.70 mAE |

Datum nail: **25.23 mAE**.

The grid values are already signed. The trench book writes
`150E/20S`; the spreadsheet stores `150/-20`, because the site's rule that
South and West are negative is applied before the number reaches the sheet. It
is not applied twice.

## What comes back

```text
source: surveyed | datum: 25.23 mAE
  north wall  origin=(150.0, -20.0)  bearing=90    surfaceZ=24.28
  east wall   origin=(155.0, -20.0)  bearing=180   surfaceZ=None
  south wall  origin=(155.0, -25.0)  bearing=270   surfaceZ=24.16
  west wall   origin=(150.0, -25.0)  bearing=0     surfaceZ=24.70

note: no opening elevation recorded for 155E/20S. The procedures ask for one
      at every corner; without them the affected faces have no surfaceZ and
      the build will refuse
```

All four sides come out 5.00 m, which is what the Trench Layout section says
the trench is. The config declares `source: "surveyed"`, so the
[multi-wall build](../workflows/09-multi-wall-trench.md) will not mistake these
for placeholders.

And the east wall does not build.

## Why the missing elevation is not a clerical error

It is tempting to treat a blank field as sloppiness and fill it in with
something plausible: the mean of the other three, say, or the value from a
later day. Both would be wrong, and the reason is archaeological rather than
administrative.

T905's northeastern meters overlap a trench dug and backfilled in a previous
season. Locus 1, the opening topsoil, covers only the ground that had not been
dug before. **There was no undisturbed opening surface at that corner to
measure.** The elevation list in the trench book stops at 151E/20S, the eastern
limit of Locus 1, and the trench's own northeast corner never receives an
opening reading at all.

That corner does eventually get an elevation: 23.96 mAE, as Locus 3's `NE3`,
fifteen days and two loci later. It is a floor surface, 0.32 m below the
opening ground elevation at the northwest corner. Registering the east wall to
it would put that wall's top a third of a metre below the other three, and the
resulting model would show a step along one side of the trench that nothing in
the ground ever had.

So the module refuses. From `trench_layout.py`:

> **It will not invent an elevation.** Opening elevations are taken "for at
> least all corners of your trench", so a layout that has corners but no
> elevations is incomplete rather than defaultable.

A refusal is not the same as having nothing. The east wall still gets its
origin and its bearing, because the corner nail's *position* is recorded: two
of its four registration values are real, and only the third is missing. What
you cannot do is build until someone supplies it or decides what to do without
it.

## The corner that is high for the wrong reason

The southwest corner reads 24.70 mAE, 0.42 m above the northwest and 0.54 m
above the southeast. On a 5 m trench that is a lot of relief, and it would be
easy to read it as a sloping ground surface worth modelling.

It is a **spoil heap**. An earlier season dumped its excavated soil in that
corner, and the trench book says so plainly: the dump "sloped significantly in
this southwest corner and was 0.52 m deep", and it was removed as part of Locus
1 along with the topsoil beneath it.

By the time Locus 1 closed, that corner read 24.07 mAE, 0.63 m lower. The
0.52 m of dump plus the 8 cm of topsoil under it account for 0.60 m of that,
which is as close as two independently measured numbers get.

The consequence for registration is direct. The **west wall's origin corner is
SW**, so its `surfaceZ` is 24.70, the top of a modern dirt pile. That is a
faithful record of the opening surface, and it is the correct value to store.
It is not the top of any archaeological deposit, and anything that reads
`surfaceZ` as "where the stratigraphy begins" will be almost half a metre out
on that wall.

!!! note "Two kinds of relief"

    A high corner can mean the ground sloped, or it can mean somebody stood a
    wheelbarrow there for a season. The elevation alone does not distinguish
    them. Only the locus description does, which is why an elevation without
    its context is a number and not a measurement.

## The datum moved by half a metre

The datum was first shot at **25.73 mAE**. Partway through the season it was
found that the season's datum points had been set **0.50 m high because of a
transit error**. They were reshot, and every elevation recorded before that
point was corrected. T905's datum is **25.23 mAE**.

This is worth dwelling on because a corrected series and an uncorrected one
look identical. Nothing in a column of numbers announces which scale it is on.

Here it can be checked, and the check does not depend on trusting the note. The
locus that closed the day before the reshoot and the locus that opened the day
after are **continuous**: one closes at 23.87–24.02 mAE, the next opens at
23.87–23.99 mAE at points inside it. A 0.50 m step at that boundary would be
unmissable, and there is none.

Two conclusions follow, and only one of them is comfortable:

- the elevations are on the corrected scale, so they can be used together;
- had the correction been applied to some records and not others, this
  continuity check is what would have caught it, and had it not been applied
  to *any*, the check would have shown nothing wrong at all.

A datum correction is only detectable inside a record that spans the change.
Anything measured entirely before it, or entirely after, carries no evidence of
which scale it is on. That is a reason to record the datum's value beside every
elevation series rather than once at the front of a book.

## Two more ways to be wrong

**Corners listed out of order.** Two labels transposed make a bow-tie: still a
valid polygon, but its derived bearings would send two walls diagonally across
the pit. This is refused, not registered.

**A mistyped corner label.** A wall longer than any trench at the site is
flagged in the notes. Check the derived lengths against the drawings: T905's
come out 5.00 m on all four sides, which is what the plan sheets show.

## Related

- [Place on site](../workflows/06-place-on-site.md): what the registration is for
- [Combine walls into one trench](../workflows/09-multi-wall-trench.md): the build that consumes it
- [Coordinate spaces](../concepts/coordinate-spaces.md): Grid North, the two local grids, and mAE
- [Datum](../archaeology/datum.md) and [elevation](../archaeology/elevation.md)
- [Trench layout](../archaeology/trench-layout.md): the trench book section these values come from
