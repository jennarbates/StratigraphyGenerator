"""T905, the synthetic trench the whole pipeline is worked through.

Everything under ``docs/fixtures/`` is a clean synthetic example: it shows what
a well-formed input looks like. T905 is the other kind. It is invented too, but
it is invented *badly on purpose* -- modelled on the shape of a real season's
paperwork, with the gaps, contradictions and transcription slips that real
paperwork has -- because a pipeline demonstrated only on tidy input has never
been shown to refuse anything.

It holds four claims still:

**The refusals fire.** T905's northeast corner has no opening elevation,
because that corner falls inside a previous season's backfilled trench and had
no undisturbed surface to measure. One wall therefore cannot be registered, and
the documented refusal is what stops it rather than a placeholder quietly
standing in.

**The redundancies agree.** Four vertices are recorded twice on different loci;
the sounding's four surfaces chain exactly from one locus to the next; a stated
20 cm layer thickness recomputes from the elevations. Those agreements are what
make the disagreements meaningful.

**The disagreements are counted, not hidden.** Five of the 26 special finds
plot outside the volume their locus occupies, and each fails a different check
-- two on plan position, one on elevation, one on both. That number is asserted
here so a change to the fixture has to argue with a test.

**The schema's silences are recorded.** Three 'is bound to' assertions have no
representation in a younger-to-older graph. The fixture keeps them anyway, so
the loss is visible.

Fixtures: ``tests/fixtures/t905-2025-*.json``.
"""

import json
import math

import pytest

from pipeline import merge_walls, site_elevation, site_grid
from pipeline.harris_matrix import (
    HarrisMatrix,
    correlation_components,
    topological_order,
    validate_matrix_graph,
)
from pipeline.trench_layout import build_grid_config, read_layout

WALLS = ["north wall", "east wall", "south wall", "west wall"]

DATUM = 25.23
DATUM_AS_FIRST_SHOT = 25.73
TRANSIT_ERROR_M = 0.50

# The trench, from its Trench Layout section: 150E-155E by 20S-25S.
TRENCH_X = (150.0, 155.0)
TRENCH_Y = (-25.0, -20.0)

# The Locus 6 sounding, from its opening coordinates: 153E-154E by 22S-24S.
SOUNDING_X = (153.0, 154.0)
SOUNDING_Y = (-24.0, -22.0)

# A find this far outside its locus is a transcription problem rather than the
# few centimetres of scatter a plumb bob and a line level produce.
TOLERANCE_M = 0.10

SOUNDING_LOCI = (6, 7, 8)

# Loci 3, 4 and 5 were opened on the same morning and closed on the same
# morning, so a point on the boundary between two of them is one point measured
# twice.
SAME_DAY_LOCI = (3, 4, 5)


def _load(repo_root, name):
    path = repo_root / "tests" / "fixtures" / f"t905-2025-{name}.json"
    return json.loads(path.read_text())


@pytest.fixture
def layout(repo_root):
    return _load(repo_root, "layout")


@pytest.fixture
def loci(repo_root):
    return _load(repo_root, "loci")


@pytest.fixture
def finds(repo_root):
    return _load(repo_root, "special-finds")


@pytest.fixture
def by_locus(loci):
    return {entry["locus"]: entry for entry in loci["loci"]}


@pytest.fixture
def registration(layout):
    return build_grid_config(layout)


def _vertices(locus, phase):
    return locus[f"{phase}_vertices"]


def _elevation_at(locus, phase, label):
    for vertex in _vertices(locus, phase):
        if vertex["label"] == label:
            return vertex["elevation"]
    raise AssertionError(f"locus {locus['locus']} has no {phase} vertex {label}")


def _point(vertex):
    """A vertex's coordinates, rounded so they can be dictionary keys."""
    return (round(vertex["gridX"], 2), round(vertex["gridY"], 2))


def _inside(value, bounds):
    return bounds[0] - TOLERANCE_M <= value <= bounds[1] + TOLERANCE_M


# ---------------------------------------------------------------------------
# The fixtures are what they claim to be
# ---------------------------------------------------------------------------


