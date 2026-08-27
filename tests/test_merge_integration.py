"""End-to-end check that merge -> convert -> build works on real plumbing.

Everything here is test code: Chunks 1 to 3 built the merge layer, and this
file proves the merged document is accepted unchanged by the existing
pipeline. The point is that no production code downstream of the merge needed
to change -- convert() was already multi-face, so a merged document is just an
ordinary multi-face document to it.

The synthetic trench is the contract's T900 (see fixtures_merge): two walls
meeting at the corner (4, 3), north running east on bearing 90, east running
south on bearing 180.
"""

import csv
import json

import pytest
from fixtures_merge import (
    EAST_WALL,
    GRID_T900,
    GRID_T900_WEST,
    LABEL_L1,
    NORTH_WALL,
    SURFACE_L1,
    SURFACE_L2,
    WEST_ILLUSTRATOR,
)

from pipeline import canonical, convert_coords, validator
from pipeline.merge_walls import merge_extractions, merged_series_order

# GRID_T900 is keyed by the full wall names, so merge under those labels.
WALL_LABELS = ("north wall", "east wall")


@pytest.fixture
def merged():
    doc, _notes = merge_extractions(
        [(WALL_LABELS[0], NORTH_WALL), (WALL_LABELS[1], EAST_WALL)]
    )
    return doc


@pytest.fixture
def converted(merged, tmp_path):
    """Run the real converter over the merged document. Returns
    (result, points rows, orientation rows)."""
    out_csv = str(tmp_path / "points.csv")
    result = convert_coords.run_convert(merged, GRID_T900, out_csv)
    points = read_csv(result["points_csv"])
    orientations = read_csv(result["orientations_csv"])
    return result, points, orientations


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def rows_for(rows, face):
    return [r for r in rows if r["face"] == face]


# 1. The merged document converts cleanly, and every wall lands where its
#    registration says it should.
def test_merged_document_converts_to_site_coordinates(converted):
    result, points, _ = converted

    assert result["missing_faces"] == []
    # 2 faces x 3 modelled lines x 5 boundary points. Three lines, not two:
    # each layer's top plus the deepest layer's base (D2).
    assert result["n_points"] == 30
    assert len(points) == 30

    assert {r["face"] for r in points} == set(WALL_LABELS)

    # Bearing 90 from origin (0, 3): all displacement goes into X, so the
    # north wall stays on Y = 3. Bearing 180 from (4, 3): X holds at 4.
    for row in rows_for(points, "north wall"):
        assert float(row["Y"]) == pytest.approx(3.0, abs=1e-6)
    for row in rows_for(points, "east wall"):
        assert float(row["X"]) == pytest.approx(4.0, abs=1e-6)

    # Ground is at 100.0 and the deepest modelled boundary is under half a
    # metre down, so every point sits just below the surface.
    for row in points:
        assert 99.0 < float(row["Z"]) <= 100.0


# 2. The correctness payoff: one deposit is ONE surface string spanning both
#    walls, which is what lets GemPy fuse the two walls into one interface.
def test_each_surface_appears_on_both_faces(converted):
    _result, points, _ = converted

    faces_by_surface = {}
    for row in points:
        faces_by_surface.setdefault(row["surface"], set()).add(row["face"])

    assert set(faces_by_surface) == {SURFACE_L1, SURFACE_L2, canonical.BASE_SURFACE_ID}
    for surface, faces in faces_by_surface.items():
        assert faces == set(WALL_LABELS), f"{surface} is not on both walls"


# 3. Orientations: one per modelled line per face, dipping along its own wall.
def test_orientations_follow_each_wall_bearing(converted):
    result, _points, orientations = converted

    assert result["n_orientations"] == 6
    assert len(orientations) == 6

    for row in rows_for(orientations, "north wall"):
        assert float(row["azimuth"]) in (90.0, 270.0)
    for row in rows_for(orientations, "east wall"):
        assert float(row["azimuth"]) in (180.0, 0.0)


