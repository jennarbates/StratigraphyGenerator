---
title: Place on site
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/static/app/stages/convert.js
verified_against: a8b58f1
---

# Place on site

Turn the cleaned extraction into site-wide coordinates before you build a model.

> [!warning]
> Synthetic documentation example only. The values below are placeholder smoke-test values and are not a surveyed registration. Do not treat them as a scientific result.

## Before you start

You should already have a cleaned extraction and a face name. This step is the handoff from the drawing to the site-coordinate system used by the model builder.

The four registration fields are:

- `originX`: the site coordinate of the face's local $x = 0$ edge.
- `originY`: the site coordinate of the same edge on the perpendicular axis.
- `surfaceZ`: the ground-surface elevation at that edge.
- `bearing_deg`: the clockwise-from-north direction of the face's local $+x$ axis.

## Do this

1. Open the registration step after validation.
   - Action: enter the four values for each face.
   - Artifact: a grid-registration entry stored with the job.
2. Use the repository's coordinate formula exactly as implemented in the converter.

```text
X = originX + x * sin(bearing)
Y = originY + x * cos(bearing)
Z = surfaceZ - depth
```

The bearing is clockwise from north. Convert degrees to radians before applying the formula; the formula itself stays the same.

3. Continue to conversion.
   - Artifact: a `points.csv` file and a `points_orientations.csv` file for the job.

### Synthetic example

Use a placeholder example only for smoke testing:

```json
{
  "face": "Synthetic face",
  "originX": 0.0,
  "originY": 0.0,
  "surfaceZ": 100.0,
  "bearing_deg": 90.0
}
```

These values are for a documentation walkthrough only. Replace them with real site data before any real analysis or publication.

## What the application creates

- A registered grid configuration for the face.
- A converted point table in `points.csv`.
- A converted orientation table in `points_orientations.csv`.

## Check your result

- The registration values are complete for every face that will be modelled.
- The point and orientation exports exist in the job folder.
- You have not treated the placeholder values as a surveyed result.

## Common problems

- A field sheet has a single wall but the registration is entered as if several faces were already known.
- The bearing is entered as a slope or a visual angle rather than a compass direction clockwise from north.
- Placeholder values are left in place and later described as if they were recorded survey data.

## Under the hood

The converter in `poggio_webapp/pipeline/convert_coords.py` uses the formula above to turn face-local coordinates into site-wide coordinates. The web app exposes the registration fields in the conversion stage and writes the export files for the later model step.

## Next

Continue to [Create the model](07-create-model.md) when the registration step has produced the CSV exports.
