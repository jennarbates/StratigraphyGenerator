import json

import pytest

from poggio_webapp.pipeline.harris_matrix import (
    HarrisMatrix,
    correlation_components,
    topological_order,
    transitive_reduction,
    validate_matrix_graph,
)

A = "unit-00000000000a"
B = "unit-00000000000b"
C = "unit-00000000000c"
D = "unit-00000000000d"


def unit(unit_id, label=None):
    return {
        "id": unit_id,
        "label": label or unit_id[-1].upper(),
        "unit_type": "deposit",
        "description": None,
        "source_refs": [],
    }


def relation(number, younger_id, older_id, kind="above"):
    return {
        "id": f"rel-{number:012x}",
        "younger_id": younger_id,
        "older_id": older_id,
        "kind": kind,
        "evidence": "",
        "source": "manual",
        "notes": None,
    }


def correlation(number, unit_ids):
    return {
        "id": f"corr-{number:012x}",
        "unit_ids": unit_ids,
        "notes": None,
    }


def matrix(*, units=(), relations=(), correlations=()):
    return HarrisMatrix.model_validate(
        {
            "schema_version": 1,
            "matrix_id": "0123456789ab",
            "revision": 0,
            "title": "Graph test",
            "site": "Poggio Civitate",
            "trench": "T123",
            "notes": "",
            "source_job_ids": [],
            "units": list(units),
            "relations": list(relations),
            "correlations": list(correlations),
            "suggestions": [],
            "created_at": "2026-07-28T08:00:00+00:00",
            "updated_at": "2026-07-28T08:00:00+00:00",
        }
    )


def issues_with_code(report, code):
    return [
        issue
        for issue in report["errors"] + report["warnings"]
        if issue["code"] == code
    ]


def test_empty_matrix_is_valid_and_report_is_json_serializable():
    report = validate_matrix_graph(matrix())

    assert report == {
        "ok": True,
        "errors": [],
        "warnings": [],
        "topological_order": [],
        "display_edges": [],
    }
    json.dumps(report)


def test_simple_chain_is_valid_and_orders_younger_before_older():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[
            relation(1, A, B),
            relation(2, B, C),
        ],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is True
    assert report["topological_order"] == [A, B, C]
    assert report["display_edges"] == [(A, B), (B, C)]
    assert topological_order(graph) == [A, B, C]


