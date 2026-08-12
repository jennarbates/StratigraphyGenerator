"""The site's controlled vocabularies and identifier formats.

Every expected value here is transcribed from a project document, not chosen
to match the implementation. Where a document gives a worked example, that
example is the test case.
"""

import pytest

from pipeline.site_vocab import (
    BULK_MATERIALS,
    DRAWN_FEATURE_TYPES,
    HARRIS_UNIT_TYPES,
    SURVEY_POINT_CODES,
    VocabError,
    bulk_find_id,
    catalogued_id,
    feature_type,
    material_name,
    parse_find_id,
    special_find_id,
)

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------


def test_bulk_material_letters_match_the_kobo_instructions():
    assert BULK_MATERIALS == {
        "T": "Tile",
        "P": "Plaster",
        "C": "Pottery/Ceramic",
        "B": "Bone",
        "M": "Metal",
        "S": "Stone",
        "A": "Architectural",
        "O": "Other",
    }


def test_survey_point_codes_match_the_total_station_workflow():
    assert set(SURVEY_POINT_CODES) == {
        "CTRL",
        "UNIT",
        "WALL",
        "STONE",
        "ART",
        "FEAT",
        "TEST",
        "TOPO",
    }
    assert SURVEY_POINT_CODES["TOPO"] == "Ground surface"
    assert SURVEY_POINT_CODES["UNIT"] == "Unit corner"


def test_material_name_handles_the_other_suffix_form():
    assert material_name("T") == "Tile"
    assert material_name("t") == "Tile"
    assert material_name("O-Slag") == "Other (Slag)"
    assert material_name("Z") is None
    assert material_name(None) is None


# ---------------------------------------------------------------------------
# Drawn feature types
# ---------------------------------------------------------------------------


def test_drawn_feature_keys_are_unique():
    keys = [entry["key"] for entry in DRAWN_FEATURE_TYPES]
    assert len(keys) == len(set(keys))


def test_material_features_carry_a_real_bulk_material_letter():
    for entry in DRAWN_FEATURE_TYPES:
        if entry["kind"] == "material":
            head = entry["material"].split("-")[0]
            assert head in BULK_MATERIALS, entry["key"]


def test_stratigraphic_features_carry_a_real_harris_unit_type():
    """The Harris module already models the Museum of London vocabulary that
    the procedures cite; drawn units must not invent a parallel one."""
    for entry in DRAWN_FEATURE_TYPES:
        if entry["kind"] == "unit":
            assert entry["unitType"] in HARRIS_UNIT_TYPES, entry["key"]


def test_survey_codes_on_features_are_real_codes():
    for entry in DRAWN_FEATURE_TYPES:
        code = entry.get("surveyCode")
        if code is not None:
            assert code in SURVEY_POINT_CODES, entry["key"]


def test_the_t104_sheet_key_is_fully_expressible():
    """Stone, Terracotta, Bone and Tree Stump are the four keys on the two
    T104 plan sheets. All four must be recordable."""
    for key in ("stone", "terracotta", "bone", "tree-stump"):
        assert feature_type(key) is not None, key


def test_tree_stump_is_an_intrusion_not_a_find_or_a_deposit():
    """Root disturbance is neither material recovered nor a stratigraphic
    unit; filing it as either would misrepresent it."""
    stump = feature_type("tree-stump")
    assert stump["kind"] == "intrusion"
    assert "material" not in stump
    assert "unitType" not in stump


def test_unknown_feature_key_is_none():
    assert feature_type("nonexistent") is None


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


def test_special_find_id_matches_the_documented_example():
    assert special_find_id("T111", 2025, "1", "1") == "sf-T111-2025-1-1"


def test_bulk_find_id_matches_the_documented_example():
    assert bulk_find_id("T104", 2025, "1", "T") == "bf-T104-2025-1-T"


def test_catalogued_id_matches_the_documented_example():
    assert catalogued_id("pc", 2024, 1) == "pc20240001"
    assert catalogued_id("PC", "2024", "0001") == "pc20240001"


def test_identifier_construction_canonicalizes_its_parts():
    """A recorder typing 'T-111' and ' 1 ' must not produce a second
    identifier for the same find."""
    assert special_find_id("T-111", 2025, " 1 ", 1) == "sf-T111-2025-1-1"


def test_parsing_accepts_the_lowercase_tag_spelling():
    """Hand-written tags use lowercase; the Kobo examples use the canonical
    trench spelling. Both name the same find."""
    parsed = parse_find_id("sf-t108-2024-2-2")
    assert parsed.kind == "special"
    assert parsed.trench == "T108"
    assert parsed.year == "2024"
    assert parsed.locus == "2"
    assert parsed.number == "2"
    assert parsed.text == "sf-T108-2024-2-2"
    assert parsed.as_tag() == "sf-t108-2024-2-2"


def test_parsing_a_bulk_find_reads_its_material():
    parsed = parse_find_id("bf-ca100-2024-4-C")
    assert parsed.kind == "bulk"
    assert parsed.trench == "CA100"
    assert parsed.material == "C"
    assert material_name(parsed.material) == "Pottery/Ceramic"


def test_parsing_a_bulk_find_reads_an_other_suffix():
    assert parse_find_id("bf-T104-2025-1-O-slag").material == "O-Slag"


def test_parsing_a_catalogued_object():
    parsed = parse_find_id("PC 20250017")
    assert parsed.kind == "catalogued"
    assert parsed.year == "2025"
    assert parsed.number == "0017"
    assert parsed.text == "pc20250017"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "sf-T111-25-1-1",  # two-digit year
        "sf-T111-2025-1",  # missing find number
        "xx-T111-2025-1-1",  # unknown prefix
        "pc2025001",  # catalogue number too short
        None,
    ],
)
def test_malformed_identifiers_raise_with_an_explanation(bad):
    with pytest.raises(VocabError) as caught:
        parse_find_id(bad)
    assert str(caught.value)


def test_an_unknown_material_letter_is_named_in_the_error():
    with pytest.raises(VocabError) as caught:
        parse_find_id("bf-T104-2025-1-Z")
    assert "'Z'" in str(caught.value)


def test_constructing_with_a_bad_material_lists_the_valid_ones():
    with pytest.raises(VocabError) as caught:
        bulk_find_id("T104", 2025, "1", "Z")
    assert "A, B, C" in str(caught.value)


def test_constructing_with_a_blank_part_says_which_part():
    with pytest.raises(VocabError) as caught:
        special_find_id("", 2025, "1", "1")
    assert "trench" in str(caught.value)
