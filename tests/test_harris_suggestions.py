import json
import math
from datetime import datetime, timezone

import pytest

from poggio_webapp.pipeline.harris_import import import_source_jobs
from poggio_webapp.pipeline.harris_matrix import (
    HarrisCorrelation,
    HarrisMatrix,
    HarrisRelation,
    HarrisUnit,
)
from poggio_webapp.pipeline.harris_suggestions import (
    HarrisSuggestionError,
    generate_suggestions,
    review_suggestion,
)


FIELD_JOB = "111111111111"
SECOND_JOB = "222222222222"


def empty_matrix():
    timestamp = datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc)
    return HarrisMatrix(
        schema_version=1,
        matrix_id="aaaaaaaaaaaa",
        revision=0,
        title="Suggestion test",
        site="Poggio Civitate",
        trench="T123",
        notes="",
        source_job_ids=[],
        units=[],
        relations=[],
        correlations=[],
        suggestions=[],
        created_at=timestamp,
        updated_at=timestamp,
    )


def field_point(x, depth, confidence="high"):
    return {
        "xMeters": x,
        "depthMeters": depth,
        "confidence": confidence,
    }


def illustrator_point(x, depth, confidence="human-traced"):
    return {
        "xCoordinateMeters": x,
        "yCoordinateMeters": depth,
        "confidence": confidence,
    }


def field_document(
    *,
    face="North baulk",
    labels=("Upper", "Lower"),
    upper_bottom=None,
    lower_top=None,
):
    if upper_bottom is None:
        upper_bottom = [
            field_point(0.0, 0.4),
            field_point(1.0, 0.5),
        ]
    if lower_top is None:
        lower_top = [
            field_point(0.0, 0.4, "low"),
            field_point(1.0, 0.5, "medium"),
        ]
    return {
        "trenchLabel": "T123",
        "faceLabel": face,
        "loci": [],
        "layers": [
            {
                "locusNumber": labels[0],
                "topBoundary": [
                    field_point(0.0, 0.0),
                    field_point(1.0, 0.0),
                ],
                "bottomBoundary": upper_bottom,
            },
            {
                "locusNumber": labels[1],
                "topBoundary": lower_top,
                "bottomBoundary": [
                    field_point(0.0, 0.9),
                    field_point(1.0, 1.0),
                ],
            },
        ],
    }


def illustrator_document(
    *,
    face="East",
    labels=("Upper", "Lower"),
    upper_bottom=None,
    lower_top=None,
):
    if upper_bottom is None:
        upper_bottom = [
            illustrator_point(0.0, 0.4),
            illustrator_point(1.0, 0.5),
        ]
    if lower_top is None:
        lower_top = [
            illustrator_point(0.0, 0.4, "low"),
            illustrator_point(1.0, 0.5, "medium"),
        ]
    return {
        "metadata": {"trenchLabel": "T123"},
        "trenchProfiles": [
            {
                "face": face,
                "layers": [
                    {
                        "layerName": labels[0],
                        "topBoundary": [
                            illustrator_point(0.0, 0.0),
                            illustrator_point(1.0, 0.0),
                        ],
                        "bottomBoundary": upper_bottom,
                    },
                    {
                        "layerName": labels[1],
                        "topBoundary": lower_top,
                        "bottomBoundary": [
                            illustrator_point(0.0, 0.9),
                            illustrator_point(1.0, 1.0),
                        ],
                    },
                ],
            }
        ],
    }


def write_job(jobs_dir, job_id, document):
    job_dir = jobs_dir / job_id
    job_dir.mkdir(parents=True)
    (job_dir / "extraction_output.json").write_text(
        json.dumps(document),
        encoding="utf-8",
    )
    return job_dir


def imported_matrix(jobs_dir, documents):
    for job_id, document in documents:
        write_job(jobs_dir, job_id, document)
    matrix, _warnings = import_source_jobs(
        empty_matrix(),
        [job_id for job_id, _document in documents],
        jobs_dir,
    )
    return matrix


def suggestions_of_type(matrix, suggestion_type):
    return [
        suggestion
        for suggestion in matrix.suggestions
        if suggestion.suggestion_type == suggestion_type
    ]


