"""Surface identity is the locus number; the soil colour is a label.

GemPy fuses interface points into a surface by exact string match on the
`surface` column, so whatever is inside that string is part of a deposit's
identity. A Munsell reading used to be, and the consequences ran through the
whole merge layer: two walls reading one deposit's colour slightly differently
produced two model surfaces, so ~60 lines existed to force the readings to
agree. These tests pin the separation that removed it.
"""

import json

import pytest
from fixtures_merge import EAST_WALL, GRID_T900, NORTH_WALL

from pipeline import convert_coords, merge_walls
from pipeline.build_gempy import write_viewer_manifest
from pipeline.convert_coords import surface_id


def _merged():
    """Merged under the wall labels GRID_T900 registers, so the same document
    can be converted as well as inspected."""
    return merge_walls.merge_extractions(
        [("north wall", NORTH_WALL), ("east wall", EAST_WALL)])


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_surface_id_is_the_locus_number_alone():
    assert surface_id("6") == "Locus 6"
    assert "10YR" not in surface_id("6")


def test_a_colour_disagreement_no_longer_splits_one_deposit(tmp_path):
    """The fixture's two walls read locus 2 differently on purpose. Under the
    old naming that produced two surfaces from one deposit."""
    merged, _ = _merged()
    rows, _orient, _missing, _notes = convert_coords.convert(
        merged, GRID_T900, str(tmp_path / "points.csv"))

    surfaces = {row["surface"] for row in rows}
    assert surfaces == {"Locus 1", "Locus 2"}

    # Both walls contribute to each surface -- the point of merging at all.
    for surface in surfaces:
        faces = {row["face"] for row in rows if row["surface"] == surface}
        assert faces == {"north wall", "east wall"}, surface


def test_no_surface_name_contains_a_munsell_reading(tmp_path):
    merged, _ = _merged()
    rows, _o, _m, _n = convert_coords.convert(
        merged, GRID_T900, str(tmp_path / "points.csv"))
    for row in rows:
        assert "YR" not in row["surface"]


def test_the_written_csv_carries_identities_not_labels(tmp_path):
    """Belt and braces on the file itself: the CSV is what GemPy reads."""
    merged, _ = _merged()
    out = tmp_path / "points.csv"
    convert_coords.convert(merged, GRID_T900, str(out))
    text = out.read_text()

    assert "Locus 1" in text
    assert "10YR" not in text


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def test_labels_carry_the_colour_beside_the_identity():
    merged, _ = _merged()
    labels = convert_coords.surface_labels(merged)

    assert labels["Locus 1"] == "Locus 1 (10YR 5/3 brown)"
    # The north wall is first in the merge, so its reading labels locus 2.
    assert labels["Locus 2"] == "Locus 2 (10YR 3/2 very dark grayish brown)"


def test_a_disagreement_is_reported_rather_than_resolved_away():
    """The reading is no longer forced to agree, but a supervisor still needs
    to know the two walls describe the deposit differently."""
    _merged_doc, notes = _merged()
    disagreements = [note for note in notes if "Munsell disagrees" in note]

    assert len(disagreements) == 1
    assert "north wall" in disagreements[0]
    assert "east wall" in disagreements[0]
    assert "still model one surface" in disagreements[0]


def test_a_locus_with_no_colour_has_no_label_entry():
    """An identity is not a label; a map of surface -> itself is noise."""
    sheet = {"loci": [], "layers": [{"locusNumber": "3", "topBoundary": []}]}
    adapted, _ = convert_coords.fieldwall_to_profiles(sheet, face_name="w")

    assert convert_coords.surface_labels(adapted) == {}


def test_run_convert_returns_labels_beside_the_csv(tmp_path):
    merged, _ = _merged()
    result = convert_coords.run_convert(
        merged, GRID_T900, str(tmp_path / "points.csv"))

    assert result["surface_labels"]["Locus 1"] == "Locus 1 (10YR 5/3 brown)"


# ---------------------------------------------------------------------------
# The viewer manifest
# ---------------------------------------------------------------------------


def _manifest(tmp_path, **kwargs):
    path = tmp_path / "viewer.json"
    write_viewer_manifest(
        path,
        extent=[0, 1, 0, 1, 0, 1],
        resolution=[2, 2, 2],
        series_order=["Locus 1"],
        single_face_note=None,
        mesh_paths=[tmp_path / "Locus_1.obj"],
        lith_block_path=tmp_path / "lith.npz",
        **kwargs,
    )
    return json.loads(path.read_text())


def test_the_manifest_carries_both_identity_and_label(tmp_path):
    manifest = _manifest(
        tmp_path, surface_labels={"Locus 1": "Locus 1 (10YR 5/3 brown)"})

    assert manifest["schema_version"] == 2
    assert manifest["surfaces"][0]["name"] == "Locus 1"
    assert manifest["surfaces"][0]["label"] == "Locus 1 (10YR 5/3 brown)"


def test_a_surface_with_no_label_falls_back_to_its_identity(tmp_path):
    manifest = _manifest(tmp_path)
    assert manifest["surfaces"][0]["label"] == "Locus 1"


def test_series_order_holds_identities(tmp_path):
    """series_order is matched against the CSV's surface column, so it must be
    identities. run_build rejects an order naming anything absent from it."""
    manifest = _manifest(
        tmp_path, surface_labels={"Locus 1": "Locus 1 (10YR 5/3 brown)"})
    assert manifest["series_order"] == ["Locus 1"]


def test_merged_series_order_is_built_from_identities():
    merged, _ = _merged()
    order, _notes = merge_walls.merged_series_order(merged)
    assert order == ["Locus 1", "Locus 2"]


# ---------------------------------------------------------------------------
# What the merge layer no longer does
# ---------------------------------------------------------------------------


def test_the_merge_no_longer_rewrites_recorded_colours():
    """The canonicalization pass overwrote each sheet's Munsell values with a
    trench-wide reading. A recorder's observation is not the application's to
    edit; nothing but the correlation map may change a sheet now."""
    merged, _ = _merged()
    labels = convert_coords.surface_labels(merged)

    # The east wall's own reading is still its own, even though it is not the
    # one chosen as the surface's label.
    east_reading = EAST_WALL["loci"][1]["munsell"]
    assert east_reading == "10YR 3/1 very dark gray"
    assert east_reading not in labels.values()


def test_canonicalization_helpers_are_gone():
    assert not hasattr(merge_walls, "_canonical_munsell")
    assert not hasattr(merge_walls, "_canonicalize_sheet")


@pytest.mark.parametrize("locus", ["6", "12", "1"])
def test_identity_is_stable_regardless_of_recorded_colour(locus):
    sheets = [
        {"loci": [{"locusNumber": locus, "munsell": colour}],
         "layers": [{"locusNumber": locus, "topBoundary": []}]}
        for colour in ("10YR 5/3 brown", "7.5YR 4/2 dark brown", None)
    ]
    produced = set()
    for sheet in sheets:
        adapted, _ = convert_coords.fieldwall_to_profiles(sheet, face_name="w")
        produced.add(adapted["trenchProfiles"][0]["layers"][0]["layerName"])

    assert produced == {surface_id(locus)}
