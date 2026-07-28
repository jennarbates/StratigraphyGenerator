import json

import pytest
from pydantic import ValidationError

from poggio_webapp.pipeline.harris_matrix import (
    HarrisCorrelation,
    HarrisMatrix,
    HarrisRelation,
    HarrisSuggestion,
    HarrisUnit,
    SourceRef,
)


def section_7_example():
    return {
        "schema_version": 1,
        "matrix_id": "a1b2c3d4e5f6",
        "revision": 0,
        "title": "T123 Harris Matrix",
        "site": "Poggio Civitate",
        "trench": "T123",
        "notes": "",
        "source_job_ids": ["87d03515849d"],
        "units": [
            {
                "id": "unit-0123456789ab",
                "label": "7",
                "unit_type": "deposit",
                "description": None,
                "source_refs": [
                    {
                        "job_id": "87d03515849d",
                        "schema_type": "FieldWallProfile",
                        "face": "N Baulk",
                        "layer_index": 0,
                        "source_label": "7",
                    }
                ],
            }
        ],
        "relations": [
            {
                "id": "rel-0123456789ab",
                "younger_id": "unit-0123456789ab",
                "older_id": "unit-fedcba987654",
                "kind": "above",
                "evidence": "Confirmed shared boundary",
                "source": "suggestion",
                "notes": None,
            }
        ],
        "correlations": [
            {
                "id": "corr-0123456789ab",
                "unit_ids": [
                    "unit-0123456789ab",
                    "unit-111111111111",
                ],
                "notes": None,
            }
        ],
        "suggestions": [
            {
                "id": "suggestion-0123456789ab",
                "suggestion_type": "ordering",
                "status": "pending",
                "younger_id": "unit-0123456789ab",
                "older_id": "unit-fedcba987654",
                "relation_kind": "above",
                "correlation_unit_ids": [],
                "reason": (
                    "Consecutive source layers share a recorded boundary."
                ),
                "source_refs": [],
            }
        ],
        "created_at": "2026-07-28T08:00:00+00:00",
        "updated_at": "2026-07-28T08:00:00+00:00",
    }


def test_complete_section_7_example_validates_and_round_trips_through_json():
    example = section_7_example()

    matrix = HarrisMatrix.model_validate(example)
    serialized = matrix.model_dump_json()

    assert HarrisMatrix.model_validate_json(serialized) == matrix
    serialized_data = json.loads(serialized)
    assert set(serialized_data) == set(example)
    assert set(serialized_data["units"][0]) == set(example["units"][0])
    assert set(serialized_data["relations"][0]) == set(
        example["relations"][0]
    )
    assert set(serialized_data["correlations"][0]) == set(
        example["correlations"][0]
    )
    assert set(serialized_data["suggestions"][0]) == set(
        example["suggestions"][0]
    )


def test_schema_version_other_than_one_is_rejected():
    example = section_7_example()
    example["schema_version"] = 2

    with pytest.raises(ValidationError, match="schema_version"):
        HarrisMatrix.model_validate(example)


@pytest.mark.parametrize(
    ("path", "invalid_id"),
    [
        (("matrix_id",), "A1B2C3D4E5F6"),
        (("units", 0, "id"), "unit-123"),
        (("relations", 0, "id"), "relation-0123456789ab"),
        (("correlations", 0, "id"), "corr-0123456789AB"),
        (("suggestions", 0, "id"), "suggestion-0123456789"),
        (("relations", 0, "younger_id"), "0123456789ab"),
        (("correlations", 0, "unit_ids", 0), "unit-not-hexadecimal"),
        (("source_job_ids", 0), "job-87d03515849d"),
    ],
)
def test_invalid_matrix_and_object_id_formats_are_rejected(path, invalid_id):
    example = section_7_example()
    target = example
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = invalid_id

    with pytest.raises(ValidationError):
        HarrisMatrix.model_validate(example)


@pytest.mark.parametrize(
    ("path", "unknown_value"),
    [
        (("units", 0, "unit_type"), "occupation"),
        (("relations", 0, "kind"), "below"),
        (("relations", 0, "source"), "automatic"),
        (("suggestions", 0, "suggestion_type"), "sequence"),
        (("suggestions", 0, "status"), "ignored"),
    ],
)
def test_every_enum_rejects_unknown_values(path, unknown_value):
    example = section_7_example()
    target = example
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = unknown_value

    with pytest.raises(ValidationError):
        HarrisMatrix.model_validate(example)


def test_blank_unit_labels_are_rejected_after_trimming():
    example = section_7_example()
    example["units"][0]["label"] = " \n\t "

    with pytest.raises(ValidationError, match="label"):
        HarrisMatrix.model_validate(example)


def test_human_text_is_trimmed_but_source_label_is_preserved_exactly():
    source_label = "  Locus 7 \n"
    example = section_7_example()
    example["title"] = "  T123 Harris Matrix  "
    example["units"][0]["label"] = "  7  "
    example["units"][0]["source_refs"][0]["source_label"] = source_label

    matrix = HarrisMatrix.model_validate(example)

    assert matrix.title == "T123 Harris Matrix"
    assert matrix.units[0].label == "7"
    assert matrix.units[0].source_refs[0].source_label == source_label


def test_source_refs_reject_negative_layer_indexes():
    source_ref = section_7_example()["units"][0]["source_refs"][0]
    source_ref["layer_index"] = -1

    with pytest.raises(ValidationError, match="layer_index"):
        SourceRef.model_validate(source_ref)


