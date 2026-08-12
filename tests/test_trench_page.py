"""The trenches page (Chunk 7).

The page is a shell: every trench, wall and build message on it comes from
/api/trenches and /api/trenches/<label>/build at run time, so these tests check
the shell, the wiring in its script, and the two optional grouping inputs on
the upload/editor form. The build behaviour itself is covered by
tests/test_trench_routes.py, and the click-through is the operator's manual
gate.
"""

from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from app import app


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.scripts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "script":
            self.scripts.append(attributes)
        if tag == "a":
            self.links.append(attributes)


@pytest.fixture
def client(tmp_path, monkeypatch):
    app.config.update(TESTING=True)
    return app.test_client()


def _parse(response):
    parser = _PageParser()
    parser.feed(response.get_data(as_text=True))
    return parser


def test_trenches_page_renders_the_trench_container(client):
    response = client.get("/trenches")
    page = _parse(response)
    container = [
        attributes
        for _tag, attributes in page.elements
        if "data-trench-list" in attributes
    ]

    assert response.status_code == 200
    assert len(container) == 1
    assert container[0]["id"] == "trench-list"
    assert container[0]["aria-live"] == "polite"
    assert page.scripts == [
        {
            "type": "module",
            "src": "/static/trenches.js",
        }
    ]
    assert any(link.get("href") == "/" for link in page.links)
    assert str(REPO_ROOT).encode() not in response.data


def test_trenches_script_uses_the_existing_routes(client):
    script = client.get("/static/trenches.js")
    source = script.get_data(as_text=True)

    assert script.status_code == 200
    assert "/api/trenches" in source
    assert "/build" in source
    # The starter config flow: no grid means the route answers needs_grid, and
    # the page pre-fills the textarea with what it returned.
    assert "needs_grid" in source
    assert "payload.starter" in source
    # Notes and warnings are rendered, not swallowed.
    assert "grid_warnings" in source
    assert "payload.notes" in source
    # Task progress reuses the existing status endpoint.
    assert "/api/tasks/" in source


def test_upload_form_offers_the_two_grouping_inputs(client):
    scan_form = client.get("/static/app/stages/scan.js")
    source = scan_form.get_data(as_text=True)

    assert scan_form.status_code == 200
    assert 'name="trench_label"' in source
    assert 'name="wall_label"' in source
    # Both start methods reach a route that persists the labels: the upload
    # posts them as form fields, the blank canvas as JSON.
    assert "trench_label" in source
    assert "wall_label" in source
    assert "/editor/new" in source
