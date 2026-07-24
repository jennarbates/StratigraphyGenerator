---
title: Glossary
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/extract_fieldwall.py
  - poggio_webapp/pipeline/extract_illustrator.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/editor.py
verified_against: eac1f51
---

# Glossary

This glossary defines the archaeological, geometric, and application terms
used in the guide without requiring knowledge of the source code.

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

### Boundary

An ordered line of measured or traced points that separates stratigraphic
units. A layer or locus can have a top boundary and a bottom boundary. On a
field sheet, the named top of the next locus also closes the locus above it;
the deepest locus needs a separate final base line.

### Calibration

The step that connects distances on an image to distances in metres. In the
manual tracer, a person identifies reference points on the drawing and
supplies the known real distance between them. The resulting scale converts
later clicks from image pixels into face-local measurements. Calibration does
not place the face in the site coordinate system; that is grid registration.

### Face

One vertical wall or named side represented by a trench profile. Measurements
along a face use their own local horizontal starting point. An illustrated
diagram can contain multiple faces, while a field-wall record represents one
wall; the primary upload tracer creates one face per drawing.

### Feature

A discrete object or shape drawn within a stratigraphic unit, such as a stone,
cut, lens, or void. A feature may be stored as a traced outline or an
approximate box and belongs to one layer or locus. It does not define the
layer boundary.

### Find

A record of a recovered artifact, with information such as face, local
position, elevation, locus, and description. Finds are stored with a job and
can exist independently of finalized stratigraphy. A find is not a point in a
boundary and is not a drawn feature.

### GemPy

An optional Python library that the project can use to interpolate a
geological model from interface points and orientation seeds. GemPy and
`gempy_viewer` are not part of the core installation, and the current model
build is `experimental`. A computed model is not proof that its input geometry
or archaeological interpretation is correct.

### Grid registration

The surveyed placement of each face in the wider site coordinate system. The
application asks for the site coordinates of the face's local origin, the
ground-surface elevation there, and the compass bearing of the face's
positive horizontal direction. Generated starter values are placeholders and
must be replaced with real survey values before scientific use.

### Interface point

A site-coordinate point on a named stratigraphic surface. Coordinate
conversion turns selected boundary points into interface points with `X`,
`Y`, and `Z` positions. GemPy uses groups of these points to estimate where a
surface passes through the model.

### Job

One local working session and its saved files. Starting work creates a job
directory containing source copies, derived images, structured data, reports,
and later outputs as they become available. Jobs persist on local disk, while
the status of a currently running asynchronous task is held only in the
server process.

### Layer

A band or unit shown between boundaries in a trench profile. In illustrated
drawings, a layer can have a name, material description, visual pattern, and
features. On a field sheet, the corresponding unit is associated with a locus
number and Munsell soil-colour information.

### Locus

An excavation recording identifier for a context or stratigraphic unit. In
this project's field-sheet data, a locus has a number and may have a Munsell
soil-colour record and description. A locus's named line is its top boundary;
it should not be shifted to the boundary below.

### Marker

A small deliberate dot on a field recording sheet at a measured boundary
vertex. Markers collectively describe boundary geometry; they are not stones,
features, or finds. Automated marker detection and assignment is currently
`backend-only`, so beginners should trace field-sheet boundaries manually.

### Normalization

Automated cleanup that makes structured drawing data more consistent before
later processing. It can standardize null-like values and remove certain
duplicate or misplaced entries. Normalization does not verify the source
drawing, supply missing survey evidence, or guarantee a correct
interpretation.

### Orientation seed

A site-coordinate point paired with a dip and compass direction that guides
the model's estimate of a surface's orientation. The project derives one seed
for a usable boundary from the best-fit slope across its points and the
registered face bearing. It is a modeling input, not an independently
surveyed orientation measurement.

### Trench profile

A side-view drawing of a vertical trench wall that records the visible
sequence and shape of stratigraphic units. It may be a polished illustrated
sheet or a hand-drawn field record. The profile is a two-dimensional source;
placing it on the site and modeling between surfaces require additional
coordinate information.

### Validation

Automated checks on structured drawing data. The validator reports errors
that block a required next step and warnings that call for review. A report
can pass with warnings, so validation is evidence of data consistency, not
scientific approval.

## Related concepts

- [What this project does](what-this-project-does.md) puts the terms into the
  overall drawing-to-data process.
- [Markers, features, and finds](../concepts/markers-features-and-finds.md)
  compares those three records in more depth.
- [Geometric normalization](../concepts/geometric-normalization.md) explains
  image rotation and measurement geometry.
- [Current capability status](../project/capability-status.md) records which
  related features are available in the live application.
