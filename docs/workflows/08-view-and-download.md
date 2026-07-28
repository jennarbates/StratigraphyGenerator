---
title: View and download
audience: beginner
status: current
source_files:
  - poggio_webapp/static/visualizer/view.js
  - poggio_webapp/static/visualizer/model3d.js
  - poggio_webapp/static/model3d-viewer.js
  - poggio_webapp/static/app/stages/visualize.js
  - poggio_webapp/backend/routes/pages.py
verified_against: 09ad663
---

# View and download

Review either the traced 2D drawing or the completed GemPy boundary surfaces,
then save the extraction data for later review.

> [!warning]
> The visualizer is a review aid, not a scientifically authoritative
> reconstruction. Retain the extraction provenance, replace placeholder
> registration with surveyed coordinates, read validation warnings, and note
> that a surface constrained by one face is interpolated across the entire
> model extent.

## Before you start

You need a traced extraction for 2D review, a completed GemPy viewer manifest
for 3D review, or both. Open the interactive view from **View and download**.
A completed job opened at `/visualizer?job=<job_id>` starts in 3D when a valid
surface model is available.

## Do this

1. Choose **2D drawing** to inspect extraction geometry.
   - Switch faces with the face tabs.
   - Overlay the source image and check its calibration or adjustable
     approximate alignment.
   - Use A/B comparison to compare two extraction runs for the same face.
2. Choose **3D model** to inspect all exported GemPy boundary surfaces.
   - Drag to orbit, use the wheel or pinch to zoom, and right-drag or the
     platform-equivalent gesture to pan.
   - Show or hide each named surface, or use **Show all** and **Hide all**.
   - Adjust opacity, toggle wireframe, and show or hide axes and bounds.
   - Use **Reset**, **Top**, **Front**, **Side**, and **3D** camera views.
     The model is Z-up and axis units are metres.
3. Download the traced JSON or model artifacts that you need. The 2D and 3D
   modes do not edit either source.

## What the application creates

- An interactive 2D view of the current extraction, when one exists.
- An interactive 3D view of every readable surface named by the completed
  model's durable manifest, when one exists.
- A downloaded JSON file containing the traced data for the current job.
- Optional side-by-side comparison views for two runs.

The saved-job results page and the interactive visualizer share the same OBJ
renderer. Three.js `0.185.1`, OrbitControls, and OBJLoader are served from
local pinned files, so the viewer does not need a JavaScript CDN at runtime.

## Check your result

- In 2D, you can switch faces, compare runs, and explain the overlay alignment.
- In 3D, every expected surface is listed and visible, Z points up, and the
  model is neither mirrored nor flattened.
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

## Under the hood

The 2D path reads extraction JSON and draws face-local geometry. The 3D path
reads the safe `model3d` data returned by the job's `visualizer-files`
endpoint, then loads each OBJ independently. Surface labels and partial-load
failures are announced in an accessible live region. Switching modes keeps
2D controls separate from 3D controls and avoids duplicate WebGL canvases.

Phase A displays interpolated **boundary surfaces**. Although the builder also
saves `trench_model_lith_block.npz`, this viewer does not display the solid
lithology volume or voxel cells.

## Next

Use [Log a find](logging-finds.md) if you want to record an artifact independently of the stratigraphic geometry.