def test_every_fixture_records_where_its_values_came_from(layout, loci, finds):
    """A coordinate with no stated provenance cannot be told apart from one
    somebody made up -- which, here, all of them are. The habit is the point:
    the field is the same one a real fixture has to fill in."""
    for fixture in (layout, loci, finds):
        assert fixture["_sources"]
        for field, source in fixture["_sources"].items():
            assert source["record"], field


def test_every_fixture_states_its_known_problems(layout, loci, finds):
    for fixture in (layout, loci, finds):
        assert fixture["_known_problems"]


def test_every_fixture_says_plainly_that_it_is_invented(layout, loci, finds):
    """These files carry coordinates, elevations and findspots in exactly the
    form real ones do. Nothing about their contents distinguishes them, so the
    header has to."""
    for fixture in (layout, loci, finds):
        assert any("SYNTHETIC" in line for line in fixture["_comment"])
        assert any("invented" in line for line in fixture["_comment"])


def test_all_three_fixtures_describe_the_same_trench_and_season(
    layout,
    loci,
    finds,
):
    for fixture in (layout, loci, finds):
        assert fixture["trench"] == "T905"
        assert fixture["season"] == "2025"
        assert fixture["site_grid"] == "poggio-civitate"


# ---------------------------------------------------------------------------
# Registration, and the wall that cannot be registered
# ---------------------------------------------------------------------------


def test_the_trench_is_five_metres_square(registration):
    _config, notes = registration
    lengths = [note for note in notes if " m from " in note]

    assert len(lengths) == 4
    assert all("5.00 m" in note for note in lengths)


def test_three_walls_register_from_surveyed_values(registration):
    config, _notes = registration

    assert config["source"] == "surveyed"
    for wall in ("north wall", "south wall", "west wall"):
        assert config["faces"][wall]["surfaceZ"] is not None
        assert not merge_walls.is_placeholder(config["faces"][wall], config)


def test_the_east_wall_has_no_surface_elevation_and_the_build_refuses_it(
    registration,
):
    """The northeast corner fell inside a previous season's backfilled trench,
    so there was no opening surface there to measure. The module will not
    invent one, and this is the whole reason the fixture has that gap."""
    config, notes = registration

    assert config["faces"]["east wall"]["surfaceZ"] is None
    assert any("155E/20S" in note and "no opening elevation" in note for note in notes)


def test_the_east_wall_still_gets_its_origin_and_bearing(registration):
    """Only the elevation is missing. The corner nail's position is recorded,
    so two of the four registration values are real. A refusal is not the same
    as having nothing."""
    config, _notes = registration
    face = config["faces"]["east wall"]

    assert (face["originX"], face["originY"]) == (155.0, -20.0)
    assert face["bearing_deg"] == 180.0


def test_each_wall_carries_the_bearing_its_corners_imply(registration):
    config, _notes = registration

    assert config["faces"]["north wall"]["bearing_deg"] == 90.0
    assert config["faces"]["east wall"]["bearing_deg"] == 180.0
    assert config["faces"]["south wall"]["bearing_deg"] == 270.0
    assert config["faces"]["west wall"]["bearing_deg"] == 0.0


def test_the_registration_puts_the_walls_back_on_the_corner_nails(
    layout,
    registration,
):
    """End to end: walk each wall its own length along its derived bearing and
    it must arrive at the next nail."""
    config, _notes = registration
    corners = read_layout(layout)["corners"]

    for index, wall in enumerate(WALLS):
        face = config["faces"][wall]
        start = corners[index]
        end = corners[(index + 1) % len(corners)]
        length = math.dist(
            (start["gridX"], start["gridY"]), (end["gridX"], end["gridY"])
        )
        theta = math.radians(face["bearing_deg"])

        assert face["originX"] + length * math.sin(theta) == pytest.approx(
            end["gridX"], abs=1e-6
        ), wall
        assert face["originY"] + length * math.cos(theta) == pytest.approx(
            end["gridY"], abs=1e-6
        ), wall


def test_the_corner_labels_parse_to_the_coordinates_a_spreadsheet_stores(
    layout,
):
    """A trench book writes '150E/20S'; a season spreadsheet stores the same
    nail already signed, as '150/-20'. One is the other read through the site's
    cardinal-inversion rule, and getting that backwards moves a trench."""
    signed = [
        (c["corner"], *site_grid.label_to_grid(c["label"])) for c in layout["corners"]
    ]

    assert signed == [
        ("NW", 150.0, -20.0),
        ("NE", 155.0, -20.0),
        ("SE", 155.0, -25.0),
        ("SW", 150.0, -25.0),
    ]


