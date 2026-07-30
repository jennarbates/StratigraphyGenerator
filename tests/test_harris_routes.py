import json
from datetime import datetime, timezone
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest


import storage
from backend import config, create_app, harris_store
from pipeline.harris_matrix import HarrisMatrix


UNIT_A = "unit-00000000000a"
UNIT_B = "unit-00000000000b"
FIELD_JOB = "111111111111"
ILLUSTRATOR_JOB = "222222222222"
MALFORMED_JOB = "333333333333"


@pytest.fixture
def route_context(tmp_path, monkeypatch):
    matrices_dir = storage.MATRICES_DIR
    jobs_dir = storage.JOBS_DIR
    source_dir = jobs_dir / "111111111111"
    source_dir.mkdir(parents=True)
    (source_dir / "meta.json").write_bytes(b'{"title":"source"}\n')
    (source_dir / "extraction_output.json").write_bytes(
        b'{"schemaType":"FieldWallProfile"}\n'
    )
    app = create_app()
    app.config.update(TESTING=True)
    return SimpleNamespace(
        app=app,
        client=app.test_client(),
        matrices_dir=matrices_dir,
        jobs_dir=jobs_dir,
    )


def _create(client, **overrides):
    payload = {
        "title": "T123 Harris Matrix",
        "site": "Poggio Civitate",
        "trench": "T123",
        **overrides,
    }
    response = client.post("/api/harris-matrices", json=payload)
    assert response.status_code == 201
    return response.get_json()


def _unit(unit_id):
    return {
        "id": unit_id,
        "label": unit_id,
        "unit_type": "deposit",
        "description": None,
        "source_refs": [],
    }


def _relation(relation_id, younger_id, older_id):
    return {
        "id": relation_id,
        "younger_id": younger_id,
        "older_id": older_id,
        "kind": "above",
        "evidence": "",
        "source": "manual",
        "notes": None,
    }


def _source_snapshot(jobs_dir):
    return {
        path.relative_to(jobs_dir): path.read_bytes()
        for path in sorted(jobs_dir.rglob("*"))
        if path.is_file()
    }


def _field_point(x, depth):
    return {"xMeters": x, "depthMeters": depth}


def _illustrator_point(x, y):
    return {"xCoordinateMeters": x, "yCoordinateMeters": y}


def _field_document(labels=("Shared", "Lower")):
    shared_boundary = [
        _field_point(0.0, 0.4),
        _field_point(1.0, 0.5),
    ]
    return {
        "trenchLabel": "T123",
        "faceLabel": "North baulk",
        "loci": [
            {"locusNumber": label, "description": f"Locus {label}"}
            for label in labels
        ],
        "layers": [
            {
                "locusNumber": labels[0],
                "topBoundary": [
                    _field_point(0.0, 0.0),
                    _field_point(1.0, 0.0),
                ],
                "bottomBoundary": shared_boundary,
            },
            {
                "locusNumber": labels[1],
                "topBoundary": shared_boundary,
                "bottomBoundary": [
                    _field_point(0.0, 0.9),
                    _field_point(1.0, 1.0),
                ],
            },
        ],
    }


def _illustrator_document():
    return {
        "metadata": {"trenchLabel": "T123"},
        "trenchProfiles": [
            {
                "face": "East",
                "layers": [
                    {
                        "layerName": "Shared",
                        "topBoundary": [
                            _illustrator_point(0.0, 0.0),
                            _illustrator_point(1.0, 0.0),
                        ],
                        "bottomBoundary": [
                            _illustrator_point(0.0, 0.5),
                            _illustrator_point(1.0, 0.5),
                        ],
                    }
                ],
            },
            {
                "face": "West",
                "layers": [
                    {
                        "layerName": "West layer",
                        "topBoundary": [
                            _illustrator_point(0.0, 0.0),
                            _illustrator_point(1.0, 0.0),
                        ],
                        "bottomBoundary": [
                            _illustrator_point(0.0, 0.6),
                            _illustrator_point(1.0, 0.6),
                        ],
                    }
                ],
            },
        ],
    }


