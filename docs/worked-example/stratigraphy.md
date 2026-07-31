---
title: T905's stratigraphy
audience: user
status: current
source_files:
  - poggio_webapp/pipeline/harris_matrix.py
  - tests/fixtures/t905-2025-loci.json
  - tests/test_t905_worked_example.py
verified_against: 13091c9
---

# T905's stratigraphy

Eight loci, seven ordering relationships, one correlation, and three assertions
the schema has nowhere to put. This page follows each of them from the
recording form into the matrix, and is as much about what does not survive the
trip as what does.

![A Harris matrix of eight loci running from topsoil to an unexcavated layer, with two loci joined by a dashed correlation and one dashed edge marked as asserted but dropped from the display](../assets/diagrams/we-matrix.svg)

*One correlation and one redundant edge, both taken from the recording forms
rather than inferred.*

## What the forms assert

Each locus has an SU form with a sequential-stratigraphy block: `OVERLIES`,
`UNDERLIES`, `EQUAL TO`, `IS BOUND TO`, `CUTS`, `IS FILLED BY`. Read across the
eight forms, T905's ordering comes out as:

| Younger | Older | Grounds |
|---|---|---|
| 1 | 2 | Locus 2 was opened at Locus 1's closing surface, across the whole trench |
| 2 | 3 | Locus 2 overlies the structure's features; Locus 3's form gives previous loci 1, 2 |
| 2 | 4 | Locus 4's form: `UNDERLIES Locus 2` |
| 2 | 5 | Locus 5 was revealed by the removal of Locus 2 |
| 6 | 7 | Locus 6's form: `OVERLIES Loci 7, 8`; Locus 7 opened at Locus 6's closing surface |
| 6 | 8 | Locus 6's form: `OVERLIES Loci 7, 8` |
| 7 | 8 | A soil change at the base of Locus 7 prompted a new locus |

Every edge carries the grounds it was drawn from. That is not decoration: an
edge is an *interpretation*, and one with no stated basis can only be believed,
never reviewed. The test suite asserts that no relation in the fixture has an
empty `evidence` field.

## Loci 3 and 6 are the same deposit

Locus 6 is the 2 × 1 m sounding that was cut through Locus 3, the building's
floor. Both SU forms say `EQUAL TO` and point at each other.

The season's own drawn matrix, however, stacks Locus 6 one level *below* Locus
3, as though 3 were younger. That is a drafting convenience — the units were
excavated on different dates, so they were drawn in the order they were dug —
and taken literally it says a deposit is younger than itself.

The forms are right. Encoded as a **[correlation](../archaeology/correlation.md)**,
which is exactly what the schema has for this:

> Correlation is different. It says that two or more imported observations are
> interpreted as parts of the same stratigraphic unit. A correlation is not a
> chronological edge.

Eight loci therefore render as **seven display nodes**. Loci 3 and 6 collapse
into one, the edge `2 → 3` and the edge `6 → 7` both attach to it, and the
result is still acyclic.

!!! warning "This is not automatic, and must not be"

    The application never merges two units because their labels match. Two
    excavators can and do reuse a number for genuinely different deposits, and
    a silent merge would be unrecoverable. A correlation is a proposal a person
    accepts. Here a person had already accepted it, twice, on two forms.

## The edge that is dropped from the diagram

Locus 6's form asserts that it overlies **both** 7 and 8. Since 7 overlies 8,
the `6 → 8` edge follows from the `6 → 7 → 8` path: it is true, and it is
redundant.

The renderer's [transitive reduction](../workflows/harris-matrix.md) drops it
from the drawn diagram and raises a `redundant-relation` warning. The assertion
itself stays in the saved JSON.

That split is deliberate and worth stating plainly: **the diagram shows
immediate relationships; the record keeps everything that was asserted.**
Deleting the redundant edge would quietly discard something an excavator wrote
down, and the fact that it is currently implied by other edges is no guarantee
it will stay implied — remove `7 → 8` later and `6 → 8` is suddenly load-bearing
again.

## Three assertions that do not survive

Three of T905's forms carry `IS BOUND TO`:

| Loci | Recorded on |
|---|---|
| 3 and 4 | Locus 3's form |
| 3 and 5 | Locus 3's form |
| 4 and 6 | Locus 6's form |

`IS BOUND TO` says two units **abut** — the floor runs up against the wall, the
floor meets the cobbles. That is a claim about contemporaneity, or at least
about physical contact, and it is often the most interesting thing on the form:
it is what tells you the floor and the wall belong to one building.

Every edge in the Harris schema is younger-to-older. A correlation asserts
sameness, not contact. **There is nowhere for an abutment to go.**

The fixture records all three anyway, under `stratigraphy.abutments`, with a
note saying why they are there and not in the matrix. The test suite checks
that none of them has leaked in as an ordering relationship in either
direction. This is the honest option: the alternative is a matrix that silently
knows less than the paperwork it came from, with nothing to say so.

## What the sequence says

Reading the collapsed graph from youngest to oldest:

```text
Locus 1                    topsoil and an old spoil heap
Locus 2                    the deposit above the structure
Locus 3 = Locus 6          the floor, and the sounding through it
Locus 4, Locus 5           the wall and the cobbles, both under Locus 2
Locus 7                    beneath the floor
Locus 8                    unexcavated
```

Loci 4 and 5 are terminal: nothing was excavated beneath them, because both
were left standing. They are not *isolated* — each has an edge from Locus 2 —
but the matrix stops there, and it stops there because the excavation did.

Locus 8 is terminal for the same reason, one season later. An unexcavated locus
at the bottom of a matrix is not an untidy end; it is the record correctly
declining to describe ground nobody has looked at.

## Where the forms contradict each other

Two problems in T905's paperwork are worth knowing about because they are the
kinds that recur.

**`PREVIOUS` and `FOLLOWING` are used in opposite directions on different
forms.** Locus 3's form gives previous loci 1, 2 and following loci 8, 7 —
*previous* meaning stratigraphically above, that is, later in time. Locus 4's
form gives previous loci 6, 7, 8 and following loci 1, 2, which is exactly the
reverse. Locus 6's form follows Locus 4's convention.

Read literally, the two conventions together produce a **cycle**, which the
validator would reject outright. Only `OVERLIES`, `UNDERLIES` and `EQUAL TO`
are used here, and those are consistent across every form. Where a form has
two ways of saying the same thing and one of them is ambiguous, use the other
one.

**The tracking spreadsheet says the locus forms are complete.** Four of the
eight have blank coordinate tables, and the date and Munsell fields are blank
on the forms for loci 1 to 5. Every one of those values exists in the daily
log, so nothing is actually lost — but a completeness flag records that
somebody ticked a box, not what is on the page.

## Related

- [Build and review a Harris Matrix](../workflows/harris-matrix.md) — the tool, its error codes, and its limits
- [Harris matrix](../archaeology/harris-matrix.md) and [correlation](../archaeology/correlation.md)
- [Stratigraphic relationships](../archaeology/stratigraphic-relationships.md)
- [The sounding](the-sounding.md) — loci 6, 7 and 8 as measured surfaces
