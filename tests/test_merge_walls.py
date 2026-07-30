import copy
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline.merge_walls import (
    check_trench_grid_config,
    face_endpoints,
    make_trench_starter_config,
    merge_extractions,
    merged_series_order,
)

from fixtures_merge import (
    EAST_WALL,
    GRID_T900,
    NORTH_WALL,
    SURFACE_L1,
    SURFACE_L2,
)


def merge_t900(**kwargs):
    return merge_extractions(
        [("north", NORTH_WALL), ("east", EAST_WALL)], **kwargs)


def face_names(merged):
    return [f["face"] for f in merged["trenchProfiles"]]


def surfaces_of(merged, face_name):
    (face,) = [f for f in merged["trenchProfiles"] if f["face"] == face_name]
    return [layer["layerName"] for layer in face["layers"]]


# 1. Two field-wall sheets merge into two named faces with two layers each.
def test_two_walls_merge_to_two_faces():
    merged, _ = merge_t900()
    assert face_names(merged) == ["north", "east"]
    for face in merged["trenchProfiles"]:
        assert len(face["layers"]) == 2


# 2. The same locus gets the exact same surface string on both faces.
def test_same_locus_shares_surface_string_across_faces():
    merged, _ = merge_t900()
    assert surfaces_of(merged, "north") == [SURFACE_L1, SURFACE_L2]
    assert surfaces_of(merged, "east") == [SURFACE_L1, SURFACE_L2]
    # Belt and braces: per locus, one string trench-wide.
    for position in (0, 1):
        names = {surfaces_of(merged, f)[position] for f in ("north", "east")}
        assert len(names) == 1


# 3. Munsell disagreement: first sheet's reading wins, and a note names the
#    locus and both walls.
def test_munsell_disagreement_noted_and_first_reading_wins():
    merged, notes = merge_t900()
    assert SURFACE_L2 in surfaces_of(merged, "east")  # north's reading
    disagreement = [n for n in notes
                    if "disagrees" in n and "north" in n and "east" in n]
    assert len(disagreement) == 1
    assert "2" in disagreement[0]


# 4. Correlation map renames a locus on one wall only.
def test_correlation_renames_locus():
    merged, notes = merge_t900(correlation={"east:2": "7"})
    east = surfaces_of(merged, "east")
    north = surfaces_of(merged, "north")
    assert "Locus 7 (10YR 3/1 very dark gray)" in east
    assert SURFACE_L2 not in east
    assert SURFACE_L2 in north
    assert any("east" in n and "7" in n and "renamed" in n for n in notes)
    # With the rename, locus 2 no longer disagrees between walls.
    assert not any("disagrees" in n for n in notes)


# 5. Caller's dicts are never mutated.
def test_inputs_not_mutated():
    north_before = copy.deepcopy(NORTH_WALL)
    east_before = copy.deepcopy(EAST_WALL)
    merge_t900(correlation={"east:2": "7"})
    assert NORTH_WALL == north_before
    assert EAST_WALL == east_before


# 6. Bad inputs raise.
def test_duplicate_wall_labels_raise():
    with pytest.raises(ValueError):
        merge_extractions([("north", NORTH_WALL), ("North", EAST_WALL)])


def test_empty_sheet_list_raises():
    with pytest.raises(ValueError):
        merge_extractions([])


def test_empty_wall_label_raises():
    with pytest.raises(ValueError):
        merge_extractions([("   ", NORTH_WALL)])


# 7. An illustrator-shaped sheet passes through beside a field sheet.
def test_illustrator_sheet_passes_through():
    plan = {"trenchProfiles": [{"face": "East", "layers": []}]}
    merged, _ = merge_extractions([("north", NORTH_WALL), ("plan", plan)])
    assert face_names(merged) == ["north", "East"]


# Extra: a cross-sheet face-name collision gets the illustrator face
# prefixed with its wall label, and a note says so.
def test_cross_sheet_collision_prefixes_illustrator_face():
    plan = {"trenchProfiles": [{"face": "north", "layers": []}]}
    merged, notes = merge_extractions([("north", NORTH_WALL), ("plan", plan)])
    assert face_names(merged) == ["north", "plan: north"]
    assert any("renamed" in n and "plan: north" in n for n in notes)


