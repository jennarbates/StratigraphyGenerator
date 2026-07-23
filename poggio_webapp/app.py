"""
Trench Digitization Pipeline — web GUI backend.

Wraps the original numbered-stage scripts (02_preprocess ... 06_gempy_model)
as a Flask API, one job directory per session, so the full pipeline —
scan -> preprocess -> AI extraction -> normalize -> validate -> convert
coords -> GemPy model -> visualize — can be driven from a browser.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""

import json
import os
import threading
import time
import traceback
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory, abort

from pipeline import preprocess as p_preprocess
from pipeline import normalizer as p_normalizer
from pipeline import validator as p_validator
from pipeline import convert_coords as p_convert_coords
# extract_illustrator / extract_fieldwall / build_gempy pull in heavier,
# optional dependencies (google-genai, gempy) -- imported lazily inside the
# routes that need them so the rest of the app still runs without them.

BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(exist_ok=True)

ALLOWED_SCAN_EXT = {".png", ".jpg", ".jpeg", ".pdf", ".tif", ".tiff"}

app = Flask(__name__, static_folder="static", template_folder="templates")

# In-memory task registry for long-running (async) stages: extraction, gempy.
# {task_id: {"status": "running"|"done"|"error", "result": ..., "error": ..., "log": [...]}}
TASKS = {}


# ---------------------------------------------------------------------------
# job helpers
# ---------------------------------------------------------------------------

def job_dir(job_id):
    d = JOBS_DIR / job_id
    if not d.exists():
        abort(404, description="unknown job id")
    return d


def meta_path(job_id):
    return job_dir(job_id) / "meta.json"


def load_meta(job_id):
    mp = meta_path(job_id)
    if not mp.exists():
        return {}
    return json.loads(mp.read_text())


def save_meta(job_id, meta):
    meta_path(job_id).write_text(json.dumps(meta, indent=2))


def rel_url(job_id, abs_path):
    """Build the /api/jobs/<id>/file?path=... URL for a path inside the job dir."""
    rel = os.path.relpath(str(abs_path), str(job_dir(job_id)))
    return f"/api/jobs/{job_id}/file?path={rel}"


def safe_job_path(job_id, rel_path):
    """Resolve rel_path under the job dir, refusing to escape it."""
    base = job_dir(job_id).resolve()
    target = (base / rel_path).resolve()
    if base not in target.parents and target != base:
        abort(400, description="invalid path")
    return target


def start_task(fn, *args, **kwargs):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running", "result": None, "error": None, "log": [],
                       "started_at": time.time()}

    def runner():
        try:
            def log_cb(msg):
                TASKS[task_id]["log"].append(str(msg))
            if "progress_cb" in fn.__code__.co_varnames:
                kwargs["progress_cb"] = log_cb
            if "log_cb" in fn.__code__.co_varnames:
                kwargs["log_cb"] = log_cb
            result = fn(*args, **kwargs)
            TASKS[task_id]["result"] = result
            TASKS[task_id]["status"] = "done"
        except Exception as e:
            TASKS[task_id]["error"] = _friendly_error(e)
            TASKS[task_id]["error_detail"] = f"{e}\n{traceback.format_exc()}"
            TASKS[task_id]["status"] = "error"

    threading.Thread(target=runner, daemon=True).start()
    return task_id


# ---------------------------------------------------------------------------
# static pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.route("/visualizer")
def visualizer():
    return send_from_directory(app.static_folder, "visualizer.html")


@app.route("/api/jobs/<job_id>/visualizer-files")
def visualizer_files(job_id):
    """Everything the visualizer can auto-load for this job, so the user
    doesn't have to re-pick files the server already has. JSONs are served
    as-is; the visualizer normalizes either extraction shape client-side."""
    meta = load_meta(job_id)
    out = {"sheet_type": meta.get("sheet_type"), "jsons": []}

    # Image: preprocessed clean image if present, else the raw scan —
    # unless the scan is a PDF, which a browser <img> can't show.
    img = meta.get("clean_image_path") or meta.get("scan_path")
    if img and Path(img).exists() and not img.lower().endswith(".pdf"):
        out["image_url"] = rel_url(job_id, Path(img))

    def add(label, path_str, front=False):
        if path_str and Path(path_str).exists():
            entry = {"label": label, "url": rel_url(job_id, Path(path_str))}
            out["jsons"].insert(0, entry) if front else out["jsons"].append(entry)

    add("normalized", meta.get("normalized_path"))
    add("raw extraction", meta.get("extraction_path"))

    # Field-wall JSON is served raw: the visualizer adapts the
    # FieldWallProfile shape itself (see ingest() in visualizer.html), and
    # unlike fieldwall_to_profiles() it keeps topBoundary and features —
    # the Python adapter only carries what convert() needs. Serving both
    # raw and normalized also keeps A/B compare working for field sheets.

    return jsonify(out)


# ---------------------------------------------------------------------------
# job lifecycle
# ---------------------------------------------------------------------------

@app.route("/api/jobs", methods=["POST"])
def create_job():
    job_id = uuid.uuid4().hex[:12]
    d = JOBS_DIR / job_id
    for sub in ["01_scan", "02_preprocess", "03_extraction",
                "04_normalize_validate", "05_convert_coords", "06_gempy_model"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    save_meta(job_id, {"job_id": job_id, "sheet_type": None})
    return jsonify({"job_id": job_id})


@app.route("/api/jobs/<job_id>/file")
def get_file(job_id):
    rel = request.args.get("path")
    if not rel:
        abort(400, description="missing path")
    path = safe_job_path(job_id, rel)
    if not path.exists():
        abort(404)
    return send_file(path)


# ---------------------------------------------------------------------------
# stage 1: upload scan
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/scan", methods=["POST"])
def upload_scan(job_id):
    d = job_dir(job_id)
    sheet_type = request.form.get("sheet_type", "illustrator")
    if sheet_type not in ("illustrator", "fieldwall"):
        abort(400, description="sheet_type must be 'illustrator' or 'fieldwall'")

    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, description="no file uploaded")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_SCAN_EXT:
        abort(400, description=f"unsupported file type {ext}")

    scan_path = d / "01_scan" / file.filename
    file.save(scan_path)

    dims = None
    recommendation = None
    if ext != ".pdf":
        try:
            width, height = p_preprocess.probe_dimensions(str(scan_path))
            dims = {"width": width, "height": height}
            recommendation = p_preprocess.recommend_upscale(width, height)
        except Exception:
            pass  # non-fatal: recommendation is a nicety, not required to proceed

    meta = load_meta(job_id)
    meta["sheet_type"] = sheet_type
    meta["scan_path"] = str(scan_path)
    meta["scan_filename"] = file.filename
    save_meta(job_id, meta)

    return jsonify({
        "scan_url": rel_url(job_id, scan_path),
        "sheet_type": sheet_type,
        "is_pdf": ext == ".pdf",
        "dimensions": dims,
        "recommended_upscale": recommendation,
    })


# ---------------------------------------------------------------------------
# stage 2: preprocess
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/preprocess", methods=["POST"])
def run_preprocess(job_id):
    meta = load_meta(job_id)
    if "scan_path" not in meta:
        abort(400, description="upload a scan first")

    body = request.get_json(force=True, silent=True) or {}
    outdir = job_dir(job_id) / "02_preprocess"

    try:
        result = p_preprocess.run_preprocess(
            meta["scan_path"], str(outdir),
            upscale=float(body.get("upscale", 2.0)),
            deskew_flag=bool(body.get("deskew", False)),
            highcontrast=bool(body.get("highcontrast", False)),
            pdf_dpi=int(body.get("pdf_dpi", 300)),
            pdf_page=int(body.get("pdf_page", 1)),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    outputs = {k: rel_url(job_id, v) for k, v in result["outputs"].items()}
    meta["clean_image_path"] = result["outputs"]["clean"]
    save_meta(job_id, meta)

    return jsonify({"deskew_angle": result["deskew_angle"], "outputs": outputs})


# ---------------------------------------------------------------------------
# stage 3: extraction (async — calls Gemini)
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/extract", methods=["POST"])
def run_extract(job_id):
    meta = load_meta(job_id)
    if "clean_image_path" not in meta:
        abort(400, description="run preprocess first")

    body = request.get_json(force=True, silent=True) or {}
    api_key = body.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "no Gemini API key provided (and GEMINI_API_KEY not set "
                                  "in the server environment)"}), 400

    image_path = meta["clean_image_path"]
    out_dir = job_dir(job_id) / "03_extraction"
    sheet_type = meta.get("sheet_type", "illustrator")
    max_output_tokens = int(body.get("max_output_tokens", 65536))

    try:
        if sheet_type == "illustrator":
            from pipeline import extract_illustrator as p_extract_illustrator
            out_path = out_dir / "output.json"
            task_id = start_task(
                p_extract_illustrator.run_extraction,
                image_path, str(out_path), api_key,
                max_output_tokens=max_output_tokens,
            )
        else:
            square_cm = body.get("square_cm")
            if not square_cm:
                return jsonify({"error": "square_cm is required for field-wall sheets"}), 400
            from pipeline import extract_fieldwall as p_extract_fieldwall
            out_path = out_dir / "field_wall.json"
            task_id = start_task(
                p_extract_fieldwall.run_extraction,
                image_path, float(square_cm), str(out_path), api_key,
                max_output_tokens=max_output_tokens,
            )
    except ImportError as e:
        return jsonify({"error": f"missing dependency: {e}. Install with "
                                  f"`pip install google-genai pillow pydantic --break-system-packages`."}), 400

    meta["extraction_path"] = str(out_path)
    meta["extraction_task_id"] = task_id
    # a normalize run from a previous extraction no longer describes this one
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)
    return jsonify({"task_id": task_id})


@app.route("/api/jobs/<job_id>/extract/upload", methods=["POST"])
def upload_extraction(job_id):
    """Reuse a previous extraction JSON instead of calling Gemini.

    Accepts a multipart .json upload, checks that it parses and matches one
    of the two known schemas, and installs it as this job's extraction so
    normalize / validate / convert / visualize pick it up unchanged. Does
    not require preprocess to have run — the whole point is skipping the
    image-analysis path.
    """
    meta = load_meta(job_id)

    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, description="no file uploaded")
    if os.path.splitext(file.filename)[1].lower() != ".json":
        abort(400, description="expected a .json file")

    raw = file.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"not valid JSON: {e}"}), 400

    if isinstance(data, dict) and "trenchProfiles" in data:
        detected = "illustrator"
    elif isinstance(data, dict) and p_convert_coords.is_field_wall(data):
        detected = "fieldwall"
    else:
        return jsonify({"error": "this JSON is neither an illustrator extraction "
                                  "(trenchProfiles) nor a field-wall extraction "
                                  "(loci/layers) — refusing to install it"}), 400

    out_path = job_dir(job_id) / "03_extraction" / "uploaded.json"
    out_path.write_text(raw)

    meta["extraction_path"] = str(out_path)
    meta["sheet_type"] = detected
    meta.pop("extraction_task_id", None)
    meta.pop("normalized_path", None)  # belongs to the previous extraction
    save_meta(job_id, meta)

    return jsonify({"raw_json": raw, "sheet_type": detected,
                    "file_url": rel_url(job_id, out_path)})


# ---------------------------------------------------------------------------
# stage 3 alternative for field-wall sheets: CV marker detection
# (detect_markers finds the recorder's circle-marked vertices — geometry CV
# can't fabricate; assign_markers has Gemini only CLASSIFY those fixed
# points and read the sheet's labels)
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/markers/preview", methods=["POST"])
def markers_preview(job_id):
    """Write the rotated working copy the user clicks reference points on.
    All later pixel coordinates are in this rotated frame."""
    meta = load_meta(job_id)
    if "scan_path" not in meta:
        abort(400, description="upload a scan first")
    if meta["scan_path"].lower().endswith(".pdf"):
        return jsonify({"error": "marker detection works on photo scans, not "
                                  "PDFs — upload the photo directly"}), 400
    body = request.get_json(force=True, silent=True) or {}
    rotate = int(body.get("rotate", 0))
    from pipeline import detect_markers as p_detect_markers
    out_dir = job_dir(job_id) / "03_extraction"
    out_path = out_dir / "marker_source_rotated.png"
    try:
        w, h = p_detect_markers.write_rotated_preview(
            meta["scan_path"], rotate, str(out_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    meta["marker_rotate"] = rotate
    save_meta(job_id, meta)
    return jsonify({"image_url": rel_url(job_id, out_path),
                    "width": w, "height": h})


@app.route("/api/jobs/<job_id>/markers/detect", methods=["POST"])
def markers_detect(job_id):
    meta = load_meta(job_id)
    if "scan_path" not in meta:
        abort(400, description="upload a scan first")
    body = request.get_json(force=True, silent=True) or {}
    for k in ("square_cm", "origin_px", "ref_px", "ref_meters", "bottom_px_y"):
        if body.get(k) in (None, "", []):
            return jsonify({"error": f"{k} is required — click the wall's "
                                      "top-left, top-right, and lowest point, "
                                      "and give the real width between the top "
                                      "corners"}), 400
    from pipeline import detect_markers as p_detect_markers
    out_dir = job_dir(job_id) / "03_extraction"
    try:
        result = p_detect_markers.run_detect(
            meta["scan_path"],
            origin_px=body["origin_px"], ref_px=body["ref_px"],
            ref_meters=float(body["ref_meters"]),
            bottom_px_y=float(body["bottom_px_y"]),
            square_cm=float(body["square_cm"]),
            out_dir=str(out_dir),
            rotate=int(body.get("rotate", meta.get("marker_rotate", 0))),
            min_marker_paper_mm=float(body.get("min_marker_paper_mm", 0.5)),
            max_marker_paper_mm=float(body.get("max_marker_paper_mm", 2.5)),
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    markers_path = out_dir / "markers.json"
    markers_path.write_text(json.dumps(result["markers"]))
    meta["markers_path"] = str(markers_path)
    meta["marker_square_cm"] = float(body["square_cm"])
    save_meta(job_id, meta)

    return jsonify({
        "n_accepted": result["n_accepted"],
        "n_rejected_in_box": result["n_rejected_in_box"],
        "px_per_m": result["px_per_m"],
        "debug_image_url": rel_url(job_id, result["debug_image"]),
        "csv_url": rel_url(job_id, result["csv"]),
    })


@app.route("/api/jobs/<job_id>/markers/assign", methods=["POST"])
def markers_assign(job_id):
    """Async (calls Gemini): classify the detected markers, assemble the
    extraction JSON, and install it as this job's extraction."""
    meta = load_meta(job_id)
    if "markers_path" not in meta:
        abort(400, description="run marker detection first")
    body = request.get_json(force=True, silent=True) or {}
    api_key = body.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "no Gemini API key provided (and "
                                  "GEMINI_API_KEY not set in the server "
                                  "environment)"}), 400

    markers = json.loads(Path(meta["markers_path"]).read_text())
    rotated = job_dir(job_id) / "03_extraction" / "marker_source_rotated.png"
    if not rotated.exists():
        abort(400, description="rotated working image missing — re-run "
                               "marker detection")
    out_path = job_dir(job_id) / "03_extraction" / "field_wall_cv.json"

    try:
        from pipeline import assign_markers as p_assign_markers
        task_id = start_task(
            p_assign_markers.run_assign,
            str(rotated), markers, meta.get("marker_square_cm", 20.0),
            str(out_path), api_key,
            max_output_tokens=int(body.get("max_output_tokens", 65536)),
        )
    except ImportError as e:
        return jsonify({"error": f"missing dependency: {e}. Install with "
                                  f"`pip install google-genai pillow pydantic "
                                  f"--break-system-packages`."}), 400

    meta["extraction_path"] = str(out_path)
    meta["extraction_task_id"] = task_id
    meta["sheet_type"] = "fieldwall"
    meta.pop("normalized_path", None)
    save_meta(job_id, meta)
    return jsonify({"task_id": task_id})


