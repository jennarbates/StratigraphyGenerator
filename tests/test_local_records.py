"""Invariant checks for real excavation records, which live outside the repo.

Real trench records hold coordinates, elevations and personnel names, so they
are not committed: ``.gitignore`` keeps everything under ``local/`` on the
machine it was put on. This module runs against whatever is there and skips
when there is nothing, so a fresh clone and CI both pass with none of it
present.

**This file contains no excavation data, and must not acquire any.** Every
expectation is either derived from the fixture under test or declared inside
that fixture. That is why the assertions here look indirect -- a test that
hardcoded ``28.28`` would put a surveyed elevation into a public repository just
as surely as the fixture would, and would additionally only ever work for one
trench.

The checks are the ones a season's records can be held to without knowing
anything about the season:

* a coordinate or elevation with no recorded source is indistinguishable from
  one somebody invented, so every fixture has to say where its values came from;
* walking each wall its own length along its derived bearing has to arrive at
  the next corner nail;
* a locus cannot close higher than it opened, and an unexcavated one cannot
  close lower;
* where two loci share an edge, or one is opened on the surface another closed
  on, the two records of that surface have to agree;
* a findspot has to lie inside the locus it is filed under, in all three
  dimensions -- except for those the fixture itself declares as known bad.

To use it, drop a trench's records in as::

    local/fixtures/<trench>-<season>-layout.json
    local/fixtures/<trench>-<season>-loci.json           (optional)
    local/fixtures/<trench>-<season>-special-finds.json  (optional)

in the shape of ``tests/fixtures/t905-2025-*.json``, which is the synthetic
worked example and is documented at ``docs/worked-example/``. Layouts are
discovered automatically, so a second or third trench needs no change here.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pipeline import merge_walls, site_elevation
from pipeline.harris_matrix import (
    HarrisMatrix,
    correlation_components,
    validate_matrix_graph,
)
from pipeline.trench_layout import build_grid_config, read_layout

LOCAL_FIXTURES = Path(__file__).resolve().parents[1] / "local" / "fixtures"

# Wide enough to pass the few centimetres a plumb bob, a line level and a tape
# scatter by, and narrow enough that a transposed digit -- which moves a point
# by a decimetre at least -- still fails.
TOLERANCE_M = 0.10

# No datum nail at this site stands metres clear of the ground it measures, so
# a corner further below it than this means the datum or the reading is wrong.
MAX_DEPTH_BELOW_DATUM_M = 5.0

# How far apart two readings of the SAME surface can legitimately be.
#
# This is not a guess. A trench book records one surface twice whenever a locus
# closes and the next opens on it, and those pairs are the measurement's own
# error bars: readings taken a day apart routinely differ by a few centimetres,
# and some of them RISE, which excavation cannot do. Features left standing --
# a stone wall defined and drawn but never dug -- do the same across weeks.
#
# Six centimetres is the largest such rise observed in the records this suite
# was written against. It is the tolerance for "did this surface go down",
# because below it the instrument cannot tell, and it is far tighter than the
# decimetres a swapped opening/closing column would produce.
MEASUREMENT_SCATTER_M = 0.06


def _discover():
    """Every trench with a layout in ``local/fixtures``, newest name last."""
    if not LOCAL_FIXTURES.is_dir():
        return []
    return sorted(
        path.name[: -len("-layout.json")]
        for path in LOCAL_FIXTURES.glob("*-layout.json")
    )


TRENCHES = _discover()

pytestmark = pytest.mark.skipif(
    not TRENCHES,
    reason=(
        "no real records in local/fixtures/ -- this is the expected state for a "
        "fresh clone and for CI. See the module docstring."
    ),
)


def _read(stem, part):
    path = LOCAL_FIXTURES / f"{stem}-{part}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text())


@pytest.fixture(params=TRENCHES, ids=TRENCHES)
def record(request):
    """One trench's layout, and its loci and finds where they exist."""
    stem = request.param
    layout = _read(stem, "layout")
    if layout is None:                              # pragma: no cover - guarded
        pytest.skip(f"{stem} has no layout")
    return {
        "stem": stem,
        "layout": layout,
        "loci": _read(stem, "loci"),
        "finds": _read(stem, "special-finds"),
    }


@pytest.fixture
def loci(record):
    if record["loci"] is None:
        pytest.skip(f"{record['stem']} has no loci fixture")
    return record["loci"]


@pytest.fixture
def by_locus(loci):
    return {entry["locus"]: entry for entry in loci["loci"]}


@pytest.fixture
def finds(record):
    if record["finds"] is None:
        pytest.skip(f"{record['stem']} has no special finds fixture")
    return record["finds"]


