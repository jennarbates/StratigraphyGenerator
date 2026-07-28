# GemPy 3D Visualizer Implementation Contract

Baseline reviewed: repository commit `d5511cc`

This document is a master contract for implementing an interactive browser
viewer for the GemPy result. It is intentionally divided into small,
sequential chunks so that an AI coding agent can complete one bounded task at
a time without redesigning unrelated parts of the application.

Do not give the agent the entire implementation as one task. Give it exactly
one chunk, review the result, and run the stated gate before assigning the
next chunk.

## 1. Final user outcome

When a job has a completed GemPy model, opening
`/visualizer?job=<job_id>` must let the user:

1. Switch between the existing 2D profile view and a new 3D model view.
2. See every exported GemPy surface in the same 3D scene.
3. Rotate, zoom, and pan the scene.
4. Show or hide individual surfaces.
5. Adjust surface opacity and toggle wireframe display.
6. Reset the camera and use named top/front/side views.
7. See the model extent, axes, units, layer names, and loading/error state.
8. Continue using all existing 2D overlay and A/B comparison behavior.
9. Use the viewer without a runtime connection to a JavaScript CDN.

After the surface viewer is accepted, a second phase may add the complete
GemPy lithology block as a colored voxel volume with slice controls.

## 2. Scope definitions

### Phase A: full surface model

"Full surface model" means every surface mesh produced by the current GemPy
calculation is loaded into one interactive scene. Phase A is complete only
when all valid surfaces can be viewed together and controlled individually.

### Phase B: lithology volume

"Lithology volume" means the values from GemPy's `lith_block` are displayed
as colored 3D cells. This is a separate phase because an OBJ boundary surface
does not contain the volume between boundaries.

### Explicit non-goals

The agent must not do any of the following unless a later, separate contract
authorizes it:

- Change GemPy interpolation, series ordering, resolution defaults, or model
  extent calculation.
- Change coordinate registration or extraction schemas.
- Replace the existing 2D visualizer.
- Add editing of GemPy geometry in the browser.
- Add 3D model comparison.
- Add uploads of arbitrary third-party OBJ, GLB, VTK, or NPZ files.
- Add terrain, photogrammetry, excavation architecture, or finds to the scene.
- Add authentication, cloud storage, a database, or a task queue.
- Convert the entire frontend to a framework or introduce a general bundler.
- Remove or replace the existing 3D viewer on the saved-job results page.
- Refactor unrelated application routes or CSS.
- Implement Phase B while any Phase A acceptance test is failing.

## 3. Existing architecture the agent must preserve

- GemPy is built in
  `poggio_webapp/pipeline/build_gempy.py`.
- The builder already writes one OBJ file per surface and a NumPy
  `trench_model_lith_block.npz` file.
- Job-owned files are served through
  `GET /api/jobs/<job_id>/file?path=<relative-path>`.
- Visualizer auto-load data comes from
  `GET /api/jobs/<job_id>/visualizer-files`.
- The visualizer HTML shell is
  `poggio_webapp/static/visualizer.html`.
- Existing visualizer modules live under
  `poggio_webapp/static/visualizer/`.
- A separate, already-working OBJ viewer exists on the saved-job results page:
  - `poggio_webapp/static/viewer3d.js` contains its current renderer;
  - `poggio_webapp/templates/index.html` provides its HTML and import map;
  - `poggio_webapp/static/style.css` provides its `.viewer3d-*` styles;
  - `app.py::_job_record()` discovers `*_meshes/*.obj` and supplies
    `mesh_urls`;
  - `tests/test_editor_routes.py` covers the results-page integration.
- The existing results-page viewer is the implementation seed for the shared
  renderer. Preserve its user-facing behavior while extracting its reusable
  parts. Do not maintain two independent OBJ loading/rendering engines.
- At the reviewed baseline, the results page loads Three.js `0.169.0` from
  unpkg. Phase A replaces that runtime CDN dependency with one local pinned
  version shared by both pages.
- Existing browser-side unit tests are plain Node `.mjs` files and do not
  require a browser test framework.
- The Python test suite uses `pytest` and temporary job directories.

## 4. Master agent rules

These rules apply to every chunk.

### Before editing

The agent must:

1. Read this entire contract.
2. Read only the source files listed for its current chunk plus directly
   imported helpers needed to understand them.
3. Run `git status --short`.
4. Stop and report if an existing user change overlaps an allowed file.
5. Run the chunk's pre-change tests.
6. State the exact chunk number it is implementing.

### While editing

The agent must:

- Edit only the chunk's allowlisted files.
- Add or update the tests required by that chunk.
- Use test-first order where the chunk says "red-green test."
- Make the smallest change that satisfies the acceptance criteria.
- Preserve all existing public response keys and visualizer behavior.
- Keep reusable calculations in pure functions that can run without Flask,
  GemPy, a DOM, or WebGL wherever practical.
- Never weaken, skip, delete, or mark an existing test as expected failure.
- Never hide errors with a broad `except Exception` or empty JavaScript
  `catch`.
- Never expose absolute server paths in an API response or manifest.
- Never trust a path read from a manifest without resolving it beneath the
  job directory.
- Never load Three.js from a CDN at application runtime.
- Never guess about GemPy coordinate transforms or lithology ID/name
  mappings. Use the stop conditions below.

### After editing

The agent must:

1. Run every test listed for the chunk.
2. Run `git diff --check`.
3. Run `git status --short`.
4. Inspect `git diff -- <allowed files>`.
5. Report:
   - files changed;
   - tests added;
   - exact test commands and results;
   - acceptance criteria satisfied;
   - any assumption or unresolved risk.