# ---------------------------------------------------------------------------
# The datum, and the 0.50 m it moved
# ---------------------------------------------------------------------------


def test_the_datum_correction_is_exactly_the_transit_error(layout):
    """The datum was first shot 0.50 m high and reshot mid-season. Every
    elevation recorded before that was corrected by the same amount."""
    assert layout["vertical"]["datumNail"]["absoluteZ"] == DATUM
    assert DATUM_AS_FIRST_SHOT - DATUM == pytest.approx(TRANSIT_ERROR_M)


def test_every_recorded_corner_sits_below_the_datum_nail(layout):
    """The nail is driven to clear the ground, so a corner above it would mean
    the datum or a reading is wrong."""
    for corner in layout["corners"]:
        if corner.get("elevation") is None:
            continue
        depth = DATUM - corner["elevation"]
        assert 0 < depth < 3, corner["corner"]


def test_the_datum_still_clears_the_deepest_point_reached(by_locus):
    """The bottom of the sounding is the lowest surface of the season."""
    deepest = min(vertex["elevation"] for vertex in _vertices(by_locus[8], "closing"))

    assert deepest == 23.51
    assert DATUM - deepest == pytest.approx(1.72)


def test_the_recorded_elevations_round_trip_through_the_datum(layout):
    """Absolute and below-datum are two spellings of one measurement."""
    vertical = layout["vertical"]
    for corner in layout["corners"]:
        if corner.get("elevation") is None:
            continue
        below = DATUM - corner["elevation"]
        recovered = site_elevation.absolute_from_below_datum(below, DATUM)
        assert recovered == pytest.approx(corner["elevation"])
        assert site_elevation.resolve(corner["elevation"], vertical) == (
            pytest.approx(corner["elevation"])
        )


