"""The shared label rules in naming.py.

``safe_filename`` and ``safe_label`` used to be separate copies of the same
regex in pipeline/build_gempy.py and backend/routes/trenches.py. Phase 2 of
MODULARIZATION_PLAN.md merged them, so these tests pin the merged behaviour for
both callers.
"""

import pytest

import storage
from backend import create_app
from naming import clean_label, safe_filename


@pytest.mark.parametrize("raw,expected", [
    ("T104", "T104"),
    ("T104 south", "T104_south"),
    ("T104 / south!!", "T104_south"),
    ("T104.2", "T104.2"),          # dots inside a name are legal
    ("east-wall", "east-wall"),
    ("  padded  ", "padded"),
])
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
