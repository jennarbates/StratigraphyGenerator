---
title: Coordinate spaces
audience: beginner
status: current
source_files:
  - docs/workflows/03-trace-layers.md
  - docs/workflows/06-place-on-site.md
  - docs/workflows/07-create-model.md
  - poggio_webapp/pipeline/convert_coords.py
verified_against: a8b58f1
---

# Coordinate spaces

Coordinate spaces are the different ways the project describes where a point is: first in the drawing image, then in the face-local reference frame, and finally in the wider site coordinate system.

## Why it matters here

A point can be correct in one coordinate space and still be meaningless in another. The tracing step works in image pixels, the later registration step works in a local face frame, and the model step works in site-wide coordinates. Mixing these spaces would produce a model with the wrong geometry even if the drawing still looks sensible.

This concept matters because beginners often assume that a point in the drawing image is already the same thing as a point in the site grid. It is not.

## Example

Synthetic documentation example: a boundary point is first clicked in the image, then converted from pixels into local metres during tracing, and finally turned into a site-wide coordinate after registration. Each conversion changes the meaning of the measurement, but the point still refers to the same feature in the real world.

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

The bearing is interpreted as clockwise from north. Degrees are converted to radians before the trigonometry is applied. The formula itself stays the same.

## Related concepts

- [From archaeology to 3D](archaeology-to-3d.md) shows how coordinate conversion supports the model build.
- [Layers and boundaries](layers-and-boundaries.md) explains what gets turned into points.
- [Accuracy and provenance](accuracy-and-provenance.md) explains how to judge the reliability of the converted values.
- Workflows: [Trace the layers](../workflows/03-trace-layers.md), [Place on site](../workflows/06-place-on-site.md), [Create the model](../workflows/07-create-model.md), and the [Glossary](../start-here/glossary.md).
