"""Trench identity: one trench must be one group, and locus numbers must only
be merged when they demonstrably mean the same thing.

Both rules come from the project's recording standards rather than from this
application's own conventions -- see naming.canonical_trench and
trench_builder.check_locus_epochs for the citations.
"""

import json

import pytest

import storage
from backend import create_app
from backend.services.trench_builder import (
    TrenchBuildError,
    build,
    check_locus_epochs,
    grouped_members,
    label_variants,
)


def _write_job(job_id, **meta):
    directory = storage.JOBS_DIR / job_id
    directory.mkdir(parents=True, exist_ok=True)
    normalized = directory / "normalized.json"
    normalized.write_text(json.dumps({"loci": [], "layers": []}))
    payload = {
        "job_id": job_id,
        "sheet_type": "fieldwall",
        "normalized_path": str(normalized),
    }
    payload.update(meta)
    (directory / "meta.json").write_text(json.dumps(payload))
    return directory


def _member(job_id, season=None, locus_epoch=None):
    return {
        "job_id": job_id,
        "wall_label": job_id,
        "sheet_type": "fieldwall",
        "season": season,
        "locus_epoch": locus_epoch,
        "has_normalized": True,
        "_normalized_path": None,
    }


# W1.1 -- one trench, one group


def test_differently_spelled_labels_group_as_one_trench(jobs_dir):
    """Regression: grouping on the raw string built two trenches from one,
    each holding a subset of the walls and each producing a confident model of
    half a pit. The T104 field drawings are titled "T-104" while the Open
    Context records read "T104", so both spellings are already in circulation
    on the same material."""
    _write_job("job_north", trench_label="T-104", wall_label="north wall")
    _write_job("job_east", trench_label="T104", wall_label="east wall")
    _write_job("job_south", trench_label="t 104", wall_label="south wall")

    grouped = grouped_members()

    assert list(grouped) == ["T104"]
    assert len(grouped["T104"]) == 3


def test_a_build_request_finds_the_group_under_any_spelling(jobs_dir):
    """The label arrives off the URL, so it needs the same treatment as the
    stored one -- otherwise a canonicalized group is unreachable."""
    _write_job("job_north", trench_label="T104", wall_label="north wall")

    # Reaches the group and fails later, on grid config, not on lookup.
    result = build("T-104", {})

    assert result["needs_grid"] is True


def test_unrecognised_labels_are_left_alone_and_still_group(jobs_dir):
    """A label that is not identifier-shaped must not be mangled into one."""
    _write_job("job_a", trench_label="Piano del Tesoro", wall_label="a")
    _write_job("job_b", trench_label="Piano del Tesoro", wall_label="b")

    assert list(grouped_members()) == ["Piano del Tesoro"]


def test_jobs_without_a_trench_label_are_still_skipped(jobs_dir):
    _write_job("job_orphan", wall_label="north wall")
    _write_job("job_blank", trench_label="   ", wall_label="east wall")

    assert grouped_members() == {}


def test_a_merge_across_spellings_is_reported_not_hidden(jobs_dir):
    """Stored metadata keeps what the operator typed, so a merge could
    otherwise happen entirely out of sight."""
    _write_job("job_north", trench_label="T-104", wall_label="north wall")
    _write_job("job_east", trench_label="T104", wall_label="east wall")

    assert label_variants(grouped_members()["T104"]) == ["T-104", "T104"]


def test_a_trench_recorded_consistently_reports_no_variants(jobs_dir):
    _write_job("job_north", trench_label="T104", wall_label="north wall")
    _write_job("job_east", trench_label="T104", wall_label="east wall")

    assert label_variants(grouped_members()["T104"]) == []


def test_the_listing_route_exposes_variants_only_when_they_exist(jobs_dir):
    client = create_app().test_client()

    _write_job("job_north", trench_label="T104", wall_label="north wall")
    assert "label_variants" not in client.get("/api/trenches").get_json()

    _write_job("job_east", trench_label="T-104", wall_label="east wall")
    body = client.get("/api/trenches").get_json()
    assert body["label_variants"] == {"T104": ["T-104", "T104"]}


# W1.2 -- locus numbering epochs


def test_one_season_needs_no_epoch():
    notes = []
    check_locus_epochs(
        [_member("a", season="2025"), _member("b", season="2025")], notes
    )
    assert notes == []


def test_no_season_recorded_at_all_is_permitted():
    """Most jobs are single sheets that never carried a season."""
    notes = []
    check_locus_epochs([_member("a"), _member("b")], notes)
    assert notes == []


def test_consecutive_seasons_merge_and_say_so():
    """Procedures: a trench reopened in consecutive years continues its locus
    sequence, so these numbers are one sequence."""
    notes = []
    check_locus_epochs(
        [
            _member("a", season="2023"),
            _member("b", season="2024"),
            _member("c", season="2025"),
        ],
        notes,
    )
    assert any("consecutive seasons 2023-2025" in note for note in notes)


def test_a_gap_between_seasons_is_refused():
    """Procedures: a trench reopened after a gap "may" restart its numbering.
    Either guess -- fusing two deposits or splitting one -- produces a
    plausible-looking model, so neither is made."""
    with pytest.raises(TrenchBuildError) as caught:
        check_locus_epochs(
            [_member("a", season="2019"), _member("b", season="2025")], []
        )
    message = str(caught.value)
    assert "non-consecutive" in message
    assert "2019" in message and "2025" in message
    assert "locus_epoch" in message


def test_a_declared_epoch_overrides_the_season_gap():
    """The operator knows whether numbering continued; the application does
    not. A declaration settles it."""
    notes = []
    check_locus_epochs(
        [
            _member("a", season="2019", locus_epoch="T104:1"),
            _member("b", season="2025", locus_epoch="T104:1"),
        ],
        notes,
    )
    assert notes == []


def test_conflicting_epochs_are_refused():
    with pytest.raises(TrenchBuildError) as caught:
        check_locus_epochs(
            [_member("a", locus_epoch="T104:1"), _member("b", locus_epoch="T104:2")], []
        )
    assert "different locus numbering epochs" in str(caught.value)


def test_a_partially_declared_epoch_is_adopted_with_a_note():
    notes = []
    check_locus_epochs(
        [
            _member("a", season="2019", locus_epoch="T104:1"),
            _member("b", season="2025"),
        ],
        notes,
    )
    assert any("declare no locus epoch" in note for note in notes)


def test_unparseable_seasons_across_sheets_are_refused():
    with pytest.raises(TrenchBuildError) as caught:
        check_locus_epochs(
            [_member("a", season="2025"), _member("b", season="summer 25")], []
        )
    assert "4-digit year" in str(caught.value)


def test_the_epoch_check_runs_before_a_build(jobs_dir):
    _write_job("job_old", trench_label="T104", wall_label="north", season="2019")
    _write_job("job_new", trench_label="T104", wall_label="east", season="2025")

    with pytest.raises(TrenchBuildError) as caught:
        build("T104", {})

    assert "non-consecutive" in str(caught.value)