# Extra: a locus used in layers[] but missing from loci[] on one wall still
# gets the trench-wide canonical name, so the deposit stays one surface.
def test_layer_locus_missing_from_loci_uses_canonical_name():
    east = copy.deepcopy(EAST_WALL)
    east["loci"] = [entry for entry in east["loci"]
                    if entry["locusNumber"] != "2"]
    merged, notes = merge_extractions([("north", NORTH_WALL), ("east", east)])
    assert surfaces_of(merged, "east") == [SURFACE_L1, SURFACE_L2]
    assert any("not" in n and "loci" in n and "east" in n for n in notes)


# --------------------------------------------------------------------------
# CHUNK 2: merged_series_order
# --------------------------------------------------------------------------

def wall(face_name, *surfaces):
    """A merged-document face whose layers are the given surfaces, in order
    (top to bottom = young to old)."""
    return {"face": face_name,
            "layers": [{"layerName": s, "inferredMaterial": s,
                        "bottomBoundary": []} for s in surfaces]}


def doc(*faces):
    return {"trenchProfiles": list(faces)}


# 1. The A6 fixture: locus 1 above locus 2 on both walls.
def test_series_order_of_merged_fixture():
    merged, _ = merge_t900()
    order, _notes = merged_series_order(merged)
    assert order == [SURFACE_L1, SURFACE_L2]


# 2. Constraints from two walls chain together: (P, Q) + (Q, R) -> P, Q, R.
def test_series_order_chains_across_walls():
    order, _ = merged_series_order(
        doc(wall("A", "P", "Q"), wall("B", "Q", "R")))
    assert order == ["P", "Q", "R"]


# 3. Contradicting walls are a cycle, and it refuses to guess.
def test_contradicting_walls_raise():
    with pytest.raises(ValueError) as excinfo:
        merged_series_order(doc(wall("A", "P", "Q"), wall("B", "Q", "P")))
    message = str(excinfo.value)
    assert "P" in message and "Q" in message


# 4. A surface seen on only one wall is allowed, and noted with its face.
def test_single_wall_surface_is_noted():
    order, notes = merged_series_order(
        doc(wall("A", "P", "Q"), wall("B", "P", "Q", "R")))
    assert order == ["P", "Q", "R"]
    single = [n for n in notes if "'R'" in n]
    assert len(single) == 1
    assert "B" in single[0]
    # Surfaces on both walls are not flagged.
    assert not any("'P'" in n for n in notes)


# 5. Deterministic: same input, same list, every time.
def test_series_order_is_deterministic():
    merged, _ = merge_t900()
    first, _ = merged_series_order(merged)
    second, _ = merged_series_order(merged)
    assert first == second

    # Unconstrained surfaces fall back to first-seen input order, so an
    # independent second wall cannot reshuffle the first.
    independent = doc(wall("A", "P", "Q"), wall("B", "M", "N"))
    assert merged_series_order(independent)[0] == ["P", "Q", "M", "N"]
    assert merged_series_order(independent)[0] == \
        merged_series_order(independent)[0]


# Extra: the order names exactly the surfaces present, so it can be handed to
# run_build's series_order without tripping its "names not found" check.
def test_series_order_covers_every_surface_once():
    merged, _ = merge_t900()
    order, _ = merged_series_order(merged)
    present = {layer["inferredMaterial"]
               for face in merged["trenchProfiles"]
               for layer in face["layers"]}
    assert set(order) == present
    assert len(order) == len(set(order))


# Extra: an empty document is not an error, just an empty order plus a note.
def test_empty_document_yields_empty_order():
    order, notes = merged_series_order({"trenchProfiles": []})
    assert order == []
    assert any("no stratigraphic order" in n or "no named layers" in n
               for n in notes)


# --------------------------------------------------------------------------
# CHUNK 3: trench grid config helpers
# --------------------------------------------------------------------------

# GRID_T900 is keyed by the full wall names, so merge with those labels.
def merge_t900_grid_labels():
    merged, _ = merge_extractions(
        [("north wall", NORTH_WALL), ("east wall", EAST_WALL)])
    return merged


@pytest.fixture
def merged_t900():
    return merge_t900_grid_labels()