6. Stop. The agent must not start the next chunk on its own.

### Universal stop conditions

The agent must stop and ask for review if:

- A required behavior conflicts with an existing test.
- GemPy's installed API differs from the API named in this contract.
- Exported vertices cannot be restored to the original model coordinate
  system.
- A path must escape the job directory to make the feature work.
- A new production dependency other than the approved pinned Three.js files
  appears necessary.
- More than two non-allowlisted production files appear necessary.
- Existing 2D visualizer behavior breaks.
- The agent cannot explain why a test is failing.

## 5. Test commands used by the gates

Run commands from the repository root.

### Python command selection

```bash
PYTHON=.venv/bin/python
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi
```

### Existing visualizer unit tests

```bash
node poggio_webapp/static/visualizer/viewbox.test.mjs
node poggio_webapp/static/visualizer/alignment-policy.test.mjs
node poggio_webapp/static/visualizer/schema-core.test.mjs
node poggio_webapp/static/visualizer/coordinates.test.mjs
```

### Full existing regression suite

```bash
"$PYTHON" -m pytest -q
node poggio_webapp/static/canvas/grid.test.mjs
node poggio_webapp/static/app/stages/start-options.test.mjs
node poggio_webapp/static/app/text-metadata.test.mjs
node poggio_webapp/static/app/stages/verify-text-navigation.test.mjs
node poggio_webapp/static/visualizer/viewbox.test.mjs
node poggio_webapp/static/visualizer/alignment-policy.test.mjs
node poggio_webapp/static/visualizer/schema-core.test.mjs
node poggio_webapp/static/visualizer/coordinates.test.mjs
git diff --check
```

## 6. Phase A chunk map

| Chunk | Deliverable | May continue when |
|---|---|---|
| A0 | Baseline and evidence report | Existing tests pass or failures are documented as pre-existing |
| A1 | Correct site-coordinate OBJ export | Mesh coordinate unit tests pass |
| A2 | Durable viewer manifest | Manifest unit tests pass and contain no absolute paths |
| A3 | Safe model data in `visualizer-files` | Route tests pass, including traversal and missing-file cases |
| A4 | Local pinned Three.js runtime | Static dependency checks pass and no CDN reference exists |
| A5 | Pure 3D state/calculation helpers | Node unit tests pass |
| A6 | Refactor the existing results renderer into one shared renderer | Results-page regressions, syntax tests, and standalone smoke test pass |
| A7 | Visualizer UI integration | 2D regressions and 3D integration smoke test pass |
| A8 | Controls, errors, and accessibility | Control tests and manual QA pass |
| A9 | Final regression and documentation | Full suite and final acceptance checklist pass |

---

# Phase A: full surface model

## Chunk A0 — Baseline and evidence report

### Purpose

Establish that later failures were not present before the feature work.

### Allowed changes

None.

### Required work

1. Record `git rev-parse --short HEAD`.
2. Record `git status --short`.
3. Run the full existing regression suite from section 5.
4. Check whether a completed job with
   `06_gempy_model/trench_model_meshes/*.obj` exists locally.
5. Inspect the existing saved-job results viewer and record:
   - whether its import map still uses a CDN;
   - whether its OBJ renderer still rotates the model group;
   - its current controls and default vertical exaggeration;
   - the existing results-page tests that cover it.
6. Check whether GemPy can be imported without installing or changing
   anything:

   ```bash
   "$PYTHON" -c "import gempy; print(gempy.__version__)"
   ```

7. Do not install GemPy if it is missing. Report that fact.

### Output contract

Return a short baseline report containing:

- commit;
- clean/dirty worktree;
- test pass/fail counts;
- GemPy installed/not installed;
- real completed model fixture available/not available;
- existing results-page viewer behavior and test coverage.

### Gate A0

If tests fail, record exact failures. Do not continue until a reviewer decides
whether they are pre-existing and safe to work around.

---

## Chunk A1 — Correct OBJ vertices to site coordinates

### Purpose

The current exporter writes GemPy mesh vertices directly. Current GemPy
documentation states that mesh vertices are transformed internally and must
be restored using:

```python
geo_model.input_transform.apply_inverse(vertices)
```

The browser must receive real site-coordinate geometry, not GemPy's internal
normalized coordinates.

### Allowed files

- `poggio_webapp/pipeline/build_gempy.py`
- `tests/test_gempy_mesh_export.py` (new)

### Red-green tests to create first

Create tests using fake solution and model objects. Do not import GemPy.

Required cases:

1. `export_meshes` calls `input_transform.apply_inverse` once for every
   exported vertex array.
2. OBJ `v` lines contain the inverse-transformed values.
3. OBJ `f` lines remain one-based triangle indices.
4. Surface names are sanitized only for filenames; the OBJ comment retains
   the original surface name.
5. A surface containing `NaN` or infinity is rejected with a clear
   `ValueError`.
6. A surface with vertices not shaped as `N x 3` is rejected.
7. A face with an out-of-range vertex index is rejected.
8. Surface ordering remains identical to `surf_order`.

### Implementation requirements

- Add a small pure validation helper for a vertex/face pair.
- Call `geo_model.input_transform.apply_inverse(verts)` before writing.
- Convert the returned value to a NumPy array without mutating the input.
- Keep the existing OBJ format and returned list of paths.
- Do not add GemPy to the default requirements.

### Targeted tests

```bash
"$PYTHON" -m pytest -q tests/test_gempy_mesh_export.py
```

Then run:

```bash
"$PYTHON" -m pytest -q tests/test_gempy_mesh_export.py tests/test_editor_status.py
git diff --check
```

