"""The site's horizontal frame.

The cardinal-inversion test below is the single most load-bearing assertion in
this repository. A sign error there mirrors the whole site north-to-south while
leaving every distance, slope and model internally consistent, so nothing
downstream can catch it. The expected values are transcribed from the
project's own worked example, not chosen to match the implementation.
"""

import pytest

from pipeline.site_grid import (
    GRIDS,
    POGGIO_CIVITATE,
    VESCOVADO_DI_MURLO,
    GridError,
    format_label,
    grid_north_offset_degrees,
    grid_to_site,
    label_to_grid,
    normalize_grid_name,
    project_model_footprint,
    to_epsg3003,
)

# ---------------------------------------------------------------------------
# The inversion rule
# ---------------------------------------------------------------------------


def test_the_documented_worked_example():
    """Stated identically in Master Grid Origins, Conservation Kobo Form
    Instructions and the 2025 Kobo Deployment guide:
    170.56E/64.26S is Grid X = 170.56, Grid Y = -64.26."""
    assert label_to_grid("170.56E/64.26S") == (170.56, -64.26)


@pytest.mark.parametrize(
    "label,expected",
    [
        ("190E/53S", (190.0, -53.0)),  # T104 north-west corner
        ("194E/53S", (194.0, -53.0)),
        ("190E/56S", (190.0, -56.0)),
        ("194E/56S", (194.0, -56.0)),  # south-east corner
    ],
)
def test_the_t104_sheet_corners(label, expected):
    assert label_to_grid(label) == expected


def test_north_and_east_are_positive_south_and_west_negative():
    assert label_to_grid("10E/10N") == (10.0, 10.0)
    assert label_to_grid("10W/10S") == (-10.0, -10.0)


def test_the_t104_trench_is_four_by_three_metres():
    """A sanity check on the whole rule at once: if a sign were inverted the
    sheet's own corner labels would not describe a 4 x 3 m trench."""
    west, north = label_to_grid("190E/53S")
    east, south = label_to_grid("194E/56S")
    assert east - west == pytest.approx(4.0)
    assert north - south == pytest.approx(3.0)


@pytest.mark.parametrize(
    "label,expected",
    [
        ("190e/53s", (190.0, -53.0)),
        ("  190E / 53S  ", (190.0, -53.0)),
        ("190E,53S", (190.0, -53.0)),
        ("190E53S", (190.0, -53.0)),
    ],
)
def test_transcription_variants_read_the_same(label, expected):
    assert label_to_grid(label) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        None,
        190,
        "190/53",
        "190E",
        "53S",
        "E190/S53",
        "190N/53E",  # axes swapped: easting must come first
        "190E/53S/12",
    ],
)
def test_unreadable_labels_raise_rather_than_guess(bad):
    with pytest.raises(GridError):
        label_to_grid(bad)


def test_format_label_round_trips():
    for label in ("190E/53S", "170.56E/64.26S", "10W/10N"):
        assert format_label(*label_to_grid(label)) == label


# ---------------------------------------------------------------------------
# Model coordinates are grid coordinates
# ---------------------------------------------------------------------------


def test_grid_to_site_is_the_identity():
    """Not a simplification made here: convert_coords already computes in this
    frame. The function exists so the assumption has one name."""
    assert grid_to_site(190.0, -53.0) == (190.0, -53.0)
    assert grid_to_site(0, 0) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Two grids
# ---------------------------------------------------------------------------


def test_both_local_grids_are_named():
    assert set(GRIDS) == {POGGIO_CIVITATE, VESCOVADO_DI_MURLO}


@pytest.mark.parametrize(
    "raw",
    [
        "poggio-civitate",
        "Poggio Civitate",
        "POGGIO_CIVITATE",
        " poggio-civitate ",
    ],
)
def test_grid_names_are_recognised_however_they_are_spelled(raw):
    assert normalize_grid_name(raw) == POGGIO_CIVITATE


def test_an_absent_grid_name_is_empty_not_an_error():
    """Absent is a state the caller decides about; wrong is not."""
    assert normalize_grid_name(None) == ""
    assert normalize_grid_name("   ") == ""


def test_an_unknown_grid_name_raises():
    with pytest.raises(GridError) as caught:
        normalize_grid_name("tesoro")
    assert "poggio-civitate" in str(caught.value)


# ---------------------------------------------------------------------------
# Projection, for export
# ---------------------------------------------------------------------------


def test_projection_uses_the_published_affine():
    x, y = to_epsg3003(0, 0, POGGIO_CIVITATE)
    assert x == pytest.approx(169513.520)
    assert y == pytest.approx(478065.144)


def test_projection_is_grid_specific():
    poggio = to_epsg3003(100, 46, POGGIO_CIVITATE)
    vescovado = to_epsg3003(100, 46, VESCOVADO_DI_MURLO)
    # ~1.5 million metres apart: mixing the grids is never a near miss.
    assert abs(poggio[0] - vescovado[0]) > 1_000_000


def test_projection_preserves_distance_to_within_a_percent():
    """The affine is very slightly anisotropic but is essentially rigid; a
    4 m trench edge must not become a noticeably different length."""
    ax, ay = to_epsg3003(190, -53, POGGIO_CIVITATE)
    bx, by = to_epsg3003(194, -53, POGGIO_CIVITATE)
    assert ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 == pytest.approx(4.0, rel=0.01)


def test_projecting_without_a_grid_refuses():
    with pytest.raises(GridError) as caught:
        to_epsg3003(190, -53, None)
    assert "site grid must be named" in str(caught.value)


def test_grid_north_is_about_two_and_a_half_degrees_off_projected_north():
    """The number behind "Grid North is an artificial reference direction",
    and the reason a magnetic bearing is recognisably wrong."""
    for offset in grid_north_offset_degrees(POGGIO_CIVITATE):
        assert offset == pytest.approx(2.5, abs=0.2)


def test_a_model_footprint_projects_its_four_corners():
    footprint = project_model_footprint(
        [190, 194, -56, -53, 28.0, 29.5], POGGIO_CIVITATE
    )

    assert footprint["crs"] == "EPSG:3003"
    assert footprint["site_grid"] == POGGIO_CIVITATE
    assert len(footprint["corners"]) == 4
    assert footprint["corners"][0] == list(to_epsg3003(190, -56, POGGIO_CIVITATE))


def test_a_footprint_keeps_elevation_untouched():
    """The projection is horizontal; mAE is already absolute metres."""
    footprint = project_model_footprint(
        [190, 194, -56, -53, 28.0, 29.5], POGGIO_CIVITATE
    )

    assert footprint["z_range"] == [28.0, 29.5]
    assert footprint["z_frame"] == "mAE"


def test_a_footprint_needs_a_full_extent():
    with pytest.raises(GridError, match="six values"):
        project_model_footprint([190, 194], POGGIO_CIVITATE)


def test_a_footprint_needs_a_named_grid():
    with pytest.raises(GridError, match="site grid must be named"):
        project_model_footprint([190, 194, -56, -53, 28.0, 29.5], None)
