import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import storage
from backend import create_app
from backend.routes import text_metadata


@pytest.fixture
def route_context(tmp_path, monkeypatch):
    jobs_dir = storage.JOBS_DIR
    app = create_app()
    app.config.update(TESTING=True)
    return SimpleNamespace(client=app.test_client(), jobs_dir=jobs_dir)


def _create_job(
    route_context,
    *,
    job_id="fieldwall-job",
    sheet_type="fieldwall",
    scan=True,
    clean=False,
):
    directory = route_context.jobs_dir / job_id
    (directory / "03_extraction").mkdir(parents=True)
    meta = {
        "job_id": job_id,
        "sheet_type": sheet_type,
    }
    if scan:
        scan_path = directory / "01_scan" / "scan.png"
        scan_path.parent.mkdir()
        scan_path.write_bytes(b"scan")
        meta["scan_path"] = str(scan_path)
    if clean:
        clean_path = directory / "02_preprocess" / "clean.png"
        clean_path.parent.mkdir()
        clean_path.write_bytes(b"clean")
        meta["clean_image_path"] = str(clean_path)
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return directory


def _candidate_payload():
    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "document": {
            "trenchLabel": None,
            "faceLabel": None,
            "date": None,
            "gridSquareCm": None,
            "northArrowPresent": None,
            "illustrators": [],
            "gridTiePoints": [],
            "marginalia": [],
            "otherText": [],
        },
        "loci": [],
    }


def _fieldwall_payload():
    return {
        "trenchLabel": None,
        "faceLabel": None,
        "illustrators": [],
        "date": None,
        "northArrowPresent": None,
        "gridSquareCm": None,
        "gridTiePoints": [],
        "loci": [],
        "layers": [],
        "marginalia": [],
        "source": "extraction",
        "finds": [],
    }


def _verified_payload():
    return {
        "schemaVersion": 1,
        "sheetType": "fieldwall",
        "reviewCompleted": True,
        "document": {
            "trenchLabel": "T104",
            "faceLabel": "Southern baulk",
            "date": "2025",
            "gridSquareCm": 20.0,
            "northArrowPresent": True,
            "illustrators": ["A. Recorder"],
            "gridTiePoints": ["194 m"],
            "marginalia": [],
            "otherText": [],
        },
        "loci": [
            {
                "locusNumber": "1042",
                "munsellRaw": "10YR 5/3",
                "description": "brown silty soil",
            }
        ],
        "audit": [],
    }


def _read_meta(directory):
    return json.loads((directory / "meta.json").read_text(encoding="utf-8"))


def _run_tasks_synchronously(monkeypatch, task_id="text-task-123"):
    task_calls = []

    def fake_start_task(function, *args, **kwargs):
        task_calls.append((function, args, kwargs))
        function(*args, **kwargs)
        return task_id

    monkeypatch.setattr(text_metadata, "start_task", fake_start_task)
    return task_calls


def _mock_successful_extraction(monkeypatch):
    extraction_calls = []
    payload = _candidate_payload()
    fieldwall = _fieldwall_payload()

    def fake_run_fieldwall_extraction(
        image_path,
        square_cm,
        output_path,
        api_key,
        max_output_tokens=65_536,
        progress_cb=None,
    ):
        extraction_calls.append(
            {
                "image_path": image_path,
                "square_cm": square_cm,
                "api_key": api_key,
                "output_path": output_path,
                "max_output_tokens": max_output_tokens,
                "progress_cb": progress_cb,
            }
        )
        raw_json = json.dumps(fieldwall)
        Path(output_path).write_text(raw_json, encoding="utf-8")
        return raw_json, None

    monkeypatch.setattr(
        text_metadata.p_extract_fieldwall,
        "run_extraction",
        fake_run_fieldwall_extraction,
    )
    return payload, extraction_calls


def test_text_metadata_blueprint_registers_all_endpoints(route_context):
    rules = {
        rule.rule for rule in route_context.client.application.url_map.iter_rules()
    }

    assert "/api/jobs/<job_id>/text-extraction" in rules
    assert "/api/jobs/<job_id>/text-verification" in rules
    assert "/api/jobs/<job_id>/text-verification/skip" in rules