### Acceptance criteria

- Tests prove exported `v` values are the inverse-transformed values.
- Existing OBJ face numbering remains unchanged.
- No production file outside the allowlist changes.

### Stop condition specific to A1

If the installed GemPy model has no `input_transform.apply_inverse`, stop and
report the actual model/transform API. Do not invent an alternative.

### Gate A1

Review the OBJ output test assertions before assigning A2.

---

## Chunk A2 — Write a durable browser-viewer manifest

### Purpose

The present `/gempy/result/<task_id>` route depends on the in-memory task
registry. The visualizer needs a durable file that remains available after a
process restart.

### Allowed files

- `poggio_webapp/pipeline/build_gempy.py`
- `tests/test_gempy_viewer_manifest.py` (new)
- `tests/test_gempy_mesh_export.py` only if a shared fixture is necessary

### Required manifest filename

```text
06_gempy_model/trench_model_viewer.json
```

### Required manifest schema version 1

```json
{
  "schema_version": 1,
  "kind": "gempy-surface-model",
  "coordinate_system": {
    "units": "m",
    "up_axis": "Z"
  },
  "extent": [0, 10, 0, 5, 90, 100],
  "resolution": [50, 50, 30],
  "series_order": ["Topsoil", "Fill"],
  "single_face_note": null,
  "surfaces": [
    {
      "name": "Topsoil",
      "mesh_path": "trench_model_meshes/Topsoil.obj"
    }
  ],
  "lith_block_path": "trench_model_lith_block.npz"
}
```

All `*_path` values must be relative to the manifest's parent directory and
must use `/` separators.

### Red-green tests to create first

1. The manifest has exactly `schema_version: 1` and the required `kind`.
2. NumPy scalar values are serialized as ordinary JSON numbers.
3. Resolution values are JSON integers.
4. Surface order and names match `series_order`.
5. Mesh paths and lith-block path are relative and contain no absolute job
   path.
6. Filenames containing spaces or punctuation still map to the actual
   sanitized mesh filename.
7. `single_face_note` can be `null` or a string.
8. An empty mesh list produces `surfaces: []` without a crash.
9. The builder result includes
   `outputs["viewer_manifest"] = <absolute manifest path>`.

### Implementation requirements

- Add a pure `write_viewer_manifest(...)` helper.
- Call it only after OBJ and lith-block output decisions are known.
- Continue writing the manifest when `make_meshes=False`, but use an empty
  `surfaces` list.
- Do not store colors in version 1. The frontend already has a deterministic
  `colorFor(name)` helper.
- Do not store URLs in the manifest. Routes create URLs.
- Do not change existing output keys.

### Targeted tests

```bash
"$PYTHON" -m pytest -q \
  tests/test_gempy_mesh_export.py \
  tests/test_gempy_viewer_manifest.py
```

### Acceptance criteria

- The manifest can be understood without loading the `.gempy` pickle.
- It is portable with the enclosing `06_gempy_model` directory.
- It contains no absolute paths.
- Existing builder outputs are unchanged except for the added
  `viewer_manifest` output.

### Gate A2

Open a generated test manifest and manually confirm every path is relative.

---

## Chunk A3 — Expose safe 3D model data to the visualizer

### Purpose

Extend the existing `visualizer-files` response without changing any existing
keys.

### Allowed files

- `poggio_webapp/backend/routes/pages.py`
- `poggio_webapp/backend/jobs.py` only if a small reusable safe-path helper is
  truly necessary
- `tests/test_visualizer_files_route.py`

### Required API addition

When a valid manifest exists, add:

```json
{
  "model3d": {
    "schema_version": 1,
    "kind": "gempy-surface-model",
    "coordinate_system": {
      "units": "m",
      "up_axis": "Z"
    },
    "extent": [0, 10, 0, 5, 90, 100],
    "resolution": [50, 50, 30],
    "series_order": ["Topsoil", "Fill"],
    "single_face_note": null,
    "surfaces": [
      {
        "name": "Topsoil",
        "url": "/api/jobs/abc/file?path=06_gempy_model/trench_model_meshes/Topsoil.obj"
      }
    ],
    "lith_block_url": "/api/jobs/abc/file?path=06_gempy_model/trench_model_lith_block.npz",
    "warnings": []
  }
}
```

Do not return `mesh_path` or `lith_block_path` to the browser.

### Manifest discovery order

1. If `meta["model_outputs"]["viewer_manifest"]` exists and is inside the job
   directory, use it.
2. Otherwise try the durable conventional path:
   `06_gempy_model/trench_model_viewer.json`.
3. If neither exists, omit `model3d`.

This fallback is required because not every current GemPy route persists
`model_outputs` in metadata.

### Red-green route tests to create first

1. Existing scan/JSON/calibration payload is unchanged when no model exists.
2. A valid manifest returns `model3d` with job file URLs.
3. The conventional manifest is found when `model_outputs` is absent.
4. A metadata manifest is preferred when both candidates exist.
5. A missing individual OBJ is omitted and produces a warning.
6. A manifest with no existing surfaces causes `model3d` to be omitted.
7. A missing lith block omits `lith_block_url` but still returns surfaces.
8. Malformed JSON does not break the 2D payload; omit `model3d` and return a
   warning only if the existing API has an appropriate top-level warning
   convention. Otherwise log server-side.
9. Unsupported `schema_version` is ignored safely.
10. `../` traversal in the manifest cannot produce a URL and cannot read a
    file outside the job.
