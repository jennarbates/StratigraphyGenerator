---
title: Finds, and what the record cannot support
audience: user
status: current
source_files:
  - tests/fixtures/t905-2025-special-finds.json
  - tests/fixtures/t905-2025-loci.json
  - tests/test_t905_worked_example.py
  - poggio_webapp/pipeline/validator.py
verified_against: ae2fc1d
---

# Finds, and what the record cannot support

T905 produced 26 special finds. Every one has a locus, a date, a trench-book
page, a coordinate and an elevation, which is more than many trenches manage,
and enough to check.

**Twenty-one of the 26 place consistently inside the locus they are filed
under. Five do not.**

This page is about those five, and then about the things the record cannot
tell you no matter how carefully it is read.

## How a findspot is recorded

The method is worth stating because it sets the precision. A plumb bob is held
over the object; a tape is run at right angles from the plumb line to two
perpendicular baulk strings, giving the easting and northing; a line level from
the datum gives the elevation.

Three of T905's finds (SF 1, 2 and 3) were recovered from a **wheelbarrow**
rather than in situ. Their coordinate is where the bucket was filled, not where
the object lay, and the trench book says so by quoting a tolerance: ±25 cm in
plan, ±6 to ±14 cm in elevation.

That distinction matters more than the tolerance does. A wheelbarrow find's
coordinate is a *provenance*, not a *findspot*, and a record that does not mark
it invites the number to be used as though it were one. The test suite asserts
that the finds carrying tolerances are exactly the finds recorded as
wheelbarrow recoveries.

## The five that do not place