# --------------------------------------------------------------------- helpers


def _vertices(locus, phase):
    return locus[f"{phase}_vertices"]


def _point(vertex):
    return (round(vertex["gridX"], 2), round(vertex["gridY"], 2))


def _corner_set(locus):
    """The coordinates a locus was measured at, as an order-free key."""
    return frozenset(_point(v) for v in _vertices(locus, "opening"))


def _by_label(locus, phase):
    return {v["label"]: v["elevation"] for v in _vertices(locus, phase)}


def _bounds(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return (min(xs), max(xs)), (min(ys), max(ys))


def _within(value, bounds):
    return bounds[0] - TOLERANCE_M <= value <= bounds[1] + TOLERANCE_M


def _datum(layout):
    return layout["vertical"]["datumNail"]["absoluteZ"]


def _recorded_elevations(layout):
    return [
        corner["elevation"] for corner in layout["corners"]
        if corner.get("elevation") is not None
    ]


# ----------------------------------------------------------------- provenance


def test_every_value_records_where_it_came_from(record):
    """The rule the whole arrangement rests on. A real coordinate with no
    provenance cannot be told apart from a guess, and a fixture that lets one
    in has stopped being a record."""
    for part in ("layout", "loci", "finds"):
        fixture = record[part]
        if fixture is None:
            continue
        assert fixture["_sources"], part
        for field, source in fixture["_sources"].items():
            assert source["record"], f"{part}.{field}"


def test_every_fixture_states_its_known_problems(record):
    """Silence is not the same as a clean record, and a fixture with nothing to
    declare is usually one nobody has read closely."""
    for part in ("layout", "loci", "finds"):
        fixture = record[part]
        if fixture is None:
            continue
        assert fixture["_known_problems"], part


def test_the_parts_of_a_record_agree_on_which_trench_they_are(record):
    layout = record["layout"]
    for part in ("loci", "finds"):
        fixture = record[part]
        if fixture is None:
            continue
        assert fixture["trench"] == layout["trench"], part
        assert fixture["season"] == layout["season"], part


# ---------------------------------------------------------------- the layout


def test_the_layout_registers(record):
    """Whatever else is wrong, the corners have to describe a trench: distinct,
    in order around the pit, and not self-crossing."""
    config, _notes = build_grid_config(record["layout"])

    assert config["source"] == "surveyed"
    assert len(config["faces"]) == len(record["layout"]["corners"])


def test_walking_each_wall_arrives_at_the_next_corner(record):
    """End to end, and entirely derived: walk each wall its own length along
    its derived bearing and it must land on the next nail. This is the check
    that a bearing convention has not been inverted somewhere."""
    layout = record["layout"]
    config, _notes = build_grid_config(layout)
    corners = read_layout(layout)["corners"]
    walls = read_layout(layout)["walls"]

    for index, wall in enumerate(walls):
        face = config["faces"][wall]
        start = corners[index]
        end = corners[(index + 1) % len(corners)]
        length = math.dist((start["gridX"], start["gridY"]),
                           (end["gridX"], end["gridY"]))
        theta = math.radians(face["bearing_deg"])

        assert face["originX"] + length * math.sin(theta) == pytest.approx(
            end["gridX"], abs=1e-6), wall
        assert face["originY"] + length * math.cos(theta) == pytest.approx(
            end["gridY"], abs=1e-6), wall


def test_a_wall_gets_a_surface_elevation_exactly_when_its_corner_has_one(
    record,
):
    """The refusal, stated as an equivalence rather than a count: surfaceZ is
    present for precisely those walls whose origin corner was measured. No wall
    may acquire a height from somewhere else, and none may lose one it has."""
    layout = record["layout"]
    config, _notes = build_grid_config(layout)
    corners = read_layout(layout)["corners"]
    walls = read_layout(layout)["walls"]

    for index, wall in enumerate(walls):
        recorded = corners[index]["elevation"] is not None
        assert (config["faces"][wall]["surfaceZ"] is not None) == recorded, wall


def test_a_wall_without_an_elevation_is_flagged_in_the_notes(record):
    """A null surfaceZ that nobody is told about is worse than no config."""
    layout = record["layout"]
    config, notes = build_grid_config(layout)
    missing = [
        wall for wall, face in config["faces"].items()
        if face["surfaceZ"] is None
    ]
    if not missing:
        pytest.skip("every corner of this trench has an opening elevation")

    assert any("no opening elevation" in note for note in notes)


def test_registered_walls_are_not_mistaken_for_placeholders(record):
    config, _notes = build_grid_config(record["layout"])

    for wall, face in config["faces"].items():
        if face["surfaceZ"] is None:
            continue
        assert not merge_walls.is_placeholder(face, config), wall


# ----------------------------------------------------------------- the datum


def test_every_recorded_corner_sits_below_the_datum_nail(record):
    """The nail is driven to clear the ground it measures. A corner above it
    means the datum, the reading, or the sign convention is wrong."""
    layout = record["layout"]
    datum = _datum(layout)
    if datum is None:
        pytest.skip("this layout records no datum elevation")

    for corner in layout["corners"]:
        if corner.get("elevation") is None:
            continue
        depth = datum - corner["elevation"]
        assert 0 < depth < MAX_DEPTH_BELOW_DATUM_M, corner.get("corner")


def test_the_elevations_round_trip_through_the_datum(record):
    """Absolute and below-datum are two spellings of one measurement, and a
    record that cannot convert between them cleanly has a unit problem."""
    layout = record["layout"]
    datum = _datum(layout)
    if datum is None:
        pytest.skip("this layout records no datum elevation")

    for elevation in _recorded_elevations(layout):
        below = datum - elevation
        assert site_elevation.absolute_from_below_datum(below, datum) == (
            pytest.approx(elevation))
        assert site_elevation.resolve(elevation, layout["vertical"]) == (
            pytest.approx(elevation))


def test_no_locus_surface_lies_above_the_datum_or_absurdly_below_it(
    record, by_locus,
):
    datum = _datum(record["layout"])
    if datum is None:
        pytest.skip("this layout records no datum elevation")

    for number, locus in by_locus.items():
        for phase in ("opening", "closing"):
            for vertex in _vertices(locus, phase):
                depth = datum - vertex["elevation"]
                assert 0 < depth < MAX_DEPTH_BELOW_DATUM_M, (number, phase)


# ------------------------------------------------------------------ the loci


def test_every_locus_is_fully_recorded(loci):
    for entry in loci["loci"]:
        number = entry["locus"]
        assert entry["munsell"], number
        for phase in ("opening", "closing"):
            vertices = _vertices(entry, phase)
            assert vertices, (number, phase)
            for vertex in vertices:
                assert vertex["gridX"] is not None
                assert vertex["gridY"] is not None
                assert vertex["elevation"] is not None


def test_the_loci_are_numbered_without_gaps(loci):
    numbers = sorted(entry["locus"] for entry in loci["loci"])

    assert numbers == list(range(min(numbers), max(numbers) + 1))


def test_no_locus_closes_meaningfully_above_where_it_opened(loci):
    """Excavation removes material, so a closing surface cannot be higher than
    the opening one -- beyond what the instruments scatter by.

    The allowance is not slack for its own sake. A feature defined and left
    standing is measured twice rather than excavated, and a plumb bob landing
    somewhere slightly different on an irregular stone top produces small rises
    that are real readings of a real surface. What this still catches is an
    opening and closing column written down the wrong way round, which moves a
    corner by decimetres.
    """
    for entry in loci["loci"]:
        opening = _by_label(entry, "opening")
        closing = _by_label(entry, "closing")
        for label in set(opening) & set(closing):
            rise = closing[label] - opening[label]
            assert rise <= MEASUREMENT_SCATTER_M + 1e-9, (
                entry["locus"], label, round(rise, 3))


def test_an_unexcavated_locus_records_no_material(loci):
    """A locus whose two surfaces are identical was never dug into, so nothing
    can have come out of it. Derived from the elevations rather than from a
    flag, because the flag is the thing that goes stale."""
    for entry in loci["loci"]:
        opening = _by_label(entry, "opening")
        closing = _by_label(entry, "closing")
        shared = set(opening) & set(closing)
        untouched = shared and all(
            closing[label] == opening[label] for label in shared)
        if not untouched:
            continue
        materials = entry.get("materials")
        if materials is None:
            continue
        assert set(materials.values()) == {0}, entry["locus"]


def test_loci_dug_one_below_another_share_the_surface_between_them(loci):
    """Where several loci were measured at the same set of coordinates, they
    are one column dug in stages: each closes on the surface the next opens on.
    Any disagreement means a reading was taken on a different day, at a
    different point, or after digging nobody recorded.

    The grouping is derived from the coordinates, so this needs to be told
    nothing about which loci form a sounding."""
    columns = {}
    for entry in loci["loci"]:
        columns.setdefault(_corner_set(entry), []).append(entry)

    checked = 0
    for members in columns.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda entry: entry["opened"]["date"])
        for younger, older in zip(members, members[1:]):
            closing = {_point(v): v["elevation"]
                       for v in _vertices(younger, "closing")}
            opening = {_point(v): v["elevation"]
                       for v in _vertices(older, "opening")}
            assert closing == opening, (younger["locus"], older["locus"])
            checked += 1

    if not checked:
        pytest.skip("no two loci in this trench share a set of corners")


