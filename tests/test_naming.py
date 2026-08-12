"""The shared label rules in naming.py.

``safe_filename`` and ``safe_label`` used to be separate copies of the same
regex in pipeline/build_gempy.py and backend/routes/trenches.py. The
modularization refactor merged them, so these tests pin the merged behaviour
for both callers.
"""

import pytest

import storage
from backend import create_app
from naming import canonical_locus, canonical_trench, clean_label, safe_filename


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("T104", "T104"),
        ("T104 south", "T104_south"),
        ("T104 / south!!", "T104_south"),
        ("T104.2", "T104.2"),  # dots inside a name are legal
        ("east-wall", "east-wall"),
        ("  padded  ", "padded"),
    ],
)
def test_safe_filename_preserves_legal_names(raw, expected):
    assert safe_filename(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "///", ".", "..", "...."])
def test_names_that_would_escape_or_vanish_fall_back(raw):
    """A component of only dots is a relative path, not a name."""
    assert safe_filename(raw, "trench") == "trench"


def test_fallback_is_per_caller():
    assert safe_filename("", "surface") == "surface"
    assert safe_filename("", "trench") == "trench"


def test_trench_file_route_cannot_escape_the_trench_directory(tmp_path):
    """Regression: a trench labelled ".." resolved to poggio_webapp/, and the
    route's containment check then compared against that escaped directory —
    so every file under it was readable."""
    outside = storage.TRENCHES_DIR.parent / "secret.txt"
    outside.write_text("SENSITIVE")

    client = create_app().test_client()
    for label in ("..", "%2e%2e"):
        response = client.get(f"/api/trenches/{label}/file?path=secret.txt")
        assert response.status_code != 200, label
        assert b"SENSITIVE" not in response.get_data(), label


def test_clean_label_is_not_path_safe_only_tidy():
    assert clean_label("  A6  ") == "A6"
    assert clean_label(None) == ""
    assert clean_label(7) == ""


# ---------------------------------------------------------------------------
# Site identifier forms. Conservation Kobo Form Instructions requires the
# property abbreviation and number "without spacing", and names "T-62" and
# "T 62" as incorrect; locus is "only the number".
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "T104",
        "T-104",
        "T 104",
        "t104",
        "t-104",
        "  T104  ",
        "T_104",
        "T.104",
    ],
)
def test_every_spelling_of_one_trench_canonicalizes_to_one_string(raw):
    assert canonical_trench(raw) == "T104"


def test_canonical_trench_keeps_multi_letter_property_abbreviations():
    """Bulk find codes carry non-T properties: bf-ca100-2024-4-C."""
    assert canonical_trench("CA 100") == "CA100"
    assert canonical_trench("ca-100") == "CA100"


def test_canonical_trench_preserves_digits_exactly():
    """T007 is not silently the same trench as T7; no label at this site is
    written with a leading zero, so collapsing them could only ever change a
    label nobody meant."""
    assert canonical_trench("T007") == "T007"
    assert canonical_trench("T7") == "T7"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("north wall", "north wall"),  # a wall label must survive untouched
        ("Piano del Tesoro", "Piano del Tesoro"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_canonical_trench_leaves_labels_it_does_not_recognise_alone(raw, expected):
    assert canonical_trench(raw) == expected


def test_canonical_trench_rejects_non_strings():
    assert canonical_trench(None) == ""
    assert canonical_trench(104) == ""


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("5", "5"),
        (" 5 ", "5"),
        ("5 ", "5"),
        ("Locus 5", "5"),
        ("locus5", "5"),
        (5, "5"),
        ("", ""),
    ],
)
def test_canonical_locus_reduces_to_the_bare_number(raw, expected):
    assert canonical_locus(raw) == expected


def test_canonical_locus_leaves_unrecognised_values_alone():
    assert canonical_locus("5a") == "5a"
    assert canonical_locus(True) == ""