11. An absolute manifest path outside the job from metadata is ignored.
12. Surface names are returned as data, never interpolated into HTML by the
    route.

### Implementation requirements

- Put manifest parsing in a focused private helper in `pages.py`.
- Validate top-level field types.
- Resolve every path beneath the manifest directory and then verify it is
  still beneath the job directory.
- Reuse `rel_url` only after validation.
- Keep the endpoint usable when GemPy is not installed.
- Do not read `.gempy` or `.npz` in this route.

### Targeted tests

```bash
"$PYTHON" -m pytest -q \
  tests/test_visualizer_files_route.py \
  tests/test_visualizer_calibration_integration.py
```

### Acceptance criteria

- Existing response behavior is byte-for-byte equivalent at the JSON-data
  level when no model manifest exists.
- A process restart does not remove the 3D model from the endpoint.
- No absolute filesystem path reaches the browser.
- Traversal attempts are harmless.

### Gate A3

Run the complete Python suite before assigning frontend work:

```bash
"$PYTHON" -m pytest -q
```

---

## Chunk A4 — Add a local pinned Three.js runtime

### Purpose

Provide the rendering library and required addons without adding a runtime CDN
dependency or a frontend build system.

### Approved dependency

Pin Three.js npm package version `0.185.1` unless a reviewer updates this
contract before the chunk begins.

### Allowed files

- `poggio_webapp/static/vendor/three/three.module.min.js` (new)
- `poggio_webapp/static/vendor/three/addons/controls/OrbitControls.js` (new)
- `poggio_webapp/static/vendor/three/addons/loaders/OBJLoader.js` (new)
- `poggio_webapp/static/vendor/three/LICENSE` (new)
- `poggio_webapp/static/vendor/three/VERSION` (new)
- `poggio_webapp/static/visualizer.html`
- `poggio_webapp/templates/index.html`
- `tests/test_visualizer_static_dependencies.py` (new)
- `tests/test_editor_routes.py` only for results-page local-import assertions

### Required import map

Add the same local import map before the relevant module script on both
`visualizer.html` and the completed-job branch of `templates/index.html`:

```html
<script type="importmap">
{
  "imports": {
    "three": "/static/vendor/three/three.module.min.js",
    "three/addons/": "/static/vendor/three/addons/"
  }
}
</script>
```

### Required tests

1. `/visualizer` contains the import map before the module entry script.
2. A completed saved-job results page contains the same local import map
   before `/static/viewer3d.js`.
3. All four mapped/required static files return HTTP 200.
4. `VERSION` contains exactly `0.185.1`.
5. The vendored license identifies the Three.js MIT license.
6. Neither page nor its viewer source contains `unpkg`, `jsdelivr`, `esm.sh`,
   `threejs.org/build`, or an `http://`/`https://` Three.js import.
7. `OrbitControls.js` and `OBJLoader.js` import the bare specifier `three`,
   which the import map resolves.

### Acquisition rule

Copy the files from the exact official npm package version. Do not copy from a
random gist, tutorial, or CDN-transformed module. Record the package integrity
or source URL in the handoff report.

### Targeted tests

```bash
"$PYTHON" -m pytest -q \
  tests/test_visualizer_static_dependencies.py \
  tests/test_editor_routes.py
```

Also run:

```bash
node --check poggio_webapp/static/vendor/three/addons/controls/OrbitControls.js
node --check poggio_webapp/static/vendor/three/addons/loaders/OBJLoader.js
git diff --check
```

### Acceptance criteria

- The browser needs no external network request to start the 3D renderer.
- Core and addons are from the same exact Three.js version.
- The pre-existing saved-job results viewer still loads.
- No package manager or bundler is required at application runtime.

### Stop condition specific to A4

If acquiring the exact official package requires permission or network access
that the agent does not have, stop and request it. Do not substitute a CDN.

### Gate A4

Inspect browser developer tools with networking disabled. Both the existing
saved-job 3D viewer and existing 2D visualizer must load without a
module-resolution error.

---

## Chunk A5 — Add pure 3D data and camera helpers

### Purpose

Make validation, view calculations, and control state testable without
WebGL.

### Allowed files

- `poggio_webapp/static/visualizer/model3d-core.mjs` (new)
- `poggio_webapp/static/visualizer/model3d-core.test.mjs` (new)

### Required pure exports

Names may change only with reviewer approval:

```javascript
validateModel3d(raw)
extentCenter(extent)
extentSize(extent)
cameraPreset(extent, viewName)
surfaceControlModel(model3d)
clampOpacity(value)
```

### Required behavior

- `validateModel3d` returns a normalized object or throws a clear `TypeError`.
- It accepts only schema version 1 and `kind: "gempy-surface-model"`.
- Extent must be six finite numbers with min less than max on every axis.
- Resolution must be three positive integers.
- Surface names must be non-empty strings.
- Surface URLs must be non-empty same-origin relative URL strings beginning
  with `/api/jobs/`.
- Duplicate surface names are rejected.
- `extentCenter` returns the world-space midpoint.
- Camera presets preserve GemPy's Z-up coordinate system:
  - top looks down negative Z;
  - front looks along negative Y;
  - side looks along negative X;
  - isometric has positive offsets on X, Y, and Z.
- `surfaceControlModel` preserves manifest order and assigns deterministic
  colors using a passed color function or a documented pure fallback.
- Opacity clamps to the inclusive range `0.1` through `1.0`.

### Required unit tests

Test:

- a valid minimal model;
- each missing/invalid required field;
- non-finite extent;
- reversed extent;
- invalid resolution;
- duplicate surface;
- unsafe URL;
- exact center and size for a non-cubic extent;
- all four camera presets;
- opacity below, inside, and above range;
- stable surface order and colors.