def test_source_refs_reject_unknown_schema_types():
    source_ref = section_7_example()["units"][0]["source_refs"][0]
    source_ref["schema_type"] = "UnknownDiagram"

    with pytest.raises(ValidationError, match="schema_type"):
        SourceRef.model_validate(source_ref)


@pytest.mark.parametrize(
    "unit_ids",
    [
        [],
        ["unit-0123456789ab"],
        ["unit-0123456789ab", "unit-0123456789ab"],
    ],
)
def test_correlations_require_at_least_two_distinct_units(unit_ids):
    correlation = section_7_example()["correlations"][0]
    correlation["unit_ids"] = unit_ids

    with pytest.raises(ValidationError, match="distinct unit"):
        HarrisCorrelation.model_validate(correlation)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("younger_id", None),
        ("older_id", None),
        ("relation_kind", None),
        ("correlation_unit_ids", ["unit-0123456789ab", "unit-111111111111"]),
    ],
)
def test_ordering_suggestions_enforce_required_and_null_fields(field, value):
    suggestion = section_7_example()["suggestions"][0]
    suggestion[field] = value

    with pytest.raises(ValidationError, match="ordering"):
        HarrisSuggestion.model_validate(suggestion)


def correlation_suggestion():
    return {
        "id": "suggestion-0123456789ab",
        "suggestion_type": "correlation",
        "status": "pending",
        "younger_id": None,
        "older_id": None,
        "relation_kind": None,
        "correlation_unit_ids": [
            "unit-0123456789ab",
            "unit-111111111111",
        ],
        "reason": "Matching normalized labels from different source faces.",
        "source_refs": [],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("younger_id", "unit-0123456789ab"),
        ("older_id", "unit-111111111111"),
        ("relation_kind", "above"),
        ("correlation_unit_ids", ["unit-0123456789ab"]),
    ],
)
def test_correlation_suggestions_enforce_required_and_null_fields(field, value):
    suggestion = correlation_suggestion()
    suggestion[field] = value

    with pytest.raises(ValidationError, match="correlation"):
        HarrisSuggestion.model_validate(suggestion)


def test_valid_correlation_suggestion_accepts_required_null_fields():
    suggestion = HarrisSuggestion.model_validate(correlation_suggestion())

    assert suggestion.younger_id is None
    assert suggestion.older_id is None
    assert suggestion.relation_kind is None


def test_revision_rejects_negative_values():
    example = section_7_example()
    example["revision"] = -1

    with pytest.raises(ValidationError, match="revision"):
        HarrisMatrix.model_validate(example)


@pytest.mark.parametrize("timestamp_field", ["created_at", "updated_at"])
@pytest.mark.parametrize(
    "invalid_timestamp",
    ["2026-07-28T08:00:00", "not-an-ISO-datetime"],
)
def test_timestamps_must_be_timezone_aware_iso_datetimes(
    timestamp_field,
    invalid_timestamp,
):
    example = section_7_example()
    example[timestamp_field] = invalid_timestamp

    with pytest.raises(ValidationError, match=timestamp_field):
        HarrisMatrix.model_validate(example)


def test_serialization_emits_only_section_7_snake_case_field_names():
    serialized = json.loads(
        HarrisMatrix.model_validate(section_7_example()).model_dump_json()
    )

    assert set(serialized) == {
        "schema_version",
        "matrix_id",
        "revision",
        "title",
        "site",
        "trench",
        "notes",
        "source_job_ids",
        "units",
        "relations",
        "correlations",
        "suggestions",
        "created_at",
        "updated_at",
    }
    assert "schemaVersion" not in serialized
    assert "matrixId" not in serialized
    assert "unitType" not in serialized["units"][0]
    assert "youngerId" not in serialized["relations"][0]


@pytest.mark.parametrize(
    "path",
    [
        (),
        ("units", 0),
        ("units", 0, "source_refs", 0),
        ("relations", 0),
        ("correlations", 0),
        ("suggestions", 0),
    ],
)
def test_extra_unknown_fields_are_rejected(path):
    example = section_7_example()
    target = example
    for key in path:
        target = target[key]
    target["unexpected"] = True

    with pytest.raises(ValidationError, match="unexpected"):
        HarrisMatrix.model_validate(example)


def test_nullable_fields_remain_nullable():
    example = section_7_example()
    example["units"][0]["source_refs"][0]["source_label"] = None

    matrix = HarrisMatrix.model_validate(example)
    correlation = HarrisSuggestion.model_validate(correlation_suggestion())

    assert matrix.units[0].description is None
    assert matrix.units[0].source_refs[0].source_label is None
    assert matrix.relations[0].notes is None
    assert matrix.correlations[0].notes is None
    assert correlation.younger_id is None
    assert correlation.older_id is None
    assert correlation.relation_kind is None


def test_each_public_model_validates_its_section_7_shape():
    example = section_7_example()

    assert SourceRef.model_validate(
        example["units"][0]["source_refs"][0]
    )
    assert HarrisUnit.model_validate(example["units"][0])
    assert HarrisRelation.model_validate(example["relations"][0])
    assert HarrisCorrelation.model_validate(example["correlations"][0])
    assert HarrisSuggestion.model_validate(example["suggestions"][0])