def _write_job(route_context, job_id, document):
    job_dir = route_context.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "meta.json").write_text(
        json.dumps({"title": f"Source {job_id}"}),
        encoding="utf-8",
    )
    (job_dir / "extraction_output.json").write_text(
        json.dumps(document),
        encoding="utf-8",
    )
    return job_dir


def _import(client, matrix, job_ids):
    return client.post(
        f"/api/harris-matrices/{matrix['matrix_id']}/sources",
        json={"job_ids": job_ids, "revision": matrix["revision"]},
    )


def _suggestion(matrix, suggestion_type):
    return next(
        suggestion
        for suggestion in matrix["suggestions"]
        if suggestion["suggestion_type"] == suggestion_type
    )


def _matrix_bytes(route_context, matrix_id):
    return (
        route_context.matrices_dir / matrix_id / "matrix.json"
    ).read_bytes()


def test_empty_list(route_context):
    response = route_context.client.get("/api/harris-matrices")

    assert response.status_code == 200
    assert response.get_json() == []


def test_create_returns_201_and_writes_one_matrix(route_context):
    before_sources = _source_snapshot(route_context.jobs_dir)

    created = _create(route_context.client)

    matrix_files = list(route_context.matrices_dir.glob("*/matrix.json"))
    assert len(matrix_files) == 1
    assert json.loads(matrix_files[0].read_text()) == created
    assert created["schema_version"] == 1
    assert created["revision"] == 0
    assert _source_snapshot(route_context.jobs_dir) == before_sources


def test_create_trims_metadata(route_context):
    created = _create(
        route_context.client,
        title="  T123 Harris Matrix  ",
        site="  Poggio Civitate ",
        trench=" T123  ",
    )

    assert created["title"] == "T123 Harris Matrix"
    assert created["site"] == "Poggio Civitate"
    assert created["trench"] == "T123"


def test_list_returns_safe_summaries_newest_first(
    route_context,
    monkeypatch,
):
    ids = iter(["aaaaaaaaaaaa", "bbbbbbbbbbbb"])
    times = iter(
        [
            datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc),
        ]
    )
    monkeypatch.setattr(
        harris_store.secrets,
        "token_hex",
        lambda _size: next(ids),
    )
    monkeypatch.setattr(harris_store, "_utc_now", lambda: next(times))
    _create(route_context.client, title="Older")
    _create(route_context.client, title="Newer")

    summaries = route_context.client.get(
        "/api/harris-matrices"
    ).get_json()

    assert [summary["title"] for summary in summaries] == [
        "Newer",
        "Older",
    ]
    assert set(summaries[0]) == {
        "matrix_id",
        "title",
        "site",
        "trench",
        "revision",
        "updated_at",
        "unit_count",
        "relation_count",
    }
    assert str(route_context.matrices_dir) not in json.dumps(summaries)


def test_get_returns_full_matrix_after_app_recreation(route_context):
    created = _create(route_context.client)
    recreated_app = create_app()
    recreated_app.config.update(TESTING=True)

    response = recreated_app.test_client().get(
        f"/api/harris-matrices/{created['matrix_id']}"
    )

    assert response.status_code == 200
    assert response.get_json() == created


def test_invalid_and_missing_ids_differ(route_context):
    invalid = route_context.client.get(
        "/api/harris-matrices/not-a-matrix"
    )
    missing = route_context.client.get(
        "/api/harris-matrices/aaaaaaaaaaaa"
    )

    assert invalid.status_code == 400
    assert invalid.get_json()["code"] == "invalid_matrix_id"
    assert missing.status_code == 404
    assert missing.get_json()["code"] == "matrix_not_found"


def test_put_increments_revision(route_context):
    created = _create(route_context.client)
    created["title"] = "Revised title"

    response = route_context.client.put(
        f"/api/harris-matrices/{created['matrix_id']}",
        json=created,
    )

    assert response.status_code == 200
    saved = response.get_json()
    assert saved["revision"] == 1
    assert saved["title"] == "Revised title"
    loaded = route_context.client.get(
        f"/api/harris-matrices/{created['matrix_id']}"
    )
    assert loaded.get_json() == saved