Two checks, run against the loci fixture: is the coordinate inside the volume
the locus occupies, and is the elevation between that locus's opening ceiling
and its closing floor? Both allow 10 cm of slack, comfortably more than the
[±6 cm the instruments repeat to](the-sounding.md#how-precise-are-these-numbers).

| Find | Problem | By how much |
|---|---|---|
| SF 8 | 149.48E is west of the west baulk at 150E | 0.52 m outside the trench |
| SF 9 | 149.18E is west of the west baulk | 0.82 m outside the trench |
| SF 16 | 153.30E/**21.21S** is north of the sounding at 22S, and 23.44 mAE is below its floor | 0.79 m outside, 0.30 m below |
| SF 17 | 152.55E is west of the sounding at 153E | 0.45 m outside |
| SF 3 | 23.75 mAE is below every Locus 1 closing reading | 0.29 m below |

**No single check catches all five.** SF 17's elevation is perfectly good (it
sits correctly within Locus 6) and only its easting is wrong. SF 3's
coordinate is fine; only its elevation is impossible. SF 16 fails both. A
findspot has to be checked in three dimensions, or it is not being checked.

### What each one probably is

**SF 8 and SF 9** are both filed under Locus 2, which exists only inside the
trench, and both were found in the northwest quadrant. Their northings are in
range. It is the eastings that are wrong, and by suspiciously similar amounts.

**SF 16** is the clearest error in the record. The daily log places it "in the
northern metre of the sounding", and the sounding runs 22S to 24S, so the
prose and the recorded northing of 21.21S disagree. Its elevation of 23.44 mAE
is below the deepest point the sounding ever reached (23.51 m) and therefore
below the surface of Locus 8, which nobody excavated. Two independent numbers,
both impossible, on a find that is otherwise well documented and catalogued.

**SF 3** was recorded on day 1 with SF 1 (24.56 mAE) and SF 2 (24.35 mAE), from
the same wheelbarrow at the same nominal spot, on a day spent lowering a spoil
heap whose crest was at 24.70 mAE. At 23.75 mAE it is 0.60 m below the find
recorded immediately before it. Nothing on site was at that elevation that day.

Note what is *not* being claimed. The record does not say what any of these
should be, and neither does this page. A transposed digit is a plausible story
for SF 16 and for SF 3, but it is a story. The defensible statement is that
five findspots contradict their loci, not that five findspots have known
correct values.

## The 21 that do place

The other 21 are consistent with the surfaces recorded around them, and two
further checks pass across all 26:

**Every find is dated inside its locus's open-to-close window.** A find dated
outside it would mean the locus number or the date is wrong. None are. The
dates are the part of this record that holds together best.

**The catalogued finds agree between the list and the locus form.** Locus 6 is
the only locus whose form lists catalogue numbers, and all three appear in the
special finds list against Locus 6 finds.

One of those three is instructive. `CAT-0126` is on the locus form and in the
locus description, but the special finds list's own `Cataloged?` column says
**No** and leaves the number column blank. The same thing happens to `CAT-0145`
and `CAT-0146`, which are marked "not catalogued" in rows that give their
catalogue numbers.

The flag is wrong and the numbers are right, which is the usual direction: a
tick-box gets stale, a written identifier does not.

## What the record cannot support

Beyond the five bad findspots, there are claims T905's paperwork simply cannot
settle. These are the ones worth naming before anyone builds an argument on
them.

### Depths quoted in prose do not reproduce

The log records SF 15 as lying "ca. 13 cm below the surface of the floor".
Interpolating Locus 6's opening surface at its coordinates gives about
23.89 mAE, and the find is at 23.82, so **7 cm**, not 13.

The Locus 6 description puts its Archaic material "approximately 15 to 20 cm
beneath the floor" while grouping SF 15 with SF 20 and SF 21. Those two are in
Locus 7 and recompute to about **24 cm**. The stated range does not contain
either figure, and the two finds it groups are at quite different depths.

Nobody was careless here. A depth quoted in the field is estimated against the
nearby trench floor by eye, which is not the same operation as subtracting two
surveyed surfaces. **The recomputed depth is the one with a provenance**, and
where the two disagree the prose figure should be treated as an impression.

### An identification changed and the record did not say so

`CAT-0051` is a "glass shard" in the field record and on the finds list. In the
Lithics Summary it is an obsidian flake, and it is the trench's *only* lithic,
so the entire lithic count for the season rests on it.

Obsidian is volcanic glass. This is very plausibly a re-identification during
study rather than a contradiction, and the two records may both be right about
what they were looking at when they were written. **No record says so**, and
nothing distinguishes this case from a genuine disagreement.

If it is glass, the season's lithic count is zero, and any statement about
lithic use in this trench is a statement about one object that may not be a
lithic. Not every disagreement between records is an error, and the record
rarely tells you which kind you are looking at.

### Summary tables contradict themselves

Three of T905's material summaries do not survive arithmetic:

- The **slag summary's** Locus 2 row reads 0 fragments, 100.00% by number, 4 g,
  0.00% by weight. Its prose says most of the slag came from Locus 3 while its
  own table puts 53 of the 62 g in Locus 1.
- The **bone summary's** prose says loci 3, 4 and 5 were not excavated and
  yielded no bone; its table gives Locus 3 six fragments weighing 29 g. Loci 4,
  5 and 8 are the unexcavated ones.
- The **SU forms' ceramic counts** disagree with the pottery chart for two
  loci: 238 against 221, and 437 against 436.

The counts and weights are transcribed as printed, and the fixture records the
disagreement rather than resolving it. Where a table and its own summary prose
conflict, the itemised table is the better source, because you can see what it
is made of.

### Three things the schema cannot hold at all

- Abutment. Three forms record `IS BOUND TO`: the floor runs up against
  the wall. There is no younger-to-older edge for "touches", so the assertion
  is recorded in the fixture and absent from the matrix. See
  [stratigraphy](stratigraphy.md).
- The east wall's surface. No opening elevation was ever measured at that
  corner, so it cannot be registered. See [registration](registration.md).
- Anything below Locus 8. It was never excavated. A surface drawn beneath
  it is invention.

## The habit worth copying

None of the checks on this page needed the application. They needed the
findspots and the locus surfaces in the same place, and a willingness to
subtract.

That is most of what a fixture like this is for. The
[synthetic fixtures](../fixtures/README.md) show what a clean input looks like;
T905 shows what an ordinary one looks like, and 5 in 26 is not an unusual rate.
A pipeline that has only ever been demonstrated on clean input has not been
shown to refuse anything, and refusing is the part that protects the
interpretation.

## Related

- [Log a find](../workflows/logging-finds.md): recording findspots in the application
- [Check for problems](../workflows/05-check-problems.md): the validator and its rules
- [Markers, features, and finds](../concepts/markers-features-and-finds.md)
- [Accuracy and provenance](../concepts/accuracy-and-provenance.md)
- [Find identifiers](../archaeology/find-identifiers.md)
