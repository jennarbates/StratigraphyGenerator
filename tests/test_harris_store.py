import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from backend import config, harris_store
from pipeline.harris_matrix import HarrisMatrix


UNIT_A = "unit-00000000000a"
UNIT_B = "unit-00000000000b"


@pytest.fixture
def storage(tmp_path, monkeypatch):
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
    return {
        "matrices_dir": matrices_dir,
        "jobs_dir": jobs_dir,
    }


def candidate_from(matrix):
    return matrix.model_dump(mode="json")


def unit(unit_id, label="Locus 1"):
    return {
        "id": unit_id,
        "label": label,
        "unit_type": "deposit",
        "description": None,
        "source_refs": [],
    }


def relation(relation_id, younger_id, older_id):
    return {
        "id": relation_id,
        "younger_id": younger_id,
        "older_id": older_id,
        "kind": "above",
        "evidence": "",
        "source": "manual",
        "notes": None,
    }


def source_snapshot(jobs_dir):
    return {
        path.relative_to(jobs_dir): path.read_bytes()
        for path in sorted(jobs_dir.rglob("*"))
        if path.is_file()
    }


def test_create_returns_valid_id_and_writes_version_one_json(storage):
    matrix = harris_store.create_matrix()

    assert isinstance(matrix, HarrisMatrix)
    assert len(matrix.matrix_id) == 12
    assert all(
        character in "0123456789abcdef"
        for character in matrix.matrix_id
    )
    assert matrix.revision == 0

    matrix_path = (
        storage["matrices_dir"] / matrix.matrix_id / "matrix.json"
    )
    assert matrix_path.is_file()
    persisted = HarrisMatrix.model_validate_json(matrix_path.read_text())
    assert persisted == matrix
    assert json.loads(matrix_path.read_text())["schema_version"] == 1


def test_create_honors_only_safe_initial_fields(storage, monkeypatch):
    monkeypatch.setattr(
        harris_store.secrets,
        "token_hex",
        lambda _size: "0123456789ab",
    )

    matrix = harris_store.create_matrix(
        {
            "title": "  T123 Harris Matrix  ",
            "site": " Poggio Civitate ",
            "trench": " T123 ",
            "matrix_id": "ffffffffffff",
            "revision": 99,
        }
    )

    assert matrix.title == "T123 Harris Matrix"
    assert matrix.site == "Poggio Civitate"
    assert matrix.trench == "T123"
    assert matrix.matrix_id == "0123456789ab"
    assert matrix.revision == 0


def test_load_rejects_invalid_id_before_joining_a_filesystem_path(
    storage,
    monkeypatch,
):
    class FailOnJoin:
        def __truediv__(self, _other):
            raise AssertionError("filesystem path was joined")

    monkeypatch.setattr(config, "MATRICES_DIR", FailOnJoin())

    with pytest.raises(
        harris_store.InvalidMatrixIdError,
        match="12 lowercase hexadecimal",
    ):
        harris_store.load_matrix("../../jobs")


def test_load_reports_not_found_distinctly_from_invalid_id(storage):
    with pytest.raises(harris_store.MatrixNotFoundError, match="aaaaaaaaaaaa"):
        harris_store.load_matrix("aaaaaaaaaaaa")

    with pytest.raises(harris_store.InvalidMatrixIdError):
        harris_store.load_matrix("not-an-id")


def test_load_reports_malformed_persisted_matrix(storage):
    matrix_dir = storage["matrices_dir"] / "aaaaaaaaaaaa"
    matrix_dir.mkdir()
    (matrix_dir / "matrix.json").write_text("{not-json")

    with pytest.raises(harris_store.InvalidMatrixError, match="invalid"):
        harris_store.load_matrix("aaaaaaaaaaaa")


def test_save_increments_revision_once_and_updates_timestamp(storage):
    created = harris_store.create_matrix()
    candidate = candidate_from(created)
    candidate["title"] = "Revised title"

    saved = harris_store.save_matrix(
        created.matrix_id,
        candidate,
        expected_revision=0,
    )

    assert saved.revision == 1
    assert saved.title == "Revised title"
    assert saved.updated_at > created.updated_at
    assert harris_store.load_matrix(created.matrix_id) == saved


def test_save_preserves_server_owned_identity_and_creation_fields(storage):
    created = harris_store.create_matrix()
    candidate = candidate_from(created)
    candidate.update(
        {
            "matrix_id": "ffffffffffff",
            "revision": 88,
            "created_at": "2020-01-01T00:00:00+00:00",
            "updated_at": "2020-01-01T00:00:00+00:00",
        }
    )

    saved = harris_store.save_matrix(
        created.matrix_id,
        candidate,
        expected_revision=0,
    )

    assert saved.matrix_id == created.matrix_id
    assert saved.created_at == created.created_at
    assert saved.revision == 1
    assert saved.updated_at > created.updated_at


def test_save_accepts_a_valid_model_candidate(storage):
    created = harris_store.create_matrix()

    saved = harris_store.save_matrix(
        created.matrix_id,
        created,
        expected_revision=0,
    )

    assert saved.revision == 1


