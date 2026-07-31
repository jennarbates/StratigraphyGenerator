"""The two seeded demonstrations, and the promises they are only useful under.

The pair exists to show one thing: the same four wall drawings and the same
record produce a model or no model depending on a single surveyed number. Both
halves are asserted here, because a demonstration that quietly starts building
the trench it is supposed to refuse is worse than no demonstration -- it is a
claim that the refusals work, made by something that no longer refuses.

The other promises are about what the seeder is allowed to touch. It writes
only into the three runtime storage roots, and it never draws invented wall
sections for a real trench. Both are enforced here rather than trusted.
"""

import csv
import json

import pytest

import storage
from demo import datasets, seed, walls
from demo.run import run

pytestmark = pytest.mark.usefixtures("storage_dirs")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


# 1. The tracked record set is always there, so a fresh clone can demo.
def test_the_shipped_dataset_is_discoverable():
    found = datasets.discover()
    assert "T905" in found
    assert found["T905"].real_records is False
    assert found["T905"].season == "2025"


# 2. Anything found under local/ is marked real, whether or not this machine
#    has any. Real trenches here are T1xx and synthetic ones T9xx.
def test_local_record_sets_are_marked_real():
    for label, dataset in datasets.discover().items():
        expected = dataset.root == datasets.LOCAL_ROOT
        assert dataset.real_records is expected, label
        assert ("Real excavation records" in dataset.provenance) is expected


# 3. A layout with no loci or finds beside it is not half-offered.
def test_an_incomplete_record_set_is_not_offered(tmp_path, monkeypatch):
    (tmp_path / "t950-2025-layout.json").write_text("{}")
    monkeypatch.setattr(datasets, "TRACKED_ROOT", tmp_path)
    monkeypatch.setattr(datasets, "LOCAL_ROOT", tmp_path / "absent")
    assert datasets.discover() == {}


# 4. A missing local/ is the ordinary case -- a fresh clone and CI both have
#    none -- and must not be an error.
def test_a_missing_local_root_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(datasets, "LOCAL_ROOT", tmp_path / "nothing here")
    assert "T905" in datasets.discover()


# ---------------------------------------------------------------------------
# The demonstration that stops
# ---------------------------------------------------------------------------


@pytest.fixture
def stops():
    return seed.seed("stops")


@pytest.fixture
def complete():
    return seed.seed("complete")


# 5. It seeds a whole trench: four walls, a matrix, and the finds.
def test_stops_seeds_four_walls_a_matrix_and_the_finds(stops):
    assert stops["trench"] == "T905"
    assert len(stops["jobs"]) == 4
    assert stops["walls"] == [
        "north wall", "east wall", "south wall", "west wall"]
    assert stops["matrix_id"]
    assert stops["finds"] == 26


# 6. Exactly one corner is unregistered, and the seeder says which.
def test_stops_reports_the_unregistered_corner(stops):
    assert stops["unregistered_corners"] == ["155E/20S"]
    assert any("no opening elevation recorded" in note
               for note in stops["notes"])


# 7. The headline promise: the build refuses, and names the wall that corner
#    registers rather than failing somewhere vaguer.
def test_stops_refuses_the_build_by_name(stops):
    outcome = run(stops["trench"])
    assert outcome["outcome"] == "refused"
    assert "east wall" in outcome["message"]
    assert "surfaceZ" in outcome["message"]


# 8. It refuses for the right reason. Reaching the registration check means
#    everything upstream -- four normalized extractions, the merge, the site
#    grid and vertical frame checks -- already passed.
def test_stops_gets_all_the_way_to_the_registration_check(stops):
    outcome = run(stops["trench"])
    assert "no jobs are labelled" not in outcome["message"]
    assert "no normalized extraction" not in outcome["message"]


# ---------------------------------------------------------------------------
# The demonstration that goes all the way
# ---------------------------------------------------------------------------


# 9. It is the same trench with one number added, under its own label so both
#    demonstrations can sit in the application at once.
def test_complete_is_the_same_trench_with_the_corner_supplied(complete):
    assert complete["trench"] == "T906"
    assert complete["unregistered_corners"] == []
    assert any("demonstration value, not a measurement" in note
               for note in complete["notes"])


# 10. The stand-in comes from the opening locus, not from whatever reading
#     happens to be nearest. The nearest reading to this corner is Locus 3's
#     floor, 0.3 m below the ground surface; using it would have put every
#     depth on that wall a third of a metre out.
def test_the_stand_in_elevation_comes_from_the_opening_locus(complete):
    (note,) = [n for n in complete["notes"] if "stands in" in n]
    assert "on locus 1" in note
    layout = json.loads(
        (storage.TRENCHES_DIR / "T906" / "grid_config.json").read_text())
    north = layout["grid"]["faces"]["east wall"]["surfaceZ"]
    assert north == pytest.approx(24.13)


# 11. The headline promise, asserted from one build rather than three.
#
#     A gempy solve takes upwards of thirty seconds, and every fact below is a
#     fact about the same run: that it finished, what it converted, and what
#     ordered it. Splitting them into a test each tripled the cost of the whole
#     suite to re-derive one result.
#
#     'built' and 'ready' are both accepted. Without gempy installed the last
#     stage cannot run, and that is an environment gap rather than a data one;
#     'refused' and 'failed' are not.
def test_complete_runs_the_whole_pipeline(complete):
    outcome = run(complete["trench"])
    assert outcome["outcome"] in {"built", "ready"}

    # What the model is built from: three surfaces, points on every wall,
    # and orientations beside them.
    trench_directory = storage.TRENCHES_DIR / "T906"
    with open(trench_directory / "points.csv", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["surface"] for row in rows} == {
        "Locus 1", "Locus 2", "Locus 3"}
    assert len(rows) == 132
    assert (trench_directory / "points_orientations.csv").is_file()
    assert (trench_directory / "merged.json").is_file()

    # The stratigraphy is used, not decoration: the order comes from the
    # matrix rather than from the elevation fallback.
    assert any("using the Harris matrix" in note for note in outcome["notes"])

    # And where gempy is installed, the demonstration ends in an actual model:
    # one mesh per deposit. Conditional rather than its own test for the same
    # reason as above -- a second test would mean a second thirty-second solve
    # to assert something this one already has on disk.
    if outcome["outcome"] == "built":
        meshes = sorted(
            (trench_directory / "06_gempy_model" / "trench_model_meshes")
            .glob("*.obj"))
        assert [path.stem for path in meshes] == [
            "Locus_1", "Locus_2", "Locus_3"]


