import json
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from backend import config, create_app


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.captions = []
        self.controls = []
        self.headings = []
        self.labels = []
        self.regions = []
        self.scripts = []
        self.live_regions = []
        self._capture = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"button", "caption", "h1", "h2"}:
            self._capture = (tag, attributes)
            self._text = []
        elif tag == "label":
            self._capture = (tag, attributes)
            self._text = []
        if tag in {"input", "select", "textarea"}:
            self.controls.append(attributes)
        if tag == "section" and "data-harris-region" in attributes:
            self.regions.append(attributes["data-harris-region"])
        if tag == "script":
            self.scripts.append(attributes)
        if "aria-live" in attributes:
            self.live_regions.append(attributes)

    def handle_endtag(self, tag):
        if self._capture is None or self._capture[0] != tag:
            return
        text = " ".join("".join(self._text).split())
        if tag in {"h1", "h2"}:
            self.headings.append(text)
        elif tag == "button":
            self.buttons.append(text)
        elif tag == "caption":
            self.captions.append(text)
        else:
            self.labels.append((self._capture[1], text))
        self._capture = None
        self._text = []

    def handle_data(self, data):
        if self._capture is not None:
            self._text.append(data)


@pytest.fixture
def page_context(tmp_path, monkeypatch):
    matrices_dir = tmp_path / "matrices"
    jobs_dir = tmp_path / "jobs"
    matrices_dir.mkdir()
    jobs_dir.mkdir()
    monkeypatch.setattr(config, "MATRICES_DIR", matrices_dir)
    monkeypatch.setattr(config, "JOBS_DIR", jobs_dir)

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client(), matrices_dir


def _parse(response):
    parser = _PageParser()
    parser.feed(response.get_data(as_text=True))
    return parser


def _create_matrix(client, title="T123 Harris Matrix"):
    response = client.post(
        "/api/harris-matrices",
        json={
            "title": title,
            "site": "Poggio Civitate",
            "trench": "T123",
        },
    )
    assert response.status_code == 201
    return response.get_json()


def test_dashboard_get_is_reachable_and_creates_nothing(page_context):
    client, matrices_dir = page_context

    response = client.get("/harris")
    page = _parse(response)

    assert response.status_code == 200
    assert list(matrices_dir.iterdir()) == []
    assert "Harris matrices" in page.headings
    assert {"Title", "Site", "Trench"} <= {
        text for _attributes, text in page.labels
    }
    normalized_html = " ".join(
        response.get_data(as_text=True).split()
    )
    assert "one or more drawing jobs" in normalized_html
    assert page.scripts == [{
        "type": "module",
        "src": "/static/harris/dashboard.js",
    }]
    assert page.live_regions
    assert str(matrices_dir).encode() not in response.data


def test_editor_shell_loads_without_embedding_matrix_metadata(page_context):
    client, matrices_dir = page_context
    hostile_title = '</script><script data-injected="yes">alert(1)</script>'
    hostile_unit = '<img src=x onerror="alert(2)">'
    matrix = _create_matrix(client, hostile_title)
    matrix["units"] = [{
        "id": "unit-000000000001",
        "label": hostile_unit,
        "unit_type": "unknown",
        "description": hostile_unit,
        "source_refs": [],
    }]
    saved = client.put(
        f"/api/harris-matrices/{matrix['matrix_id']}",
        json=matrix,
    )
    assert saved.status_code == 200

    response = client.get(f"/harris/{matrix['matrix_id']}")
    page = _parse(response)

    assert response.status_code == 200
    assert "Harris matrix editor" in page.headings
    label_text = {text for _attributes, text in page.labels}
    expected_labels = {
        "Title",
        "Site",
        "Trench",
        "Notes",
        "Search units",
        "Manual unit label",
        "Manual unit type",
        "Manual unit description",
        "Younger unit",
        "Older unit",
        "Relationship kind",
        "Relationship evidence",
        "Relationship notes",
        "Units to correlate",
        "Correlation notes",
    }
    assert all(
        any(text.startswith(expected) for text in label_text)
        for expected in expected_labels
    )
    assert set(page.regions) == {
        "sources",
        "units",
        "relationships",
        "correlations",
        "suggestions",
        "diagram",
    }
    assert page.scripts == [{
        "type": "module",
        "src": "/static/harris/editor.js",
    }]
    assert any(
        region.get("id") == "save-status"
        and region.get("aria-live") == "polite"
        for region in page.live_regions
    )
    assert hostile_title.encode() not in response.data
    assert hostile_unit.encode() not in response.data
    assert b'data-injected="yes"' not in response.data
    assert str(matrices_dir).encode() not in response.data
    assert {"Matrix units", "Saved relationships"} <= set(page.captions)

    labelled_ids = {
        attributes["for"]
        for attributes, _text in page.labels
        if "for" in attributes
    }
    for control in page.controls:
        if control.get("type") == "hidden":
            continue
        assert (
            control.get("id") in labelled_ids
            or "aria-label" in control
            or "aria-labelledby" in control
        ), control

    assert all("all" not in text.casefold() for text in page.buttons)
    normalized_html = " ".join(response.get_data(as_text=True).split())
    assert "bulk-accept" not in normalized_html.casefold()
    assert "<script>" not in normalized_html


def test_editor_shell_rejects_invalid_and_missing_ids(page_context):
    client, _matrices_dir = page_context

    invalid = client.get("/harris/not-a-matrix")
    missing = client.get("/harris/aaaaaaaaaaaa")

    assert invalid.status_code == 400
    assert invalid.get_json()["code"] == "invalid_matrix_id"
    assert missing.status_code == 404
    assert missing.get_json()["code"] == "matrix_not_found"


def test_page_html_contains_no_server_paths(page_context):
    client, matrices_dir = page_context
    matrix = _create_matrix(client)

    rendered = b"\n".join([
        client.get("/harris").data,
        client.get(f"/harris/{matrix['matrix_id']}").data,
    ])

    assert str(REPO_ROOT).encode() not in rendered
    assert str(matrices_dir).encode() not in rendered
    assert json.dumps(str(matrices_dir)).encode() not in rendered