# 4. The Chunk 2 order names exactly the surfaces the CSV carries, which is
#    the precondition run_build enforces before it will accept a series_order.
def test_series_order_matches_the_converted_surfaces(merged, converted):
    _result, points, _ = converted
    order, _notes = merged_series_order(merged)

    assert set(order) == {row["surface"] for row in points}
    assert order == [SURFACE_L1, SURFACE_L2, canonical.BASE_SURFACE_ID]


# 5. Validator smoke test: the merged document is a legal extraction, and its
#    deliberately irregular vertex spacing does not trip the fabrication check.
def test_validator_accepts_the_merged_document(merged, tmp_path):
    path = tmp_path / "merged.json"
    path.write_text(json.dumps(merged))

    report = validator.run_validate(str(path))

    assert report["errors"] == []
    assert report["ok"] is True
    assert not [w for w in report["warnings"] if "evenly spaced" in w]


# Cross-medium: a field wall and an illustrator wall of one trench build as
# one trench, with one consistent surface per drawn interface (the P3b gate).


@pytest.fixture
def cross_medium(tmp_path):
    merged, _notes = merge_extractions(
        [("north wall", NORTH_WALL), ("west", WEST_ILLUSTRATOR)]
    )
    out_csv = str(tmp_path / "points.csv")
    result = convert_coords.run_convert(merged, GRID_T900_WEST, out_csv)
    return merged, result, read_csv(result["points_csv"])


def test_cross_medium_surfaces_span_both_mediums(cross_medium):
    _merged, result, points = cross_medium
    assert result["missing_faces"] == []

    faces_by_surface = {}
    for row in points:
        faces_by_surface.setdefault(row["surface"], set()).add(row["face"])

    assert set(faces_by_surface) == {SURFACE_L1, SURFACE_L2, canonical.BASE_SURFACE_ID}
    for surface, faces in faces_by_surface.items():
        assert faces == {"north wall", "west baulk"}, surface


def test_cross_medium_series_order_matches_the_csv(cross_medium):
    """The recorded-sequence path must name the surfaces the CSV carries, or
    run_build refuses the order. Before the merge read the canonical form,
    the illustrator wall contributed material names here instead."""
    merged, _result, points = cross_medium
    order, _notes = merged_series_order(merged)

    assert set(order) == {row["surface"] for row in points}
    assert order == [SURFACE_L1, SURFACE_L2, canonical.BASE_SURFACE_ID]


def test_cross_medium_labels_keep_each_mediums_observation(cross_medium):
    """Identity fuses the walls; each medium's own reading survives as the
    display label, first sheet's label winning."""
    _merged, result, _points = cross_medium
    labels = result["surface_labels"]
    assert labels[SURFACE_L1] == LABEL_L1


def test_validator_accepts_the_cross_medium_document(cross_medium, tmp_path):
    merged, _result, _points = cross_medium
    path = tmp_path / "cross.json"
    path.write_text(json.dumps(merged))

    report = validator.run_validate(str(path))

    assert report["errors"] == []
    assert report["ok"] is True


# 6. The real build, when gempy is installed. importorskip skips rather than
#    fails where it is not.
def test_full_gempy_build(merged, converted, tmp_path):
    pytest.importorskip("gempy")
    from pipeline import build_gempy

    result, _points, _orientations = converted
    order, _notes = merged_series_order(merged)

    built = build_gempy.run_build(
        result["points_csv"],
        result["orientations_csv"],
        str(tmp_path / "t900"),
        resolution=(20, 20, 15),
        series_order=order,
        make_plot=False,
        make_meshes=True,
        save_model=False,
        make_zoom_plot=False,
    )

    assert built["series_order"] == order
    # Both surfaces have points on both walls, so nothing is interpolated
    # from a single face.
    assert built["single_face_note"] is None
