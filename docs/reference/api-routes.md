---
title: API Routes
audience: developer
status: current
source_files:
  - poggio_webapp/backend/routes/jobs.py
  - poggio_webapp/backend/routes/scans.py
  - poggio_webapp/backend/routes/preprocess.py
  - poggio_webapp/backend/routes/extraction.py
  - poggio_webapp/backend/routes/features.py
  - poggio_webapp/backend/routes/markers.py
  - poggio_webapp/backend/routes/manual.py
  - poggio_webapp/backend/routes/processing.py
  - poggio_webapp/backend/routes/gempy.py
  - poggio_webapp/backend/routes/task_status.py
  - poggio_webapp/backend/routes/pages.py
  - poggio_webapp/backend/routes/harris.py
  - poggio_webapp/backend/routes/trenches.py
verified_against: 2267711
---

# API Routes

This reference documents all HTTP endpoints available in the Flask backend. All routes are prefixed with `/api/` except where noted.

## Route Reference

| Endpoint | Method | Request | Response | Async | Status | Notes |
|----------|--------|---------|----------|-------|--------|-------|
| `/api/jobs` | POST | `{}` | `{job_id: str}` | No | supported | Creates a new job with UUID identifier and folder structure |
| `/api/jobs/<job_id>/file` | GET | query `path=<rel>` | binary | No | supported | Retrieve any file from the job folder by relative path |
| `/api/jobs/<job_id>/scan` | POST | multipart: `sheet_type`, `file` | `{scan_url, sheet_type, is_pdf, dimensions, recommended_upscale}` | No | supported | Upload source image (PNG, JPG, PDF, TIFF) |
| `/api/jobs/<job_id>/preprocess` | POST | JSON: `upscale`, `deskew`, `highcontrast`, `pdf_dpi`, `pdf_page` | `{deskew_angle, outputs}` | No | supported | Rotate, deskew, and normalize image brightness |
| `/api/jobs/<job_id>/extract` | POST | JSON: `api_key`, `square_cm` (fieldwall only), `max_output_tokens` | `{task_id}` | **Yes** | supported | Start AI extraction using Gemini; returns task ID |
| `/api/jobs/<job_id>/extract/upload` | POST | multipart: `file` | `{raw_json, sheet_type, file_url}` | No | supported | Import extraction JSON from external source |
| `/api/jobs/<job_id>/normalize` | POST | `{}` | `{data, log, file_url}` | No | supported | Clean and structure extraction data |
| `/api/jobs/<job_id>/validate` | POST | JSON: `monotonic_tolerance`, `top_continuity_tolerance`, `max_depth` | `{errors, warnings, ok}` | No | supported | Validate normalized data against geometric rules |
| `/api/jobs/<job_id>/gridconfig/starter` | GET | none | `{...grid_config}` | No | supported | Generate starter grid configuration from extraction |
| `/api/jobs/<job_id>/convert` | POST | JSON: `grid_config` | `{n_points, points_csv, orientations_csv, ...}` | No | supported | Convert to site-wide coordinates |
| `/api/jobs/<job_id>/boundaries/manual` | POST | JSON: boundary polylines, calibration, features | `{extraction_json}` | No | supported | Manual tracing: pixel coordinates to FieldWallProfile or ArchaeologicalDiagram |
| `/api/jobs/<job_id>/features/detect` | POST | JSON: `api_key`, `max_output_tokens` | `{task_id}` | **Yes** | experimental | Detect features using AI |
| `/api/jobs/<job_id>/features/confirm` | POST | JSON: feature list | `{...}` | No | experimental | Accept or reject AI-detected features |
| `/api/jobs/<job_id>/markers/preview` | POST | JSON: `image_path`, `api_key` | `{markers_json, task_id}` | **Yes** | experimental | Preview marker detection without saving |
| `/api/jobs/<job_id>/markers/detect` | POST | JSON: `api_key` | `{task_id}` | **Yes** | experimental | Start marker detection on field-wall image |
| `/api/jobs/<job_id>/markers/confirm` | POST | JSON: marker list | `{...}` | No | experimental | Accept or reject detected markers |
| `/api/jobs/<job_id>/markers/assign` | POST | JSON: assignment list | `{...}` | No | experimental | Assign markers to loci |
| `/api/jobs/<job_id>/markers/finalize` | POST | `{}` | `{extraction_json}` | No | experimental | Convert marker assignments to FieldWallProfile |
| `/api/jobs/<job_id>/gempy` | POST | JSON: `points_csv`, `orientations_csv`, `output_prefix` | `{task_id}` | **Yes** | supported | Start GemPy 3D model build |
| `/api/jobs/<job_id>/gempy/result/<task_id>` | GET | none | `{status, result, error}` | No | supported | Poll for GemPy build results |
| `/api/tasks/<task_id>` | GET | none | `{status, result, error, progress}` | No | supported | Get status of any asynchronous task |
| `/api/jobs/<job_id>/visualizer-files` | GET | none | `{...file_urls, model3d?}` | No | supported | List 2D assets and, when valid surfaces exist, safe 3D model data |
| `/api/harris-matrices` | GET | none | matrix summary array | No | supported | List valid matrices newest first |
| `/api/harris-matrices` | POST | JSON: `title`, `site`, `trench` | version 1 matrix | No | supported | Create an empty trench-level workspace |
| `/api/harris-source-jobs` | GET | none | safe source summary array | No | supported | Discover jobs with a supported usable extraction artifact |
| `/api/harris-matrices/<matrix_id>` | GET | none | version 1 matrix | No | supported | Load one matrix |
| `/api/harris-matrices/<matrix_id>` | PUT | complete version 1 matrix with current `revision` | saved matrix | No | supported | Validate, atomically save, and increment revision |
| `/api/harris-matrices/<matrix_id>/sources` | POST | `{job_ids: [str], revision: int}` | saved matrix plus `import_warnings` | No | supported | Idempotently import units and regenerate proposals |
| `/api/harris-matrices/<matrix_id>/suggestions/<suggestion_id>` | POST | `{action: "accept" \| "reject", revision: int}` | saved matrix | No | supported | Review one proposal and increment revision |
| `/api/harris-matrices/<matrix_id>/export.json` | GET | none | JSON attachment | No | supported | Download the saved version 1 record |
| `/api/harris-matrices/<matrix_id>/export.svg` | GET | optional `inline=1` | SVG attachment or inline image | No | supported | Render the deterministic reduced display graph |
| `/api/trenches` | GET | none | `{trenches: {label: [member, ...]}}` | No | backend-only | Group jobs by their `trench_label`; jobs without one are skipped |
| `/api/trenches/<label>/build` | POST | JSON: `grid`, optional `correlation`, `series_order` | `{needs_grid, starter, notes}` or `{task_id, notes, grid_warnings}` | **Yes** | backend-only | Merge every wall of a trench and build one model. Omit `grid` to get a starter config back without writing anything |
| `/api/trenches/<label>/file` | GET | query `path=<rel>` | binary | No | backend-only | Retrieve a file from the trench folder, refusing to escape it |
| `/` | GET | none | HTML | No | supported | Render the vanilla JavaScript drawing workflow |
| `/visualizer` | GET | query `job=<job_id>` (optional) | HTML | No | supported | Interactive 2D extraction and 3D surface viewer |
| `/harris` | GET | optional `source_job=<job_id>` | HTML | No | supported | Matrix dashboard; a usable source can be preselected without mutation |
| `/harris/<matrix_id>` | GET | none | HTML | No | supported | Matrix editor shell |

