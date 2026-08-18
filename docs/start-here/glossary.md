---
title: Glossary
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/extract_fieldwall.py
  - poggio_webapp/pipeline/extract_illustrator.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/editor/schema.py
  - poggio_webapp/naming.py
  - poggio_webapp/pipeline/site_vocab.py
  - poggio_webapp/pipeline/series_order.py
  - poggio_webapp/pipeline/trench_layout.py
  - poggio_webapp/backend/services/trench_builder.py
verified_against: ae2fc1d
---

# Glossary

This glossary defines the archaeological, geometric, and application terms
used in the guide without requiring knowledge of the source code.

![A labelled trench section naming the trench, wall, face, locus, layer, boundary, and feature](../assets/diagrams/glossary-anatomy.svg)

*Most glossary terms are visible on one section. This is that section.*

## Why it matters here

The project translates a drawing made for archaeological recording into
coordinates and structured data. Similar words can refer to different kinds
of evidence: a marker is not a feature, a feature is not a find, and a layer
is not always named in the same way as a locus.

Use these definitions to understand what the application asks you to record.
They do not replace project-specific recording conventions or expert
archaeological review.

## Example

**Synthetic documentation example:** a profile drawing shows two soil layers
on one face. The boundary between them contains several measured markers, a
stone is drawn as a feature inside the lower layer, and a pottery find was
recorded separately for the same locus. Calibration turns positions on the
image into metres; grid registration later places those local measurements in
the site's coordinate system.

This example is invented for documentation and is not archaeological evidence.

## How the repository represents it

Each term below closes with an **In depth** line. The glossary gives you the
paragraph you want while working; those pages give the archaeological reasoning,
the exact schema field, and (the part that causes most trouble) the
neighbouring term each one is confused with. The full set is the
[archaeology reference](../archaeology/index.md).

### Boundary

An ordered line of measured or traced points that separates stratigraphic
units. A layer or locus can have a top boundary and a bottom boundary. On a
field sheet, the named top of the next locus also closes the locus above it;
the deepest locus needs a separate final base line.

*In depth: [Boundary](../archaeology/boundary.md)*
### Calibration

The step that connects distances on an image to distances in metres. In the
manual tracer, a person identifies reference points on the drawing and
supplies the known real distance between them. The resulting scale converts
later clicks from image pixels into face-local measurements. Calibration does
not place the face in the site coordinate system; that is grid registration.

*In depth: [Scale and DPI](../archaeology/scale-and-dpi.md) · [Similarity transforms](../cs/similarity-transforms.md)*
### Face

One vertical wall or named side represented by a trench profile. Measurements
along a face use their own local horizontal starting point. An illustrated
diagram can contain multiple faces, while a field-wall record represents one
wall; the primary upload tracer creates one face per drawing.

*In depth: [Face](../archaeology/face.md)*
### Feature

A discrete object or shape drawn within a stratigraphic unit, such as a stone,
cut, lens, or void. A feature may be stored as a traced outline or an
approximate box and belongs to one layer or locus. It does not define the
layer boundary.

*In depth: [Feature](../archaeology/feature.md)*
### Find

A record of a recovered artifact, with information such as face, local
position, elevation, locus, and description. Finds are stored with a job and
can exist independently of finalized stratigraphy. A find is not a point in a
boundary and is not a drawn feature.

*In depth: [Find](../archaeology/find.md) · [Find identifiers](../archaeology/find-identifiers.md)*
### GemPy

An optional Python library that the project can use to interpolate a
geological model from interface points and orientation seeds. GemPy and
`gempy_viewer` are not part of the core installation, and the current model
build is `experimental`. A computed model is not proof that its input geometry
or archaeological interpretation is correct.

*In depth: [Spatial interpolation and kriging](../cs/spatial-interpolation-and-kriging.md) · [Interpolation versus measurement](../cs/interpolation-vs-measurement.md)*
### Grid registration