def source_snapshot(jobs_dir):
    return {
        path.relative_to(jobs_dir): path.read_bytes()
        for path in sorted(jobs_dir.rglob("*"))
        if path.is_file()
    }


def manual_relation(number, younger_id, older_id):
    return HarrisRelation(
        id=f"rel-{number:012x}",
        younger_id=younger_id,
        older_id=older_id,
        kind="above",
        evidence="Manual relationship",
        source="manual",
        notes=None,
    )


def test_exact_shared_field_wall_boundary_suggests_above(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [(FIELD_JOB, field_document())],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    ordering = suggestions_of_type(generated, "ordering")
    assert len(ordering) == 1
    assert ordering[0].younger_id == matrix.units[0].id
    assert ordering[0].older_id == matrix.units[1].id
    assert ordering[0].relation_kind == "above"
    assert ordering[0].status == "pending"


def test_exact_shared_illustrator_boundary_suggests_above(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [(FIELD_JOB, illustrator_document())],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    ordering = suggestions_of_type(generated, "ordering")
    assert len(ordering) == 1
    assert ordering[0].younger_id == matrix.units[0].id
    assert ordering[0].older_id == matrix.units[1].id
    assert ordering[0].relation_kind == "above"


def test_boundaries_inside_tolerance_match_after_sorting(tmp_path):
    jobs_dir = tmp_path / "jobs"
    upper_bottom = [
        field_point(1.0, 0.5, "certain"),
        field_point(0.0, 0.4, "certain"),
    ]
    lower_top = [
        field_point(0.019, 0.381, "uncertain"),
        field_point(0.981, 0.519, "uncertain"),
    ]
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(
                    upper_bottom=upper_bottom,
                    lower_top=lower_top,
                ),
            )
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir, tolerance_m=0.02)

    assert len(suggestions_of_type(generated, "ordering")) == 1


def test_boundary_value_outside_tolerance_does_not_match(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(
                    lower_top=[
                        field_point(0.0, 0.4),
                        field_point(1.021, 0.5),
                    ]
                ),
            )
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir, tolerance_m=0.02)

    assert suggestions_of_type(generated, "ordering") == []


def test_unequal_boundary_point_counts_do_not_match(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(
                    lower_top=[
                        field_point(0.0, 0.4),
                        field_point(0.5, 0.45),
                        field_point(1.0, 0.5),
                    ]
                ),
            )
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    assert suggestions_of_type(generated, "ordering") == []


@pytest.mark.parametrize(
    ("upper_bottom", "lower_top"),
    [
        (
            [field_point(0.0, 0.4)],
            [field_point(0.0, 0.4)],
        ),
        (
            [
                field_point(0.0, 0.4),
                field_point(math.inf, 0.5),
            ],
            [
                field_point(0.0, 0.4),
                field_point(math.inf, 0.5),
            ],
        ),
    ],
)
def test_non_finite_or_one_point_boundaries_do_not_match(
    tmp_path,
    upper_bottom,
    lower_top,
):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(
                    upper_bottom=upper_bottom,
                    lower_top=lower_top,
                ),
            )
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    assert suggestions_of_type(generated, "ordering") == []


def test_consecutive_layers_without_shared_geometry_do_not_suggest_ordering(
    tmp_path,
):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(
                    lower_top=[
                        field_point(0.0, 0.7),
                        field_point(1.0, 0.8),
                    ]
                ),
            )
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    assert suggestions_of_type(generated, "ordering") == []


def test_same_trimmed_case_insensitive_label_across_jobs_suggests_correlation(
    tmp_path,
):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(labels=(" Shared locus ", "Lower A")),
            ),
            (
                SECOND_JOB,
                field_document(
                    face="South baulk",
                    labels=("shared LOCUS", "Lower B"),
                ),
            ),
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    correlation = suggestions_of_type(generated, "correlation")
    assert len(correlation) == 1
    assert correlation[0].correlation_unit_ids == sorted(
        [matrix.units[0].id, matrix.units[2].id]
    )
    assert generated.correlations == []


def test_equal_labels_on_same_job_and_face_do_not_suggest_correlation(
    tmp_path,
):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [(FIELD_JOB, field_document(labels=("Same", "same")))],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    assert suggestions_of_type(generated, "correlation") == []


