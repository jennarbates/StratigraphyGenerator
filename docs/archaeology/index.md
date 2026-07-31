---
title: Archaeology reference
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/extract_fieldwall.py
  - poggio_webapp/pipeline/extract_illustrator.py
  - poggio_webapp/pipeline/harris_matrix.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/editor/schema.py
  - poggio_webapp/pipeline/series_order.py
  - poggio_webapp/pipeline/trench_layout.py
  - poggio_webapp/pipeline/locus_import.py
  - poggio_webapp/pipeline/provenance.py
verified_against: 40e4a0d
---

# Archaeology reference

Every archaeological term this project uses, one page each, in depth.

The [glossary](../start-here/glossary.md) gives you a paragraph per term, which
is what you want while you are working. These pages are the other thing: what
the term means in excavation practice, why the practice exists, exactly which
field in this project's data holds it, and — most importantly — which
neighbouring term it is constantly confused with.

That last part is not padding. This application makes distinctions that a
drawing does not: a **marker** is not a **feature**, a **feature** is not a
**find**, a **layer** is not always a **locus**, and an **apparent dip** is not
a **true dip**. Recording one as another produces data that validates cleanly
and means something else.

## How to read a term page

Every page has the same seven sections.

| Section | Answers |
|---|---|
| **What it is** | The definition, in plain language |
| **The picture** | Where it appears on a real trench section |
| **Why excavation records it** | The archaeological reasoning, not the software's |
| **How this project stores it** | The exact schema fields, with real JSON |
| **What it is not** | The terms it is confused with, and how to tell them apart |
| **Getting it wrong** | Common recording mistakes, and what the validator says |
| **Related pages** | Neighbouring terms and the workflow step that captures it |

## The catalogue

Thirty-seven terms. **Phasing** — grouping units into periods of activity — is
deliberately absent: it is a later interpretive step this application does not
perform, and several pages below say so where it would otherwise be assumed.

### The trench and its anatomy

- [Trench](trench.md) · [Trench profile](trench-profile.md) · [Wall and baulk](wall-and-baulk.md) · [Face](face.md)
- [Locus](locus.md) · [Layer](layer.md) · [Boundary](boundary.md) · [Cut](cut.md) · [Fill](fill.md) · [Natural](natural.md)

### Stratigraphy and chronology

- [Stratigraphy](stratigraphy.md) · [Law of superposition](law-of-superposition.md) · [Harris Matrix](harris-matrix.md)
- [Stratigraphic relationships](stratigraphic-relationships.md) · [Correlation](correlation.md) · [Locus numbering epochs](locus-numbering-epochs.md) · [Series order](series-order.md)
- [Feature](feature.md) · [Find](find.md) · [Find identifiers](find-identifiers.md) · [Marker](marker.md) · [Munsell colour](munsell-colour.md)

### Survey, measurement, and recording

- [Datum](datum.md) · [Elevation](elevation.md) · [Grid registration](grid-registration.md) · [Site coordinates](site-coordinates.md)
- [Bearing and azimuth](bearing-and-azimuth.md) · [Apparent and true dip](apparent-and-true-dip.md) · [Interface point](interface-point.md)
- [Orientation seed](orientation-seed.md) · [Survey point codes](survey-point-codes.md) · [Grid tie point](grid-tie-point.md)
- [Scale and DPI](scale-and-dpi.md) · [Recording sheet](recording-sheet.md) · [Trench layout](trench-layout.md)

### Records beyond this application

- [Kobo locus import](kobo-locus-import.md) · [Provenance links](provenance-links.md)

## Related concepts

- [Glossary](../start-here/glossary.md) — the one-paragraph version of every
  term below.
- [From archaeology to 3D](../concepts/archaeology-to-3d.md) — how these terms
  become geometry.
- [Computer science concepts](../cs/index.md) — the same treatment for the
  techniques, for readers who know the excavation and not the code.
