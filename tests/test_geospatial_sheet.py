"""Reading the season\'s Geospatial Spreadsheet.

Tested against ``tests/fixtures/geospatial-sample.csv``, which reproduces the
shape of a real season sheet without any of its content. Every trench number,
coordinate and name in it is invented; the real sheet holds personnel names and
site coordinates and is deliberately not in this repository.

What the sample does keep is every quirk the parser has to survive, because
those are the specification: continuation rows where only the first carries the
trench id, a stray word in the trench column, free text bleeding into the
Adjusted Elevations columns, a trench extended mid-season onto eight unlabelled
vertices, decimal coordinates, and trenches on both sides of the origin line.
"""

import pytest

from pipeline import site_grid, trench_layout
from pipeline.geospatial_sheet import (
    CLOSING,
    OPENING,
    SheetError,
    elevation_readiness,
    layout_for,
    parse_corner,
    read_sheet,
    wall_names,
)

WALLS = ["north wall", "east wall", "south wall", "west wall"]


@pytest.fixture
def sheet(repo_root):
    text = (repo_root / "tests" / "fixtures" / "geospatial-sample.csv").read_text()
    return read_sheet(text)


# Corner cells


@pytest.mark.parametrize(
    "text,expected",
    [
        ("NW: 100/-20", ("NW", 100.0, -20.0)),
        ("SE: 115/-25 ", ("SE", 115.0, -25.0)),  # trailing space in the sheet
        ("130.25/40.75", (None, 130.25, 40.75)),  # an extended trench\'s vertex
        ("NW: 120/8", ("NW", 120.0, 8.0)),  # north of the origin line
    ],
)
def test_corner_cells_parse(text, expected):
    assert parse_corner(text) == expected


def test_coordinates_are_taken_as_written():
    """They are already Grid X and Grid Y with South and West negative.
    Applying the inversion here would apply it twice and mirror the site."""
    _label, x, y = parse_corner("NW: 100/-20")

    assert (x, y) == site_grid.label_to_grid("100E/20S")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Closed",
        "contact removed Updated Loci 1 and 2",
        "No locus forms uploaded yet",
        None,
    ],
)
def test_cells_that_are_not_corners_are_not_read_as_corners(text):
    assert parse_corner(text) is None


# The sheet as a whole


def test_every_trench_in_the_season_is_read(sheet):
    assert len(sheet["trenches"]) == 6
    assert "T900" in sheet["trenches"]


def test_a_trenchs_rows_are_gathered_across_continuation_lines(sheet):
    """Only the first row carries the trench id; the rest hold its remaining
    corners and its second supervisor."""
    trench = sheet["trenches"]["T900"]

    assert len(trench[OPENING]) == 4
    assert trench["supervisors"] == ["Supervisor One", "Supervisor Two"]
    assert trench["trenchbook"] == "ABC/DEF I"
    assert trench["state"] == "Closed"


def test_corners_are_read_in_order_around_the_trench(sheet):
    corners = sheet["trenches"]["T900"][OPENING]

    assert [(c["corner"], c["gridX"], c["gridY"]) for c in corners] == [
        ("NW", 100.0, -20.0),
        ("NE", 104.0, -20.0),
        ("SE", 104.0, -23.0),
        ("SW", 100.0, -23.0),
    ]


def test_a_stray_word_in_the_trench_column_is_noted_not_obeyed(sheet):
    """A real sheet had the word 'list' sitting in a trench column."""
    assert any("is not a trench identifier" in note for note in sheet["notes"])
    assert "list" not in sheet["trenches"]


def test_an_extended_trench_keeps_all_its_closing_vertices(sheet):
    """T116 was extended mid-season and closes on eight corners."""
    trench = sheet["trenches"]["T904"]

    assert len(trench[OPENING]) == 4
    assert len(trench[CLOSING]) == 8


def test_free_text_in_the_flag_columns_is_kept_as_a_note(sheet):
    trench = sheet["trenches"]["T902"]
    assert any("Updated Loci 1 and 2" in note for note in trench["notes"])


def test_trenches_north_of_the_origin_keep_their_positive_northing(sheet):
    """Most of the site is negative-Y, so a sign error would fold half of it
    onto the other half rather than merely shifting it."""
    assert sheet["trenches"]["T902"][OPENING][0]["gridY"] == 8.0
    assert sheet["trenches"]["T900"][OPENING][0]["gridY"] == -20.0


def test_a_sheet_that_is_not_this_one_is_refused():
    with pytest.raises(SheetError, match="Geospatial Spreadsheet"):
        read_sheet("a,b\n1,2\n")