@pytest.mark.parametrize("label", ["Polygon 1", None])
def test_generic_and_unlabeled_labels_do_not_suggest_correlation(
    tmp_path,
    label,
):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (FIELD_JOB, field_document(labels=(label, "Lower A"))),
            (
                SECOND_JOB,
                field_document(
                    face="South baulk",
                    labels=(label, "Lower B"),
                ),
            ),
        ],
    )

    generated = generate_suggestions(matrix, jobs_dir)

    assert suggestions_of_type(generated, "correlation") == []


def test_suggestion_ids_and_order_are_deterministic(tmp_path):
    jobs_dir = tmp_path / "jobs"
    documents = [
        (
            FIELD_JOB,
            field_document(labels=("Shared upper", "Shared lower")),
        ),
        (
            SECOND_JOB,
            field_document(
                face="South baulk",
                labels=("shared upper", "shared lower"),
            ),
        ),
    ]
    first = imported_matrix(jobs_dir, documents)
    second = first.model_copy(deep=True)
    second.units.reverse()

    first_generated = generate_suggestions(first, jobs_dir)
    second_generated = generate_suggestions(second, jobs_dir)
    first_dump = [
        suggestion.model_dump(mode="json")
        for suggestion in first_generated.suggestions
    ]
    second_dump = [
        suggestion.model_dump(mode="json")
        for suggestion in second_generated.suggestions
    ]

    assert first_dump == second_dump
    assert [item["id"] for item in first_dump] == sorted(
        item["id"] for item in first_dump
    )


def test_regeneration_is_idempotent_and_preserves_rejected_status(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [(FIELD_JOB, field_document())],
    )
    generated = generate_suggestions(matrix, jobs_dir)
    suggestion_id = generated.suggestions[0].id
    rejected = review_suggestion(generated, suggestion_id, "reject")

    regenerated = generate_suggestions(rejected, jobs_dir)
    regenerated_again = generate_suggestions(regenerated, jobs_dir)

    assert len(regenerated.suggestions) == 1
    assert regenerated.suggestions[0].status == "rejected"
    assert regenerated.model_dump(mode="json") == regenerated_again.model_dump(
        mode="json"
    )


