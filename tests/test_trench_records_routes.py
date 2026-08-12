"""Routes for the two record-driven paths: layout and locus import.

Both are read-only and offline. Neither writes to the system of record, and
neither makes a network request.
"""

import io
import json

import pytest

from backend import create_app
from pipeline import site_grid

LAYOUT = {
    "site_grid": site_grid.POGGIO_CIVITATE,
    "corners": [
        {"label": "190E/53S", "elevation": 29.10},
        {"label": "194E/53S", "elevation": 29.02},
        {"label": "194E/56S", "elevation": 28.55},
        {"label": "190E/56S", "elevation": 28.94},
    ],
    "walls": ["north wall", "east wall", "south wall", "west wall"],
}

EXPORT = (
    "Trench,Locus,Munsell,Opening Elevation\n"
    "T104,6,10YR 5/3 brown,29.10\n"
    "T900,1,7.5YR 4/2 dark brown,31.00\n"
)


@pytest.fixture
def client():
    return create_app().test_client()


def test_a_layout_returns_a_grid_config_without_writing_anything(client):
    response = client.post("/api/trenches/T104/layout", json=LAYOUT)

    assert response.status_code == 200
    body = response.get_json()
    assert body["grid"]["source"] == "surveyed"
    assert body["grid"]["faces"]["north wall"]["originX"] == 190.0
    assert body["grid"]["faces"]["north wall"]["bearing_deg"] == 90.0
    assert any("north wall" in note for note in body["notes"])


def test_a_bad_layout_is_a_400_with_the_reason(client):
    broken = {**LAYOUT, "walls": ["north wall"]}
    response = client.post("/api/trenches/T104/layout", json=broken)

    assert response.status_code == 400
    assert "4 wall name" in response.get_json()["error"]


def test_a_locus_export_is_read_for_this_trench_only(client):
    response = client.post(
        "/api/trenches/T104/loci/import",
        data={"file": (io.BytesIO(EXPORT.encode()), "loci.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    body = response.get_json()
    assert [locus["locusNumber"] for locus in body["loci"]] == ["6"]
    assert body["column_map"]["opening_elevation"] == "Opening Elevation"


def test_an_export_with_no_recognisable_columns_is_refused(client):
    response = client.post(
        "/api/trenches/T104/loci/import",
        data={"file": (io.BytesIO(b"a,b\n1,2\n"), "loci.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "locus_number" in response.get_json()["error"]


def test_an_explicit_column_map_is_honoured(client):
    text = "unit,ctx\nT104,6\n"
    response = client.post(
        "/api/trenches/T104/loci/import",
        data={
            "file": (io.BytesIO(text.encode()), "loci.csv"),
            "column_map": json.dumps({"locus_number": "ctx", "trench": "unit"}),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["loci"][0]["locusNumber"] == "6"


def test_a_missing_file_is_refused(client):
    response = client.post(
        "/api/trenches/T104/loci/import", data={}, content_type="multipart/form-data"
    )

    assert response.status_code == 400


def test_a_byte_order_mark_does_not_break_the_header(client):
    """Spreadsheet exports routinely carry one."""
    response = client.post(
        "/api/trenches/T104/loci/import",
        data={"file": (io.BytesIO(b"\xef\xbb\xbf" + EXPORT.encode()), "loci.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["loci"][0]["locusNumber"] == "6"


# ---------------------------------------------------------------------------
# A whole season from the Geospatial Spreadsheet
# ---------------------------------------------------------------------------


@pytest.fixture
def sheet_bytes(repo_root):
    return (repo_root / "tests" / "fixtures" / "geospatial-sample.csv").read_bytes()


def _post_sheet(client, sheet_bytes, **form):
    data = {"file": (io.BytesIO(sheet_bytes), "geospatial.csv")}
    data.update(form)
    return client.post(
        "/api/trenches/geospatial-sheet", data=data, content_type="multipart/form-data"
    )


def test_a_whole_season_registers_from_one_file(client, sheet_bytes):
    response = _post_sheet(client, sheet_bytes, site_grid=site_grid.POGGIO_CIVITATE)

    assert response.status_code == 200
    body = response.get_json()
    assert len(body["registered"]) == 6
    assert body["needs_wall_names"] == {}

    first = body["registered"]["T900"]["grid"]
    assert first["source"] == "surveyed"
    assert first["faces"]["north wall"]["originX"] == 100.0
    assert first["faces"]["north wall"]["bearing_deg"] == 90.0


def test_the_registration_carries_its_trenchbook_and_supervisors(
    client,
    sheet_bytes,
):
    body = _post_sheet(client, sheet_bytes).get_json()
    trench = body["registered"]["T900"]

    assert trench["trenchbook"] == "ABC/DEF I"
    assert "Supervisor One" in trench["supervisors"]


def test_outstanding_elevation_corrections_travel_with_the_trench(
    client,
    sheet_bytes,
):
    """A trench whose locus forms are still flagged FALSE has no elevations
    this application can build to yet."""
    body = _post_sheet(client, sheet_bytes).get_json()

    assert any(
        "corrected to absolute" in note for note in body["registered"]["T900"]["notes"]
    )


def test_an_extended_trench_is_reported_rather_than_guessed_at(
    client,
    sheet_bytes,
):
    body = _post_sheet(client, sheet_bytes, phase="closing").get_json()

    assert set(body["needs_wall_names"]) == {"T904"}
    reason = body["needs_wall_names"]["T904"]["reason"]
    assert "name its walls explicitly" in reason
    assert len(body["needs_wall_names"]["T904"]["corners"]) == 8


def test_the_stray_trench_column_value_is_reported(client, sheet_bytes):
    body = _post_sheet(client, sheet_bytes).get_json()
    assert any("not a trench identifier" in note for note in body["notes"])


def test_an_unknown_phase_is_refused(client, sheet_bytes):
    assert _post_sheet(client, sheet_bytes, phase="midway").status_code == 400


def test_a_file_that_is_not_the_geospatial_sheet_is_refused(client):
    response = client.post(
        "/api/trenches/geospatial-sheet",
        data={"file": (io.BytesIO(b"a,b\n1,2\n"), "other.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Geospatial Spreadsheet" in response.get_json()["error"]