def warnings_about(warnings, face_name):
    return [w for w in warnings if repr(face_name) in w]


# 1. The real registration for the A6 trench is clean: walls share the corner
#    (4, 3) exactly, no placeholders, one datum.
def test_good_grid_produces_no_warnings(merged_t900):
    assert check_trench_grid_config(GRID_T900, merged_t900) == []


# 2. Nudging the east wall off the shared corner disconnects exactly it.
def test_disconnected_wall_is_flagged(merged_t900):
    grid = copy.deepcopy(GRID_T900)
    grid["faces"]["east wall"]["originX"] = 4.5
    warnings = check_trench_grid_config(grid, merged_t900)
    assert len(warnings_about(warnings, "east wall")) == 1
    assert "not connected" in warnings_about(warnings, "east wall")[0]
    assert warnings_about(warnings, "north wall") == []


# 3. The untouched starter config flags every face.
def test_starter_config_flags_every_face(merged_t900):
    starter = make_trench_starter_config(merged_t900)
    warnings = check_trench_grid_config(starter, merged_t900)
    placeholders = [w for w in warnings if "starter placeholder" in w]
    assert len(placeholders) == 2
    for name in ("north wall", "east wall"):
        assert warnings_about(placeholders, name)


# 4. Elevations that cannot share a benchmark are flagged.
def test_datum_spread_is_flagged(merged_t900):
    grid = copy.deepcopy(GRID_T900)
    grid["faces"]["east wall"]["surfaceZ"] = 103.5
    warnings = check_trench_grid_config(grid, merged_t900)
    assert any("datum" in w for w in warnings)


# 5. A face absent from the config is unusable, not a warning.
def test_missing_face_raises(merged_t900):
    grid = copy.deepcopy(GRID_T900)
    del grid["faces"]["east wall"]
    with pytest.raises(ValueError) as excinfo:
        check_trench_grid_config(grid, merged_t900)
    assert "east wall" in str(excinfo.value)


# 6. Endpoint math: bearing 90 sends all displacement into X, none into Y.
def test_face_endpoint_math():
    start, end = face_endpoints(GRID_T900["faces"]["north wall"], 4.0)
    assert start == pytest.approx((0.0, 3.0), abs=1e-6)
    assert end == pytest.approx((4.0, 3.0), abs=1e-6)
    # East wall: bearing 180 runs south, so Y decreases and X holds.
    start, end = face_endpoints(GRID_T900["faces"]["east wall"], 3.0)
    assert start == pytest.approx((4.0, 3.0), abs=1e-6)
    assert end == pytest.approx((4.0, 0.0), abs=1e-6)


# Extra: the starter config keeps its shape and gains the merged-trench
# warning in _comment.
def test_starter_config_comment_mentions_merged_trench(merged_t900):
    starter = make_trench_starter_config(merged_t900)
    assert set(starter["faces"]) == {"north wall", "east wall"}
    assert "MERGED" in starter["_comment"]
    assert "corner" in starter["_comment"]
    # Still the same starter values convert_coords produces.
    assert starter["faces"]["north wall"]["bearing_deg"] == 90.0


# Extra: a face with no points cannot be placed, so the adjacency check says
# so instead of guessing a length.
def test_pointless_face_is_skipped_with_a_warning(merged_t900):
    merged = copy.deepcopy(merged_t900)
    merged["trenchProfiles"].append({"face": "plan", "layers": []})
    grid = copy.deepcopy(GRID_T900)
    grid["faces"]["plan"] = {"originX": 0.0, "originY": 3.0,
                             "surfaceZ": 100.0, "bearing_deg": 0.0}
    warnings = check_trench_grid_config(grid, merged)
    skipped = warnings_about(warnings, "plan")
    assert len(skipped) == 1
    assert "no boundary points" in skipped[0]


# Extra: a single-wall trench has no corners to check, so no warning either
# way; the datum check needs two faces too.
def test_single_face_has_no_adjacency_or_datum_warnings():
    merged, _ = merge_extractions([("north wall", NORTH_WALL)])
    grid = {"faces": {"north wall": copy.deepcopy(
        GRID_T900["faces"]["north wall"])}}
    assert check_trench_grid_config(grid, merged) == []