The surveyed placement of each face in the wider site coordinate system. The
application asks for the site grid coordinates of the face's local origin
(South and West negative, so `190E/53S` is `originX 190`, `originY -53`), the
ground-surface elevation there in mAE, and the bearing of the face's positive
horizontal direction in degrees clockwise from **Grid North**, not magnetic
north. Generated starter values are placeholders, declare themselves as such,
and must be replaced with real survey values from the master Geospatial
Spreadsheet before scientific use.

*In depth: [Grid registration](../archaeology/grid-registration.md) · [Site coordinates](../archaeology/site-coordinates.md)*
### Interface point

A site-coordinate point on a named stratigraphic surface. Coordinate
conversion turns selected boundary points into interface points with `X`,
`Y`, and `Z` positions. GemPy uses groups of these points to estimate where a
surface passes through the model.

*In depth: [Interface point](../archaeology/interface-point.md)*
### Job

One local working session and its saved files. Starting work creates a job
directory containing source copies, derived images, structured data, reports,
and later outputs as they become available. Jobs persist on local disk, while
the status of a currently running asynchronous task is held only in the
server process.

*In depth: [Jobs, sheets, and trenches](../concepts/jobs-sheets-and-trenches.md)*
### Layer

A band or unit shown between boundaries in a trench profile. In illustrated
drawings, a layer can have a name, material description, visual pattern, and
features. On a field sheet, the corresponding unit is associated with a locus
number and Munsell soil-colour information.

*In depth: [Layer](../archaeology/layer.md)*
### Locus

An excavation recording identifier for a context or stratigraphic unit. In
this project's field-sheet data, a locus has a number and may have a Munsell
soil-colour record and description. A locus's named line is its top boundary;
it should not be shifted to the boundary below.

A locus is identified by its **trench and number**: `T104`, Locus 6. The
Munsell reading is an attribute of the locus, not part of its name: readings of
one deposit differ legitimately between recorders and between wet and dry soil.
Locus numbers are entered as the bare number, `5`, never `" 5 "`.

That distinction reaches the model. A locus becomes a GemPy **surface** named
`Locus 6`, and the colour rides alongside as a display label,
`Locus 6 (10YR 5/3 brown)`. The viewer shows the label; everything that has to
match (fusing two walls into one surface, stratigraphic order, mesh files)
uses the identity.

*In depth: [Locus](../archaeology/locus.md)*
### Locus epoch

Which run of locus numbering a job belongs to. A trench reopened in consecutive
years **continues** its numbering (if last year ended at Locus 10, this year
starts at Locus 11), but a trench reopened after a gap may restart, and an
administratively new trench over older ones restarts at Locus 1.

So the same number can mean one deposit or two, depending on the trench's
history. The application cannot work that out, so where sheets span
non-consecutive seasons it asks for the epoch rather than guessing. Consecutive
seasons need no epoch.

*In depth: [Locus numbering epochs](../archaeology/locus-numbering-epochs.md)*
### Marker

A small deliberate dot on a field recording sheet at a measured boundary
vertex. Markers collectively describe boundary geometry; they are not stones,
features, or finds. Automated marker detection and assignment is currently
`backend-only`, so beginners should trace field-sheet boundaries manually.

*In depth: [Marker](../archaeology/marker.md)*
### Normalization

Automated cleanup that makes structured drawing data more consistent before
later processing. It can standardize null-like values and remove certain
duplicate or misplaced entries. Normalization does not verify the source
drawing, supply missing survey evidence, or guarantee a correct
interpretation.

*In depth: [Pipeline walkthrough](../architecture/pipeline-walkthrough.md)*
### Orientation seed

A site-coordinate point paired with a dip and compass direction that guides
the model's estimate of a surface's orientation. The project derives one seed
for a usable boundary from the best-fit slope across its points and the
registered face bearing. It is a modeling input, not an independently
surveyed orientation measurement.

