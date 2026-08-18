"""The site's vertical frame: mAE, datum nails, and recorded uncertainty."""

import pytest

from pipeline import extract_fieldwall, manual_extraction
from pipeline.site_elevation import (
    MAE,
    MASL,
    ElevationError,
    absolute_from_below_datum,
    datum_absolute_z,
    describe,
    midpoint_and_uncertainty_cm,
    normalize_frame,
    resolve,
)

BELOW_DATUM = {
    "frame": MAE,
    "entryForm": "below-datum",
    "datumNail": {"absoluteZ": 29.34},
}
ABSOLUTE = {"frame": MAE, "entryForm": "absolute"}


# Frames


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("mAE", MAE),
        ("mae", MAE),
        (" MAE ", MAE),
        ("mASL", MASL),
    ],
)
def test_frames_are_recognised_case_insensitively(raw, expected):
    assert normalize_frame(raw) == expected


def test_an_absent_frame_is_empty_not_an_error():
    assert normalize_frame(None) == ""
    assert normalize_frame("  ") == ""


def test_an_unknown_frame_raises_and_explains_mae():
    with pytest.raises(ElevationError) as caught:
        normalize_frame("feet")
    assert "meters absolute elevation" in str(caught.value)


# Below datum -> absolute


def test_a_below_datum_reading_is_subtracted_from_the_nail():
    assert absolute_from_below_datum(0.61, 29.34) == pytest.approx(28.73)


def test_a_point_above_the_datum_is_allowed():
    """The nail clears the trench corners, not everything around them."""
    assert absolute_from_below_datum(-0.5, 29.34) == pytest.approx(29.84)


def test_an_absolute_elevation_entered_as_below_datum_is_caught():
    """28.73 typed into a below-datum field would silently place the point
    almost 29 m under the trench floor."""
    with pytest.raises(ElevationError) as caught:
        absolute_from_below_datum(28.73, 29.34)
    assert "implausible" in str(caught.value)


@pytest.mark.parametrize("bad", [None, "0.61", True, float("nan"), float("inf")])
def test_non_numeric_readings_raise(bad):
    with pytest.raises(ElevationError):
        absolute_from_below_datum(bad, 29.34)


# Resolving against a trench's vertical block


def test_absolute_readings_pass_through():
    assert resolve(28.73, ABSOLUTE) == pytest.approx(28.73)


def test_below_datum_readings_are_converted():
    assert resolve(0.61, BELOW_DATUM) == pytest.approx(28.73)


def test_a_missing_vertical_block_is_read_as_absolute():
    """Every job predating this feature stored plain elevations."""
    assert resolve(28.73, None) == pytest.approx(28.73)
    assert resolve(28.73, {}) == pytest.approx(28.73)


def test_below_datum_without_a_datum_height_is_refused_not_defaulted():
    """A missing datum treated as zero produces a model that is internally
    consistent, plausible-looking, and tens of metres from the trench. It is
    the one failure mode nothing downstream can detect."""
    with pytest.raises(ElevationError) as caught:
        resolve(0.61, {"frame": MAE, "entryForm": "below-datum"})
    message = str(caught.value)
    assert "no datum nail elevation" in message
    assert "zero" in message


def test_an_unknown_entry_form_raises():
    with pytest.raises(ElevationError):
        resolve(1.0, {"entryForm": "guessed"})


def test_datum_absolute_z_reads_the_nail_or_returns_none():
    assert datum_absolute_z(BELOW_DATUM) == pytest.approx(29.34)
    assert datum_absolute_z({"entryForm": "below-datum"}) is None
    assert datum_absolute_z(None) is None


# Uncertainty


def test_the_documented_ranged_reading_arithmetic():
    """The Kobo guide's worked example: an elevation range of 27.00-27.50 mAE
    is entered as 27.25 with +/- 25 cm."""
    midpoint, uncertainty = midpoint_and_uncertainty_cm(27.00, 27.50)
    assert midpoint == pytest.approx(27.25)
    assert uncertainty == pytest.approx(25.0)


def test_a_reversed_range_is_read_the_same_way():
    assert midpoint_and_uncertainty_cm(27.50, 27.00) == midpoint_and_uncertainty_cm(
        27.00, 27.50
    )


def test_a_precise_reading_has_no_uncertainty():
    assert midpoint_and_uncertainty_cm(27.25, 27.25) == (27.25, 0.0)


# Describing a trench's vertical state


def test_describe_names_the_frame_for_absolute_records():
    assert "absolute" in describe(ABSOLUTE)
    assert MAE in describe(ABSOLUTE)


def test_describe_says_below_datum_records_are_unfinished():
    """By the site's own rule, below-datum is transitional: it "must be
    corrected/rectified with absolute elevation for your final paperwork"."""
    assert "correct them" in describe(BELOW_DATUM)


def test_describe_flags_an_unresolvable_datum():
    text = describe({"frame": MAE, "entryForm": "below-datum"})
    assert "not yet known" in text


# Uncertainty survives tracing and validation


def _traced(uncertainty=None, **extra):
    """One traced field-wall locus, optionally carrying an uncertainty."""
    top = {"kind": "top", "name": "1", "points": [[0, 0], [100, 0]]}
    top.update(extra)
    if uncertainty is not None:
        top["uncertaintyCm"] = uncertainty
    payload = {
        "calibration": {
            "origin_px": [0, 0],
            "ref_px": [100, 0],
            "lowest_px": [0, 100],
            "ref_meters": 1.0,
        },
        "boundaries": [top, {"kind": "base", "points": [[0, 90], [100, 90]]}],
    }
    calibration = manual_extraction.make_calibration(payload)
    data, _ = manual_extraction.build_fieldwall(payload, calibration, None)
    return data["layers"][0]["topBoundary"]


def test_a_traced_boundary_carries_its_uncertainty():
    for point in _traced(uncertainty=25):
        assert point["uncertaintyCm"] == 25.0


def test_a_boundary_without_an_uncertainty_omits_the_key():
    """An invented precision is worse than an absent one."""
    for point in _traced():
        assert "uncertaintyCm" not in point


@pytest.mark.parametrize("bad", ["25", -1, True, float("nan")])
def test_an_unusable_uncertainty_is_dropped_rather_than_stored(bad):
    for point in _traced(uncertainty=bad):
        assert "uncertaintyCm" not in point


def test_the_extraction_schema_keeps_uncertainty_through_validation():
    """Pydantic drops unknown fields silently by default, so without the
    schema field a traced uncertainty would vanish at finalize with no error."""
    point = extract_fieldwall.BoundaryPoint.model_validate(
        {"xMeters": 0.0, "depthMeters": 0.1, "uncertaintyCm": 25.0}
    )
    assert point.uncertaintyCm == 25.0