@app.route("/api/tasks/<task_id>")
def task_status(task_id):
    t = TASKS.get(task_id)
    if not t:
        abort(404)
    resp = {"status": t["status"], "log": t["log"],
            "elapsed_seconds": round(time.time() - t["started_at"])}
    if t["status"] == "done":
        r = t["result"]
        # extraction returns str or (str, warning); gempy returns a dict
        if isinstance(r, tuple):
            resp["raw_json"] = r[0]
            resp["warning"] = r[1]
        elif isinstance(r, str):
            resp["raw_json"] = r
        else:
            resp["result"] = r
    elif t["status"] == "error":
        resp["error"] = t["error"]
        resp["error_detail"] = t.get("error_detail")
    return jsonify(resp)


def _friendly_error(e):
    """Translate the errors users actually hit into what-to-do-next text.
    The raw exception + traceback still travels alongside as error_detail;
    this string is the one shown in the red banner."""
    import json as _json
    if isinstance(e, _json.JSONDecodeError):
        return (f"{e} — this is almost always a truncated Gemini response "
                 "(cut off by the output-token limit). Go back to the "
                 "Extraction step, raise max_output_tokens, and re-run.")

    # Gemini API errors, matched by status code so this works whether the
    # SDK raises ServerError or ClientError.
    code = getattr(e, "code", None)
    if code in (504, 503, 500, 502):
        return (
            f"Gemini's servers failed with a {code} on every retry attempt. "
            "This is a problem on Google's side, not with your scan or this "
            "app. What to do: (1) wait 15–30 minutes and try once more — "
            "don't hammer re-run, each attempt re-sends the whole image and "
            "uses your quota; (2) if it persists, check Google's status at "
            "https://status.cloud.google.com and the AI Studio forum; "
            "(3) as a workaround, shrink the request — lower "
            "max_output_tokens, or reduce MAX_SEND_DIMENSION in the "
            "extraction module. If it still fails after a day, report it "
            "on this project's issue tracker with the log above."
        )
    if code == 429:
        return (
            "Gemini says your API key is out of quota (429). Retrying will "
            "not help until the quota resets. Check your usage and limits "
            "at https://aistudio.google.com — free-tier keys have daily "
            "caps that a few large extractions can exhaust. Wait for the "
            "reset (or use a key from a project with billing enabled), "
            "then re-run once."
        )
    if code in (400, 401, 403):
        return (
            f"Gemini rejected the request ({code}) — usually an invalid or "
            "restricted API key, or a key from a project without the "
            "Gemini API enabled. Double-check the key you pasted (get one "
            "at https://aistudio.google.com/apikey) and re-run. Retrying "
            "with the same key will keep failing."
        )
    return str(e)


