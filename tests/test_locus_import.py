"""Reading a Kobo Locus Entry export.

The load-bearing design choice here is that column names are never guessed. A
Kobo export\'s headers depend on how the form was built, and mis-mapping a
column would attach the wrong elevations to real loci without anything looking
wrong. So the importer suggests a mapping, says which one it used, and refuses
when it cannot identify a required column -- listing the headers it saw, which
is the one thing that makes the mapping easy to fix.
"""

import pytest

from pipeline.locus_import import (
    LocusImportError,
    merge_into_sheet,
    read_export,
    suggest_column_map,
)

EXPORT = """Trench,Locus,Season,Munsell,Description,Opening Elevation,Closing Elevation,_uuid
T104,6,2025,10YR 5/3 brown,Debris deposit,29.10,28.55,1a329746-b924-4a7b-b9f3-feb82e2c3d51
T104,7,2025,10YR 3/2 very dark grayish brown,Intermediate surface,28.55,28.02,
T900,1,2025,7.5YR 4/2 dark brown,Topsoil,31.00,30.40,
"""


# Column mapping


def test_plausible_headers_are_suggested_not_required_to_match_exactly():
    mapping, unmatched = suggest_column_map(
        ["Trench", "Locus", "Opening Elevation", "_uuid"]
    )

    assert mapping["trench"] == "Trench"
    assert mapping["locus_number"] == "Locus"
    assert mapping["opening_elevation"] == "Opening Elevation"
    assert mapping["kobo_record_id"] == "_uuid"
    assert "munsell" in unmatched


def test_an_unrecognised_export_refuses_and_shows_its_headers():
    """Guessing here would silently attach the wrong numbers to real loci."""
    with pytest.raises(LocusImportError) as caught:
        read_export("Column A,Column B\n1,2\n")
    message = str(caught.value)

    assert "locus_number" in message
    assert "'Column A'" in message
    assert "guessing here would" in message


def test_an_explicit_column_map_overrides_the_suggestion():
    text = "unit,ctx,soil\nT104,6,10YR 5/3 brown\n"
    result = read_export(
        text, {"locus_number": "ctx", "trench": "unit", "munsell": "soil"}
    )

    assert result["loci"][0]["locusNumber"] == "6"
    assert result["loci"][0]["munsell"] == "10YR 5/3 brown"


def test_a_column_map_naming_a_missing_column_refuses():
    with pytest.raises(LocusImportError, match="does not have"):
        read_export(EXPORT, {"locus_number": "nonexistent"})


def test_the_mapping_actually_used_is_returned_for_checking():
    result = read_export(EXPORT)
    assert result["column_map"]["opening_elevation"] == "Opening Elevation"


# Reading rows


def test_loci_are_read_with_their_elevations():
    result = read_export(EXPORT, trench="T104")
    locus_6 = result["loci"][0]

    assert locus_6["locusNumber"] == "6"
    assert locus_6["openingElevation"] == pytest.approx(29.10)
    assert locus_6["closingElevation"] == pytest.approx(28.55)
    assert locus_6["munsell"] == "10YR 5/3 brown"
    assert locus_6["confidence"] == "imported-from-locus-record"


def test_one_trenchs_rows_are_selected_from_a_whole_season():
    result = read_export(EXPORT, trench="T104")
    assert [locus["locusNumber"] for locus in result["loci"]] == ["6", "7"]


def test_the_trench_filter_uses_canonical_labels():
    result = read_export(EXPORT, trench="T-104")
    assert len(result["loci"]) == 2


def test_without_a_trench_filter_every_row_is_read():
    assert len(read_export(EXPORT)["loci"]) == 3


def test_provenance_links_are_carried_and_validated():
    result = read_export(EXPORT, trench="T104")

    assert result["loci"][0]["koboRecordId"] == ("1a329746-b924-4a7b-b9f3-feb82e2c3d51")
    assert "koboRecordId" not in result["loci"][1]


def test_a_bad_value_in_one_row_does_not_cost_the_others():
    """One malformed entry should not cost the operator the other forty."""
    text = EXPORT.replace("29.10", "about 29")
    result = read_export(text, trench="T104")

    assert len(result["loci"]) == 2
    assert result["loci"][0]["openingElevation"] is None
    assert any("not a number" in note for note in result["notes"])


def test_a_repeated_locus_keeps_the_first_and_says_so():
    text = EXPORT + "T104,6,2025,different,,29.9,,\n"
    result = read_export(text, trench="T104")

    assert len(result["loci"]) == 2
    assert result["loci"][0]["munsell"] == "10YR 5/3 brown"
    assert any("already read from row" in note for note in result["notes"])


def test_below_datum_elevations_are_resolved_through_the_vertical_frame():
    text = "Trench,Locus,Opening Elevation\nT104,6,0.5\n"
    result = read_export(
        text,
        vertical={
            "frame": "mAE",
            "entryForm": "below-datum",
            "datumNail": {"absoluteZ": 29.6},
        },
    )

    assert result["loci"][0]["openingElevation"] == pytest.approx(29.1)


def test_below_datum_without_a_datum_refuses_the_whole_import():
    text = "Trench,Locus,Opening Elevation\nT104,6,0.5\n"
    with pytest.raises(LocusImportError, match="no datum nail elevation"):
        read_export(text, vertical={"frame": "mAE", "entryForm": "below-datum"})


def test_an_empty_export_refuses():
    with pytest.raises(LocusImportError, match="empty"):
        read_export("")


def test_a_trench_with_no_matching_rows_says_so():
    result = read_export(EXPORT, trench="T555")

    assert result["loci"] == []
    assert any("no locus rows" in note for note in result["notes"])


def test_unmatched_columns_are_reported():
    result = read_export("Trench,Locus\nT104,6\n")
    assert any("no column was matched" in note for note in result["notes"])


# Merging into a traced sheet


def test_an_import_fills_only_what_the_sheet_is_missing():
    sheet = {"loci": [{"locusNumber": "6", "munsell": None, "description": None}]}
    imported = read_export(EXPORT, trench="T104")["loci"]

    merged, _notes = merge_into_sheet(sheet, imported)

    assert merged["loci"][0]["munsell"] == "10YR 5/3 brown"
    assert merged["loci"][0]["openingElevation"] == pytest.approx(29.10)


def test_the_recorders_own_reading_wins_over_an_import():
    """They traced the sheet and typed what they saw on it. An import is a
    second source, not a correction."""
    sheet = {"loci": [{"locusNumber": "6", "munsell": "10YR 4/4 dark brown"}]}
    imported = read_export(EXPORT, trench="T104")["loci"]

    merged, notes = merge_into_sheet(sheet, imported)

    assert merged["loci"][0]["munsell"] == "10YR 4/4 dark brown"
    assert any("sheet's own reading is kept" in note for note in notes)


def test_overwrite_is_available_but_not_the_default():
    sheet = {"loci": [{"locusNumber": "6", "munsell": "10YR 4/4 dark brown"}]}
    imported = read_export(EXPORT, trench="T104")["loci"]

    merged, _notes = merge_into_sheet(sheet, imported, overwrite=True)

    assert merged["loci"][0]["munsell"] == "10YR 5/3 brown"


def test_a_locus_absent_from_the_sheet_is_added_and_flagged():
    sheet = {"loci": [{"locusNumber": "6"}]}
    imported = read_export(EXPORT, trench="T104")["loci"]

    merged, notes = merge_into_sheet(sheet, imported)

    numbers = [entry["locusNumber"] for entry in merged["loci"]]
    assert numbers == ["6", "7"]
    assert any("not on this sheet" in note for note in notes)
