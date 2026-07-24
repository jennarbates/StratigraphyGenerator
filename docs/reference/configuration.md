---
title: Configuration
audience: developer
status: current
source_files:
  - poggio_webapp/backend/config.py
  - poggio_webapp/backend/__init__.py
  - poggio_webapp/app.py
  - poggio_webapp/requirements.txt
  - requirements-docs.txt
verified_against: a8b58f1
---

# Configuration

This reference documents environment variables, dependencies, and configuration paths.

## Environment Variables

### Required for AI Extraction

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `GEMINI_API_KEY` | Google Gemini Vision API authentication | none | `AIza...` |

Without `GEMINI_API_KEY`, the `/api/jobs/<job_id>/extract` and marker-detection routes return HTTP 400.

### Optional

| Variable | Purpose | Default |
|----------|---------|---------|
| `FLASK_ENV` | Flask development mode | `production` |
| `FLASK_DEBUG` | Enable debug mode and auto-reload | `0` |

### Not Configurable (Hardcoded)

The application does not read environment variables for:

- Job storage directory (always `poggio_webapp/jobs/`)
- Static file directory (always `poggio_webapp/static/`)
- Template directory (always `poggio_webapp/templates/`)
- Allowed file extensions (hardcoded in `config.py`)

---

## Application Dependencies

### Core Runtime (in `requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | latest | Web framework |
| `opencv-python-headless` | latest | Image processing |
| `numpy` | latest | Numerical arrays |
| `pandas` | latest | Data manipulation |
| `pillow` | latest | Image I/O |
| `google-genai` | latest | Gemini Vision API client |
| `pydantic` | latest | Data validation |
| `pdf2image` | latest | PDF → image conversion |

### Optional (Stage 06: GemPy 3D Modeling)

The following are commented in `requirements.txt` because they are heavy to install and only needed if you build 3D models:

```
gempy
gempy_viewer
```

Install them with:

```bash
pip install gempy gempy_viewer --break-system-packages
```

Then `/api/jobs/<job_id>/gempy` becomes available.

### Documentation Build (in `requirements-docs.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `mkdocs` | 1.6.1 | Documentation generator |
| `mkdocs-material` | 9.7.7 | Material theme |
| `pymdown-extensions` | 11.0.1 | Markdown extensions (Mermaid, tabs) |
| `PyYAML` | 6.0.3 | YAML parsing for site config |

### Test Dependencies

Tests use the application dependencies plus:

- `pytest` — unit test framework
- `pytest-cov` — coverage reporting

---

## Filesystem Structure

### Job Storage

Jobs are created in `poggio_webapp/jobs/` with structure:

```
jobs/
├── <job_id>/
│   ├── 01_scan/
│   ├── 02_preprocess/
│   ├── 03_extraction/
│   ├── 04_normalize_validate/
│   ├── 05_convert_coords/
│   ├── 06_gempy_model/
│   ├── meta.json               # Job state (created on init)
│   ├── editor_meta.json        # Manual editor state (if applicable)
│   └── extraction_output.json  # Manual extraction (if applicable)
```

The application creates these directories automatically on first POST to `/api/jobs`.

**Job ID format:** 12-character lowercase hexadecimal (UUID)

### Scan Upload Directory

Scans are saved to `01_scan/` with their original filename. Allowed extensions (in `backend/config.py`):

```python
ALLOWED_SCAN_EXT = {".png", ".jpg", ".jpeg", ".pdf", ".tif", ".tiff"}
```

### Preprocessed Output

Preprocessing saves to `02_preprocess/` with filenames:

- `clean.png` — deskewed, rotated image
- `deskew_angle.txt` — rotation angle (degrees)
- others (context-dependent)

### Extraction Output

Extraction saves to `03_extraction/` with names:

- `output.json` — AI extraction (Gemini-generated)
- `field_wall.json` — AI extraction (field-wall variant)
- `uploaded.json` — user-provided JSON

### Normalized Data

Normalization saves to `04_normalize_validate/`:

- `output_clean.json` — structured, validated data
- validation report (in `meta.json`)

### Coordinate Conversion

Conversion saves to `05_convert_coords/`:

- `points.csv` — site-wide 3D points
- `orientations_csv` — optional orientations

### GemPy Model

Model building saves to `06_gempy_model/`:

- `trench_model.gempy` — pickled GemPy model
- others (GemPy-specific outputs)

### Meta File Format

`meta.json` contains:

