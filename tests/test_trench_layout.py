"""Deriving a grid config from a trench's surveyed corners.

The corner coordinates already exist -- staked by total station, written on the
corner nails, logged in the Geospatial Spreadsheet. This turns them into the
registration an operator otherwise types by hand, which is the roadmap's top
item.

T104 is the worked example throughout: 190E/53S to 194E/56S, a 4 m by 3 m
trench, corners taken clockwise from the north-west.
"""

import math

import pytest

from pipeline import site_grid
from pipeline.trench_layout import (
    LayoutError,
    bearing_degrees,
    build_grid_config,
    read_layout,
)

T104_CORNERS = [
    {"label": "190E/53S", "elevation": 29.10},  # NW
    {"label": "194E/53S", "elevation": 29.02},  # NE
    {"label": "194E/56S", "elevation": 28.55},  # SE -- the low corner
    {"label": "190E/56S", "elevation": 28.94},  # SW
]
T104_WALLS = ["north wall", "east wall", "south wall", "west wall"]


def t104(**overrides):
    layout = {
        "site_grid": site_grid.POGGIO_CIVITATE,
        "corners": [dict(corner) for corner in T104_CORNERS],
        "walls": list(T104_WALLS),
    }
    layout.update(overrides)
    return layout


# ---------------------------------------------------------------------------
# Bearings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ((0, 0), (0, 1), 0.0),  # due Grid North
        ((0, 0), (1, 0), 90.0),  # due Grid East
        ((0, 0), (0, -1), 180.0),  # South
        ((0, 0), (-1, 0), 270.0),  # West
    ],
)
def test_bearings_match_the_total_station_convention(start, end, expected):
    """HA 0 Grid North, 90 East, 180 South, 270 West -- and the same
    convention convert_coords already computes in."""
    assert bearing_degrees(start, end) == pytest.approx(expected)


def test_a_wall_with_no_length_has_no_bearing():
    with pytest.raises(LayoutError, match="no direction"):
        bearing_degrees((190, -53), (190, -53))


# ---------------------------------------------------------------------------
# Reading a layout
# ---------------------------------------------------------------------------


def test_corner_labels_are_read_through_the_site_grid_rule():
    read = read_layout(t104())

    assert read["corners"][0]["gridX"] == 190.0
    assert read["corners"][0]["gridY"] == -53.0
    assert read["corners"][2]["gridY"] == -56.0


def test_numeric_corners_are_accepted_without_a_label():
    read = read_layout(
        t104(
            corners=[
                {"gridX": 190.0, "gridY": -53.0, "elevation": 29.1},
                {"gridX": 194.0, "gridY": -53.0, "elevation": 29.0},
                {"gridX": 194.0, "gridY": -56.0, "elevation": 28.6},
                {"gridX": 190.0, "gridY": -56.0, "elevation": 28.9},
            ]
        )
    )
    assert [c["gridY"] for c in read["corners"]] == [-53.0, -53.0, -56.0, -56.0]


def test_the_ring_closes_back_to_the_first_corner():
    """Corners are the distinct vertices; the last wall closes the trench."""
    read = read_layout(t104())

    assert read["side_lengths_m"] == [4.0, 3.0, 4.0, 3.0]


def test_transposed_corners_are_refused_rather_than_registered():
    """Swapping two corners makes a bow-tie: still a valid polygon, but its
    derived bearings would send two walls diagonally across the pit."""
    corners = [dict(c) for c in T104_CORNERS]
    corners[2], corners[3] = corners[3], corners[2]

    with pytest.raises(LayoutError, match="self-crossing"):
        read_layout(t104(corners=corners))


def test_an_implausibly_long_wall_is_flagged():
    corners = [dict(c) for c in T104_CORNERS]
    corners[1]["label"] = "990E/53S"
    read = read_layout(t104(corners=corners))

    assert any("longer than any trench" in note for note in read["notes"])


def test_too_few_corners_refuses():
    with pytest.raises(LayoutError, match="at least three corners"):
        read_layout(t104(corners=T104_CORNERS[:2], walls=["north wall"]))


def test_duplicate_corners_refuse():
    corners = [dict(c) for c in T104_CORNERS]
    corners[1]["label"] = "190E/53S"
    with pytest.raises(LayoutError, match="same coordinates"):
        read_layout(t104(corners=corners))


def test_an_unreadable_corner_label_names_the_corner():
    corners = [dict(c) for c in T104_CORNERS]
    corners[2]["label"] = "somewhere"
    with pytest.raises(LayoutError, match="corner 3"):
        read_layout(t104(corners=corners))