# ---------------------------------------------------------------------------
# stage 4: normalize + validate
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/normalize", methods=["POST"])
def run_normalize(job_id):
    meta = load_meta(job_id)
    if "extraction_path" not in meta:
        abort(400, description="run extraction first")

    out_path = job_dir(job_id) / "04_normalize_validate" / "output_clean.json"
    try:
        data, log = p_normalizer.run_normalize(meta["extraction_path"], str(out_path))
    except Exception as e:
        return jsonify({"error": _friendly_error(e)}), 400

    meta["normalized_path"] = str(out_path)
    save_meta(job_id, meta)
    return jsonify({"data": data, "log": log, "file_url": rel_url(job_id, out_path)})


@app.route("/api/jobs/<job_id>/validate", methods=["POST"])
def run_validate(job_id):
    meta = load_meta(job_id)
    path = meta.get("normalized_path") or meta.get("extraction_path")
    if not path:
        abort(400, description="run extraction (and ideally normalize) first")

    body = request.get_json(force=True, silent=True) or {}
    try:
        report = p_validator.run_validate(
            path,
            monotonic_tolerance=float(body.get("monotonic_tolerance",
                                                p_validator.DEFAULT_MONOTONIC_TOLERANCE_M)),
            top_continuity_tolerance=float(body.get("top_continuity_tolerance",
                                                     p_validator.DEFAULT_TOP_CONTINUITY_TOLERANCE_M)),
            max_depth=float(body.get("max_depth", p_validator.DEFAULT_MAX_PLAUSIBLE_DEPTH_M)),
        )
    except Exception as e:
        return jsonify({"error": _friendly_error(e)}), 400

    return jsonify(report)