def test_stale_expected_revision_raises_dedicated_conflict(storage):
    created = harris_store.create_matrix()
    harris_store.save_matrix(
        created.matrix_id,
        candidate_from(created),
        expected_revision=0,
    )

    with pytest.raises(harris_store.MatrixConflictError) as error:
        harris_store.save_matrix(
            created.matrix_id,
            candidate_from(created),
            expected_revision=0,
        )

    assert error.value.expected_revision == 0
    assert error.value.actual_revision == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("title", {"not": "text"}),
    ],
)
def test_invalid_schema_is_not_written(storage, field, value):
    created = harris_store.create_matrix()
    matrix_path = (
        storage["matrices_dir"] / created.matrix_id / "matrix.json"
    )
    before = matrix_path.read_bytes()
    candidate = candidate_from(created)
    candidate[field] = value

    with pytest.raises(harris_store.InvalidMatrixError, match="schema"):
        harris_store.save_matrix(
            created.matrix_id,
            candidate,
            expected_revision=0,
        )

    assert matrix_path.read_bytes() == before


def test_graph_errors_are_not_written(storage):
    created = harris_store.create_matrix()
    matrix_path = (
        storage["matrices_dir"] / created.matrix_id / "matrix.json"
    )
    before = matrix_path.read_bytes()
    candidate = candidate_from(created)
    candidate["units"] = [unit(UNIT_A)]
    candidate["relations"] = [
        relation("rel-000000000001", UNIT_A, UNIT_B)
    ]

    with pytest.raises(harris_store.InvalidMatrixError) as error:
        harris_store.save_matrix(
            created.matrix_id,
            candidate,
            expected_revision=0,
        )

    assert "missing-unit" in error.value.error_codes
    assert matrix_path.read_bytes() == before


def test_graph_warnings_are_allowed(storage):
    created = harris_store.create_matrix()
    candidate = candidate_from(created)
    candidate["units"] = [unit(UNIT_A, "Polygon 1")]

    saved = harris_store.save_matrix(
        created.matrix_id,
        candidate,
        expected_revision=0,
    )

    assert saved.revision == 1
    assert saved.units[0].label == "Polygon 1"


def test_save_atomically_replaces_from_same_matrix_directory(
    storage,
    monkeypatch,
):
    created = harris_store.create_matrix()
    destination = (
        storage["matrices_dir"] / created.matrix_id / "matrix.json"
    )
    real_replace = harris_store.os.replace
    replace_call = {}

    def track_replace(source, target):
        source_path = harris_store.Path(source)
        target_path = harris_store.Path(target)
        replace_call["source"] = source_path
        replace_call["target"] = target_path
        assert source_path.parent == destination.parent
        assert target_path == destination
        assert source_path.is_file()
        real_replace(source, target)

    monkeypatch.setattr(harris_store.os, "replace", track_replace)

    harris_store.save_matrix(
        created.matrix_id,
        candidate_from(created),
        expected_revision=0,
    )

    assert replace_call["target"] == destination
    assert not replace_call["source"].exists()


def test_list_is_newest_first_with_lexical_id_tie_breaking(
    storage,
    monkeypatch,
):
    ids = iter(["bbbbbbbbbbbb", "aaaaaaaaaaaa", "cccccccccccc"])
    times = iter(
        [
            datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc),
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
    harris_store.create_matrix({"title": "B"})
    harris_store.create_matrix({"title": "A"})
    harris_store.create_matrix({"title": "C"})

    summaries = harris_store.list_matrices()

    assert [item["matrix_id"] for item in summaries] == [
        "cccccccccccc",
        "aaaaaaaaaaaa",
        "bbbbbbbbbbbb",
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


def test_list_skips_malformed_and_invalid_matrix_folders(storage):
    valid = harris_store.create_matrix({"title": "Valid"})
    malformed_dir = storage["matrices_dir"] / "aaaaaaaaaaaa"
    malformed_dir.mkdir()
    (malformed_dir / "matrix.json").write_text("{}")
    invalid_id_dir = storage["matrices_dir"] / "not-a-matrix"
    invalid_id_dir.mkdir()
    (invalid_id_dir / "matrix.json").write_text("{}")

    summaries = harris_store.list_matrices()

    assert [item["matrix_id"] for item in summaries] == [valid.matrix_id]


def test_summaries_and_persisted_json_contain_no_absolute_paths(storage):
    created = harris_store.create_matrix(
        {
            "title": "T123",
            "site": "Poggio Civitate",
            "trench": "T123",
        }
    )

    summaries = harris_store.list_matrices()
    persisted = (
        storage["matrices_dir"] / created.matrix_id / "matrix.json"
    ).read_text()

    assert str(storage["matrices_dir"]) not in json.dumps(summaries)
    assert str(storage["jobs_dir"]) not in json.dumps(summaries)
    assert str(storage["matrices_dir"]) not in persisted
    assert str(storage["jobs_dir"]) not in persisted


def test_store_operations_never_modify_source_job_directories(storage):
    before = source_snapshot(storage["jobs_dir"])

    created = harris_store.create_matrix()
    saved = harris_store.save_matrix(
        created.matrix_id,
        candidate_from(created),
        expected_revision=0,
    )
    harris_store.load_matrix(saved.matrix_id)
    harris_store.list_matrices()

    assert source_snapshot(storage["jobs_dir"]) == before


def test_saved_matrix_survives_a_fresh_store_module_import(storage):
    created = harris_store.create_matrix({"title": "Persistent"})

    reloaded_store = importlib.reload(harris_store)

    assert reloaded_store.load_matrix(created.matrix_id).title == "Persistent"


def test_store_has_no_delete_operation():
    assert not hasattr(harris_store, "delete_matrix")