*In depth: [Orientation seed](../archaeology/orientation-seed.md) · [Apparent and true dip](../archaeology/apparent-and-true-dip.md)*
### Season

The four-digit excavation year a sheet belongs to, as it appears between the
trench and the locus in the site's find codes: `sf-T104-2025-6-1`. Recorded on
every job that has one, and used to decide whether locus numbering is
continuous (see **locus epoch**). It is not part of a locus's identity.

*In depth: [Locus numbering epochs](../archaeology/locus-numbering-epochs.md) · [Find identifiers](../archaeology/find-identifiers.md)*
### Stratigraphic order

The young-to-old sequence of surfaces a model is built from. Three sources can
supply it, and they are not equally trustworthy:

1. A Harris matrix: the excavation's own record of which deposit lies
   above which. Preferred whenever one exists for the trench.
2. The recorded layer sequence: each wall's layers are drawn top to
   bottom, so adjacent pairs are constraints. Real evidence, but only about
   what one wall saw.
3. Mean elevation: an assumption that higher means younger. This site's
   procedures record cases where it is false: *"stratigraphically newer
   deposits may exist at lower elevations than stratigraphically older
   deposits"*. A model ordered this way says so, in the build log and in the
   viewer.

Some deposits have **no** order relative to each other: either side of a wall,
for instance, excavated at the same level. A Harris matrix represents that by
having no relationship between them; a model cannot, because it needs a total
order. Where an order was imposed on unordered deposits, the model records
which pairs, because that boundary is not evidence.

*In depth: [Stratigraphic relationships](../archaeology/stratigraphic-relationships.md) · [Harris matrix](../archaeology/harris-matrix.md) · [Law of superposition](../archaeology/law-of-superposition.md)*
### Trench layout

The trenchbook section recording how a trench was set out: its opening
dimensions, the grid coordinates of its four corners, how it was sited off a
baseline, and the location and elevation of its datum nail.

Those corner coordinates are the same numbers grid registration needs, so the
application can derive a registration from them instead of asking anyone to
work out a bearing. A layout is refused if its corners describe a self-crossing
shape. Two labels transposed makes a bow-tie, which is a valid polygon but not
a trench.

*In depth: [Grid registration](../archaeology/grid-registration.md) · [Datum](../archaeology/datum.md)*
### Trench

The excavated pit, and the unit every other identifier hangs off. Written the
way the site records it: the property abbreviation followed by the number with
no space or punctuation: `T104`, not `T-104` or `T 104`. The application reads
all three spellings as the same trench, because drawings and database records
already disagree: the T104 field sheets are titled "T-104" while the Open
Context records read "T104".

*In depth: [Trench](../archaeology/trench.md)*
### Trench profile

A side-view drawing of a vertical trench wall that records the visible
sequence and shape of stratigraphic units. It may be a polished illustrated
sheet or a hand-drawn field record. The profile is a two-dimensional source;
placing it on the site and modeling between surfaces require additional
coordinate information.

*In depth: [Trench profile](../archaeology/trench-profile.md) · [Recording sheet](../archaeology/recording-sheet.md)*
### Validation

Automated checks on structured drawing data. The validator reports errors
that block a required next step and warnings that call for review. A report
can pass with warnings, so validation is evidence of data consistency, not
scientific approval.

*In depth: [Error taxonomies](../cs/error-taxonomies.md) · [Validation rules](../reference/validation-rules.md)*
## Related concepts

- [Archaeology reference](../archaeology/index.md): every term above, in depth,
  with what it is *not*.
- [What this project does](what-this-project-does.md) puts the terms into the
  overall drawing-to-data process.
- [Markers, features, and finds](../concepts/markers-features-and-finds.md)
  compares those three records in more depth.
- [Geometric normalization](../concepts/geometric-normalization.md) explains
  image rotation and measurement geometry.
- [Current capability status](../project/capability-status.md) records which
  related features are available in the live application.