def test_unknown_job_returns_404(route_context):
    response = route_context.client.post(
        "/api/jobs/unknown/text-extraction",
        json={"api_key": "secret"},
    )

    assert response.status_code == 404


def test_illustrator_job_is_rejected_for_extraction(route_context):
    _create_job(route_context, sheet_type="illustrator")

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": "secret"},
    )

    assert response.status_code == 400
    assert "field-wall" in response.get_json()["error"]


def test_job_without_uploaded_image_is_rejected(route_context):
    _create_job(route_context, scan=False)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": "secret"},
    )

    assert response.status_code == 400
    assert "upload" in response.get_json()["error"]


def test_missing_api_key_is_rejected(route_context, monkeypatch):
    _create_job(route_context)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={},
    )

    assert response.status_code == 400
    assert "api_key" in response.get_json()["error"]


def test_missing_grid_square_size_is_rejected(route_context):
    _create_job(route_context)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": "secret"},
    )

    assert response.status_code == 400
    assert "square_cm" in response.get_json()["error"]


def test_clean_image_is_preferred_and_async_completion_is_recorded(
    route_context,
    monkeypatch,
):
    directory = _create_job(route_context, clean=True)
    _run_tasks_synchronously(monkeypatch)
    payload, extraction_calls = _mock_successful_extraction(monkeypatch)
    api_key = "never-write-this-key"

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": api_key, "square_cm": 20},
    )

    candidates_path = directory / "03_extraction" / "text_candidates.json"
    extraction_path = directory / "03_extraction" / "field_wall.json"
    meta = _read_meta(directory)
    assert response.status_code == 200
    assert response.get_json() == {"task_id": "text-task-123"}
    assert extraction_calls[0]["image_path"] == meta["clean_image_path"]
    assert extraction_calls[0]["square_cm"] == 20
    assert extraction_calls[0]["output_path"] == str(extraction_path)
    assert json.loads(candidates_path.read_text(encoding="utf-8")) == payload
    assert meta["extraction_path"] == str(extraction_path)
    assert meta["text_candidates_path"] == str(candidates_path)
    assert meta["text_verification_status"] == "ready_for_review"
    assert meta["text_extraction_task_id"] == "text-task-123"
    assert api_key not in (directory / "meta.json").read_text(encoding="utf-8")


def test_scan_image_is_used_as_fallback(route_context, monkeypatch):
    directory = _create_job(route_context)
    _run_tasks_synchronously(monkeypatch)
    _, extraction_calls = _mock_successful_extraction(monkeypatch)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": "secret", "square_cm": 20},
    )

    assert response.status_code == 200
    assert extraction_calls[0]["image_path"] == _read_meta(directory)["scan_path"]


def test_status_is_extracting_before_async_task_starts(
    route_context,
    monkeypatch,
):
    directory = _create_job(route_context)
    status_at_start = []

    def fake_start_task(function, *args, **kwargs):
        status_at_start.append(_read_meta(directory)["text_verification_status"])
        return "pending-task"

    monkeypatch.setattr(text_metadata, "start_task", fake_start_task)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": "secret", "square_cm": 20},
    )

    assert response.status_code == 200
    assert status_at_start == ["extracting"]
    assert _read_meta(directory)["text_verification_status"] == "extracting"


def test_async_failure_records_only_a_safe_error(route_context, monkeypatch):
    directory = _create_job(route_context)
    api_key = "secret-that-must-not-reach-disk"

    def failing_extraction(*args, **kwargs):
        raise RuntimeError(f"provider failed while using {api_key}")

    def fake_start_task(function, *args, **kwargs):
        try:
            function(*args, **kwargs)
        except RuntimeError:
            pass
        return "failed-task"

    monkeypatch.setattr(
        text_metadata.p_extract_fieldwall,
        "run_extraction",
        failing_extraction,
    )
    monkeypatch.setattr(text_metadata, "start_task", fake_start_task)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-extraction",
        json={"api_key": api_key, "square_cm": 20},
    )

    meta_text = (directory / "meta.json").read_text(encoding="utf-8")
    meta = json.loads(meta_text)
    state = route_context.client.get(
        "/api/jobs/fieldwall-job/text-extraction"
    ).get_json()
    assert response.status_code == 200
    assert meta["text_verification_status"] == "error"
    assert meta["text_extraction_error"] == "Text extraction failed. Please try again."
    assert state["error"] == meta["text_extraction_error"]
    assert api_key not in meta_text


