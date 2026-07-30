import math


from backend.routes.markers import _build_marker_calib


def _representative_calibration():
    body = {
        "origin_px": [100, 200],
        "ref_px": [500, 195],
        "ref_meters": 4.0,
        "bottom_px_y": 650,
    }
    return _build_marker_calib(body, px_per_m=100.5)


def test_build_marker_calib_shape():
    calibration = _representative_calibration()

    assert set(calibration) == {
        "kind",
        "origin_px",
        "ref_px",
        "lowest_px",
        "ref_meters",
        "px_per_m",
    }
    assert calibration["kind"] == "manual"
    assert calibration["lowest_px"] == [100, 650.0]


def test_build_marker_calib_passes_frontend_validation():
    calibration = _representative_calibration()
    pixel_pairs = [
        calibration["origin_px"],
        calibration["ref_px"],
        calibration["lowest_px"],
    ]

    assert calibration["kind"] == "manual"
    assert (
        isinstance(calibration["ref_meters"], (int, float))
        and math.isfinite(calibration["ref_meters"])
        and calibration["ref_meters"] > 0
    )
    assert (
        isinstance(calibration["px_per_m"], (int, float))
        and math.isfinite(calibration["px_per_m"])
        and calibration["px_per_m"] > 0
    )
    assert all(
        isinstance(pair, list)
        and len(pair) == 2
        and all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for value in pair
        )
        for pair in pixel_pairs
    )
    assert calibration["origin_px"] != calibration["ref_px"]
