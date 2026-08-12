"""The demonstration's own routes, and the registration route it depends on.

The registration route is here rather than with the other trench routes
because it exists for the same reason the demo does. Derived registration was
written to the trench directory and read by nothing, so the interface asked
for values the application had already worked out -- and a gridless build
answers with the *starter placeholder*, which it then refuses. A seeded trench
with a perfectly good surveyed registration on disk was, from the page,
indistinguishable from one with none.
"""

import json

import pytest

import storage
from demo import seed

pytestmark = pytest.mark.usefixtures("storage_dirs")


@pytest.fixture
def seeded(client):
    client.post("/api/demo/seed", json={"scenario": "stops"})
    client.post("/api/demo/seed", json={"scenario": "complete"})
    return client


# ---------------------------------------------------------------------------
# Describing what is on offer
# ---------------------------------------------------------------------------


# 1. Both scenarios are offered, and the shipped record set makes them runnable.
def test_both_scenarios_are_offered(client):
    payload = client.get("/api/demo").get_json()
    names = {s["name"]: s for s in payload["scenarios"]}
    assert set(names) == {"stops", "complete"}
    assert all(s["available"] for s in names.values())
    assert all(s["seeded"] is None for s in names.values())


# 2. Every record set is listed with its provenance, so the interface never has
#    to decide for itself whether something is real.
def test_datasets_are_listed_with_their_provenance(client):
    payload = client.get("/api/demo").get_json()
    labels = {d["label"]: d for d in payload["datasets"]}
    assert "T905" in labels
    assert labels["T905"]["real_records"] is False
    assert "Synthetic" in labels["T905"]["provenance"]


# 3. Seeded state is read from disk, not from a flag, so deleting a job
#    directory by hand is reflected rather than remembered wrongly.
def test_seeded_state_follows_the_jobs_on_disk(seeded):
    payload = seeded.get("/api/demo").get_json()
    names = {s["name"]: s for s in payload["scenarios"]}
    assert names["stops"]["seeded"]["trench"] == "T905"
    assert len(names["stops"]["seeded"]["jobs"]) == 4

    for directory in list(storage.JOBS_DIR.iterdir()):
        if directory.name.startswith("demo-t905-"):
            for path in sorted(directory.rglob("*"), reverse=True):
                path.unlink() if path.is_file() else path.rmdir()
            directory.rmdir()

    after = {s["name"]: s for s in seeded.get("/api/demo").get_json()["scenarios"]}
    assert after["stops"]["seeded"] is None
    assert after["complete"]["seeded"]["trench"] == "T906"


# ---------------------------------------------------------------------------
# Seeding and removing
# ---------------------------------------------------------------------------


# 4. Seeding answers in the request rather than handing back a task. The
#    seeder is fast; the build is the slow part and has its own machinery.
def test_seeding_returns_the_summary_directly(client):
    response = client.post("/api/demo/seed", json={"scenario": "stops"})
    assert response.status_code == 200
    summary = response.get_json()
    assert summary["trench"] == "T905"
    assert len(summary["jobs"]) == 4
    assert summary["unregistered_corners"] == ["155E/20S"]


# 5. A scenario nobody has is refused with the ones that exist named.
def test_an_unknown_scenario_is_refused_helpfully(client):
    response = client.post("/api/demo/seed", json={"scenario": "everything"})
    assert response.status_code == 400
    assert "stops" in response.get_json()["error"]


# 6. A request with no scenario at all is a 400, not a stack trace.
def test_seeding_without_a_scenario_is_refused(client):
    assert client.post("/api/demo/seed", json={}).status_code == 400
    assert client.post("/api/demo/seed", json={"scenario": "  "}).status_code == 400


# 7. Removal is scoped to the demonstration's own trenches and leaves the
#    operator's work alone.
def test_removing_clears_the_demonstration_only(seeded):
    (storage.JOBS_DIR / "mine").mkdir()
    (storage.JOBS_DIR / "mine" / "meta.json").write_text(
        json.dumps({"job_id": "mine", "trench_label": "T104"})
    )

    response = seeded.delete("/api/demo")
    assert response.status_code == 200
    assert response.get_json()["removed"]

    remaining = {d.name for d in storage.JOBS_DIR.iterdir() if d.is_dir()}
    assert remaining == {"mine"}
    after = seeded.get("/api/demo").get_json()
    assert all(s["seeded"] is None for s in after["scenarios"])