### Test command

```bash
node poggio_webapp/static/visualizer/model3d-core.test.mjs
```

Also run all existing visualizer Node tests.

### Acceptance criteria

- The new module has no import from `three`, Flask, `window`, or `document`.
- Every pure behavior listed above is unit-tested.

### Gate A5

No renderer work begins until all pure helper tests pass.

---

## Chunk A6 — Build the isolated surface renderer

### Purpose

Create a focused renderer module without yet changing the main visualizer
navigation or existing 2D draw path.

### Allowed files

- `poggio_webapp/static/visualizer/model3d.js` (new)
- `poggio_webapp/static/visualizer/model3d-core.mjs`
- `poggio_webapp/static/visualizer/model3d-core.test.mjs`
- `poggio_webapp/static/visualizer/visualizer.css` only for classes prefixed
  `.model3d-`
- `tests/fixtures/gempy-viewer/surface-a.obj` (new)
- `tests/fixtures/gempy-viewer/surface-b.obj` (new)
- `tests/fixtures/gempy-viewer/model.json` (new)
- `tests/fixtures/gempy-viewer/smoke.html` (new)
- `poggio_webapp/static/visualizer.html` only for a temporary hidden smoke
  mount if a reviewer explicitly approves it; remove that mount before the
  chunk ends

### Required renderer interface

```javascript
const viewer = new SurfaceModelViewer(container, model3d, options);
await viewer.load();
viewer.setSurfaceVisible(surfaceName, visible);
viewer.setOpacity(opacity);
viewer.setWireframe(enabled);
viewer.setCameraView("isometric"); // also top, front, side
viewer.resetCamera();
viewer.resize();
viewer.dispose();
```

### Rendering requirements

- Use `WebGLRenderer`, `PerspectiveCamera`, `OrbitControls`, and `OBJLoader`.
- Set `camera.up` to `(0, 0, 1)`. Do not rotate the exported geometry to make
  Y look like up.
- Use the model extent center as the initial orbit target.
- Load all surfaces with `Promise.allSettled` or equivalent so that one failed
  OBJ does not discard all successful surfaces.
- Apply deterministic per-surface colors.
- Use `DoubleSide` materials because exported geological surfaces may be
  open.
- Compute vertex normals after load if they are absent.
- Default opacity is `0.72`.
- Include ambient/hemisphere and directional light sufficient to read shape.
- Add a bounding box and labeled or color-coded X/Y/Z axes.
- Use a `ResizeObserver` for the container.
- Show loading progress through a callback or status event.
- If WebGL construction fails, show/return a clear recoverable error.
- `dispose()` must:
  - stop the animation frame;
  - disconnect the resize observer;
  - dispose controls;
  - dispose geometries and materials;
  - dispose the renderer;
  - remove the canvas from the container.

### Prohibited behavior

- No global mutable renderer singleton.
- No assignment to `window.onresize`.
- No HTML string construction with unescaped surface names.
- No fetch of NPZ or `.gempy`.
- No clipping planes or volume rendering in this chunk.
- No change to existing `view.js`.

### Automated checks

```bash
node --check poggio_webapp/static/visualizer/model3d.js
node poggio_webapp/static/visualizer/model3d-core.test.mjs
```

### Required manual smoke test

Create a deterministic fixture under `tests/fixtures/gempy-viewer/` unless a
reviewer provides an existing one. The two OBJ files must have visibly
different Z elevations and non-equal X/Y dimensions so that mirrored,
transposed, or flattened output is obvious. `model.json` must follow the
validated browser `model3d` shape. `smoke.html` may contain only the minimum
container and module bootstrap needed to create and dispose the renderer.

Serve the repository root locally or use a completed local job, then verify:

1. Both surfaces appear.
2. X/Y/Z orientation matches the OBJ coordinates.
3. Orbit, zoom, and pan work.
4. Reset restores the whole model.
5. Hiding one surface leaves the other.
6. Repeated create/dispose does not leave extra canvases or animation loops.
7. A deliberately missing second OBJ still displays the first and reports
   the failure.

Record screenshots or a precise observation list in the handoff report.

### Acceptance criteria

- The renderer is usable in isolation.
- One bad surface is non-fatal.
- Cleanup is explicit and verified.

### Gate A6

A reviewer must approve the standalone rendering orientation before UI
integration. A visually rotated or mirrored model must not proceed.

---

## Chunk A7 — Integrate 3D into the existing visualizer

### Purpose

Connect the safe API model to the isolated renderer while preserving 2D
behavior.

### Allowed files

- `poggio_webapp/static/visualizer.html`
- `poggio_webapp/static/visualizer/files.js`
- `poggio_webapp/static/visualizer/state.js`
- `poggio_webapp/static/visualizer/view.js`
- `poggio_webapp/static/visualizer/model3d.js`
- `poggio_webapp/static/visualizer/model3d-core.mjs`
- `poggio_webapp/static/visualizer/visualizer.css`
- `poggio_webapp/static/visualizer/view-mode.mjs` (new, optional pure helper)
- `poggio_webapp/static/visualizer/view-mode.test.mjs` (new, required if the
  helper is added)

### UI structure

Add two mode buttons near the top of the main view:

- `2D drawing`
- `3D model`

Rules:

- Hide `3D model` when no valid `model3d` exists.
- If a model exists, default to 3D for a completed job opened with `?job=`.
- If extraction data exists, the user can always return to 2D.
- If only a model exists, the visualizer must still initialize.
- Switching to 2D disposes or pauses the 3D renderer.
- Switching back to 3D creates or resumes exactly one renderer.
- Existing face tabs, overlay controls, and A/B comparison apply only to 2D.
- 3D controls live in their own clearly separated sidebar section.