def test_provider_schema_400_is_not_misreported_as_an_api_key_error():
    class ProviderSchemaError(Exception):
        code = 400

    error = ProviderSchemaError(
        "Invalid JSON payload at generation_config.response_schema"
    )

    assert text_metadata._safe_extraction_error(error) == (
        "Gemini rejected the structured-output schema. "
        "This is a server configuration error, not an API-key error."
    )


def test_get_returns_candidates_when_available(route_context):
    directory = _create_job(route_context)
    candidates = _candidate_payload()
    candidates_path = directory / "03_extraction" / "text_candidates.json"
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
    meta = _read_meta(directory)
    meta.update(
        {
            "text_candidates_path": str(candidates_path),
            "text_verification_status": "ready_for_review",
        }
    )
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    response = route_context.client.get("/api/jobs/fieldwall-job/text-extraction")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ready_for_review",
        "candidates": candidates,
    }


def test_get_returns_verified_text_when_available(route_context):
    directory = _create_job(route_context)
    verified = _verified_payload()
    verified_path = directory / "03_extraction" / "verified_text.json"
    verified_path.write_text(json.dumps(verified), encoding="utf-8")
    meta = _read_meta(directory)
    meta.update(
        {
            "verified_text_path": str(verified_path),
            "text_verification_status": "verified",
        }
    )
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    response = route_context.client.get("/api/jobs/fieldwall-job/text-extraction")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "verified",
        "verified_text": verified,
    }


def test_valid_verification_is_written_and_sets_verified_status(route_context):
    directory = _create_job(route_context)
    verified = _verified_payload()

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-verification",
        json=verified,
    )

    output_path = directory / "03_extraction" / "verified_text.json"
    meta = _read_meta(directory)
    assert response.status_code == 200
    assert response.get_json() == verified
    assert json.loads(output_path.read_text(encoding="utf-8")) == verified
    assert meta["verified_text_path"] == str(output_path)
    assert meta["text_verification_status"] == "verified"


@pytest.mark.parametrize(
    "payload",
    [
        {"reviewCompleted": False},
        {
            "schemaVersion": 1,
            "sheetType": "fieldwall",
            "reviewCompleted": True,
            "layers": [],
        },
    ],
    ids=["review-incomplete", "unexpected-geometry"],
)
def test_invalid_verification_returns_400(route_context, payload):
    directory = _create_job(route_context)

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-verification",
        json=payload,
    )

    assert response.status_code == 400
    assert not (directory / "03_extraction" / "verified_text.json").exists()


def test_skip_sets_status_without_deleting_candidates(route_context):
    directory = _create_job(route_context)
    candidates_path = directory / "03_extraction" / "text_candidates.json"
    candidates_path.write_text(
        json.dumps(_candidate_payload()),
        encoding="utf-8",
    )
    meta = _read_meta(directory)
    meta["text_candidates_path"] = str(candidates_path)
    meta["text_verification_status"] = "ready_for_review"
    (directory / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    response = route_context.client.post(
        "/api/jobs/fieldwall-job/text-verification/skip"
    )

    meta = _read_meta(directory)
    assert response.status_code == 200
    assert response.get_json() == {"status": "skipped"}
    assert meta["text_verification_status"] == "skipped"
    assert meta["text_candidates_path"] == str(candidates_path)
    assert candidates_path.exists()
    assert "verified_text_path" not in meta
    assert not (directory / "03_extraction" / "verified_text.json").exists()
