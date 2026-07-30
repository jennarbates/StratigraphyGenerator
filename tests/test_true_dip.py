"""True dip solved from two walls (Chunk 9).

The fixture plane is Z = 100 - 0.1X - 0.05Y: it dips toward ENE, so neither of
the A6 walls sees its full dip. That is the whole point of the chunk, and
test_apparent_dips_understate_the_true_dip is where it is pinned down.
"""

import copy
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline import convert_coords
from pipeline.merge_walls import merge_extractions
from pipeline.true_dip import true_orientations

from fixtures_merge import EAST_WALL, GRID_T900, NORTH_WALL


SURFACE = "Locus 1"
NORTH_XS = (0.0, 0.9, 2.1, 3.2, 4.0)
EAST_YS = (3.0, 2.2, 1.4, 0.5, 0.0)


def plane(x_gradient, y_gradient):
    """Z of the test plane at a site position, dipping by the given gradients."""
    return lambda x, y: 100.0 - (x_gradient * x) - (y_gradient * y)


def rows_on_walls(height, surface=SURFACE):
    """The plane sampled along the A6 walls: north at Y=3, east at X=4."""
    rows = [
        {"X": x, "Y": 3.0, "Z": height(x, 3.0),
         "surface": surface, "face": "north wall"}
        for x in NORTH_XS
    ]
    rows += [
        {"X": 4.0, "Y": y, "Z": height(4.0, y),
         "surface": surface, "face": "east wall"}
        for y in EAST_YS
    ]
    return rows


def test_two_walls_solve_the_plane_they_were_cut_from():
    rows = rows_on_walls(plane(0.1, 0.05))

    orientations, notes = true_orientations(rows, GRID_T900)

    assert len(orientations) == 1
    solved = orientations[0]
    assert solved["surface"] == SURFACE
    assert solved["dip"] == pytest.approx(
        math.degrees(math.atan(math.hypot(0.1, 0.05))), abs=1e-6)
    assert solved["azimuth"] == pytest.approx(
        math.degrees(math.atan2(0.1, 0.05)), abs=1e-6)
    assert set(solved["faces"]) == {"north wall", "east wall"}
    assert notes == []


def test_apparent_dips_understate_the_true_dip():
    """Why this module exists: each wall sees a shallower dip than the truth,
    so a merged model built from the per-wall seeds fits neither drawing."""
    rows = rows_on_walls(plane(0.1, 0.05))
    north_apparent = math.degrees(math.atan(0.1))
    east_apparent = math.degrees(math.atan(0.05))

    solved, _notes = true_orientations(rows, GRID_T900)

    assert north_apparent < solved[0]["dip"]
    assert east_apparent < solved[0]["dip"]


def test_a_horizontal_surface_reports_no_dip_direction():
    rows = rows_on_walls(plane(0.0, 0.0))

    solved, _notes = true_orientations(rows, GRID_T900)

    assert solved[0]["dip"] == pytest.approx(0.0, abs=1e-9)
    assert solved[0]["azimuth"] == 0.0


def test_a_nearly_flat_surface_keeps_its_solved_direction():
    """Near-horizontal layers are the normal case here, not the exception.
    Rounding their azimuth to zero would not neutralise the orientation, it
    would aim the same nudge north."""
    rows = rows_on_walls(plane(0.004, 0.002))

    solved, _notes = true_orientations(rows, GRID_T900)

    assert solved[0]["dip"] < 0.5
    assert solved[0]["azimuth"] == pytest.approx(
        math.degrees(math.atan2(0.004, 0.002)), abs=1e-6)


def test_each_seed_sits_on_a_real_traced_point_of_its_own_wall():
    rows = rows_on_walls(plane(0.1, 0.05))
    traced = {
        (row["face"], row["X"], row["Y"], round(row["Z"], 9))
        for row in rows
    }

    solved, _notes = true_orientations(rows, GRID_T900)
    seeds = solved[0]["seeds"]

    assert [seed["face"] for seed in seeds] == solved[0]["faces"]
    for seed in seeds:
        assert (
            seed["face"], seed["X"], seed["Y"], round(seed["Z"], 9),
        ) in traced


def test_a_surface_on_one_wall_is_left_to_its_apparent_dip():
    rows = [
        row for row in rows_on_walls(plane(0.1, 0.05))
        if row["face"] == "north wall"
    ]

    solved, notes = true_orientations(rows, GRID_T900)

    assert solved == []
    assert any(
        SURFACE in note and "north wall" in note for note in notes
    )


def test_parallel_walls_are_refused_rather_than_solved_badly():
    """Two walls facing the same line do not constrain the plane. Nothing is
    emitted: an invented orientation would look like an improvement."""
    grid = {
        "faces": {
            "north wall": {"bearing_deg": 90.0},
            "south wall": {"bearing_deg": 270.0},
        }
    }
    height = plane(0.1, 0.05)
    rows = [
        {"X": x, "Y": 3.0, "Z": height(x, 3.0),
         "surface": SURFACE, "face": "north wall"}
        for x in NORTH_XS
    ] + [
        {"X": x, "Y": 0.0, "Z": height(x, 0.0),
         "surface": SURFACE, "face": "south wall"}
        for x in NORTH_XS
    ]

    solved, notes = true_orientations(rows, grid)

    assert solved == []
    assert any("parallel" in note for note in notes)


def test_the_least_parallel_pair_of_three_walls_wins():
    grid = {
        "faces": {
            "north wall": {"bearing_deg": 90.0},
            "east wall": {"bearing_deg": 180.0},
            "skew wall": {"bearing_deg": 175.0},
        }
    }
    height = plane(0.1, 0.05)
    rows = rows_on_walls(height) + [
        {"X": 1.0 + (0.1 * step), "Y": 3.0 - (1.14 * step),
         "Z": height(1.0 + (0.1 * step), 3.0 - (1.14 * step)),
         "surface": SURFACE, "face": "skew wall"}
        for step in range(5)
    ]

    solved, _notes = true_orientations(rows, grid)

    assert set(solved[0]["faces"]) == {"north wall", "east wall"}


def test_repeated_calls_agree():
    rows = rows_on_walls(plane(0.1, 0.05))

    first = true_orientations(rows, GRID_T900)
    second = true_orientations(rows, GRID_T900)

    assert first == second


def test_inputs_are_not_mutated():
    rows = rows_on_walls(plane(0.1, 0.05))
    original_rows = copy.deepcopy(rows)
    original_grid = copy.deepcopy(GRID_T900)

    true_orientations(rows, GRID_T900)

    assert rows == original_rows
    assert GRID_T900 == original_grid


def test_the_merged_fixture_trench_solves_every_surface(tmp_path):
    """End to end on real plumbing: merge the A6 walls, convert them, and feed
    the CSV rows back in as strings the way a caller would."""
    merged, _notes = merge_extractions(
        [("north wall", NORTH_WALL), ("east wall", EAST_WALL)])
    conversion = convert_coords.run_convert(
        merged, GRID_T900, str(tmp_path / "points.csv"))

    import csv

    with open(conversion["points_csv"], newline="") as handle:
        rows = list(csv.DictReader(handle))

    solved, notes = true_orientations(rows, GRID_T900)

    surfaces = {orientation["surface"] for orientation in solved}
    assert len(solved) == 2
    assert len(surfaces) == 2
    for orientation in solved:
        assert set(orientation["faces"]) == {"north wall", "east wall"}
        assert len(orientation["seeds"]) == 2
        # The fixture's layers are near-horizontal but not flat.
        assert 0.0 <= orientation["dip"] < 5.0
        assert 0.0 <= orientation["azimuth"] < 360.0
    assert notes == []
