---
title: View and download
audience: beginner
status: current
source_files:
  - poggio_webapp/static/visualizer/view.js
  - poggio_webapp/static/visualizer/model3d.js
  - poggio_webapp/static/visualizer/volume3d.js
  - poggio_webapp/static/visualizer/volume3d-core.mjs
  - poggio_webapp/static/model3d-viewer.js
  - poggio_webapp/static/app/stages/visualize.js
  - poggio_webapp/backend/routes/pages.py
verified_against: 15173f2
---

# View and download

Review the traced 2D drawing, interpolated GemPy boundary surfaces, or
classified GemPy volume cells, then save the extraction data for later
review.

!!! warning

    The visualizer is a review aid, not a scientifically authoritative reconstruction. Retain the extraction provenance, replace placeholder registration with surveyed coordinates, read validation warnings, and note that a surface constrained by one face is interpolated across the entire model extent.

## Before you start

You need a traced extraction for 2D review, a completed GemPy viewer manifest
for 3D review, or both. The optional manifest `volume` entry makes
**Lithology volume** available. Open the interactive view from
**View and download**. A completed job opened at
`/visualizer?job=<job_id>` starts in 3D when a valid model is available.

## Do this

1. Choose **2D drawing** to inspect extraction geometry.
   - Switch faces with the face tabs.
   - Overlay the source image and check its calibration or adjustable
     approximate alignment.
   - Use A/B comparison to compare two extraction runs for the same face.
2. Choose **3D model**, then **Surfaces**, to inspect all exported GemPy
   boundary surfaces.
   - Drag to orbit, use the wheel or pinch to zoom, and right-drag or the
     platform-equivalent gesture to pan.
   - Show or hide each named surface, or use **Show all** and **Hide all**.
   - Adjust opacity, toggle wireframe, and show or hide axes and bounds.
   - Use **Reset**, **Top**, **Front**, **Side**, and **3D** camera views.
     The model is Z-up and axis units are metres.
3. Choose **Lithology volume** to inspect the regular-grid classifications.
   - Show or hide each lithology ID.
   - Move **X maximum**, **Y maximum**, or **Z maximum** to retain cells from
     index `0` through the selected index, inclusive. The three limits apply
     together, so the visible result is an origin-anchored sub-volume.
   - Use the matching Side, Front, or Top camera to read the selected X, Y,
     or Z outer face as a cross-section.
     Side looks from `+X` toward `-X`, Front from `+Y` toward `-Y`, and Top
     from `+Z` toward `-Z`. With Z kept upright, Front therefore places `+X`
     toward screen-left; use the axis helper when comparing it with a GemPy
     plot whose horizontal X axis increases to the right.
   - Choose **Reset slices** to restore all cells.
4. Download the traced JSON or model artifacts that you need. The 2D and 3D
   modes do not edit either source.

## What the application creates

- An interactive 2D view of the current extraction, when one exists.
- An interactive 3D view of every readable surface named by the completed
  model's durable manifest, when one exists.
- An optional classified-cell volume when the manifest contains a readable
  browser binary and supported volume metadata.
- A downloaded JSON file containing the traced data for the current job.
- Optional side-by-side comparison views for two runs.

The saved-job results page and the interactive visualizer share the same OBJ
renderer. Three.js `0.185.1`, OrbitControls, and OBJLoader are served from
local pinned files, so the viewer does not need a JavaScript CDN at runtime.

## Check your result

- In 2D, you can switch faces, compare runs, and explain the overlay alignment.
- In 3D, every expected surface is listed and visible, Z points up, and the
  model is neither mirrored nor flattened.
- In volume mode, the displayed shape matches the manifest resolution, every
  expected ID is listed, and X/Y/Z slices agree with GemPy reference sections.
- Orbit, zoom, pan, layer visibility, opacity, wireframe, camera views, and
  resize all work.
- Page source and API JSON expose no server filesystem paths, and browser
  networking shows no Three.js CDN request.
- The download you choose contains either traced data or the named model
  artifact; viewing does not silently convert one format into the other.

## Common problems

- The visualizer shows no drawable points because the extraction has empty or non-numeric coordinates.
- The overlay does not appear because there is no source-image calibration.
- A comparison view is confusing because the two runs are not the same face or the same dataset.
- A missing or invalid viewer manifest leaves the existing 2D visualizer
  available and hides 3D mode.
- If one OBJ cannot load, the status region names that surface while keeping
  successfully loaded surfaces usable.
- If every OBJ fails or WebGL is unavailable, the viewer shows a recoverable
  error. Return to 2D or download the job files for inspection.
- If **Lithology volume** is absent, the manifest has no supported readable
  volume binary; surface mode remains available.

![The same model as smooth interpolated surfaces and as resolution-dependent classified cells](../assets/diagrams/w08-surface-vs-volume.svg)

*Two views of one model. Volume cells depend on grid resolution; surfaces do not.*

## Under the hood

The 2D path reads extraction JSON and draws face-local geometry. The 3D path
reads the safe `model3d` data returned by the job's `visualizer-files`
endpoint. Surface mode loads each OBJ independently. Volume mode fetches the
raw little-endian `uint16` browser binary and creates one `InstancedMesh` per
lithology ID. Switching representation disposes the inactive renderer and
avoids duplicate WebGL canvases.

Interpolated boundary **surfaces** are triangle geometry located at geological
contacts. Classified **volume cells** occupy the regular-grid cells described
by the model extent and resolution. They are discrete, resolution-dependent
samples, not smooth closed geological solids. Unknown IDs are shown
conservatively as `Lithology <id>`; they are never named from surface order,
and ID `0` is not assumed to mean empty space.

The default `50 × 50 × 30` grid contains 75,000 instances and is the supported
performance gate. Slice rebuilds target less than 200 ms on the review
machine. A raw binary uses two bytes per cell, and instance count, memory, and
slice work grow with `nx × ny × nz`; larger volumes may not remain interactive.

## Next

Use [Log a find](logging-finds.md) if you want to record an artifact independently of the stratigraphic geometry.