def test_loci_opened_together_agree_where_their_edges_meet(loci):
    """Loci opened on the same day and sharing a boundary have vertices in
    common, and those are one measurement written onto two forms. Disagreement
    means the boundary between them was drawn differently on each."""
    days = {}
    for entry in loci["loci"]:
        days.setdefault(entry["opened"]["date"], []).append(entry)

    checked = 0
    for members in days.values():
        if len(members) < 2:
            continue
        for phase in ("opening", "closing"):
            readings = {}
            for entry in members:
                for vertex in _vertices(entry, phase):
                    readings.setdefault(_point(vertex), []).append(
                        (entry["locus"], vertex["elevation"]))
            for point, entries in readings.items():
                if len(entries) < 2:
                    continue
                checked += 1
                assert len({elev for _n, elev in entries}) == 1, (phase, point)

    if not checked:
        pytest.skip("no two loci in this trench share a vertex")


# --------------------------------------------------------------- the matrix


def _matrix(loci):
    def unit_id(number):
        return f"unit-{number:012x}"

    strat = loci["stratigraphy"]
    return HarrisMatrix.model_validate({
        "schema_version": 1,
        "matrix_id": "0123456789ab",
        "revision": 0,
        "title": f"{loci['trench']} {loci['season']}",
        "site": "Poggio Civitate",
        "trench": loci["trench"],
        "notes": "",
        "source_job_ids": [],
        "units": [
            {
                "id": unit_id(entry["locus"]),
                "label": f"Locus {entry['locus']}",
                "unit_type": entry["unit_type"],
                "description": entry["summary"],
                "source_refs": [],
            }
            for entry in loci["loci"]
        ],
        "relations": [
            {
                "id": f"rel-{index:012x}",
                "younger_id": unit_id(relation["younger"]),
                "older_id": unit_id(relation["older"]),
                "kind": relation["kind"],
                "evidence": relation["evidence"],
                "source": "manual",
                "notes": relation.get("note"),
            }
            for index, relation in enumerate(strat["relations"])
        ],
        "correlations": [
            {
                "id": f"corr-{index:012x}",
                "unit_ids": [unit_id(n) for n in correlation["loci"]],
                "notes": correlation["evidence"],
            }
            for index, correlation in enumerate(strat["correlations"])
        ],
        "suggestions": [],
        "created_at": "2026-07-31T08:00:00+00:00",
        "updated_at": "2026-07-31T08:00:00+00:00",
    })