# 8. Removing when nothing is seeded is a no-op rather than an error.
def test_removing_nothing_is_not_an_error(client):
    response = client.delete("/api/demo")
    assert response.status_code == 200
    assert response.get_json()["removed"] == []


# ---------------------------------------------------------------------------
# The registration route
# ---------------------------------------------------------------------------


# 9. The stored registration comes back, and says it is surveyed rather than
#    leaving the page to guess.
def test_a_seeded_trench_serves_its_registration(seeded):
    payload = seeded.get("/api/trenches/T906/registration").get_json()
    assert payload["source"] == "surveyed"
    assert payload["grid"]["faces"]["east wall"]["surfaceZ"] == pytest.approx(24.13)
    assert any("stands in" in note for note in payload["notes"])


# 10. Including the one with a hole in it. The registration is served; what
#     the build does with a null surfaceZ is the build's business.
def test_an_unregistered_corner_still_serves_its_registration(seeded):
    payload = seeded.get("/api/trenches/T905/registration").get_json()
    assert payload["grid"]["faces"]["east wall"]["surfaceZ"] is None
    assert payload["grid"]["faces"]["north wall"]["surfaceZ"] == pytest.approx(24.28)


# 11. A trench with no derived registration is the ordinary case for one built
#     from hand-entered values, so it 404s rather than inventing a config.
def test_a_trench_without_a_registration_is_a_404(client):
    assert client.get("/api/trenches/T104/registration").status_code == 404


# 12. An unreadable registration is refused rather than half-served.
def test_a_corrupt_registration_is_refused(seeded):
    path = storage.TRENCHES_DIR / "T906" / "grid_config.json"
    path.write_text("{not json")
    assert seeded.get("/api/trenches/T906/registration").status_code == 400

    path.write_text(json.dumps({"notes": []}))
    assert seeded.get("/api/trenches/T906/registration").status_code == 400


# ---------------------------------------------------------------------------
# Provenance reaching the interface
# ---------------------------------------------------------------------------


# 13. The trenches page can tell a demonstration from the operator's own work.
def test_the_trenches_api_carries_the_demo_marker(seeded):
    payload = seeded.get("/api/trenches").get_json()
    for label, expected in (("T905", "stops"), ("T906", "complete")):
        markers = [member["demo"] for member in payload["trenches"][label]]
        assert all(marker["scenario"] == expected for marker in markers)
        assert all("Synthetic" in marker["provenance"] for marker in markers)


# 14. And so can the index page's job list, which renders the badge from it.
def test_the_index_page_badges_seeded_drawings(seeded):
    body = seeded.get("/").get_data(as_text=True)
    assert "demo-flag" in body
    assert "Synthetic demonstration data" in body
    assert 'data-real="no"' in body


# 14b. And names them. The list shows the last six characters of a job id,
#      which is right for a uuid and useless for 'demo-t905-north-wall' --
#      it rendered as 'Drawing h-wall'.
def test_seeded_drawings_are_named_rather_than_truncated(seeded):
    body = seeded.get("/").get_data(as_text=True)
    for wall in ("north", "east", "south", "west"):
        assert f"T905 {wall} wall" in body
    assert "Drawing h-wall" not in body


# 15. A job of the operator's carries no marker, so the badge cannot leak onto
#     real work.
def test_an_ordinary_job_carries_no_marker(client, jobs_dir):
    (jobs_dir / "ordinary").mkdir()
    (jobs_dir / "ordinary" / "meta.json").write_text(
        json.dumps(
            {"job_id": "ordinary", "trench_label": "T104", "wall_label": "north wall"}
        )
    )
    payload = client.get("/api/trenches").get_json()
    assert payload["trenches"]["T104"][0]["demo"] is None
    assert "demo-flag" not in client.get("/").get_data(as_text=True)


# 16. The label rule is shared between seeding and removal rather than being
#     re-derived. If they drift, a removal silently leaves a trench behind.
def test_seed_and_remove_agree_on_the_trench_labels():
    assert seed.trench_label_for(seed.SCENARIOS["stops"]) == "T905"
    assert seed.trench_label_for(seed.SCENARIOS["complete"]) == "T906"