```json
{
  "job_id": "abc123def456",
  "sheet_type": "illustrator" | "fieldwall",
  "scan_path": "...",
  "scan_filename": "...",
  "clean_image_path": "...",
  "extraction_path": "...",
  "extraction_task_id": "...",
  "normalized_path": "...",
  "normalization_log": "...",
  "validation_report": {
    "errors": [...],
    "warnings": [...],
    "ok": true | false
  },
  "points_csv": "...",
  "orientations_csv": "...",
  "task_id": "...",
  "gempy_task_id": "...",
  "status": "editing" | "complete" | "error" | ...,
  "stage": "normalizing" | "validating" | ...,
  "message": "...",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

All paths are absolute filesystem paths.

---

## Flask Configuration

### Application Factory

The Flask app is created by `backend.create_app()` in `poggio_webapp/backend/__init__.py`:

```python
def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(STATIC_DIR),
        template_folder=str(TEMPLATES_DIR),
        static_url_path="/static",
    )
    register_blueprints(app)
    # ... error handlers
    return app
```

### Blueprints

All routes are registered as blueprints from `backend.routes`:

- `pages_bp` — UI pages (`/`, `/visualizer`)
- `jobs_bp` — job lifecycle
- `scans_bp` — scan upload
- `preprocess_bp` — image preprocessing
- `extraction_bp` — AI/manual extraction
- `features_bp` — feature detection
- `markers_bp` — marker detection (experimental)
- `manual_bp` — manual tracing
- `task_status_bp` — task polling
- `processing_bp` — normalize/validate/convert
- `gempy_bp` — 3D model building

### Error Handling

All HTTP errors return JSON:

```json
{
  "error": "description",
  "status": 400
}
```

Unhandled exceptions return HTTP 500 with error logged.

---

## Runtime Initialization

### Startup

Starting the application:

```bash
cd poggio_webapp
python app.py
```

This:

1. Creates the Flask app via `backend.create_app()`
2. Registers all blueprints
3. Ensures `poggio_webapp/jobs/` directory exists
4. Starts the Flask development server on `http://localhost:5000/`

The development server reloads on Python file changes (default Flask behavior).

### Directories Created Automatically

- `poggio_webapp/jobs/` — created if it does not exist
- Each job's subdirectories — created on first job creation

---

## Scaling and Persistence

### Limitations

- **In-memory tasks:** Asynchronous tasks (extraction, GemPy build) are stored in memory. If the server restarts, running tasks are lost.
- **File-based jobs:** Completed job data (meta.json, artifacts) persists on disk.
- **Single-threaded task queue:** Tasks run in a thread pool; concurrent extractions may wait if the pool is saturated.

### Restart Behavior

After a server restart:

1. Old job folders remain on disk.
2. Running task data is lost.
3. Frontend must check `/api/tasks/<task_id>` and get an error; job status can be inferred from `meta.json`.

---

## Preprocessing Tuning

Preprocessing parameters can be adjusted per-job via `/api/jobs/<job_id>/preprocess`:

| Parameter | Range | Notes |
|-----------|-------|-------|
| `upscale` | 1.0, 2.0, 3.0, 4.0 | Higher = better detail but slower; default 2.0 for low-res scans |
| `deskew` | boolean | Auto-rotate to straighten tilted images; default false |
| `highcontrast` | boolean | Boost brightness contrast; default false |
| `pdf_dpi` | 150, 200, 300, 600 | PDF rendering resolution; default 300 |
| `pdf_page` | 1, 2, ... | Which page to extract (1-indexed); default 1 |

---

## Validation Thresholds

Validation parameters can be adjusted per-job via `/api/jobs/<job_id>/validate`:

| Parameter | Default | Unit | Notes |
|-----------|---------|------|-------|
| `monotonic_tolerance` | 0.02 | meters | Allow bottom boundary to be slightly above previous layer bottom (overlap detection) |
| `top_continuity_tolerance` | 0.10 | meters | Allow gap between layer bottom and next layer top |
| `max_plausible_depth` | 5.0 | meters | Flag deeper measurements as implausibly deep (warning) |

These can be overridden per-request; defaults come from `poggio_webapp/pipeline/validator.py`.

---

## Under the Hood

### Task Execution

Asynchronous tasks use Python's `threading.Thread` and a task registry in `backend/tasks.py`. No external job queue (Celery, etc.) is used.

### Job Metadata Locking

In `app.py`, meta file access is protected by `threading.Lock` to avoid corruption during concurrent edits:

```python
_EDITOR_META_LOCK = threading.Lock()
_STATUS_MESSAGES_LOCK = threading.Lock()
```

### Static and Template Paths

All paths are resolved relative to `poggio_webapp/`:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
```