def test_the_southwest_corner_is_high_because_of_a_spoil_heap(layout):
    """Not all relief is archaeology. This trench's highest corner is a modern
    dirt dump, and registering the west wall to it would set that wall's
    surface almost half a metre too high."""
    heights = {
        c["corner"]: c["elevation"]
        for c in layout["corners"]
        if c.get("elevation") is not None
    }

    assert max(heights, key=heights.get) == "SW"
    assert heights["SW"] - heights["NW"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# The loci, as measured surfaces
# ---------------------------------------------------------------------------


def test_all_eight_loci_are_present_and_numbered_one_to_eight(loci):
    assert [entry["locus"] for entry in loci["loci"]] == list(range(1, 9))


def test_every_locus_carries_a_munsell_value_and_both_surfaces(loci):
    for entry in loci["loci"]:
        assert entry["munsell"]
        assert entry["opening_vertices"]
        assert entry["closing_vertices"]


def test_the_sounding_is_one_continuous_column_of_measured_surfaces(by_locus):
    """Locus 6's floor is Locus 7's ceiling, and Locus 7's floor is Locus 8's
    ceiling, at all four corners. This is the geometry the pipeline consumes,
    and it closes without a gap."""
    for younger, older in zip(SOUNDING_LOCI, SOUNDING_LOCI[1:]):
        closing = {
            _point(v): v["elevation"] for v in _vertices(by_locus[younger], "closing")
        }
        opening = {
            _point(v): v["elevation"] for v in _vertices(by_locus[older], "opening")
        }

        assert closing == opening, f"loci {younger} and {older}"


def test_the_sounding_keeps_the_same_four_corners_throughout(by_locus):
    corners = {
        (153.0, -22.0),
        (154.0, -22.0),
        (154.0, -24.0),
        (153.0, -24.0),
    }
    for number in SOUNDING_LOCI:
        for phase in ("opening", "closing"):
            assert {_point(v) for v in _vertices(by_locus[number], phase)} == corners, (
                f"locus {number} {phase}"
            )


def test_every_surface_in_the_sounding_descends(by_locus):
    """No corner of any sounding locus is deeper at opening than at closing."""
    for number in SOUNDING_LOCI:
        locus = by_locus[number]
        for vertex in _vertices(locus, "opening"):
            closing = _elevation_at(locus, "closing", vertex["label"])
            assert closing <= vertex["elevation"], (number, vertex["label"])


def test_the_recorded_floor_thickness_recomputes_from_the_elevations(by_locus):
    """The description and the SU form both give the floor as about 20 cm
    thick. Subtracting Locus 6's two surfaces gives 13 to 21 cm across the four
    corners, with the northwest corner at exactly 0.20 m -- so the stated
    figure is a real measurement of one corner, not of the layer."""
    locus = by_locus[6]
    thicknesses = {
        vertex["label"]: round(
            vertex["elevation"] - _elevation_at(locus, "closing", vertex["label"]), 2
        )
        for vertex in _vertices(locus, "opening")
    }

    assert thicknesses == {"NW": 0.20, "NE": 0.21, "SE": 0.17, "SW": 0.13}
    assert (
        min(thicknesses.values())
        <= locus["recorded_thickness_m"]
        <= max(thicknesses.values())
    )


def test_the_unexcavated_locus_has_no_thickness(by_locus):
    """An unexcavated locus opens and closes on the same surface."""
    locus = by_locus[8]

    for vertex in _vertices(locus, "opening"):
        assert _elevation_at(locus, "closing", vertex["label"]) == (vertex["elevation"])


def test_the_two_features_left_in_situ_record_no_material(by_locus):
    """Loci 4 and 5 were defined, drawn, photographed and left standing, so
    every material count for them must be zero."""
    for number in (4, 5):
        assert set(by_locus[number]["materials"].values()) == {0}


def test_points_shared_between_loci_carry_the_same_elevation(by_locus):
    """Loci 3, 4 and 5 were opened together and closed together, so a vertex on
    the boundary between two of them is one point measured once. Four such
    points exist, and all four agree exactly in both phases -- which is the
    check that the boundaries between the three loci were drawn consistently."""
    shared = 0
    for phase in ("opening", "closing"):
        readings = {}
        for number in SAME_DAY_LOCI:
            for vertex in _vertices(by_locus[number], phase):
                readings.setdefault(_point(vertex), []).append(
                    (number, vertex["elevation"])
                )

        for point, entries in readings.items():
            if len(entries) < 2:
                continue
            shared += 1
            elevations = {elevation for _number, elevation in entries}
            assert len(elevations) == 1, (phase, point, entries)

    assert shared == 8  # four points, opening and closing


def test_the_same_surface_read_a_day_apart_agrees_to_within_six_centimetres(
    by_locus,
):
    """Locus 1's closing and Locus 2's opening are the same physical surface,
    read at the same eight points a day apart.

    Three of the eight rise, by up to 6 cm. Ground that has been excavated
    between two readings cannot rise, so that 6 cm is the measurement and not
    the surface: it is what a plumb bob, a line level and a tape repeat to on
    cut soil. Every elevation in these fixtures carries that much uncertainty,
    which is worth knowing before treating a 2 cm difference as a finding.
    """
    closing = {_point(v): v["elevation"] for v in _vertices(by_locus[1], "closing")}
    opening = {_point(v): v["elevation"] for v in _vertices(by_locus[2], "opening")}
    shared = set(closing) & set(opening)

    assert len(shared) == 8
    differences = [round(opening[point] - closing[point], 2) for point in shared]

    assert len([value for value in differences if value > 0]) == 3
    assert max(abs(value) for value in differences) == 0.06


# ---------------------------------------------------------------------------
# The Harris matrix, built from the SU forms
# ---------------------------------------------------------------------------


def _matrix(loci):
    """The fixture's stratigraphy as a HarrisMatrix, one unit per locus."""

    def unit_id(number):
        return f"unit-{number:012x}"

    strat = loci["stratigraphy"]
    return HarrisMatrix.model_validate(
        {
            "schema_version": 1,
            "matrix_id": "0123456789ab",
            "revision": 0,
            "title": "T905 2025",
            "site": "Poggio Civitate",
            "trench": "T905",
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
                    "unit_ids": [unit_id(number) for number in correlation["loci"]],
                    "notes": correlation["evidence"],
                }
                for index, correlation in enumerate(strat["correlations"])
            ],
            "suggestions": [],
            "created_at": "2026-07-31T08:00:00+00:00",
            "updated_at": "2026-07-31T08:00:00+00:00",
        }
    )


