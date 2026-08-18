"""Where a model's stratigraphic order comes from.

Three sources, unequal. A Harris matrix is the excavation's own record; the
recorded layer sequence is what one wall saw; mean elevation is an assumption
that *Excavation and Documentation Procedures* documents as sometimes false at
this site -- "stratigraphically newer deposits may exist at lower elevations
than stratigraphically older deposits". These tests pin that the best available
source is used and that the weakest one says what it is.
"""

import pytest

from pipeline import series_order
from pipeline.harris_matrix import HarrisMatrix

A = "unit-00000000000a"
B = "unit-00000000000b"
C = "unit-00000000000c"
D = "unit-00000000000d"


def unit(unit_id, label, schema_type="FieldWallProfile", face="north wall"):
    return {
        "id": unit_id,
        "label": label,
        "unit_type": "deposit",
        "description": None,
        "source_refs": [
            {
                "job_id": "0123456789ab",
                "schema_type": schema_type,
                "face": face,
                "layer_index": 0,
                "source_label": label,
            }
        ],
    }


def relation(number, younger_id, older_id):
    return {
        "id": f"rel-{number:012x}",
        "younger_id": younger_id,
        "older_id": older_id,
        "kind": "above",
        "evidence": "",
        "source": "manual",
        "notes": None,
    }


def correlation(number, unit_ids):
    return {"id": f"corr-{number:012x}", "unit_ids": unit_ids, "notes": None}


