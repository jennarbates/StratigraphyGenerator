"""The horizontal and vertical frames, where they meet a trench build.

The frame modules themselves are covered by test_site_grid.py and
test_site_elevation.py. This file covers the wiring: what a build refuses, what
it merely reports, and what the starter config now tells an operator.
"""

import json

import pytest

import storage
from backend.services.trench_builder import (
    TrenchBuildError,
    build,
    check_site_grid,
    check_vertical_frame,
)
from pipeline import convert_coords, merge_walls, site_elevation, site_grid

FIELD_SHEET = {
    "loci": [{"locusNumber": "1", "munsell": "10YR 5/3 brown"}],
    "layers": [
        {
            "locusNumber": "1",
            "topBoundary": [
                {"xMeters": 0.0, "depthMeters": 0.1},
                {"xMeters": 2.0, "depthMeters": 0.2},
            ],
        }
    ],
    "gridTiePoints": [{"rawText": "190E/53S"}, {"rawText": "not a label"}],
}


def _write_job(job_id, **meta):
    directory = storage.JOBS_DIR / job_id
    directory.mkdir(parents=True, exist_ok=True)
    normalized = directory / "normalized.json"
    normalized.write_text(json.dumps(FIELD_SHEET))
    payload = {
        "job_id": job_id,
        "sheet_type": "fieldwall",
        "normalized_path": str(normalized),
    }
    payload.update(meta)
    (directory / "meta.json").write_text(json.dumps(payload))


def _member(job_id, grid=None):
    return {"job_id": job_id, "site_grid": grid}


# ---------------------------------------------------------------------------
# The starter config now states the frames
# ---------------------------------------------------------------------------


def test_the_starter_config_declares_both_frames_and_its_own_provenance():
    cfg = convert_coords.make_starter_config(FIELD_SHEET)

    assert cfg["site_grid"] is None  # must be chosen, not defaulted
    assert cfg["source"] == "placeholder"
    assert cfg["vertical"]["frame"] == site_elevation.MAE
    assert cfg["vertical"]["entryForm"] == "absolute"
    assert cfg["vertical"]["datumNail"]["absoluteZ"] is None


def test_the_starter_comment_names_grid_north_and_mae():
    """An operator reading "compass direction" could reasonably supply a
    magnetic bearing and silently rotate a wall."""
    comment = convert_coords.make_starter_config(FIELD_SHEET)["_comment"]
    assert "GRID NORTH" in comment
    assert "NOT magnetic north" in comment
    assert "mAE" in comment
    assert "190E/53S is originX 190, originY -53" in comment


def test_readable_tie_points_are_offered_with_their_coordinates():
    """Offered, not applied: which end of a face a label marks is a
    site-records question this module cannot answer."""
    ties = convert_coords.make_starter_config(FIELD_SHEET)["_tiePointsFromSheet"]

    assert {"rawText": "190E/53S", "gridX": 190.0, "gridY": -53.0} in ties
    assert {"rawText": "not a label", "gridX": None, "gridY": None} in ties


# ---------------------------------------------------------------------------
# Registration provenance
# ---------------------------------------------------------------------------


def test_a_declared_source_beats_the_value_pattern():
    """Real survey values that happen to match the starter pattern used to
    read as placeholders, and an operator had no way to say otherwise."""
    face = {"originX": 10.0, "originY": 0.0, "surfaceZ": 100.0, "bearing_deg": 90.0}

    assert merge_walls.is_placeholder(face) is True
    assert merge_walls.is_placeholder(face, {"source": "surveyed"}) is False
    assert merge_walls.is_placeholder(face, {"source": "placeholder"}) is True


def test_declaring_placeholder_flags_values_the_pattern_would_miss():
    face = {"originX": 190.0, "originY": -53.0, "surfaceZ": 28.9, "bearing_deg": 87.0}

    assert merge_walls.is_placeholder(face) is False
    assert merge_walls.is_placeholder(face, {"source": "placeholder"}) is True