# 14. What a younger-to-older graph cannot hold is reported, not dropped in
#     silence. The fixture records three 'is bound to' assertions.
def test_abutments_are_counted_rather_than_quietly_lost(stops):
    assert stops["dropped_abutments"] == 3


# ---------------------------------------------------------------------------
# What the seeder may touch
# ---------------------------------------------------------------------------


# 15. Reseeding replaces rather than accumulates. A demo that grows a duplicate
#     set of walls on every run builds a trench with eight of them.
def test_reseeding_replaces_the_previous_run(stops):
    again = seed.seed("stops")
    assert again["jobs"] == stops["jobs"]
    assert len(again["removed"]) >= 4
    seeded = [d for d in storage.JOBS_DIR.iterdir() if d.is_dir()]
    assert len(seeded) == 4


# 16. Nothing is written outside the three runtime roots -- in particular
#     nothing lands in the repository, and nothing is copied out of local/.
def test_nothing_is_written_outside_the_storage_roots(tmp_path):
    before = {
        path: path.stat().st_mtime
        for path in datasets.REPO_ROOT.rglob("*-2025-*.json")
        if path.is_file()
    }
    seed.seed("stops")
    seed.seed("complete")
    after = {
        path: path.stat().st_mtime
        for path in datasets.REPO_ROOT.rglob("*-2025-*.json")
        if path.is_file()
    }
    assert before == after


# 17. The one thing the seeder will not do. Invented sections under a real
#     trench's label is what the rest of this codebase consistently refuses,
#     and a demonstration is not a good enough reason to be the exception.
def test_a_real_record_set_never_gets_invented_walls(monkeypatch):
    real = datasets.DemoDataset(
        label="T111",
        season="2025",
        root=datasets.LOCAL_ROOT,
        layout_path=datasets.TRACKED_ROOT / "t905-2025-layout.json",
        loci_path=datasets.TRACKED_ROOT / "t905-2025-loci.json",
        finds_path=datasets.TRACKED_ROOT / "t905-2025-special-finds.json",
        real_records=True,
    )
    monkeypatch.setattr(datasets, "discover", lambda: {"T111": real})
    with pytest.raises(seed.DemoError) as excinfo:
        seed.seed("stops", dataset_label="T111")
    assert "real record set" in str(excinfo.value)
    assert list(storage.JOBS_DIR.iterdir()) == []


# 18. An unknown scenario names the ones that exist rather than raising a
#     KeyError at the caller.
def test_an_unknown_scenario_lists_the_real_ones():
    with pytest.raises(seed.DemoError) as excinfo:
        seed.seed("everything")
    assert "stops" in str(excinfo.value)
    assert "complete" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The generated sections
# ---------------------------------------------------------------------------


# 19. Boundaries are shared objects, not two roundings of one surface: the
#     bottom of Locus 1 and the top of Locus 2 are the same measurement.
def test_adjacent_layers_share_one_boundary():
    document = datasets.get("T905").loci()
    profile = walls.wall_profile(
        document, trench_label="T905", wall_label="north wall",
        surface_z=24.28, length_m=5.0, phase_index=0)
    layers = profile["layers"]
    assert layers[0]["bottomBoundary"] == layers[1]["topBoundary"]
    assert layers[1]["bottomBoundary"] == layers[2]["topBoundary"]


# 20. Depth runs downward from the ground surface and layers stack in order.
def test_generated_layers_deepen_in_stratigraphic_order():
    document = datasets.get("T905").loci()
    profile = walls.wall_profile(
        document, trench_label="T905", wall_label="north wall",
        surface_z=24.28, length_m=5.0, phase_index=0)
    means = [
        sum(p["depthMeters"] for p in layer["bottomBoundary"])
        / len(layer["bottomBoundary"])
        for layer in profile["layers"]
    ]
    assert means == sorted(means)
    assert all(depth > 0 for depth in means)


# 21. The sections say on themselves that they were generated. Anything that
#     leaves this application carrying invented geometry has to admit to it.
def test_generated_sections_declare_themselves():
    document = datasets.get("T905").loci()
    profile = walls.wall_profile(
        document, trench_label="T905", wall_label="north wall",
        surface_z=24.28, length_m=5.0, phase_index=0)
    assert any("not drawn in the field" in line
               for line in profile["marginalia"])
    assert all(
        point["confidence"] == "synthetic"
        for layer in profile["layers"]
        for point in layer["topBoundary"]
    )


# 22. Every seeded job carries its provenance, so nothing in the interface has
#     to guess whether it is looking at demonstration data.
def test_every_seeded_job_carries_its_provenance(stops):
    for job_id in stops["jobs"]:
        meta = json.loads(
            (storage.JOBS_DIR / job_id / "meta.json").read_text())
        assert meta["demo"]["scenario"] == "stops"
        assert meta["demo"]["generated_sections"] is True
        assert "Synthetic" in meta["demo"]["provenance"]
