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
verified_against: a8b58f1
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
| `/api/jobs/<job_id>/visualizer-files` | GET | none | `{...file_urls}` | No | supported | List available visualizer assets |
| `/` | GET | none | HTML | No | supported | Render React web UI |
| `/visualizer` | GET | none | HTML | No | supported | 3D model viewer page |

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

## File URLs

Routes returning file URLs include a `_url` suffix (e.g., `file_url`, `points_csv_url`). These URLs are relative paths that can be fetched with:

```
GET /api/jobs/<job_id>/file?path=<relative_path>
```

---

## Under the Hood

All routes are registered as Flask Blueprints and reside in `poggio_webapp/backend/routes/`. The main application factory is in `poggio_webapp/backend/__init__.py`.

Task execution uses a thread pool. Task IDs are UUIDs. Long-running Gemini calls may exceed network timeouts; the frontend retries periodically.

---

## Frontend Integration

The React UI in `poggio_webapp/static/app/` calls these endpoints from stages:

- **Scan stage** — `/api/jobs`, `/scan`, `/preprocess`
- **Extract stage** — `/extract` or `/extract/upload`
- **Editor stage** — `/boundaries/manual` (manual tracing only)
- **Processing stage** — `/normalize`, `/validate`, `/convert`
- **Visualize stage** — `/gempy`, `/visualizer-files`
- **Marker workflows** — `/markers/*` (experimental)
