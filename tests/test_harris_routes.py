import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from backend import config, create_app, harris_store


UNIT_A = "unit-00000000000a"
UNIT_B = "unit-00000000000b"


@pytest.fixture
def route_context(tmp_path, monkeypatch):
    matrices_dir = tmp_path / "matrices"
    matrices_dir.mkdir()
    jobs_dir = tmp_path / "jobs"
    source_dir = jobs_dir / "111111111111"
    source_dir.mkdir(parents=True)
    (source_dir / "meta.json").write_bytes(b'{"title":"source"}\n')
    (source_dir / "extraction_output.json").write_bytes(
        b'{"schemaType":"FieldWallProfile"}\n'
    )

    monkeypatch.setattr(config, "MATRICES_DIR", matrices_dir)
    monkeypatch.setattr(config, "JOBS_DIR", jobs_dir)
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