def test_accept_ordering_adds_exactly_one_suggestion_relation(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = generate_suggestions(
        imported_matrix(
            jobs_dir,
            [(FIELD_JOB, field_document())],
        ),
        jobs_dir,
    )

    accepted = review_suggestion(
        matrix,
        matrix.suggestions[0].id,
        "accept",
    )

    assert accepted.suggestions[0].status == "accepted"
    assert len(accepted.relations) == 1
    assert accepted.relations[0].younger_id == matrix.suggestions[0].younger_id
    assert accepted.relations[0].older_id == matrix.suggestions[0].older_id
    assert accepted.relations[0].source == "suggestion"
    assert matrix.relations == []
    assert matrix.suggestions[0].status == "pending"


def test_accept_correlation_creates_and_merges_exactly_one_group(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [
            (
                FIELD_JOB,
                field_document(labels=("Shared", "Lower A")),
            ),
            (
                SECOND_JOB,
                field_document(
                    face="South baulk",
                    labels=("shared", "Lower B"),
                ),
            ),
        ],
    )
    extra_unit = HarrisUnit(
        id="unit-00000000000f",
        label="Existing correlated unit",
        unit_type="deposit",
        description=None,
        source_refs=[],
    )
    matrix.units.append(extra_unit)
    matrix.correlations.append(
        HarrisCorrelation(
            id="corr-000000000001",
            unit_ids=[matrix.units[0].id, extra_unit.id],
            notes="Keep this group",
        )
    )
    generated = generate_suggestions(matrix, jobs_dir)
    suggestion = suggestions_of_type(generated, "correlation")[0]

    accepted = review_suggestion(generated, suggestion.id, "accept")

    assert len(accepted.correlations) == 1
    assert accepted.correlations[0].id == "corr-000000000001"
    assert accepted.correlations[0].unit_ids == sorted(
        [
            matrix.units[0].id,
            matrix.units[2].id,
            extra_unit.id,
        ]
    )
    assert accepted.correlations[0].notes == "Keep this group"
    assert next(
        item for item in accepted.suggestions if item.id == suggestion.id
    ).status == "accepted"


def test_reject_changes_only_suggestion_status(tmp_path):
    jobs_dir = tmp_path / "jobs"
    generated = generate_suggestions(
        imported_matrix(
            jobs_dir,
            [(FIELD_JOB, field_document())],
        ),
        jobs_dir,
    )
    before = generated.model_dump(mode="json")

    rejected = review_suggestion(
        generated,
        generated.suggestions[0].id,
        "reject",
    )
    after = rejected.model_dump(mode="json")

    before["suggestions"][0]["status"] = "rejected"
    assert after == before
    assert generated.suggestions[0].status == "pending"


def test_accepting_same_suggestion_twice_is_idempotent(tmp_path):
    jobs_dir = tmp_path / "jobs"
    generated = generate_suggestions(
        imported_matrix(
            jobs_dir,
            [(FIELD_JOB, field_document())],
        ),
        jobs_dir,
    )
    first = review_suggestion(
        generated,
        generated.suggestions[0].id,
        "accept",
    )

    second = review_suggestion(
        first,
        first.suggestions[0].id,
        "accept",
    )

    assert second.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(second.relations) == 1


def test_cycle_producing_acceptance_fails_without_mutation(tmp_path):
    jobs_dir = tmp_path / "jobs"
    generated = generate_suggestions(
        imported_matrix(
            jobs_dir,
            [(FIELD_JOB, field_document())],
        ),
        jobs_dir,
    )
    suggestion = suggestions_of_type(generated, "ordering")[0]
    generated.relations.append(
        manual_relation(1, suggestion.older_id, suggestion.younger_id)
    )
    before = generated.model_dump(mode="json")

    with pytest.raises(HarrisSuggestionError, match="cycle"):
        review_suggestion(generated, suggestion.id, "accept")

    assert generated.model_dump(mode="json") == before
    assert generated.suggestions[0].status == "pending"
    assert len(generated.relations) == 1


def test_correlation_conflict_acceptance_fails_without_mutation(tmp_path):
    jobs_dir = tmp_path / "jobs"
    generated = generate_suggestions(
        imported_matrix(
            jobs_dir,
            [
                (
                    FIELD_JOB,
                    field_document(labels=("Shared", "Lower A")),
                ),
                (
                    SECOND_JOB,
                    field_document(
                        face="South baulk",
                        labels=("shared", "Lower B"),
                    ),
                ),
            ],
        ),
        jobs_dir,
    )
    suggestion = suggestions_of_type(generated, "correlation")[0]
    generated.relations.append(
        manual_relation(
            1,
            suggestion.correlation_unit_ids[0],
            suggestion.correlation_unit_ids[1],
        )
    )
    before = generated.model_dump(mode="json")

    with pytest.raises(HarrisSuggestionError, match="correlation"):
        review_suggestion(generated, suggestion.id, "accept")

    assert generated.model_dump(mode="json") == before


def test_unknown_suggestion_and_action_give_focused_errors(tmp_path):
    jobs_dir = tmp_path / "jobs"
    generated = generate_suggestions(
        imported_matrix(
            jobs_dir,
            [(FIELD_JOB, field_document())],
        ),
        jobs_dir,
    )

    with pytest.raises(HarrisSuggestionError, match="Unknown suggestion"):
        review_suggestion(
            generated,
            "suggestion-ffffffffffff",
            "accept",
        )
    with pytest.raises(HarrisSuggestionError, match="action.*accept.*reject"):
        review_suggestion(
            generated,
            generated.suggestions[0].id,
            "approve",
        )


def test_generation_and_review_never_change_source_files(tmp_path):
    jobs_dir = tmp_path / "jobs"
    matrix = imported_matrix(
        jobs_dir,
        [(FIELD_JOB, field_document())],
    )
    job_dir = jobs_dir / FIELD_JOB
    (job_dir / "meta.json").write_text(
        json.dumps({"extraction_path": "extraction_output.json"}),
        encoding="utf-8",
    )
    before = source_snapshot(jobs_dir)

    generated = generate_suggestions(matrix, jobs_dir)
    reviewed = review_suggestion(
        generated,
        generated.suggestions[0].id,
        "reject",
    )

    assert reviewed.suggestions[0].status == "rejected"
    assert source_snapshot(jobs_dir) == before