---

## Job Lifecycle

Most routes expect `job_id` to be a 12-character UUID hex string. Job folders contain:

```
<JOBS_DIR>/<job_id>/
├── 01_scan/              # Original uploaded image
├── 02_preprocess/        # Deskewed, rotated output
├── 03_extraction/        # AI-extracted or manually traced JSON
├── 04_normalize_validate/ # Cleaned JSON + validation report
├── 05_convert_coords/    # Points and orientations for GemPy
├── 06_gempy_model/       # GemPy pickle and outputs
├── meta.json             # Current job state
├── editor_meta.json      # Manual editor state (if created)
└── extraction_output.json # Editor extraction (if manual)
```

Typical request order:

1. POST `/api/jobs` → `job_id`
2. POST `/api/jobs/<job_id>/scan` + file
3. POST `/api/jobs/<job_id>/preprocess` (optional; enables deskew)
4. POST `/api/jobs/<job_id>/extract` (or `/extract/upload`)
5. POST `/api/jobs/<job_id>/normalize`
6. POST `/api/jobs/<job_id>/validate`
7. POST `/api/jobs/<job_id>/convert` + grid
8. POST `/api/jobs/<job_id>/gempy`

Manual tracing skips steps 3–4 and replaces with:

3. POST `/api/jobs/<job_id>/boundaries/manual` (instead of extract/preprocess)
4. (skip normalize, go straight to validate)

---

## Asynchronous Tasks

Routes marked **Yes** in the Async column return a `task_id` immediately and process in the background. To poll results:

```
GET /api/tasks/<task_id>
```

Returns:

