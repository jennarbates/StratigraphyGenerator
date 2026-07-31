"""Links back to the records data came from.

Read-only and offline by design: a URI is validated by its shape, never by
fetching it, and only the project's own hosts are accepted -- an arbitrary URL
stored as provenance would be a link the operator never vouched for, shown in
the interface as though they had.
"""

import pytest

from pipeline.provenance import (
    ProvenanceError,
    kobo_record_id,
    open_context_uri,
    read,
    trenchbook_page,
)

# Real identifiers from the 2025 site report's citation list.
T104_2025 = "https://opencontext.org/subjects/b4282935-bb77-4b2f-8369-8e7e123c80e2"
TRENCHBOOK = "https://opencontext.org/documents/fa3dcc46-01b2-446c-bf4e-dd29ded731c7"
ARK = "https://n2t.net/ark:/28722/r2p24/pc_20230001"


def test_the_projects_own_record_links_are_accepted():
    assert open_context_uri(T104_2025) == T104_2025
    assert open_context_uri(TRENCHBOOK) == TRENCHBOOK
    assert open_context_uri(ARK) == ARK


def test_links_are_canonicalized_rather_than_stored_twice():
    """One reference, one spelling: http upgrades and a trailing slash goes."""
    assert open_context_uri(T104_2025.replace("https", "http") + "/") == T104_2025
    assert open_context_uri("https://www.opencontext.org/subjects/abc12345") == (
        "https://opencontext.org/subjects/abc12345")


def test_an_absent_link_is_empty_not_an_error():
    assert open_context_uri(None) == ""
    assert open_context_uri("   ") == ""


@pytest.mark.parametrize("bad", [
    "https://example.com/subjects/abc12345",
    "https://opencontext.org/",
    "javascript:alert(1)",
    "opencontext.org/subjects/abc12345",
    42,
])
def test_links_outside_the_projects_hosts_are_refused(bad):
    with pytest.raises(ProvenanceError):
        open_context_uri(bad)


def test_kobo_ids_drop_their_optional_prefix():
    uuid = "1a329746-b924-4a7b-b9f3-feb82e2c3d51"
    assert kobo_record_id(uuid) == uuid
    assert kobo_record_id(f"uuid:{uuid.upper()}") == uuid


def test_a_non_uuid_kobo_id_is_refused():
    with pytest.raises(ProvenanceError, match="Kobo submission id"):
        kobo_record_id("submission-17")


@pytest.mark.parametrize("raw,expected", [
    ("17", "17"), ("p. 17", "17"), ("pp. 17-19", "17-19"),
    ("17 - 19", "17-19"), (17, "17"),
])
def test_trenchbook_pages_normalize(raw, expected):
    assert trenchbook_page(raw)[0] == expected


def test_an_even_trenchbook_page_is_questioned_not_refused():
    """Entries are written on odd right-hand pages, but a supplemental find is
    written on the facing left-hand page and that reference is real."""
    pages, notes = trenchbook_page("18")

    assert pages == "18"
    assert any("even page" in note for note in notes)


def test_an_odd_page_passes_without_comment():
    assert trenchbook_page("17") == ("17", [])


def test_a_page_that_is_not_a_number_is_refused():
    with pytest.raises(ProvenanceError, match="trenchbook page"):
        trenchbook_page("somewhere near the front")


def test_read_returns_only_the_fields_supplied():
    """An absent field must not write an empty key over something stored."""
    record, _notes = read({"openContextUri": T104_2025})

    assert record == {"open_context_uri": T104_2025}


def test_read_accepts_both_snake_and_camel_spellings():
    uuid = "1a329746-b924-4a7b-b9f3-feb82e2c3d51"
    record, _notes = read({"kobo_record_id": uuid, "trenchbookPage": "p. 21"})

    assert record == {"kobo_record_id": uuid, "trenchbook_page": "21"}


def test_read_of_nothing_is_empty():
    assert read({}) == ({}, [])
    assert read(None) == ({}, [])