@pytest.fixture
def stratigraphy(loci):
    if "stratigraphy" not in loci:
        pytest.skip("this loci fixture records no stratigraphy")
    return loci


def test_the_matrix_validates_with_no_errors(stratigraphy):
    """No cycle, no self-relation, no duplicate edge, no ordering inside a
    correlation. Warnings are fine -- a redundant edge is a real thing for a
    recording form to assert."""
    report = validate_matrix_graph(_matrix(stratigraphy))

    assert report["ok"], report["errors"]


def test_every_relation_carries_its_evidence(stratigraphy):
    """An edge is an interpretation. One with no stated grounds can only be
    believed, never reviewed."""
    for relation in stratigraphy["stratigraphy"]["relations"]:
        assert relation["evidence"]


def test_every_relation_and_correlation_names_a_locus_that_exists(
    stratigraphy, by_locus,
):
    strat = stratigraphy["stratigraphy"]
    for relation in strat["relations"]:
        assert relation["younger"] in by_locus
        assert relation["older"] in by_locus
    for correlation in strat["correlations"]:
        for number in correlation["loci"]:
            assert number in by_locus


def test_correlated_loci_collapse_to_one_node(stratigraphy):
    strat = stratigraphy["stratigraphy"]
    if not strat["correlations"]:
        pytest.skip("this trench records no correlations")

    matrix = _matrix(stratigraphy)
    components = correlation_components(matrix)
    report = validate_matrix_graph(matrix)

    collapsed = 0
    for correlation in strat["correlations"]:
        ids = [f"unit-{n:012x}" for n in correlation["loci"]]
        assert len({components[unit_id] for unit_id in ids}) == 1
        collapsed += len(ids) - 1

    assert len(report["topological_order"]) == len(
        stratigraphy["loci"]) - collapsed