def test_missing_unit_references_produce_stable_error():
    graph = matrix(
        units=[unit(A)],
        relations=[relation(1, A, B)],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is False
    assert issues_with_code(report, "missing-unit")[0]["unit_ids"] == [B]
    assert issues_with_code(report, "missing-unit")[0]["relation_ids"] == [
        "rel-000000000001"
    ]


def test_self_relation_produces_stable_error():
    graph = matrix(
        units=[unit(A)],
        relations=[relation(1, A, A)],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is False
    assert issues_with_code(report, "self-relation")[0]["unit_ids"] == [A]


def test_duplicate_younger_older_pairs_produce_stable_error():
    graph = matrix(
        units=[unit(A), unit(B)],
        relations=[
            relation(2, A, B, "cuts"),
            relation(1, A, B, "above"),
        ],
    )

    duplicate = issues_with_code(
        validate_matrix_graph(graph),
        "duplicate-relation",
    )[0]

    assert duplicate["unit_ids"] == [A, B]
    assert duplicate["relation_ids"] == [
        "rel-000000000001",
        "rel-000000000002",
    ]


def test_reciprocal_pairs_produce_cycle_error():
    graph = matrix(
        units=[unit(A), unit(B)],
        relations=[
            relation(1, A, B),
            relation(2, B, A),
        ],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is False
    cycle = issues_with_code(report, "cycle")[0]
    assert cycle["unit_ids"] == [A, B, A]
    assert cycle["relation_ids"] == [
        "rel-000000000001",
        "rel-000000000002",
    ]


def test_three_node_cycle_reports_concrete_cycle_path():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[
            relation(1, A, B),
            relation(2, B, C),
            relation(3, C, A),
        ],
    )

    cycle = issues_with_code(validate_matrix_graph(graph), "cycle")[0]

    assert cycle["unit_ids"] == [A, B, C, A]
    assert f"{A} -> {B} -> {C} -> {A}" in cycle["message"]


def test_disconnected_components_are_allowed():
    graph = matrix(
        units=[unit(A), unit(B), unit(C), unit(D)],
        relations=[
            relation(1, A, B),
            relation(2, C, D),
        ],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is True
    assert report["errors"] == []
    assert report["display_edges"] == [(A, B), (C, D)]


def test_isolated_units_produce_warnings_without_invalidating_matrix():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[relation(1, A, B)],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is True
    assert issues_with_code(report, "isolated-unit")[0]["unit_ids"] == [C]


def test_generic_polygon_labels_produce_warnings():
    graph = matrix(units=[unit(A, "Polygon 12")])

    report = validate_matrix_graph(graph)

    generic = issues_with_code(report, "generic-label")[0]
    assert generic["unit_ids"] == [A]
    assert report["ok"] is True


def test_correlation_components_collapse_units_deterministically():
    graph = matrix(
        units=[unit(C), unit(B), unit(A)],
        correlations=[correlation(1, [B, A])],
    )

    first = correlation_components(graph)
    second = correlation_components(graph)

    assert first == second == {
        A: A,
        B: A,
        C: C,
    }


def test_overlapping_stored_correlations_produce_stable_error():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        correlations=[
            correlation(1, [A, B]),
            correlation(2, [B, C]),
        ],
    )

    overlap = issues_with_code(
        validate_matrix_graph(graph),
        "overlapping-correlation",
    )[0]

    assert overlap["unit_ids"] == [B]
    assert "corr-000000000001" in overlap["message"]
    assert "corr-000000000002" in overlap["message"]


def test_relation_within_correlation_component_is_rejected():
    graph = matrix(
        units=[unit(A), unit(B)],
        relations=[relation(1, A, B)],
        correlations=[correlation(1, [B, A])],
    )

    issue = issues_with_code(
        validate_matrix_graph(graph),
        "relation-within-correlation",
    )[0]

    assert issue["unit_ids"] == [A, B]
    assert issue["relation_ids"] == ["rel-000000000001"]


def test_correlation_collapse_can_reveal_a_cycle():
    graph = matrix(
        units=[unit(A), unit(B), unit(C), unit(D)],
        relations=[
            relation(1, A, B),
            relation(2, B, C),
            relation(3, C, D),
        ],
        correlations=[correlation(1, [D, A])],
    )

    report = validate_matrix_graph(graph)

    assert report["ok"] is False
    cycle = issues_with_code(report, "cycle")[0]
    assert cycle["unit_ids"] == [A, B, C, A]
    assert cycle["relation_ids"] == [
        "rel-000000000001",
        "rel-000000000002",
        "rel-000000000003",
    ]


def test_transitive_reduction_changes_display_edges_not_saved_relations():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[
            relation(1, A, B),
            relation(2, B, C),
            relation(3, A, C),
        ],
    )
    saved_before = graph.model_dump(mode="json")

    report = validate_matrix_graph(graph)

    assert report["display_edges"] == [(A, B), (B, C)]
    assert transitive_reduction(graph) == [(A, B), (B, C)]
    assert len(graph.relations) == 3
    assert graph.model_dump(mode="json") == saved_before


def test_redundant_saved_relation_produces_warning():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[
            relation(1, A, B),
            relation(2, B, C),
            relation(3, A, C),
        ],
    )

    redundant = issues_with_code(
        validate_matrix_graph(graph),
        "redundant-relation",
    )[0]

    assert redundant["unit_ids"] == [A, C]
    assert redundant["relation_ids"] == ["rel-000000000003"]


def test_lexical_tie_breaking_is_stable_across_input_orderings_and_runs():
    first = matrix(
        units=[unit(D), unit(C), unit(B), unit(A)],
        relations=[
            relation(2, C, D),
            relation(1, A, B),
        ],
    )
    second = matrix(
        units=[unit(A), unit(B), unit(C), unit(D)],
        relations=[
            relation(1, A, B),
            relation(2, C, D),
        ],
    )

    first_report = validate_matrix_graph(first)
    second_report = validate_matrix_graph(second)

    assert first_report["topological_order"] == [A, B, C, D]
    assert first_report == second_report
    assert validate_matrix_graph(first) == first_report


@pytest.mark.parametrize(
    "kind",
    ["above", "cuts", "fills", "precedes", "other"],
)
def test_relationship_kind_does_not_change_younger_to_older_direction(kind):
    graph = matrix(
        units=[unit(A), unit(B)],
        relations=[relation(1, A, B, kind)],
    )

    report = validate_matrix_graph(graph)

    assert report["topological_order"] == [A, B]
    assert report["display_edges"] == [(A, B)]