def matrix(*, units=(), relations=(), correlations=(), trench="T123"):
    return HarrisMatrix.model_validate(
        {
            "schema_version": 1,
            "matrix_id": "0123456789ab",
            "revision": 0,
            "title": "Order test",
            "site": "Poggio Civitate",
            "trench": trench,
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


# Harris units map onto model surfaces


def test_a_field_sheet_unit_becomes_the_surface_the_converter_emits():
    """Harris labels field units with the bare locus number; the converter
    emits 'Locus 6'. They must match as strings or GemPy fuses nothing."""
    order, _arbitrary, _notes = series_order.from_harris(
        matrix(units=[unit(A, "6"), unit(B, "7")], relations=[relation(1, A, B)])
    )

    assert order == ["Locus 6", "Locus 7"]


def test_an_illustrator_unit_keeps_its_layer_name():
    order, _a, _n = series_order.from_harris(
        matrix(
            units=[
                unit(A, "Topsoil", schema_type="ArchaeologicalDiagram"),
                unit(B, "Fill", schema_type="ArchaeologicalDiagram"),
            ],
            relations=[relation(1, A, B)],
        )
    )

    assert order == ["Topsoil", "Fill"]


def test_order_runs_young_to_old():
    order, _a, _n = series_order.from_harris(
        matrix(
            units=[unit(A, "1"), unit(B, "2"), unit(C, "3")],
            relations=[relation(1, A, B), relation(2, B, C)],
        )
    )

    assert order == ["Locus 1", "Locus 2", "Locus 3"]


def test_correlated_units_collapse_to_one_position():
    """The same deposit recorded on two walls under different numbers."""
    correlated = matrix(
        units=[unit(A, "1"), unit(B, "1", face="east wall"), unit(C, "2")],
        relations=[relation(1, A, C)],
        correlations=[correlation(1, [A, B])],
    )
    order, _a, _n = series_order.from_harris(correlated)

    assert order == ["Locus 1", "Locus 2"]


# Contemporaneity


def test_unrelated_deposits_are_reported_as_arbitrarily_ordered():
    """Deposits either side of a wall are contemporary and the matrix says so
    by having no edge. GemPy's stack still needs a total order, so one is
    imposed -- and recorded as imposed."""
    order, arbitrary, notes = series_order.from_harris(
        matrix(units=[unit(A, "1"), unit(B, "2")])
    )

    assert len(order) == 2
    assert arbitrary == [(order[0], order[1])]
    assert any("records no relationship" in note for note in notes)
    assert any("not evidence" in note for note in notes)


def test_a_fully_ordered_matrix_reports_nothing_arbitrary():
    _order, arbitrary, notes = series_order.from_harris(
        matrix(units=[unit(A, "1"), unit(B, "2")], relations=[relation(1, A, B)])
    )

    assert arbitrary == []
    assert notes == []


def test_an_order_implied_through_a_chain_is_not_arbitrary():
    """A relates to B and B to C, so A before C is recorded, not invented."""
    _order, arbitrary, _notes = series_order.from_harris(
        matrix(
            units=[unit(A, "1"), unit(B, "2"), unit(C, "3")],
            relations=[relation(1, A, B), relation(2, B, C)],
        )
    )

    assert arbitrary == []


# Refusals


def test_a_cycle_in_the_matrix_refuses_with_its_own_message():
    with pytest.raises(series_order.SeriesOrderError) as caught:
        series_order.from_harris(
            matrix(
                units=[unit(A, "1"), unit(B, "2")],
                relations=[relation(1, A, B), relation(2, B, A)],
            )
        )
    assert "cannot be ordered" in str(caught.value)


def test_a_modelled_surface_absent_from_the_matrix_refuses():
    """A partial order would silently drop that surface from the model."""
    with pytest.raises(series_order.SeriesOrderError) as caught:
        series_order.from_harris(
            matrix(units=[unit(A, "1")], relations=[]),
            available_surfaces={"Locus 1", "Locus 9"},
        )
    message = str(caught.value)
    assert "'Locus 9'" in message
    assert "silently drop" in message


def test_matrix_units_the_model_does_not_cover_are_dropped_quietly():
    """run_build rejects an order naming a surface the points CSV lacks, and a
    matrix legitimately covers more of a trench than one model does."""
    order, _a, _n = series_order.from_harris(
        matrix(
            units=[unit(A, "1"), unit(B, "2"), unit(C, "3")],
            relations=[relation(1, A, B), relation(2, B, C)],
        ),
        available_surfaces={"Locus 1", "Locus 3"},
    )

    assert order == ["Locus 1", "Locus 3"]


def test_the_matrix_model_guarantees_every_unit_has_a_label():
    """_unit_surface guards against a blank label, but a validated matrix
    cannot carry one -- so no unit is ever silently dropped from an order."""
    with pytest.raises(Exception, match="at least 1 character"):
        matrix(units=[unit(A, "1"), unit(B, "   ")])


# Provenance descriptions


def test_the_elevation_description_says_it_is_an_assumption():
    text = series_order.describe(series_order.ELEVATION)
    assert "assumption" in text
    assert "lower elevations" in text


@pytest.mark.parametrize(
    "source",
    [
        series_order.HARRIS,
        series_order.RECORDED,
        series_order.SUPPLIED,
    ],
)
def test_every_source_describes_itself(source):
    assert series_order.describe(source).startswith("stratigraphic order came from")


# Finding a trench's matrix


def test_matrices_are_matched_on_the_canonical_trench_label():
    summaries = [
        {"matrix_id": "a" * 12, "trench": "T-104"},
        {"matrix_id": "b" * 12, "trench": "T900"},
    ]
    matched = series_order.matrices_for_trench("T104", summaries)

    assert [m["matrix_id"] for m in matched] == ["a" * 12]


def test_no_trench_label_matches_nothing():
    assert (
        series_order.matrices_for_trench(
            "", [{"matrix_id": "a" * 12, "trench": "T104"}]
        )
        == []
    )


# Precedence, through the trench builder


def _points_csv(tmp_path, *surfaces):
    path = tmp_path / "points.csv"
    rows = "\n".join(
        f"0,0,{index},{name},north wall" for index, name in enumerate(surfaces)
    )
    path.write_text("X,Y,Z,surface,face\n" + rows + "\n")
    return path


def _merged(*surfaces):
    return {
        "trenchProfiles": [
            {
                "face": "north wall",
                "layers": [
                    {"layerName": name, "inferredMaterial": name, "bottomBoundary": []}
                    for name in surfaces
                ],
            }
        ]
    }


def test_a_supplied_order_wins_over_everything(tmp_path):
    from backend.services.trench_builder import resolve_series_order

    notes = []
    order, source, arbitrary = resolve_series_order(
        "T123",
        {"series_order": ["Locus 2", "Locus 1"]},
        _merged("Locus 1", "Locus 2"),
        _points_csv(tmp_path, "Locus 1", "Locus 2"),
        notes,
    )

    assert order == ["Locus 2", "Locus 1"]
    assert source == series_order.SUPPLIED
    assert arbitrary == []


def test_the_recorded_wall_sequence_is_used_when_no_matrix_exists(tmp_path):
    from backend.services.trench_builder import resolve_series_order

    notes = []
    order, source, _arbitrary = resolve_series_order(
        "T123",
        {},
        _merged("Locus 1", "Locus 2"),
        _points_csv(tmp_path, "Locus 1", "Locus 2"),
        notes,
    )

    assert order == ["Locus 1", "Locus 2"]
    assert source == series_order.RECORDED


def _store_matrix(trench, *, units, relations):
    """Persist a matrix for a trench, as the Harris editor would."""
    from backend import harris_store

    created = harris_store.create_matrix({"trench": trench})
    payload = created.model_dump(mode="json")
    payload["units"] = list(units)
    payload["relations"] = list(relations)
    return harris_store.save_matrix(
        created.matrix_id, payload, expected_revision=created.revision
    )


def test_a_trenchs_harris_matrix_is_preferred_to_the_wall_sequence(
    tmp_path,
    storage_dirs,
):
    """The walls list Locus 1 then Locus 2; the matrix records the reverse.
    The excavation's own record wins."""
    from backend.services.trench_builder import resolve_series_order

    _store_matrix(
        "T123", units=[unit(A, "2"), unit(B, "1")], relations=[relation(1, A, B)]
    )

    notes = []
    order, source, _arbitrary = resolve_series_order(
        "T123",
        {},
        _merged("Locus 1", "Locus 2"),
        _points_csv(tmp_path, "Locus 1", "Locus 2"),
        notes,
    )

    assert order == ["Locus 2", "Locus 1"]
    assert source == series_order.HARRIS
    assert any("Harris matrix" in note for note in notes)


def test_a_matrix_recorded_under_another_trench_is_not_used(
    tmp_path,
    storage_dirs,
):
    from backend.services.trench_builder import resolve_series_order

    _store_matrix(
        "T900", units=[unit(A, "2"), unit(B, "1")], relations=[relation(1, A, B)]
    )

    notes = []
    _order, source, _arbitrary = resolve_series_order(
        "T123",
        {},
        _merged("Locus 1", "Locus 2"),
        _points_csv(tmp_path, "Locus 1", "Locus 2"),
        notes,
    )

    assert source == series_order.RECORDED


def test_two_matrices_for_one_trench_refuse_rather_than_pick(
    tmp_path,
    storage_dirs,
):
    from backend.services.trench_builder import (
        TrenchBuildError,
        resolve_series_order,
    )

    for _ in range(2):
        _store_matrix(
            "T123", units=[unit(A, "2"), unit(B, "1")], relations=[relation(1, A, B)]
        )

    with pytest.raises(TrenchBuildError) as caught:
        resolve_series_order(
            "T123",
            {},
            _merged("Locus 1", "Locus 2"),
            _points_csv(tmp_path, "Locus 1", "Locus 2"),
            [],
        )

    assert "more than one Harris matrix" in str(caught.value)


def test_no_evidence_at_all_falls_back_to_elevation_with_a_warning(tmp_path):
    from backend.services.trench_builder import resolve_series_order

    notes = []
    order, source, _arbitrary = resolve_series_order(
        "T123", {}, {"trenchProfiles": []}, _points_csv(tmp_path, "Locus 1"), notes
    )

    assert order is None  # run_build infers it, and labels it
    assert source == series_order.ELEVATION
    assert any(note.startswith("WARNING:") for note in notes)
    assert any("assumption" in note for note in notes)


# The manifest says where the order came from


def _manifest(tmp_path, **kwargs):
    import json

    from pipeline.build_gempy import write_viewer_manifest

    path = tmp_path / "viewer.json"
    write_viewer_manifest(
        path,
        extent=[0, 1, 0, 1, 0, 1],
        resolution=[2, 2, 2],
        series_order=["Locus 1", "Locus 2"],
        single_face_note=None,
        mesh_paths=[tmp_path / "a.obj", tmp_path / "b.obj"],
        lith_block_path=tmp_path / "lith.npz",
        **kwargs,
    )
    return json.loads(path.read_text())


def test_the_manifest_records_a_harris_order_as_such(tmp_path):
    provenance = _manifest(
        tmp_path,
        order_source=series_order.HARRIS,
        arbitrary_pairs=[("Locus 1", "Locus 2")],
    )["series_order_provenance"]

    assert provenance["source"] == series_order.HARRIS
    assert "Harris matrix" in provenance["note"]
    assert provenance["arbitrary_pairs"] == [["Locus 1", "Locus 2"]]


def test_an_unlabelled_manifest_defaults_to_the_elevation_warning(tmp_path):
    """A build that never said where its order came from used elevation."""
    provenance = _manifest(tmp_path)["series_order_provenance"]

    assert provenance["source"] == series_order.ELEVATION
    assert "assumption" in provenance["note"]
    assert provenance["arbitrary_pairs"] == []