def test_an_abutment_never_leaks_in_as_an_ordering(stratigraphy):
    """'Is bound to' says two units touch, which is a claim about
    contemporaneity. It has no representation in a younger-to-older graph, so
    it must be recorded and left out rather than quietly turned into an edge in
    whichever direction came to hand."""
    strat = stratigraphy["stratigraphy"]
    abutments = strat.get("abutments")
    if not abutments:
        pytest.skip("this trench records no abutments")

    assert strat.get("abutment_note")
    ordered = {
        (relation["younger"], relation["older"])
        for relation in strat["relations"]
    }
    for abutment in abutments:
        pair = tuple(abutment["loci"])
        assert pair not in ordered
        assert tuple(reversed(pair)) not in ordered


# ----------------------------------------------------------------- the finds


def test_every_find_is_fully_located(finds):
    for find in finds["finds"]:
        assert find["locus"] is not None, find["sf"]
        assert find["gridX"] is not None, find["sf"]
        assert find["gridY"] is not None, find["sf"]
        assert find["elevation"] is not None, find["sf"]
        assert find["page"], find["sf"]


def test_the_finds_are_numbered_without_gaps(finds):
    numbers = sorted(find["sf"] for find in finds["finds"])

    assert numbers == list(range(min(numbers), max(numbers) + 1))


def test_a_stated_tolerance_appears_exactly_on_the_indirect_recoveries(finds):
    """A find sorted out of a wheelbarrow has a coordinate that says where the
    bucket was filled, not where the object lay. A record that does not mark
    that invites the number to be used as a findspot."""
    with_tolerance = {
        find["sf"] for find in finds["finds"] if "tolerance_xy_m" in find
    }
    indirect = {
        find["sf"] for find in finds["finds"]
        if find.get("recovery") not in (None, "in situ")
    }
    if not indirect and not with_tolerance:
        pytest.skip("every find in this trench was recovered in situ")

    assert with_tolerance <= indirect


def test_every_find_was_made_while_its_locus_was_open(finds, by_locus):
    """A find dated outside its locus's own open-to-close window means the
    locus number or the date is wrong."""
    for find in finds["finds"]:
        locus = by_locus[find["locus"]]
        assert locus["opened"]["date"] <= find["date"] <= (
            locus["closed"]["date"]), find["sf"]


def _misplaced(finds, by_locus):
    """Findspots that contradict the volume their locus occupies.

    Plan position is checked against the locus's own recorded vertices rather
    than the trench, so a find filed under a sounding is held to the sounding.
    Elevation is checked against the locus's opening ceiling and closing floor.
    """
    plan, vertical = set(), set()
    for find in finds["finds"]:
        locus = by_locus[find["locus"]]
        points = [_point(v) for v in _vertices(locus, "opening")]
        x_bounds, y_bounds = _bounds(points)
        slack = find.get("tolerance_xy_m", 0.0)
        if not (_within(find["gridX"], (x_bounds[0] - slack,
                                        x_bounds[1] + slack))
                and _within(find["gridY"], (y_bounds[0] - slack,
                                            y_bounds[1] + slack))):
            plan.add(find["sf"])

        ceiling = max(v["elevation"] for v in _vertices(locus, "opening"))
        floor = min(v["elevation"] for v in _vertices(locus, "closing"))
        drop = find.get("tolerance_z_m", 0.0)
        if not (floor - TOLERANCE_M - drop <= find["elevation"]
                <= ceiling + TOLERANCE_M + drop):
            vertical.add(find["sf"])

    return plan, vertical


def test_the_findspots_that_do_not_place_are_the_ones_the_record_declares(
    finds, by_locus,
):
    """The two-way check. The fixture names the findspots known to contradict
    their loci; this recomputes that set from the coordinates and the locus
    surfaces and requires the two to match exactly.

    Correcting a findspot without updating the list fails, and so does a
    transcription slip that introduces a new one. Neither can pass quietly.
    """
    declared = finds.get("expected_findspot_failures")
    if declared is None:
        pytest.skip(
            "this finds fixture declares no expected failures; add "
            "'expected_findspot_failures' to pin them")

    plan, vertical = _misplaced(finds, by_locus)

    assert plan | vertical == set(declared)


def test_most_findspots_place_correctly(finds, by_locus):
    """A guard on the guard. If a change to the fixtures ever made most finds
    fail, the check above would still pass as long as the declared list were
    updated to match -- so this fixes the standard the records are held to
    rather than the number they happen to score."""
    plan, vertical = _misplaced(finds, by_locus)
    total = len(finds["finds"])

    assert len(plan | vertical) <= total // 3