### Data-loading changes

In `files.js`:

1. Read `f.model3d`.
2. Validate it with `validateModel3d`.
3. Store it as `state.model3d`.
4. A bad model payload must log a warning and leave the 2D view working.
5. Call `ready()` if a model exists even when no extraction or image exists.

### State additions

At minimum:

```javascript
model3d: null,
viewMode: "2d",
modelViewer: null
```

Do not mix surface visibility state into extraction data.

### Refactoring constraint

Move existing 2D drawing code only when needed to select a mode. Do not
rewrite SVG generation, alignment, schema ingestion, tooltip behavior, or A/B
comparison.

### Required automated tests

Pure view-mode tests must cover:

1. No model means 2D mode only.
2. Model plus extraction defaults as specified.
3. Model-only data initializes 3D.
4. Explicit mode switch returns the expected visible control groups.
5. Invalid model does not suppress valid 2D data.

Run:

```bash
node poggio_webapp/static/visualizer/model3d-core.test.mjs
node poggio_webapp/static/visualizer/view-mode.test.mjs
```

If no pure `view-mode.mjs` is created, explain how these behaviors were
automatically tested another way. Manual-only testing is not acceptable for
mode selection.

Then run all existing visualizer Node tests and:

```bash
"$PYTHON" -m pytest -q \
  tests/test_visualizer_files_route.py \
  tests/test_visualizer_calibration_integration.py
```

### Required manual integration test

For a job containing extraction JSON, image calibration, manifest, and two
OBJ surfaces:

1. Open `/visualizer?job=<id>`.
2. Confirm 3D loads.
3. Switch to 2D.
4. Confirm the correct face and image overlay still render.
5. Toggle A/B comparison.
6. Switch repeatedly between modes.
7. Confirm only one WebGL canvas exists.
8. Resize the window.
9. Reload with browser cache disabled.
10. Confirm no external network request is made.

### Acceptance criteria

- The new model is reachable from the normal job visualizer URL.
- 2D output before and after mode switching is unchanged.
- Model-only jobs do not show the old "load output.json" empty state.

### Gate A7

Run the entire Python suite and every visualizer Node test before assigning
controls polish.

---

## Chunk A8 — Add complete controls, errors, and accessibility

### Purpose

Make the new view understandable and recoverable for non-technical users.

### Allowed files

- `poggio_webapp/static/visualizer.html`
- `poggio_webapp/static/visualizer/view.js`
- `poggio_webapp/static/visualizer/model3d.js`
- `poggio_webapp/static/visualizer/model3d-core.mjs`
- `poggio_webapp/static/visualizer/model3d-core.test.mjs`
- `poggio_webapp/static/visualizer/visualizer.css`
- `poggio_webapp/static/app/stages/visualize.js`

### Required controls

- Checkbox for each surface, initially checked.
- `Show all` and `Hide all`.
- Opacity slider from `0.1` to `1.0`, initially `0.72`.
- Wireframe checkbox, initially off.
- Camera buttons: `Reset`, `Top`, `Front`, `Side`, `3D`.
- Bounding-box/axes checkbox, initially on.
- A short mouse/touch instruction.
- Loading status with loaded count and total count.
- Visible partial-failure warning listing failed surface names.

### Required usability behavior

- Every control has a programmatic label.
- Mode and camera buttons use `aria-pressed` where appropriate.
- Loading and failure text uses an `aria-live` region.
- Keyboard focus is visible.
- Surface names are inserted with `textContent`, not raw `innerHTML`.
- Controls remain usable at narrow desktop/tablet widths.
- On screens where the old CSS hides the entire sidebar, provide a way to
  reach essential 3D controls rather than leaving only an uncontrolled
  canvas.
- The launch-stage copy says that the interactive view includes the completed
  3D model when one exists. Do not promise volume rendering in Phase A.

### Required tests

Extend pure unit tests for:

- show-all/hide-all state;
- opacity;
- camera control names;
- deterministic surface ordering;
- partial load status summary.

Add a small static HTML response test if necessary to prove required
accessibility attributes exist.

### Manual QA matrix

| Case | Expected |
|---|---|
| No model manifest | Existing 2D-only visualizer |
| Valid manifest, two valid OBJs | Both surfaces visible |
| One valid and one missing OBJ | Valid surface plus warning |
| All OBJ files missing | Recoverable error and download/use-2D path |
| Model only, no extraction | 3D initializes |
| Extraction only, no model | 2D initializes |
| WebGL unavailable | Clear error; page and 2D remain usable |
| Long punctuation-heavy surface name | Safe readable label |
| Narrow viewport | Essential controls reachable |
| Rapid mode switching | No duplicated canvases/listeners |

### Acceptance criteria

- A first-time user can discover how to manipulate the model.
- Partial failures do not become blank screens.
- Controls are keyboard reachable and safely render model-provided names.

### Gate A8

A reviewer performs the manual QA matrix. Do not begin final documentation
until every row passes or has an explicitly accepted limitation.

---

## Chunk A9 — Final regression, documentation, and release evidence

### Purpose

Close Phase A with durable documentation and evidence.

### Allowed files

- `README.md`
- `poggio_webapp/README.md`
- `docs/workflows/08-view-and-download.md`
- `docs/reference/output-files.md`
- `docs/reference/api-routes.md`
- `docs/project/capability-status.md`
- `docs/_meta/source-map.yml` if required by existing documentation policy
- Test files from earlier Phase A chunks only when fixing a discovered defect
- Production files from earlier chunks only when fixing a discovered defect

