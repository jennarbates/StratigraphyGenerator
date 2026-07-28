import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from poggio_webapp.pipeline.harris_import import (
    HarrisImportError,
    discover_source_jobs,
    extract_source_units,
    import_source_jobs,
    load_source_document,
)
from poggio_webapp.pipeline.harris_matrix import HarrisMatrix


FIELD_JOB = "111111111111"
ILLUSTRATOR_JOB = "222222222222"


def empty_matrix():
    timestamp = datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc)
    return HarrisMatrix.model_validate(
        {
            "schema_version": 1,
            "matrix_id": "aaaaaaaaaaaa",
            "revision": 0,
            "title": "T123 Harris Matrix",
            "site": "Poggio Civitate",
            "trench": "T123",
            "notes": "",
            "source_job_ids": [],
            "units": [],
            "relations": [],
            "correlations": [],
            "suggestions": [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )


def field_document(*, marker=None):
    document = {
        "trenchLabel": "T123",
        "faceLabel": "North baulk",
        "loci": [
            {
                "locusNumber": "7",
                "description": "Compact soil",
                "munsell": {
                    "raw": "10YR 5/3",
                    "colorName": "brown",
                },
            },
            {
                "locusNumber": "8",
                "description": None,
                "munsell": {
                    "raw": "2.5Y 4/3",
                    "colorName": "olive brown",
                },
            },
        ],
        "layers": [
            {"locusNumber": "7"},
            {"locusNumber": "8"},
        ],
    }
    if marker is not None:
        document["marker"] = marker
    return document


def illustrator_document():
    return {
        "metadata": {"trenchLabel": "T123"},
        "trenchProfiles": [
            {
                "face": "East",
                "layers": [
                    {
                        "layerName": "Polygon 1",
                        "description": "East soil",
                        "inferredMaterial": "Soil",
                    },
                    {
                        "layerName": "Shared",
                        "description": None,
                        "inferredMaterial": "Sandy soil",
                    },
                ],
            },
            {
                "face": "West",
                "layers": [
                    {
                        "layerName": "Shared",
                        "description": "West soil",
                        "inferredMaterial": "Stone",
                    },
                    {
                        "layerName": None,
                        "description": None,
                        "inferredMaterial": None,
                    },
                ],
            },
        ],
    }


def write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def write_job(jobs_dir, job_id, document, *, filename="extraction_output.json"):
    job_dir = jobs_dir / job_id
    job_dir.mkdir(parents=True)
    write_json(job_dir / filename, document)
    return job_dir


def source_snapshot(jobs_dir):
    return {
        path.relative_to(jobs_dir): path.read_bytes()
        for path in sorted(jobs_dir.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("expected_relative_path", "meta_fields", "create_conventional"),
    [
        (
            "custom/normalized.json",
            {"normalized_path": "custom/normalized.json"},
            True,
        ),
        ("04_normalize_validate/output_clean.json", {}, True),
        (
            "custom/extraction.json",
            {"extraction_path": "custom/extraction.json"},
            False,
        ),
        ("extraction_output.json", {}, False),
    ],
)
def test_load_source_document_uses_every_discovery_order_branch(
    tmp_path,
    expected_relative_path,
    meta_fields,
    create_conventional,
):
    jobs_dir = tmp_path / "jobs"
    job_dir = jobs_dir / FIELD_JOB
    job_dir.mkdir(parents=True)
    candidates = {
        "custom/normalized.json": "metadata-normalized",
        "04_normalize_validate/output_clean.json": "conventional-normalized",
        "custom/extraction.json": "metadata-extraction",
        "extraction_output.json": "conventional-extraction",
    }

    if create_conventional:
        write_json(
            job_dir / "04_normalize_validate/output_clean.json",
            field_document(marker=candidates[
                "04_normalize_validate/output_clean.json"
            ]),
        )
    if expected_relative_path in meta_fields.values():
        write_json(
            job_dir / expected_relative_path,
            field_document(marker=candidates[expected_relative_path]),
        )
        meta_fields = {
            field: str(job_dir / relative_path)
            for field, relative_path in meta_fields.items()
        }
    write_json(
        job_dir / "extraction_output.json",
        field_document(marker=candidates["extraction_output.json"]),
    )
    write_json(job_dir / "meta.json", meta_fields)

    document, path = load_source_document(FIELD_JOB, jobs_dir)

    assert path == (job_dir / expected_relative_path).resolve()
    assert document["marker"] == candidates[expected_relative_path]


def test_outside_job_metadata_paths_are_ignored(tmp_path):
    jobs_dir = tmp_path / "jobs"
    job_dir = jobs_dir / FIELD_JOB
    job_dir.mkdir(parents=True)
    outside = write_json(
        tmp_path / "outside.json",
        field_document(marker="outside"),
    )
    write_json(
        job_dir / "04_normalize_validate/output_clean.json",
        field_document(marker="inside"),
    )
    write_json(
        job_dir / "meta.json",
        {
            "normalized_path": str(outside),
            "extraction_path": "../outside.json",
        },
    )

    document, path = load_source_document(FIELD_JOB, jobs_dir)

    assert document["marker"] == "inside"
    assert path == (
        job_dir / "04_normalize_validate/output_clean.json"
    ).resolve()


def test_malformed_json_and_unsupported_shape_give_focused_errors(tmp_path):
    jobs_dir = tmp_path / "jobs"
    malformed_dir = jobs_dir / FIELD_JOB
    malformed_dir.mkdir(parents=True)
    (malformed_dir / "extraction_output.json").write_text(
        "{not-json",
        encoding="utf-8",
    )

    with pytest.raises(HarrisImportError, match="malformed JSON"):
        load_source_document(FIELD_JOB, jobs_dir)

    write_json(
        malformed_dir / "extraction_output.json",
        {"layers": "not-a-list"},
    )
    with pytest.raises(HarrisImportError, match="unsupported"):
        load_source_document(FIELD_JOB, jobs_dir)


def test_field_wall_units_include_labels_context_and_exact_source_refs():
    units = extract_source_units(FIELD_JOB, field_document())

    assert [unit.label for unit in units] == ["7", "8"]
    assert [unit.description for unit in units] == [
        "Compact soil",
        "2.5Y 4/3 olive brown",
    ]
    assert [unit.unit_type for unit in units] == ["deposit", "deposit"]
    assert [
        ref.model_dump()
        for unit in units
        for ref in unit.source_refs
    ] == [
        {
            "job_id": FIELD_JOB,
            "schema_type": "FieldWallProfile",
            "face": "North baulk",
            "layer_index": 0,
            "source_label": "7",
        },
        {
            "job_id": FIELD_JOB,
            "schema_type": "FieldWallProfile",
            "face": "North baulk",
            "layer_index": 1,
            "source_label": "8",
        },
    ]


def test_illustrator_units_import_every_face_without_merging_labels():
    units = extract_source_units(ILLUSTRATOR_JOB, illustrator_document())

    assert [unit.label for unit in units] == [
        "Polygon 1",
        "Shared",
        "Shared",
        "Unlabeled layer 2",
    ]
    assert [unit.description for unit in units] == [
        "East soil",
        "Sandy soil",
        "West soil",
        None,
    ]
    assert [
        (
            unit.source_refs[0].schema_type,
            unit.source_refs[0].face,
            unit.source_refs[0].layer_index,
        )
        for unit in units
    ] == [
        ("ArchaeologicalDiagram", "East", 0),
        ("ArchaeologicalDiagram", "East", 1),
        ("ArchaeologicalDiagram", "West", 0),
        ("ArchaeologicalDiagram", "West", 1),
    ]
    assert units[1].id != units[2].id


def test_two_job_import_keeps_equal_labels_as_exact_separate_source_units(
    tmp_path,
):
    jobs_dir = tmp_path / "jobs"
    write_job(jobs_dir, FIELD_JOB, field_document())
    second_document = field_document()
    second_document["faceLabel"] = "South baulk"
    write_job(jobs_dir, ILLUSTRATOR_JOB, second_document)

    imported, _warnings = import_source_jobs(
        empty_matrix(),
        [FIELD_JOB, ILLUSTRATOR_JOB],
        jobs_dir,
    )
    label_seven_units = [
        unit
        for unit in imported.units
        if unit.label == "7"
    ]

    assert len(label_seven_units) == 2
    assert label_seven_units[0].id != label_seven_units[1].id
    assert [
        source_ref.model_dump()
        for unit in label_seven_units
        for source_ref in unit.source_refs
    ] == [
        {
            "job_id": FIELD_JOB,
            "schema_type": "FieldWallProfile",
            "face": "North baulk",
            "layer_index": 0,
            "source_label": "7",
        },
        {
            "job_id": ILLUSTRATOR_JOB,
            "schema_type": "FieldWallProfile",
            "face": "South baulk",
            "layer_index": 0,
            "source_label": "7",
        },
    ]


def test_import_warnings_have_stable_codes_and_no_automatic_graph_changes(
    tmp_path,
):
    jobs_dir = tmp_path / "jobs"
    write_job(jobs_dir, ILLUSTRATOR_JOB, illustrator_document())

    imported, warnings = import_source_jobs(
        empty_matrix(),
        [ILLUSTRATOR_JOB],
        jobs_dir,
    )

    assert [warning["code"] for warning in warnings] == [
        "generic-source-label",
        "unlabeled-source-unit",
    ]
    assert all(warning["message"] for warning in warnings)
    assert imported.relations == []
    assert imported.correlations == []
    assert imported.suggestions == []


def test_reimport_is_idempotent_and_preserves_user_edits(tmp_path):
    jobs_dir = tmp_path / "jobs"
    write_job(jobs_dir, FIELD_JOB, field_document())

    imported, _warnings = import_source_jobs(
        empty_matrix(),
        [FIELD_JOB, FIELD_JOB],
        jobs_dir,
    )
    original_ids = [unit.id for unit in imported.units]
    imported.units[0].label = "Edited locus 7"
    imported.units[0].description = "Reviewer description"

    reimported, _warnings = import_source_jobs(
        imported,
        [FIELD_JOB],
        jobs_dir,
    )

    assert reimported.source_job_ids == [FIELD_JOB]
    assert [unit.id for unit in reimported.units] == original_ids
    assert len(reimported.units) == 2
    assert [len(unit.source_refs) for unit in reimported.units] == [1, 1]
    assert reimported.units[0].label == "Edited locus 7"
    assert reimported.units[0].description == "Reviewer description"


def test_discovery_omits_unusable_jobs_and_exposes_no_server_paths(tmp_path):
    jobs_dir = tmp_path / "jobs"
    write_job(jobs_dir, FIELD_JOB, field_document())
    unusable = jobs_dir / "333333333333"
    unusable.mkdir(parents=True)
    write_json(unusable / "meta.json", {"normalized_path": "/private/data"})
    invalid_id = jobs_dir / "not-a-job"
    invalid_id.mkdir()
    write_json(
        invalid_id / "extraction_output.json",
        illustrator_document(),
    )

    summaries = discover_source_jobs(jobs_dir)
    serialized = json.dumps(summaries)

    assert [summary["job_id"] for summary in summaries] == [FIELD_JOB]
    assert summaries[0]["schema_type"] == "FieldWallProfile"
    assert str(tmp_path) not in serialized
    assert "extraction_output.json" not in serialized


@pytest.mark.parametrize(
    "job_id",
    [
        "../111111111111",
        "../../etc",
        "11111111111",
        "11111111111G",
        "111111111111/",
    ],
)
def test_invalid_and_traversal_job_ids_are_rejected(tmp_path, job_id):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    with pytest.raises(HarrisImportError, match="12 lowercase hexadecimal"):
        load_source_document(job_id, jobs_dir)
    with pytest.raises(HarrisImportError, match="12 lowercase hexadecimal"):
        extract_source_units(job_id, field_document())
    with pytest.raises(HarrisImportError, match="12 lowercase hexadecimal"):
        import_source_jobs(empty_matrix(), [job_id], jobs_dir)


def test_import_never_changes_source_json_or_metadata_bytes(tmp_path):
    jobs_dir = tmp_path / "jobs"
    job_dir = write_job(jobs_dir, FIELD_JOB, field_document())
    write_json(
        job_dir / "meta.json",
        {"extraction_path": "extraction_output.json"},
    )
    before = source_snapshot(jobs_dir)

    imported, _warnings = import_source_jobs(
        empty_matrix(),
        [FIELD_JOB],
        jobs_dir,
    )

    assert imported.units
    assert source_snapshot(jobs_dir) == before
