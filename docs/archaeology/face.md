---
title: Face
audience: beginner
status: current
source_files:
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/merge_walls.py
  - poggio_webapp/pipeline/build_gempy.py
verified_against: 636b160
---

# Face

The modelled representation of one trench wall: a named plane with its own
local coordinate system and its own surveyed placement. Where a
[wall](wall-and-baulk.md) is soil, a face is data.

## What it is

A face is the unit the application computes with. It carries:

- a **name**, which must be unique within a merged document;
- a **local coordinate system** — distance along the face, and depth down from
  its top edge;
- a **[grid registration](grid-registration.md)** placing that local system in
  site coordinates;
- a list of **layers**, each with boundaries.

The local system is what makes a face useful. Measurements taken off a drawing
are naturally "so far along, so far down." Converting to site coordinates
happens once, at the end, using four registered values.

An illustrated sheet can carry several faces. A field sheet carries exactly one.

## The picture

```mermaid
flowchart LR
  P["pixels on the drawing"] -->|"calibration"| L["face-local metres<br/>(x along, depth down)"]
  L -->|"registration:<br/>originX, originY, surfaceZ, bearing_deg"| S["site coordinates<br/>(X, Y, Z)"]
  S --> M["one model, all faces together"]
```

The face is the middle box — and it is where nearly all the recorded data lives.

## Why the model needs it

A drawing has no idea where it is in the world. It records shape and scale
relative to its own edge. Something has to say where that edge sits, which way
it points, and how high it is.

Splitting that into two steps is deliberate:

**Tracing** produces face-local metres and needs only the drawing and one real
measurement. It can be done indoors, months later, by someone who never visited
the site.

**Registration** produces site coordinates and needs survey data. It is a
separate act, by a different person, from different evidence.

Keeping them apart means a mistake in one does not contaminate the other, and a
face can be re-registered without re-tracing.

## How this project stores it

Face geometry, in the extraction document:

```json
{
  "trenchProfiles": [
    {
      "face": "southern baulk",
      "layers": [
        {
          "layerName": "Locus 2 (10YR 5/6 yellowish brown)",
          "bottomBoundary": [
            { "xCoordinateMeters": 0.0, "depthMeters": 0.31 },
            { "xCoordinateMeters": 0.85, "depthMeters": 0.38 }
          ]
        }
      ]
    }
  ]
}
```

Face registration, in the grid config, keyed by the same name:

```json
{
  "faces": {
    "southern baulk": {
      "originX": 512.30,
      "originY": 1043.75,
      "surfaceZ": 271.44,
      "bearing_deg": 92.5
    }
  }
}
```

The `_comment` in a generated starter config defines each term:

> bearing_deg = compass direction (clockwise from north) that the face's local
> +x axis points. originX/Y = site coords of the face's x=0 edge. surfaceZ =
> ground-surface elevation at that edge.

### The conversion

`poggio_webapp/pipeline/convert_coords.py`:

```python
X0, Y0 = cfg["originX"], cfg["originY"]
Z0 = cfg["surfaceZ"]
th = math.radians(cfg["bearing_deg"])
sin_t, cos_t = math.sin(th), math.cos(th)

def to_site(x, depth, X0=X0, Y0=Y0, Z0=Z0, sin_t=sin_t, cos_t=cos_t):
    X = X0 + x * sin_t
    Y = Y0 + x * cos_t
    Z = Z0 - depth
    return X, Y, Z
```

`sin` on X and `cos` on Y because the bearing is a
[compass angle](bearing-and-azimuth.md). `Z = Z0 − depth` because depth runs
down and elevation runs up.

### A missing face is fatal

```python
cfg = faces_cfg.get(fname)
if cfg is None:
    missing.append(fname)
    continue
```

and the caller refuses:

```python
raise TrenchBuildError(
    "the grid config has no entry for these faces: "
    + ", ".join(repr(name) for name in conversion["missing_faces"])
    + " -- they would be dropped from the model")
```

Silently dropping a wall would produce a model missing a quarter of its evidence
and looking complete.

### Face names must be unique — GemPy fuses by string match

`poggio_webapp/pipeline/merge_walls.py` prefixes colliding names:

```python
new_name = f"{e['wall_label']}: {e['name']}"
notes.append(f"sheet {e['wall_label']!r}: face "
             f"{e['name']!r} collides with a face from "
             f"another sheet -- renamed to {new_name!r}")
```

and raises if any duplicate survives:

```python
raise ValueError("duplicate face names after merge: "
                 + ", ".join(repr(d) for d in duplicates))
```

The face name also travels into the model output, so a reader can tell which
wall a point came from:

```python
rows.append({"X": ..., "Y": ..., "Z": ..., "surface": surface, "face": fname})
```

which is what lets `build_gempy.wall_traces()` draw the recorded evidence over
the interpolated surfaces.

## What it is not

| Not a… | Because |
|---|---|
| **[Wall](wall-and-baulk.md)** | The wall is soil; the face is its data representation. In practice the wall label becomes the face name. |
| **[Trench profile](trench-profile.md)** | The profile is the paper drawing. The face is what the drawing becomes. |
| **Surface** | In GemPy a *surface* is a stratigraphic interface spanning faces. A face is a wall. One surface appears on several faces. |
| **[Site coordinates](site-coordinates.md)** | A face has its own local system; site coordinates are the shared one it maps into. |
| **Plane in the model** | The face's *data* is a plane's worth of points. The model interpolates away from it in three dimensions. |

## Getting it wrong

**Naming two faces the same.** Merging prefixes them; a surviving duplicate
raises. Within one sheet, two identically named faces are a data error.

**Leaving the registration at the starter values.** `0, 0, 100, 90` is a
smoke-test placeholder. A merged build refuses; a single-sheet build accepts it,
and nothing marks the resulting model as unsurveyed. This is the project's
stated principal limitation.

**Confusing the face's origin with the trench's corner.** `originX/Y` is the site
position of the face's **x = 0 edge** — where you started measuring — which is
not necessarily a trench corner.

**Assuming the face is vertical.** The model treats depth as straight down from
`surfaceZ`. A wall cut at a batter is not modelled as such.

**Expecting one face to constrain a 3D model.** It cannot. A single face is
extrapolated across the whole extent:

> These surfaces have points from only ONE face and will still be interpolated
> across the whole model extent

## Related pages

- [Wall and baulk](wall-and-baulk.md) — the physical thing.
- [Grid registration](grid-registration.md) — the four values.
- [Site coordinates](site-coordinates.md) — the target system.
- [Bearing and azimuth](bearing-and-azimuth.md) — the compass convention.
- [Interface point](interface-point.md) — what a face's boundaries become.
- [Coordinate spaces](../concepts/coordinate-spaces.md) — the three spaces.
- [Place on site](../workflows/06-place-on-site.md) — the workflow step.