def test_an_unrecognised_source_falls_back_to_the_pattern():
    face = {"originX": 10.0, "originY": 0.0, "surfaceZ": 100.0, "bearing_deg": 90.0}
    assert merge_walls.is_placeholder(face, {"source": "probably fine"}) is True


# ---------------------------------------------------------------------------
# Site grid agreement
# ---------------------------------------------------------------------------


def test_sheets_on_different_grids_are_refused():
    """The two local grids' origins are ~1.5 million metres apart, so this is
    one wall placed in another village, not a rounding error."""
    with pytest.raises(TrenchBuildError) as caught:
        check_site_grid(
            [
                _member("a", site_grid.POGGIO_CIVITATE),
                _member("b", site_grid.VESCOVADO_DI_MURLO),
            ],
            None,
            [],
        )
    assert "different site grids" in str(caught.value)


def test_a_config_contradicting_its_sheets_is_refused():
    with pytest.raises(TrenchBuildError) as caught:
        check_site_grid(
            [_member("a", site_grid.POGGIO_CIVITATE)],
            {"site_grid": site_grid.VESCOVADO_DI_MURLO},
            [],
        )
    assert "One of the two is wrong" in str(caught.value)


def test_agreement_returns_the_grid():
    notes = []
    agreed = check_site_grid(
        [
            _member("a", site_grid.POGGIO_CIVITATE),
            _member("b", site_grid.POGGIO_CIVITATE),
        ],
        {"site_grid": "Poggio Civitate"},
        notes,
    )
    assert agreed == site_grid.POGGIO_CIVITATE
    assert notes == []


def test_no_declared_grid_is_a_note_not_a_refusal():
    """Every job predating the field has none, and every trench modelled so
    far is on one grid."""
    notes = []
    assert check_site_grid([_member("a"), _member("b")], {}, notes) == ""
    assert any("two local grids" in note for note in notes)


def test_a_config_naming_an_unknown_grid_is_refused():
    with pytest.raises(TrenchBuildError):
        check_site_grid([_member("a")], {"site_grid": "tesoro"}, [])


# ---------------------------------------------------------------------------
# Vertical frame
# ---------------------------------------------------------------------------


def test_below_datum_without_a_datum_elevation_is_refused():
    with pytest.raises(TrenchBuildError) as caught:
        check_vertical_frame(
            {"vertical": {"frame": "mAE", "entryForm": "below-datum"}}, []
        )
    message = str(caught.value)
    assert "cannot be resolved" in message
    assert "tens of metres" in message


def test_below_datum_with_a_datum_elevation_builds_but_says_so():
    """The site's own rule: below-datum is transitional and must be corrected
    for the final record."""
    notes = []
    check_vertical_frame(
        {
            "vertical": {
                "frame": "mAE",
                "entryForm": "below-datum",
                "datumNail": {"absoluteZ": 29.34},
            }
        },
        notes,
    )
    assert any("correct them" in note for note in notes)


def test_absolute_elevations_are_reported_plainly():
    notes = []
    check_vertical_frame({"vertical": {"frame": "mAE"}}, notes)
    assert notes == ["elevations are absolute, in mAE"]


def test_a_config_with_no_vertical_block_is_silent():
    notes = []
    check_vertical_frame({}, notes)
    check_vertical_frame(None, notes)
    assert notes == []


def test_an_unknown_vertical_frame_is_refused():
    with pytest.raises(TrenchBuildError):
        check_vertical_frame({"vertical": {"frame": "feet"}}, [])


# ---------------------------------------------------------------------------
# Through a real build
# ---------------------------------------------------------------------------


def test_a_build_refuses_sheets_from_two_grids(jobs_dir):
    _write_job(
        "job_north",
        trench_label="T104",
        wall_label="north",
        site_grid=site_grid.POGGIO_CIVITATE,
    )
    _write_job(
        "job_east",
        trench_label="T104",
        wall_label="east",
        site_grid=site_grid.VESCOVADO_DI_MURLO,
    )

    with pytest.raises(TrenchBuildError) as caught:
        build("T104", {"grid": {"faces": {}}})

    assert "different site grids" in str(caught.value)