def test_an_empty_sheet_is_refused():
    with pytest.raises(SheetError, match="empty"):
        read_sheet("")


# Wall names from corner labels


def test_walls_are_named_by_the_cardinal_their_corners_share():
    corners = [{"corner": name} for name in ("NW", "NE", "SE", "SW")]
    assert wall_names(corners) == WALLS


def test_unlabelled_vertices_produce_no_name():
    corners = [{"corner": "NW"}, {"corner": None}, {"corner": "SE"}]
    assert wall_names(corners) == ["", "", ""]


# Straight into a grid config


def test_a_trench_registers_itself_from_the_spreadsheet(sheet):
    """The whole point: no bearing worked out by hand, no origin typed."""
    layout = layout_for(sheet["trenches"]["T900"], site_grid=site_grid.POGGIO_CIVITATE)
    config, _notes = trench_layout.build_grid_config(layout)

    assert config["source"] == "surveyed"
    assert config["faces"]["north wall"]["originX"] == 100.0
    assert config["faces"]["north wall"]["originY"] == -20.0
    assert config["faces"]["north wall"]["bearing_deg"] == 90.0
    assert config["faces"]["east wall"]["bearing_deg"] == 180.0


def test_every_rectangular_trench_in_the_season_registers(sheet):
    """A real regression net: 16 trenches through the whole chain at once."""
    registered = []
    for label, record in sheet["trenches"].items():
        try:
            layout = layout_for(record, site_grid=site_grid.POGGIO_CIVITATE)
        except SheetError:
            continue  # extended trenches need their walls named
        config, _notes = trench_layout.build_grid_config(layout)
        assert set(config["faces"]) == set(WALLS), label
        registered.append(label)

    assert len(registered) == 6


def test_an_extended_trench_refuses_until_its_walls_are_named(sheet):
    """Guessing "wall 5" would put a name in the grid config matching nothing
    on any drawing."""
    with pytest.raises(SheetError, match="name its walls explicitly"):
        layout_for(sheet["trenches"]["T904"], phase=CLOSING)


def test_an_extended_trench_registers_once_its_walls_are_named(sheet):
    names = [f"wall {index}" for index in range(1, 9)]
    layout = layout_for(
        sheet["trenches"]["T904"],
        phase=CLOSING,
        walls=names,
        site_grid=site_grid.POGGIO_CIVITATE,
    )
    config, _notes = trench_layout.build_grid_config(layout)

    assert len(config["faces"]) == 8


def test_the_closing_outline_can_be_registered_instead(sheet):
    """An extended trench's two phases differ, and which one a model registers
    to is the operator's decision, not this module's."""
    opening = layout_for(sheet["trenches"]["T904"], phase=OPENING)
    closing = layout_for(
        sheet["trenches"]["T904"],
        phase=CLOSING,
        walls=[f"wall {index}" for index in range(1, 9)],
    )

    assert opening["corners"] != closing["corners"]
    assert len(closing["corners"]) == 8


def test_a_phase_with_no_coordinates_refuses(sheet):
    record = dict(sheet["trenches"]["T900"], closing=[])
    record[CLOSING] = []
    with pytest.raises(SheetError, match="no closing coordinates"):
        layout_for(record, phase=CLOSING)


def test_an_unknown_phase_refuses(sheet):
    with pytest.raises(SheetError, match="phase must be"):
        layout_for(sheet["trenches"]["T900"], phase="midway")


# What the sheet says about elevations


def test_the_sheet_carries_no_elevations_at_all(sheet):
    """There is no Z column. Corner elevations live in the locus forms."""
    for record in sheet["trenches"].values():
        for phase in (OPENING, CLOSING):
            for corner in record[phase]:
                assert "elevation" not in corner


def test_a_derived_config_has_no_surfaceZ_and_says_so(sheet):
    layout = layout_for(sheet["trenches"]["T900"], site_grid=site_grid.POGGIO_CIVITATE)
    config, notes = trench_layout.build_grid_config(layout)

    assert config["faces"]["north wall"]["surfaceZ"] is None
    assert any("no opening elevation" in note for note in notes)


def test_t104s_outstanding_elevation_corrections_are_reported(sheet):
    """The Adjusted Elevations columns are compliance flags, not values, and
    T104\'s locus forms are still FALSE."""
    readiness = elevation_readiness(sheet["trenches"]["T900"])

    assert readiness
    assert "Locus Forms" in readiness[0]


def test_a_trench_with_every_correction_done_reports_nothing(sheet):
    assert elevation_readiness(sheet["trenches"]["T901"]) == []