# ---------------------------------------------------------------------------
# stage 5: coordinate conversion
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/gridconfig/starter", methods=["GET"])
def gridconfig_starter(job_id):
    meta = load_meta(job_id)
    path = meta.get("normalized_path") or meta.get("extraction_path")
    if not path:
        abort(400, description="run extraction first")
    data = json.loads(Path(path).read_text())
    if "trenchProfiles" not in data and not p_convert_coords.is_field_wall(data):
        return jsonify({"error": "this extraction is neither an illustrator sheet "
                                  "(trenchProfiles) nor a field-wall sheet (loci/layers) — "
                                  "nothing to register"}), 400
    cfg = p_convert_coords.make_starter_config(data)
    return jsonify(cfg)


@app.route("/api/jobs/<job_id>/convert", methods=["POST"])
def run_convert(job_id):
    meta = load_meta(job_id)
    path = meta.get("normalized_path") or meta.get("extraction_path")
    if not path:
        abort(400, description="run extraction first")

    body = request.get_json(force=True, silent=True) or {}
    grid = body.get("grid_config")
    if not grid:
        abort(400, description="grid_config is required")

    data = json.loads(Path(path).read_text())
    out_csv = job_dir(job_id) / "05_convert_coords" / "points.csv"

    try:
        result = p_convert_coords.run_convert(data, grid, str(out_csv))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if result["n_points"] == 0:
        return jsonify({"error": "conversion produced 0 points. Either no face in the "
                                  "extraction matched a name in the grid config "
                                  f"(unmatched: {', '.join(result['missing_faces']) or 'none'}), "
                                  "or the layers carry no usable boundary coordinates."}), 400

    meta["points_csv"] = result["points_csv"]
    meta["orientations_csv"] = result["orientations_csv"]
    save_meta(job_id, meta)

    result["points_csv_url"] = rel_url(job_id, result["points_csv"])
    result["orientations_csv_url"] = rel_url(job_id, result["orientations_csv"])
    return jsonify(result)