def test_the_wall_count_must_match_the_edges():
    with pytest.raises(LayoutError, match="4 wall name"):
        read_layout(t104(walls=["north wall", "east wall"]))


def test_walls_may_not_share_a_name():
    with pytest.raises(LayoutError, match="share a name"):
        read_layout(t104(walls=["north wall"] * 4))


def test_missing_corner_elevations_are_reported():
    """The procedures ask for an opening elevation at every corner."""
    corners = [dict(c) for c in T104_CORNERS]
    corners[2].pop("elevation")
    read = read_layout(t104(corners=corners))

    assert any("no opening elevation" in note for note in read["notes"])
    assert read["corners"][2]["elevation"] is None


def test_below_datum_corner_elevations_are_resolved():
    corners = [{**c, "elevation": 0.5} for c in T104_CORNERS]
    read = read_layout(
        t104(
            corners=corners,
            vertical={
                "frame": "mAE",
                "entryForm": "below-datum",
                "datumNail": {"absoluteZ": 29.6},
            },
        )
    )

    assert read["corners"][0]["elevation"] == pytest.approx(29.1)


def test_below_datum_without_a_datum_refuses():
    corners = [{**c, "elevation": 0.5} for c in T104_CORNERS]
    with pytest.raises(LayoutError, match="no datum nail elevation"):
        read_layout(
            t104(corners=corners, vertical={"frame": "mAE", "entryForm": "below-datum"})
        )


# ---------------------------------------------------------------------------
# The derived grid config
# ---------------------------------------------------------------------------


def test_each_wall_is_registered_from_its_start_corner():
    config, _notes = build_grid_config(t104())
    north = config["faces"]["north wall"]

    assert north["originX"] == 190.0
    assert north["originY"] == -53.0
    assert north["bearing_deg"] == pytest.approx(90.0)  # runs east
    assert north["surfaceZ"] == pytest.approx(29.10)


def test_every_wall_gets_the_bearing_of_its_own_edge():
    config, _notes = build_grid_config(t104())
    bearings = {name: config["faces"][name]["bearing_deg"] for name in T104_WALLS}

    assert bearings["north wall"] == pytest.approx(90.0)  # east
    assert bearings["east wall"] == pytest.approx(180.0)  # south
    assert bearings["south wall"] == pytest.approx(270.0)  # west
    assert bearings["west wall"] == pytest.approx(0.0)  # north


def test_the_derived_config_declares_itself_surveyed():
    """These are corner-nail coordinates, not the starter pattern, so the
    placeholder refusal must let them through."""
    from pipeline import merge_walls

    config, _notes = build_grid_config(t104())

    assert config["source"] == "surveyed"
    for name in T104_WALLS:
        assert not merge_walls.is_placeholder(config["faces"][name], config)


def test_the_derived_config_carries_the_site_grid():
    config, _notes = build_grid_config(t104())
    assert config["site_grid"] == site_grid.POGGIO_CIVITATE


def test_a_layout_with_no_site_grid_is_noted_not_refused():
    config, notes = build_grid_config(t104(site_grid=None))

    assert config["site_grid"] is None
    assert any("names no site grid" in note for note in notes)


def test_wall_lengths_are_reported_for_checking_against_the_drawings():
    _config, notes = build_grid_config(t104())
    lengths = [note for note in notes if "north wall" in note]

    assert len(lengths) == 1
    assert "4.00 m" in lengths[0]


def test_the_derived_registration_reproduces_the_corners():
    """The real check: converting each wall's far end through the same maths
    convert_coords uses must land on the next corner nail."""
    config, _notes = build_grid_config(t104())
    corners = read_layout(t104())["corners"]

    for index, name in enumerate(T104_WALLS):
        face = config["faces"][name]
        start = corners[index]
        end = corners[(index + 1) % len(corners)]
        length = math.dist(
            (start["gridX"], start["gridY"]), (end["gridX"], end["gridY"])
        )
        theta = math.radians(face["bearing_deg"])
        x = face["originX"] + length * math.sin(theta)
        y = face["originY"] + length * math.cos(theta)

        assert x == pytest.approx(end["gridX"], abs=1e-6), name
        assert y == pytest.approx(end["gridY"], abs=1e-6), name


def test_a_missing_corner_elevation_leaves_surfaceZ_unset():
    """Null rather than a plausible number: the build refuses it, which is the
    point. An invented elevation would model the trench at the wrong depth."""
    corners = [dict(c) for c in T104_CORNERS]
    corners[0].pop("elevation")
    config, _notes = build_grid_config(t104(corners=corners))

    assert config["faces"]["north wall"]["surfaceZ"] is None