### Documentation requirements

Document:

- the distinction between 2D extraction review and 3D GemPy surfaces;
- the viewer manifest schema and location;
- site-coordinate OBJ export;
- the `model3d` API response;
- local pinned Three.js files;
- controls and failure behavior;
- the limitation that Phase A shows surfaces, not the solid lithology volume;
- how to run every new test.

Do not label the visualizer as scientifically authoritative. Retain the
existing provenance and single-face interpolation warnings.

### Final automated gate

Run the full regression suite from section 5, plus:

```bash
"$PYTHON" -m pytest -q \
  tests/test_gempy_mesh_export.py \
  tests/test_gempy_viewer_manifest.py \
  tests/test_visualizer_files_route.py \
  tests/test_visualizer_static_dependencies.py
node poggio_webapp/static/visualizer/model3d-core.test.mjs
node poggio_webapp/static/visualizer/view-mode.test.mjs
"$PYTHON" tools/docs/check_docs.py
git diff --check
git status --short
```

### Final manual acceptance checklist

- [ ] Open a real completed GemPy job.
- [ ] Every expected surface is listed.
- [ ] Every expected surface can be seen.
- [ ] The model is not mirrored and Z is up.
- [ ] Axis units are metres.
- [ ] Orbit, zoom, and pan work with mouse.
- [ ] Basic touch manipulation works if a touch device is available.
- [ ] Layer visibility works.
- [ ] Opacity and wireframe work.
- [ ] All camera buttons work.
- [ ] Resize works.
- [ ] 2D overlay and A/B comparison still work.
- [ ] Reload after server restart still finds the model.
- [ ] No absolute server path appears in page source or API JSON.
- [ ] No Three.js CDN request appears.
- [ ] Partial OBJ failure gives a useful warning.
- [ ] Browser console has no uncaught errors.

### Definition of Phase A done

Phase A is done only when:

- all automated gates pass;
- the manual checklist passes;
- the documentation describes surfaces rather than claiming a solid volume;
- a reviewer accepts a screenshot of a real model with at least two visible
  surfaces.

---

# Phase B: lithology volume

Phase B must be assigned only after Phase A is complete. Each Phase B chunk is
also a separate task.

## Phase B architecture

The existing `.npz` file is a scientific/download artifact, not a convenient
browser transport. The builder will additionally write a compact,
little-endian unsigned-integer binary file:

```text
trench_model_lith_block.bin
```

The manifest will describe:

```json
{
  "volume": {
    "schema_version": 1,
    "format": "raw",
    "dtype": "uint16-le",
    "layout": "C",
    "axes": ["x", "y", "z"],
    "shape": [50, 50, 30],
    "path": "trench_model_lith_block.bin",
    "lithologies": [
      {
        "id": 1,
        "name": "Lithology 1"
      }
    ]
  }
}
```

The original NPZ remains unchanged and downloadable.

In C-order with shape `[nx, ny, nz]`, the browser index formula is:

```text
index = (x * ny + y) * nz + z
```

The browser will render cells with `InstancedMesh`, grouped by lithology ID.
Slice controls include or exclude whole cells. This produces understandable
voxel cross-sections without pretending to make smooth closed geological
solids.

## Chunk B0 — Audit GemPy lithology semantics

### Allowed changes

None.

### Required evidence

Using a real completed model or a tiny locally computed model, report:

1. `lith_block.dtype`.
2. Unique values, including whether zero or `NaN` occurs.
3. Exact element count compared with `nx * ny * nz`.
4. Confirmation that `reshape(tuple(resolution), order="C")` matches GemPy's
   documented regular-grid layout.
5. The verified API, if any, mapping lithology IDs to structural element
   names.

### Critical mapping rule

If ID-to-name mapping cannot be proven, labels must remain
`Lithology <id>`. Do not infer IDs from `series_order`.

### Gate B0

A reviewer approves the ID semantics and layout before binary export begins.

---

## Chunk B1 — Export tested browser volume binary

### Allowed files

- `poggio_webapp/pipeline/build_gempy.py`
- `tests/test_gempy_volume_export.py` (new)
- `tests/test_gempy_viewer_manifest.py`

### Required pure helper

```python
write_lithology_binary(
    lith_block,
    resolution,
    output_path,
    lithology_names=None,
)
```

### Red-green tests

1. Element count must equal the resolution product.
2. Every finite value must be a non-negative integer.
3. Values above `65535` are rejected.
4. Output bytes are exactly little-endian `uint16`.
5. No silent rounding is allowed.
6. Unique IDs are returned in numeric order.
7. A non-cubic `2 x 3 x 4` fixture proves C-order indexing.
8. Original NPZ output remains unchanged.
9. Manifest volume metadata matches the binary.

### Acceptance criteria

- The binary can be decoded without NumPy in the browser.
- A malformed block stops model export with a useful error rather than
  emitting corrupt volume data.

---

## Chunk B2 — Safely expose volume URL

### Allowed files

- `poggio_webapp/backend/routes/pages.py`
- `tests/test_visualizer_files_route.py`

### Required behavior

- Replace manifest `volume.path` with a validated `volume.url`.
- Never return the server path.
- Missing volume binary omits `volume` but preserves surface viewing.
- Traversal and unsupported dtype/layout are rejected safely.

### Tests

Add valid, missing, malformed, and traversal cases. Run the full route test
set and Python suite.

---

## Chunk B3 — Add pure volume decoding and indexing