```json
{
  "status": "running" | "done" | "error",
  "result": {...},
  "error": null | "error message",
  "progress": "optional progress info"
}
```

Asynchronous operations:

- **`/extract`** — calls Gemini Vision API; network I/O
- **`/features/detect`** — calls Gemini Vision API; network I/O
- **`/markers/preview`** — calls Gemini Vision API; network I/O
- **`/markers/detect`** — calls Gemini Vision API; network I/O
- **`/gempy`** — builds 3D model; CPU-intensive; may take minutes

### Task Persistence

- Tasks are stored in memory only.
- If the server restarts, running tasks are lost.
- Completed tasks remain queryable until next restart.
- Job metadata (`meta.json`) persists across restarts.

---

## Request/Response Details

### Preprocessing Parameters

**POST `/api/jobs/<job_id>/preprocess`**

```json
{
  "upscale": 1.0 | 2.0 | 3.0 | 4.0,
  "deskew": false | true,
  "highcontrast": false | true,
  "pdf_dpi": 150 | 200 | 300 | 600,
  "pdf_page": 1
}
```

Defaults: `upscale: 2.0`, `deskew: false`, `highcontrast: false`, `pdf_dpi: 300`, `pdf_page: 1`.

### Extraction Parameters

**POST `/api/jobs/<job_id>/extract`**

```json
{
  "api_key": "GEMINI_API_KEY or null (uses GEMINI_API_KEY env var)",
  "square_cm": 1.0,
  "max_output_tokens": 65536
}
```

For field-wall profiles, `square_cm` (grid square size in centimeters) is **required**.

For illustrator diagrams, `square_cm` is ignored.

### Validation Parameters

**POST `/api/jobs/<job_id>/validate`**

```json
{
  "monotonic_tolerance": 0.02,
  "top_continuity_tolerance": 0.10,
  "max_depth": 5.0
}
```

All values in meters. Defaults are `0.02`, `0.10`, `5.0` respectively.

### Grid Configuration

**POST `/api/jobs/<job_id>/convert`**

```json
{
  "grid_config": {
    "faces": [
      {
        "name": "South",
        "surface_z": 100.0
      }
    ],
    "originX": 0.0,
    "originY": 0.0,
    "bearing_deg": 0.0
  }
}
```

OR use the starter:

```
GET /api/jobs/<job_id>/gridconfig/starter
```

### Trench Build

**POST `/api/trenches/<label>/build`**

Posting without a `grid` key writes nothing and returns a starter config:

```json
{
  "needs_grid": true,
  "starter": { "faces": { "North": { "originX": 0, "originY": 0, "surfaceZ": 100, "bearing_deg": 90 } } },
  "notes": ["…"]
}
```

Posting with a filled-in `grid` starts the build:

```json
{
  "grid": { "faces": { "North": { "originX": 0, "originY": 0, "surfaceZ": 100, "bearing_deg": 90 } } },
  "correlation": { "North:3": "5" },
  "series_order": ["Locus 1 (10YR 5/4)", "Locus 3 (7.5YR 4/3)"]
}
```

`correlation` maps `"wall_label:locusNumber"` to a canonical locus number, for a
deposit recorded under different numbers on different walls. `series_order` is
derived from the walls when omitted.

The build refuses rather than guessing in seven cases — unlabelled jobs,
un-normalized walls, duplicate wall labels, placeholder registration, faces
missing from the grid, zero interface points, and contradictory layer order.
Each returns `400` with a specific message. See [combine walls into one
trench](../workflows/09-multi-wall-trench.md).

Unlike the single-job convert, **placeholder registration is fatal here.**
Identical starter values lay every wall along the same bearing, producing a row
of parallel walls instead of walls around a pit.

---

## Error Responses

All error responses return HTTP 4xx or 5xx with JSON:

```json
{
  "error": "description of what went wrong"
}
```

Common errors:

- `400` — Missing required parameter or precondition not met (e.g., "run preprocess first")
- `400` — API key missing (`GEMINI_API_KEY` not set and not provided in request)
- `400` — File type not supported (e.g., `.bmp` instead of `.png`)
- `400` — Invalid JSON input (e.g., grid_config malformed)
- `404` — Job ID or file path not found

---

### Harris Matrix errors and warnings

Harris error responses add a stable `code` and may include `details`:

```json
{
  "error": "Matrix graph is invalid: cycle.",
  "code": "invalid_matrix",
  "details": {
    "error_codes": ["cycle"]
  }
}
```