def test_the_season_matrix_validates_with_no_errors(loci):
    report = validate_matrix_graph(_matrix(loci))

    assert report["ok"], report["errors"]


def test_every_relation_carries_its_evidence(loci):
    """An edge is an interpretation. One with no stated grounds cannot be
    reviewed, only believed."""
    for relation in loci["stratigraphy"]["relations"]:
        assert relation["evidence"]


def test_loci_three_and_six_collapse_into_one_node(loci):
    """Both forms say EQUAL TO: Locus 6 is the piece of Locus 3 that was dug
    through, so it cannot be younger than itself -- which is what the season's
    drawn matrix implies by stacking them. A correlation is the assertion the
    schema has for exactly this, and it is never inferred from equal labels."""
    matrix = _matrix(loci)
    components = correlation_components(matrix)

    assert components["unit-000000000003"] == components["unit-000000000006"]

    report = validate_matrix_graph(matrix)
    assert len(report["topological_order"]) == 7  # eight loci, seven nodes


def test_the_redundant_edge_from_the_su_form_is_warned_and_not_displayed(loci):
    """Locus 6's form asserts OVERLIES Loci 7 AND 8. Since 7 overlies 8, the
    6-to-8 edge follows from the longer path. It stays in the record and drops
    out of the diagram, which is the documented split between what was asserted
    and what is shown."""
    matrix = _matrix(loci)
    report = validate_matrix_graph(matrix)

    redundant = [
        warning
        for warning in report["warnings"]
        if warning["code"] == "redundant-relation"
    ]
    assert len(redundant) == 1

    components = correlation_components(matrix)
    dropped = (components["unit-000000000006"], "unit-000000000008")
    assert dropped not in report["display_edges"]


def test_no_locus_is_left_isolated(loci):
    report = validate_matrix_graph(_matrix(loci))

    assert not [
        warning for warning in report["warnings"] if warning["code"] == "isolated-unit"
    ]


def test_the_sequence_runs_from_topsoil_to_the_unexcavated_layer(loci):
    matrix = _matrix(loci)
    order = topological_order(matrix)
    components = correlation_components(matrix)

    assert order[0] == components["unit-000000000001"]
    assert order[-1] == components["unit-000000000008"]


def test_the_abutments_are_recorded_even_though_the_schema_drops_them(loci):
    """'IS BOUND TO' says two units touch, which is a claim about
    contemporaneity. Every edge in the schema is younger-to-older, so these
    three assertions have nowhere to go. Recording them makes the loss visible
    instead of silent, and none of them may leak in as an ordering."""
    strat = loci["stratigraphy"]

    assert len(strat["abutments"]) == 3
    assert strat["abutment_note"]

    ordered = {
        (relation["younger"], relation["older"]) for relation in strat["relations"]
    }
    for abutment in strat["abutments"]:
        pair = tuple(abutment["loci"])
        assert pair not in ordered
        assert tuple(reversed(pair)) not in ordered


# ---------------------------------------------------------------------------
# The special finds, and the five that do not place
# ---------------------------------------------------------------------------


def test_all_twenty_six_special_finds_are_present_and_numbered(finds):
    assert [find["sf"] for find in finds["finds"]] == list(range(1, 27))


def test_every_find_has_a_locus_a_coordinate_and_an_elevation(finds):
    for find in finds["finds"]:
        assert find["locus"] in range(1, 9)
        assert find["gridX"] is not None
        assert find["gridY"] is not None
        assert find["elevation"] is not None
        assert find["page"]


def test_only_the_wheelbarrow_finds_carry_a_stated_tolerance(finds):
    """A wheelbarrow find's coordinate is where the bucket was filled, not
    where the object lay. A record that does not say so invites the number to
    be read as a findspot."""
    with_tolerance = {find["sf"] for find in finds["finds"] if "tolerance_xy_m" in find}
    from_wheelbarrow = {
        find["sf"] for find in finds["finds"] if find["recovery"] == "wheelbarrow"
    }

    assert with_tolerance == from_wheelbarrow == {1, 2, 3}