### Allowed files

- `poggio_webapp/static/visualizer/volume3d-core.mjs` (new)
- `poggio_webapp/static/visualizer/volume3d-core.test.mjs` (new)

### Required pure exports

```javascript
validateVolumeMetadata(raw)
decodeUint16LE(arrayBuffer, expectedCount)
volumeIndex(x, y, z, shape)
cellCenter(x, y, z, shape, extent)
visibleCellRange(shape, slices)
groupCellsByLithology(values, metadata, slices)
```

### Required unit tests

- exact byte decoding;
- odd byte length rejection;
- wrong element count rejection;
- non-cubic index layout;
- first and last cell centers;
- x/y/z slice boundaries;
- stable numeric lithology grouping;
- unknown IDs use `Lithology <id>`;
- out-of-range coordinates reject clearly.

No DOM or Three.js import is allowed in this core module.

---

## Chunk B4 — Add isolated instanced voxel renderer

### Allowed files

- `poggio_webapp/static/visualizer/volume3d.js` (new)
- `poggio_webapp/static/visualizer/volume3d-core.mjs`
- `poggio_webapp/static/visualizer/volume3d-core.test.mjs`
- `.model3d-` CSS only

### Required behavior

- Fetch the binary with an explicit HTTP error check.
- Decode only after validating expected byte count.
- Create one `InstancedMesh` per lithology ID.
- Use world-space cell sizes derived from extent and shape.
- Use cell centers, not cell corners, for instance positions.
- Preserve Z-up.
- Support lithology visibility.
- Support integer X/Y/Z maximum-slice controls.
- Debounce or animation-frame-coalesce slice rebuilds.
- Dispose instance meshes and materials.
- Do not create one ordinary `Mesh` per cell.

### Performance gate

On the default `50 x 50 x 30` grid:

- total instances must equal at most 75,000;
- initial scene remains interactive on the review machine;
- a slice update should target less than 200 ms on the review machine;
- memory growth must stabilize after repeated surface/volume switching.

If the performance gate fails, stop and profile. Do not add an unreviewed
rendering framework.

---

## Chunk B5 — Integrate surface/volume mode and controls

### Allowed files

- Existing Phase A visualizer modules
- `volume3d.js`
- `volume3d-core.mjs`
- `volume3d-core.test.mjs`
- visualizer HTML/CSS

### Required UI

Within `3D model`, add:

- `Surfaces`
- `Lithology volume`

Volume controls:

- per-lithology visibility;
- X, Y, and Z slice maximum;
- reset slices;
- axes/bounds;
- camera presets;
- explanatory text that volume cells reflect the chosen GemPy resolution.

Switching renderer type must dispose the inactive renderer.

### Test gate

Run all Phase A tests, all new volume tests, the full Python suite, and a
manual test using a non-cubic synthetic volume before using a real model.

---

## Chunk B6 — Final volume QA and documentation

Document:

- binary format;
- resolution-dependent voxel appearance;
- ID labeling rules;
- slice semantics;
- performance limits;
- difference between interpolated boundary surfaces and classified grid
  cells.

Final manual checks must compare at least one X, Y, and Z slice with GemPy's
own 2D section output. If the classifications or axes do not agree, Phase B
is not complete.

---

# 7. Reusable prompt for assigning one chunk

Copy this prompt and replace the bracketed values:

```text
Implement only Chunk [A1] from
GEMPY_3D_VISUALIZER_TASK_CONTRACT.md.

This is a bounded task. Read the master rules and the named chunk completely.
Do not begin any later chunk. Edit only the chunk's allowlisted files. Create
the required tests before the production change when the chunk specifies
red-green order.

Before editing:
1. Run git status --short.
2. Run the chunk's pre-change/target tests.
3. Report any overlapping existing changes and stop if there are any.

During the task:
- Preserve existing behavior.
- Follow every chunk-specific acceptance criterion and stop condition.
- Do not install or introduce anything outside the approved scope.

After editing:
1. Run every test named in the chunk.
2. Run git diff --check.
3. Inspect the diff for only allowlisted files.
4. Report changed files, tests added, exact command results, acceptance
   criteria, and unresolved risks.
5. Stop. Do not implement the next chunk.
```

# 8. Reviewer checklist between chunks

The reviewer should not accept "tests pass" by itself. Check:

1. Did only allowlisted files change?
2. Were required tests created before or with production code?
3. Do tests assert behavior rather than implementation trivia?
4. Is failure behavior tested?
5. Are paths safe and relative?
6. Are model-provided names escaped?
7. Is Z still the up axis?
8. Is the existing 2D view unchanged?
9. Did the agent run the exact gate commands?
10. Did the agent stop at the end of the assigned chunk?

# 9. Bug-fix rule

If a chunk exposes a defect in an earlier accepted chunk:

1. Stop the current chunk.
2. Create a regression test in the earlier chunk's test file.
3. Fix only that defect using the earlier chunk's allowlist.
4. Re-run the earlier gate and every intervening gate.
5. Resume the current chunk only after review.

Do not mix an earlier bug fix into an unrelated later chunk without calling it
out explicitly.

# 10. Completion report template

Every agent handoff should use:

```text
Chunk:

Outcome:

Files changed:

Tests added or changed:

Commands run:
- <command>: PASS/FAIL (<count or relevant output>)

Acceptance criteria:
- [x] ...
- [ ] ... (reason)

Scope check:
- Only allowlisted files changed: yes/no
- Later chunks started: no

Risks or reviewer decisions needed:

Suggested next action:
- Review this chunk and, only if accepted, assign Chunk <next>.
```