Route-level codes are:

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `invalid_request` | The JSON body or typed fields are invalid. |
| 400 | `invalid_matrix_id` | Matrix ID is not exactly 12 lowercase hexadecimal characters. |
| 400 | `matrix_id_mismatch` | Body and URL identify different matrices. |
| 400 | `invalid_matrix` | Persisted schema or graph validation failed; `details.error_codes` may name graph errors. |
| 400 | `source_import_error` | A requested job is missing, unsafe, malformed, or unsupported. |
| 400 | `suggestion_generation_error` | Conservative proposal generation could not complete. |
| 400 | `suggestion_review_error` | The requested review would create an invalid interpretation. |
| 400 | `matrix_render_error` | A matrix cannot be rendered, including the 250-unit limit. |
| 404 | `matrix_not_found` | No stored matrix has the valid ID. |
| 404 | `suggestion_not_found` | The suggestion ID is absent from the matrix. |
| 409 | `revision_conflict` | Another save advanced the revision; expected and actual revisions are returned. |

Graph error codes are `missing-unit`, `self-relation`,
`duplicate-relation`, `overlapping-correlation`,
`relation-within-correlation`, and `cycle`. Validation warnings are
`redundant-relation`, `isolated-unit`, and `generic-label`. A redundant
relationship remains in saved JSON but is omitted from SVG display edges by
transitive reduction.

Suggestions are proposals requiring individual review. The API never accepts
them automatically and never treats the resulting matrix as scientifically
verified.

---

## File URLs

Routes returning file URLs include a `_url` suffix (e.g., `file_url`, `points_csv_url`). These URLs are relative paths that can be fetched with:

```
GET /api/jobs/<job_id>/file?path=<relative_path>
```

### Visualizer model response

`GET /api/jobs/<job_id>/visualizer-files` preserves its existing scan,
extraction, and calibration keys. When a supported
`06_gempy_model/trench_model_viewer.json` contains at least one existing OBJ,
the response additionally contains:

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
        "url": "/api/jobs/abc123def456/file?path=06_gempy_model/trench_model_meshes/Topsoil.obj"
      }
    ],
    "lith_block_url": "/api/jobs/abc123def456/file?path=06_gempy_model/trench_model_lith_block.npz",
    "volume": {
      "schema_version": 1,
      "format": "raw",
      "dtype": "uint16-le",
      "layout": "C",
      "axes": ["x", "y", "z"],
      "shape": [50, 50, 30],
      "url": "/api/jobs/abc123def456/file?path=06_gempy_model/trench_model_lith_block.bin",
      "lithologies": [
        {
          "id": 1,
          "name": "Topsoil"
        }
      ]
    },
    "warnings": []
  }
}
```

The response replaces manifest `mesh_path` and `lith_block_path` values with
validated job-file URLs; filesystem paths are never returned. A metadata
`model_outputs.viewer_manifest` path is preferred when it resolves inside the
job. Otherwise the route uses the durable conventional manifest path above,
so a server restart does not depend on the in-memory GemPy task record.

A missing OBJ is omitted and named in `model3d.warnings`; other readable
surfaces remain available. If no surface exists, the route omits `model3d`.
A missing lithology archive omits `lith_block_url` without affecting surfaces.
A supported `volume` replaces its manifest `path` with a validated job-file
`url`. A missing binary or unsupported dtype, layout, axes, shape, or path
omits `volume`, adds a warning, and preserves surface viewing. Malformed JSON,
unsupported top-level schemas, absolute paths outside the job, and relative
traversal are ignored safely without breaking the existing 2D payload.
Surface and lithology names are returned only as JSON data.

The browser keeps `lith_block_url` as the discoverable NumPy
scientific/download artifact. It fetches `volume.url` for the separate raw
little-endian `uint16` transport used by the classified-cell renderer.

---

## Under the Hood

All routes are registered as Flask Blueprints and reside in `poggio_webapp/backend/routes/`. The main application factory is in `poggio_webapp/backend/__init__.py`.

Task execution uses a thread pool. Task IDs are UUIDs. Long-running Gemini calls may exceed network timeouts; the frontend retries periodically.

---

## Frontend Integration

The vanilla JavaScript UI in `poggio_webapp/static/app/` calls these
endpoints from stages:

- **Scan stage** — `/api/jobs`, `/scan`, `/preprocess`
- **Extract stage** — `/extract` or `/extract/upload`
- **Editor stage** — `/boundaries/manual` (manual tracing only)
- **Processing stage** — `/normalize`, `/validate`, `/convert`
- **Visualize stage** — `/gempy`, `/visualizer-files`
- **Marker workflows** — `/markers/*` (experimental)
- **Harris Matrix dashboard and editor** — `/api/harris-matrices`,
  `/api/harris-source-jobs`, source import, individual suggestion review, and
  JSON/SVG exports