def _outside_in_plan(finds):
    outside = set()
    for find in finds["finds"]:
        if not (_inside(find["gridX"], TRENCH_X) and _inside(find["gridY"], TRENCH_Y)):
            outside.add(find["sf"])
        elif find["locus"] in SOUNDING_LOCI and not (
            _inside(find["gridX"], SOUNDING_X) and _inside(find["gridY"], SOUNDING_Y)
        ):
            outside.add(find["sf"])
    return outside


def _outside_in_elevation(finds, by_locus):
    outside = set()
    for find in finds["finds"]:
        locus = by_locus[find["locus"]]
        ceiling = max(v["elevation"] for v in _vertices(locus, "opening"))
        floor = min(v["elevation"] for v in _vertices(locus, "closing"))
        if not (floor - TOLERANCE_M <= find["elevation"] <= ceiling + TOLERANCE_M):
            outside.add(find["sf"])
    return outside


def test_four_finds_plot_outside_the_volume_they_are_filed_under(
    finds,
    by_locus,
):
    """SF 8 and SF 9 are recorded 0.52 m and 0.82 m west of the west baulk, in
    a locus that exists only inside the trench. SF 17 is 0.45 m west of the
    sounding it is assigned to, and SF 16 is 0.79 m north of it."""
    assert _outside_in_plan(finds) == {8, 9, 16, 17}


def test_two_finds_sit_below_the_locus_they_are_assigned_to(finds, by_locus):
    """SF 16 is 0.30 m below the deepest point the sounding ever reached. SF 3
    is 0.29 m below every Locus 1 closing reading, on a day spent lowering a
    spoil heap whose crest was at 24.70 mAE."""
    assert _outside_in_elevation(finds, by_locus) == {3, 16}


def test_neither_check_alone_would_catch_all_of_them(finds, by_locus):
    """SF 17 passes on elevation and fails on plan; SF 3 passes on plan and
    fails on elevation. A findspot has to be checked in three dimensions or it
    is not being checked."""
    plan = _outside_in_plan(finds)
    elevation = _outside_in_elevation(finds, by_locus)

    assert 17 in plan and 17 not in elevation
    assert 3 in elevation and 3 not in plan
    assert 16 in plan and 16 in elevation


def test_twenty_one_of_twenty_six_finds_place_inside_their_locus(
    finds,
    by_locus,
):
    """The headline number. Five finds have a coordinate or an elevation that
    contradicts the locus they are filed under; the other 21 are consistent
    with the surfaces recorded around them."""
    failing = _outside_in_plan(finds) | _outside_in_elevation(finds, by_locus)

    assert failing == {3, 8, 9, 16, 17}
    assert len(finds["finds"]) - len(failing) == 21


def test_every_find_is_filed_under_a_locus_that_was_open_when_it_was_found(
    finds,
    by_locus,
):
    """A find dated outside its locus's own open-to-close window would mean the
    locus number or the date is wrong. None are: the dates are the part of this
    record that holds together."""
    for find in finds["finds"]:
        locus = by_locus[find["locus"]]
        assert locus["opened"]["date"] <= find["date"] <= (locus["closed"]["date"]), (
            find["sf"]
        )


def test_the_catalogued_finds_agree_between_the_list_and_the_locus_form(
    finds,
    by_locus,
):
    """Locus 6 is the only locus whose form lists catalogue numbers. All three
    appear in the special finds list against Locus 6 finds -- including
    CAT-0126, which that list's own 'Cataloged?' column says is not
    catalogued."""
    from_list = {
        find["catalog"]
        for find in finds["finds"]
        if find["locus"] == 6 and find["catalog"]
    }

    assert from_list == set(by_locus[6]["catalogued_finds"])


def test_the_sounding_finds_deepen_as_the_sounding_does(finds, by_locus):
    """Loci 6 and 7 are one column dug in sequence, so the mean find elevation
    has to fall from one to the next. SF 16 is excluded because its elevation
    is one of the known-bad ones; including it would make the sequence look
    stronger than the record supports."""
    means = {}
    for number in (6, 7):
        elevations = [
            find["elevation"]
            for find in finds["finds"]
            if find["locus"] == number and find["sf"] != 16
        ]
        means[number] = sum(elevations) / len(elevations)

    assert means[6] > means[7]
