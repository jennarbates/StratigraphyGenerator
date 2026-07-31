---
title: Coordinate spaces
audience: beginner
status: current
source_files:
  - docs/workflows/03-trace-layers.md
  - docs/workflows/06-place-on-site.md
  - docs/workflows/07-create-model.md
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/site_grid.py
  - poggio_webapp/pipeline/site_elevation.py
verified_against: 636b160
---

# Coordinate spaces

Coordinate spaces are the different ways the project describes where a point is: first in the drawing image, then in the face-local reference frame, and finally in the wider site coordinate system.

![One point plotted in pixel coordinates, in face-local metres, and in site coordinates, with the conversion between each](../assets/diagrams/three-coordinate-spaces.svg)

*The same point in all three spaces. Most confusion here is a space mix-up.*

## Why it matters here

A point can be correct in one coordinate space and still be meaningless in another. The tracing step works in image pixels, the later registration step works in a local face frame, and the model step works in site-wide coordinates. Mixing these spaces would produce a model with the wrong geometry even if the drawing still looks sensible.

This concept matters because beginners often assume that a point in the drawing image is already the same thing as a point in the site grid. It is not.

![A drawing with three numbered calibration points and the real-world distance between the first two](../assets/diagrams/w03-calibration-clicks.svg)

*Three clicks plus one real measurement convert pixels into metres.*

## Try it

<div class="pc-interactive" data-pc-converter markdown="1">

A worked example, using the synthetic fixture. With JavaScript enabled, a
converter appears above this table and these values become editable.

| Space | Value |
|---|---|
| Pixel | `(760, 520)` |
| Calibration | clicks at `(220, 180)` and `(1180, 196)`, 4 m apart; lowest click `(700, 900)` |
| Face-local metres | `x = 2.273 m`, `depth = 1.3788 m` |
| Registration | `originX 0`, `originY 0`, `surfaceZ 100`, `bearing_deg 90` |
| Site coordinates | `X = 2.273`, `Y = 0.0`, `Z = 98.6212` |

At `bearing_deg 90` the face runs due east, so all displacement lands in `X`
and `Y` stays at the origin. The scale here is 240.0333 pixels per metre.

</div>

## Example

Synthetic documentation example: a boundary point is first clicked in the image, then converted from pixels into local metres during tracing, and finally turned into a site-wide coordinate after registration. Each conversion changes the meaning of the measurement, but the point still refers to the same feature in the real world.

![A trench face annotated with originX, originY, surfaceZ, and bearing measured clockwise from north](../assets/diagrams/w06-registration-fields.svg)

*Four numbers place a face on the site. Bearing is clockwise from Grid North.*

## How the repository represents it

The repository uses three levels of coordinates:

- Pixel coordinates in the image during tracing.
- Section-local coordinates after calibration, where distances are expressed in metres relative to the face.
- Site-wide coordinates after registration, using the face origin, surface elevation, and bearing.

The conversion formula used in the repository is:

```text
X = originX + x * sin(bearing)
Y = originY + x * cos(bearing)
Z = surfaceZ - depth
```

The bearing is interpreted as clockwise from **Grid North**. Degrees are converted to radians before the trigonometry is applied. The formula itself stays the same.

## The site frame these coordinates live in

Site-wide coordinates in this application are Poggio Civitate **local site grid**
coordinates. They are not GPS, WGS84 or UTM, and no conversion sits between the two:
model `X` is grid easting and model `Y` is grid northing, both in metres.

Four things follow, and each of them changes what you should type into a grid config.

**Grid North is not north.** The site is oriented to an artificial reference
direction. The total station sets it as horizontal angle 0 — 90 East, 180 South,
270 West — and `bearing_deg` uses the same convention. Grid North sits about 2.5°
off projected north, so a bearing read from a magnetic compass is wrong by more
than rounding.

**South and West are negative.** The site's sign rule is that North and East are
positive, South and West negative. A corner labelled `190E/53S` is
`originX 190`, `originY -53`. Getting this backwards mirrors the whole site
north-to-south while leaving every distance and slope internally consistent, so
nothing downstream can catch it.

**There are two local grids** — the hill of Poggio Civitate and Vescovado di
Murlo — so a pair of coordinates is not a location until the grid is named. Their
origins are about 1.5 million metres apart once projected. The grid config carries
a `site_grid` field for this, and a trench whose sheets disagree is refused.

**Elevations are mAE — "meters absolute elevation".** Values at this site are in
the twenties; `surfaceZ 100` in the worked example above is a placeholder, not a
plausible reading. Field measurements are taken *below datum* from a nail near the
trench and converted to absolute elevation for the record, so a grid config can
declare either form. A below-datum config with no recorded datum elevation is
refused rather than defaulted to zero.

For export, the local grid can be projected to Monte Mario 1 (EPSG:3003) using the
affine the project publishes for each grid. That is an output step; nothing in the
model build leaves the local frame.

## Related concepts

- [From archaeology to 3D](archaeology-to-3d.md) shows how coordinate conversion supports the model build.
- [Layers and boundaries](layers-and-boundaries.md) explains what gets turned into points.
- [Accuracy and provenance](accuracy-and-provenance.md) explains how to judge the reliability of the converted values.
- Workflows: [Trace the layers](../workflows/03-trace-layers.md), [Place on site](../workflows/06-place-on-site.md), [Create the model](../workflows/07-create-model.md), and the [Glossary](../start-here/glossary.md).