# ---------------------------------------------------------------------------
# stage 6: GemPy model (async — can take a while)
# ---------------------------------------------------------------------------

@app.route("/api/jobs/<job_id>/gempy", methods=["POST"])
def run_gempy(job_id):
    meta = load_meta(job_id)
    if "points_csv" not in meta:
        abort(400, description="run coordinate conversion first")

    body = request.get_json(force=True, silent=True) or {}
    out_prefix = str(job_dir(job_id) / "06_gempy_model" / "trench_model")

    try:
        from pipeline import build_gempy as p_build_gempy
    except Exception as e:
        return jsonify({"error": f"gempy import failed: {e}. Install with "
                                  f"`pip install gempy gempy_viewer --break-system-packages`."}), 400

    kwargs = dict(
        project_name=body.get("project_name", "trench_model"),
        resolution=tuple(body.get("resolution", [50, 50, 30])),
        extent=body.get("extent"),
        padding_xy=float(body.get("padding_xy", 2.0)),
        padding_z=float(body.get("padding_z", 1.0)),
        series_order=body.get("series_order"),
        make_plot=bool(body.get("make_plot", True)),
        section_direction=body.get("section_direction", "y"),
        vertical_exaggeration=float(body.get("vertical_exaggeration", 5.0)),
        make_meshes=bool(body.get("make_meshes", True)),
        save_model=bool(body.get("save_model", True)),
        make_zoom_plot=bool(body.get("make_zoom_plot", True)),
        zoom_surfaces=body.get("zoom_surfaces"),
        zoom_vertical_exaggeration=body.get("zoom_vertical_exaggeration"),
    )

    task_id = start_task(
        p_build_gempy.run_build,
        meta["points_csv"], meta["orientations_csv"], out_prefix,
        **kwargs,
    )
    return jsonify({"task_id": task_id})


@app.route("/api/jobs/<job_id>/gempy/result/<task_id>")
def gempy_result_urls(job_id, task_id):
    """Convert absolute output paths from a finished gempy task into file URLs."""
    t = TASKS.get(task_id)
    if not t or t["status"] != "done":
        abort(400, description="task not done")
    outputs = t["result"].get("outputs", {})
    urls = {}
    for k, v in outputs.items():
        if isinstance(v, list):
            urls[k] = [rel_url(job_id, p) for p in v]
        else:
            urls[k] = rel_url(job_id, v)
    return jsonify({
        "extent": t["result"].get("extent"),
        "series_order": t["result"].get("series_order"),
        "single_face_note": t["result"].get("single_face_note"),
        "outputs": urls,
    })


if __name__ == "__main__":
    import os as _os
    debug = _os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=int(_os.environ.get("PORT", 5000)))