def test_put_rejects_stale_revision_with_409(route_context):
    created = _create(route_context.client)
    first = route_context.client.put(
        f"/api/harris-matrices/{created['matrix_id']}",
        json=created,
    )
    assert first.status_code == 200

    stale = route_context.client.put(
        f"/api/harris-matrices/{created['matrix_id']}",
        json=created,
    )

    assert stale.status_code == 409
    assert stale.get_json() == {
        "code": "revision_conflict",
        "error": "Matrix revision conflict.",
        "details": {
            "actual_revision": 1,
            "expected_revision": 0,
        },
    }


def test_put_rejects_changed_matrix_id(route_context):
    created = _create(route_context.client)
    original_id = created["matrix_id"]
    created["matrix_id"] = "ffffffffffff"

    response = route_context.client.put(
        f"/api/harris-matrices/{original_id}",
        json=created,
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "matrix_id_mismatch"
    assert harris_store.load_matrix(original_id).revision == 0


def test_put_rejects_graph_cycle_without_altering_stored_bytes(
    route_context,
):
    created = _create(route_context.client)
    matrix_path = (
        route_context.matrices_dir
        / created["matrix_id"]
        / "matrix.json"
    )
    before = matrix_path.read_bytes()
    created["units"] = [_unit(UNIT_A), _unit(UNIT_B)]
    created["relations"] = [
        _relation("rel-000000000001", UNIT_A, UNIT_B),
        _relation("rel-000000000002", UNIT_B, UNIT_A),
    ]

    response = route_context.client.put(
        f"/api/harris-matrices/{created['matrix_id']}",
        json=created,
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_matrix"
    assert response.get_json()["details"]["error_codes"] == ["cycle"]
    assert matrix_path.read_bytes() == before


@pytest.mark.parametrize("method", ["post", "put"])
def test_unknown_fields_are_rejected(route_context, method):
    if method == "post":
        response = route_context.client.post(
            "/api/harris-matrices",
            json={"unexpected": True},
        )
    else:
        created = _create(route_context.client)
        created["unexpected"] = True
        response = route_context.client.put(
            f"/api/harris-matrices/{created['matrix_id']}",
            json=created,
        )

    assert response.status_code == 400
    assert response.get_json()["code"] in {
        "invalid_request",
        "invalid_matrix",
    }


def test_no_response_contains_temporary_absolute_path(route_context):
    created_response = route_context.client.post(
        "/api/harris-matrices",
        json={"title": "No paths"},
    )
    created = created_response.get_json()
    responses = [
        created_response,
        route_context.client.get("/api/harris-matrices"),
        route_context.client.get(
            f"/api/harris-matrices/{created['matrix_id']}"
        ),
        route_context.client.get("/api/harris-matrices/not-a-matrix"),
    ]

    for response in responses:
        serialized = json.dumps(response.get_json())
        assert str(route_context.matrices_dir) not in serialized
        assert str(route_context.jobs_dir) not in serialized


def test_existing_non_harris_endpoint_still_responds(route_context):
    response = route_context.client.get("/")

    assert response.status_code == 200


def test_delete_is_method_not_allowed(route_context):
    created = _create(route_context.client)

    response = route_context.client.delete(
        f"/api/harris-matrices/{created['matrix_id']}"
    )

    assert response.status_code == 405


def test_source_discovery_lists_supported_schemas_with_safe_summaries(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    _write_job(
        route_context,
        ILLUSTRATOR_JOB,
        _illustrator_document(),
    )
    malformed_dir = route_context.jobs_dir / MALFORMED_JOB
    malformed_dir.mkdir()
    (malformed_dir / "extraction_output.json").write_text(
        "{not-json",
        encoding="utf-8",
    )

    response = route_context.client.get("/api/harris-source-jobs")

    assert response.status_code == 200
    summaries = response.get_json()
    assert summaries == [
        {
            "job_id": FIELD_JOB,
            "schema_type": "FieldWallProfile",
            "trench": "T123",
            "faces": ["North baulk"],
            "unit_count": 2,
        },
        {
            "job_id": ILLUSTRATOR_JOB,
            "schema_type": "ArchaeologicalDiagram",
            "trench": "T123",
            "faces": ["East", "West"],
            "unit_count": 2,
        },
    ]
    serialized = json.dumps(summaries)
    assert str(route_context.jobs_dir) not in serialized
    assert "extraction_output.json" not in serialized


def test_imports_field_wall_and_multiface_jobs_atomically(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    _write_job(
        route_context,
        ILLUSTRATOR_JOB,
        _illustrator_document(),
    )
    sources_before = _source_snapshot(route_context.jobs_dir)
    created = _create(route_context.client)

    response = _import(
        route_context.client,
        created,
        [FIELD_JOB, ILLUSTRATOR_JOB],
    )

    assert response.status_code == 200
    imported = response.get_json()
    assert imported["revision"] == 1
    assert imported["source_job_ids"] == [FIELD_JOB, ILLUSTRATOR_JOB]
    assert len(imported["units"]) == 4
    assert {
        ref["schema_type"]
        for unit in imported["units"]
        for ref in unit["source_refs"]
    } == {"FieldWallProfile", "ArchaeologicalDiagram"}
    assert {
        ref["face"]
        for unit in imported["units"]
        for ref in unit["source_refs"]
        if ref["job_id"] == ILLUSTRATOR_JOB
    } == {"East", "West"}
    assert imported["import_warnings"] == []
    assert imported["suggestions"]
    assert all(
        suggestion["status"] == "pending"
        for suggestion in imported["suggestions"]
    )
    assert imported["relations"] == []
    assert imported["correlations"] == []
    assert str(route_context.jobs_dir) not in json.dumps(imported)
    assert _source_snapshot(route_context.jobs_dir) == sources_before


def test_reimport_is_idempotent_and_preserves_sources(route_context):
    _write_job(route_context, FIELD_JOB, _field_document())
    sources_before = _source_snapshot(route_context.jobs_dir)
    created = _create(route_context.client)
    first = _import(
        route_context.client,
        created,
        [FIELD_JOB],
    ).get_json()

    response = _import(
        route_context.client,
        first,
        [FIELD_JOB, FIELD_JOB],
    )

    assert response.status_code == 200
    second = response.get_json()
    assert second["revision"] == 2
    assert second["source_job_ids"] == [FIELD_JOB]
    assert second["units"] == first["units"]
    assert second["suggestions"] == first["suggestions"]
    assert _source_snapshot(route_context.jobs_dir) == sources_before


def test_stale_import_revision_returns_409_without_writing(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    created = _create(route_context.client)
    imported = _import(
        route_context.client,
        created,
        [FIELD_JOB],
    ).get_json()
    before = _matrix_bytes(route_context, created["matrix_id"])

    response = route_context.client.post(
        f"/api/harris-matrices/{created['matrix_id']}/sources",
        json={"job_ids": [FIELD_JOB], "revision": 0},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "revision_conflict"
    assert imported["revision"] == 1
    assert _matrix_bytes(route_context, created["matrix_id"]) == before


def test_malformed_job_aborts_multi_job_import_without_partial_save(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    malformed_dir = route_context.jobs_dir / MALFORMED_JOB
    malformed_dir.mkdir()
    (malformed_dir / "meta.json").write_bytes(b'{"title":"bad"}\n')
    (malformed_dir / "extraction_output.json").write_bytes(b"{not-json")
    sources_before = _source_snapshot(route_context.jobs_dir)
    created = _create(route_context.client)
    before = _matrix_bytes(route_context, created["matrix_id"])

    response = _import(
        route_context.client,
        created,
        [FIELD_JOB, MALFORMED_JOB],
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "source_import_error"
    assert _matrix_bytes(route_context, created["matrix_id"]) == before
    assert _source_snapshot(route_context.jobs_dir) == sources_before


def test_accept_ordering_suggestion_saves_one_revision(route_context):
    _write_job(route_context, FIELD_JOB, _field_document())
    created = _create(route_context.client)
    imported = _import(
        route_context.client,
        created,
        [FIELD_JOB],
    ).get_json()
    suggestion = _suggestion(imported, "ordering")

    response = route_context.client.post(
        (
            f"/api/harris-matrices/{created['matrix_id']}"
            f"/suggestions/{suggestion['id']}"
        ),
        json={"action": "accept", "revision": imported["revision"]},
    )

    assert response.status_code == 200
    reviewed = response.get_json()
    assert reviewed["revision"] == imported["revision"] + 1
    assert _suggestion(reviewed, "ordering")["status"] == "accepted"
    assert len(reviewed["relations"]) == 1
    assert reviewed["relations"][0]["source"] == "suggestion"


def test_reject_correlation_saves_once_without_adding_group(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    _write_job(
        route_context,
        ILLUSTRATOR_JOB,
        _illustrator_document(),
    )
    created = _create(route_context.client)
    imported = _import(
        route_context.client,
        created,
        [FIELD_JOB, ILLUSTRATOR_JOB],
    ).get_json()
    suggestion = _suggestion(imported, "correlation")

    response = route_context.client.post(
        (
            f"/api/harris-matrices/{created['matrix_id']}"
            f"/suggestions/{suggestion['id']}"
        ),
        json={"action": "reject", "revision": imported["revision"]},
    )

    assert response.status_code == 200
    reviewed = response.get_json()
    assert reviewed["revision"] == imported["revision"] + 1
    assert _suggestion(reviewed, "correlation")["status"] == "rejected"
    assert reviewed["correlations"] == []


def test_suggestion_review_rejects_invalid_action_and_unknown_id(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    created = _create(route_context.client)
    imported = _import(
        route_context.client,
        created,
        [FIELD_JOB],
    ).get_json()
    suggestion = _suggestion(imported, "ordering")
    before = _matrix_bytes(route_context, created["matrix_id"])
    url = (
        f"/api/harris-matrices/{created['matrix_id']}"
        f"/suggestions/{suggestion['id']}"
    )

    invalid = route_context.client.post(
        url,
        json={"action": "maybe", "revision": imported["revision"]},
    )
    unknown = route_context.client.post(
        (
            f"/api/harris-matrices/{created['matrix_id']}"
            "/suggestions/suggestion-ffffffffffff"
        ),
        json={"action": "accept", "revision": imported["revision"]},
    )

    assert invalid.status_code == 400
    assert invalid.get_json()["code"] == "invalid_request"
    assert unknown.status_code == 404
    assert unknown.get_json()["code"] == "suggestion_not_found"
    assert _matrix_bytes(route_context, created["matrix_id"]) == before


def test_cycle_producing_acceptance_leaves_stored_bytes_unchanged(
    route_context,
):
    _write_job(route_context, FIELD_JOB, _field_document())
    created = _create(route_context.client)
    imported = _import(
        route_context.client,
        created,
        [FIELD_JOB],
    ).get_json()
    suggestion = _suggestion(imported, "ordering")
    imported.pop("import_warnings")
    imported["relations"] = [
        _relation(
            "rel-000000000001",
            suggestion["older_id"],
            suggestion["younger_id"],
        )
    ]
    saved = route_context.client.put(
        f"/api/harris-matrices/{created['matrix_id']}",
        json=imported,
    ).get_json()
    before = _matrix_bytes(route_context, created["matrix_id"])

    response = route_context.client.post(
        (
            f"/api/harris-matrices/{created['matrix_id']}"
            f"/suggestions/{suggestion['id']}"
        ),
        json={"action": "accept", "revision": saved["revision"]},
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "suggestion_review_error"
    assert "cycle" in response.get_json()["error"]
    assert _matrix_bytes(route_context, created["matrix_id"]) == before


@pytest.mark.parametrize(
    "job_id",
    ["../111111111111", "ABCDEF123456", "11111111111g"],
)
def test_import_rejects_invalid_or_traversal_job_ids(
    route_context,
    job_id,
):
    created = _create(route_context.client)
    before = _matrix_bytes(route_context, created["matrix_id"])

    response = _import(route_context.client, created, [job_id])

    assert response.status_code == 400
    assert response.get_json()["code"] == "invalid_request"
    assert _matrix_bytes(route_context, created["matrix_id"]) == before


def _save_export_matrix(route_context, *, hostile_label=None):
    matrix = _create(route_context.client)
    matrix["units"] = [
        _unit(UNIT_A),
        _unit(UNIT_B),
    ]
    matrix["units"][0]["label"] = hostile_label or "Young"
    matrix["units"][1]["label"] = "Old"
    matrix["relations"] = [
        _relation("rel-000000000001", UNIT_A, UNIT_B)
    ]
    response = route_context.client.put(
        f"/api/harris-matrices/{matrix['matrix_id']}",
        json=matrix,
    )
    assert response.status_code == 200
    return response.get_json()


def test_json_and_svg_exports_have_safe_attachment_names_and_mime_types(
    route_context,
):
    sources_before = _source_snapshot(route_context.jobs_dir)
    matrix = _save_export_matrix(route_context)
    base = f"/api/harris-matrices/{matrix['matrix_id']}/export"

    json_response = route_context.client.get(f"{base}.json")
    svg_response = route_context.client.get(f"{base}.svg")

    assert json_response.status_code == 200
    assert json_response.mimetype == "application/json"
    assert json_response.headers["Content-Disposition"] == (
        f'attachment; filename="harris-matrix-{matrix["matrix_id"]}.json"'
    )
    assert svg_response.status_code == 200
    assert svg_response.mimetype == "image/svg+xml"
    assert svg_response.headers["Content-Disposition"] == (
        f'attachment; filename="harris-matrix-{matrix["matrix_id"]}.svg"'
    )
    assert _source_snapshot(route_context.jobs_dir) == sources_before


def test_json_export_round_trips_through_versioned_model(route_context):
    matrix = _save_export_matrix(route_context)

    response = route_context.client.get(
        f"/api/harris-matrices/{matrix['matrix_id']}/export.json"
    )
    exported = HarrisMatrix.model_validate_json(response.data)

    assert exported.model_dump(mode="json") == matrix
    assert exported.schema_version == 1


def test_inline_svg_uses_renderer_without_attachment(route_context):
    matrix = _save_export_matrix(route_context)

    inline = route_context.client.get(
        f"/api/harris-matrices/{matrix['matrix_id']}/export.svg?inline=1"
    )
    attached = route_context.client.get(
        f"/api/harris-matrices/{matrix['matrix_id']}/export.svg"
    )

    assert inline.status_code == 200
    assert inline.data == attached.data
    assert not inline.headers["Content-Disposition"].startswith("attachment")


@pytest.mark.parametrize("extension", ["json", "svg"])
def test_export_routes_preserve_invalid_and_missing_matrix_behavior(
    route_context,
    extension,
):
    invalid = route_context.client.get(
        f"/api/harris-matrices/not-a-matrix/export.{extension}"
    )
    missing = route_context.client.get(
        f"/api/harris-matrices/aaaaaaaaaaaa/export.{extension}"
    )

    assert invalid.status_code == 400
    assert invalid.get_json()["code"] == "invalid_matrix_id"
    assert missing.status_code == 404
    assert missing.get_json()["code"] == "matrix_not_found"


def test_malicious_exported_label_remains_escaped_in_http_svg(
    route_context,
):
    hostile = '<script src="https://evil.example/x">& "unit"</script>'
    matrix = _save_export_matrix(
        route_context,
        hostile_label=hostile,
    )

    response = route_context.client.get(
        f"/api/harris-matrices/{matrix['matrix_id']}/export.svg"
    )
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<script" not in text.casefold()
    assert "&lt;script" in text.casefold()
    assert hostile in " ".join(ElementTree.fromstring(text).itertext())
