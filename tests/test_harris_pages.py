import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

import storage
from backend import create_app


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
        self.elements = []
        self._capture = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
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
    matrices_dir = storage.MATRICES_DIR

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
    assert {"Title", "Site", "Trench"} <= {text for _attributes, text in page.labels}
    normalized_html = " ".join(response.get_data(as_text=True).split())
    assert "one or more drawing jobs" in normalized_html
    assert page.scripts == [
        {
            "type": "module",
            "src": "/static/harris/dashboard.js",
        }
    ]
    assert page.live_regions
    assert str(matrices_dir).encode() not in response.data


def test_main_application_links_to_harris_dashboard(page_context):
    client, _matrices_dir = page_context

    response = client.get("/")
    normalized_html = " ".join(response.get_data(as_text=True).split())

    assert response.status_code == 200
    assert 'href="/harris"' in normalized_html
    assert "Harris matrices" in normalized_html


def test_dashboard_source_query_only_preselects_for_explicit_action(
    page_context,
):
    client, matrices_dir = page_context
    source_job_id = "0123456789ab"

    response = client.get(f"/harris?source_job={source_job_id}")
    page = _parse(response)
    by_id = {
        attributes["id"]: (tag, attributes)
        for tag, attributes in page.elements
        if "id" in attributes
    }
    dashboard_script = client.get("/static/harris/dashboard.js").get_data(as_text=True)

    assert response.status_code == 200
    assert list(matrices_dir.iterdir()) == []
    assert {
        "dashboard-source-job-list",
        "dashboard-source-status",
    } <= set(by_id)
    assert "URLSearchParams" in dashboard_script
    assert "source_job" in dashboard_script
    assert "/api/harris-source-jobs" in dashboard_script
    assert "checkbox.checked" in dashboard_script
    assert "/sources" in dashboard_script


def test_final_wizard_stage_offers_only_discovered_jobs_to_harris(
    page_context,
):
    client, _matrices_dir = page_context

    visualize_script = client.get("/static/app/stages/visualize.js").get_data(
        as_text=True
    )

    assert "/api/harris-source-jobs" in visualize_script
    assert "Create or add to a Harris Matrix" in visualize_script
    assert "/harris?source_job=" in visualize_script
    assert "encodeURIComponent(state.jobId)" in visualize_script


def test_editor_shell_loads_without_embedding_matrix_metadata(page_context):
    client, matrices_dir = page_context
    hostile_title = '</script><script data-injected="yes">alert(1)</script>'
    hostile_unit = '<img src=x onerror="alert(2)">'
    matrix = _create_matrix(client, hostile_title)
    matrix["units"] = [
        {
            "id": "unit-000000000001",
            "label": hostile_unit,
            "unit_type": "unknown",
            "description": hostile_unit,
            "source_refs": [],
        }
    ]
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
    assert page.scripts == [
        {
            "type": "module",
            "src": "/static/harris/editor.js",
        }
    ]
    assert any(
        region.get("id") == "save-status" and region.get("aria-live") == "polite"
        for region in page.live_regions
    )
    assert hostile_title.encode() not in response.data
    assert hostile_unit.encode() not in response.data
    assert b'data-injected="yes"' not in response.data
    assert str(matrices_dir).encode() not in response.data
    assert {"Matrix units", "Saved relationships"} <= set(page.captions)

    labelled_ids = {
        attributes["for"] for attributes, _text in page.labels if "for" in attributes
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

    rendered = b"\n".join(
        [
            client.get("/harris").data,
            client.get(f"/harris/{matrix['matrix_id']}").data,
        ]
    )

    assert str(REPO_ROOT).encode() not in rendered
    assert str(matrices_dir).encode() not in rendered
    assert json.dumps(str(matrices_dir)).encode() not in rendered


def test_editor_exposes_saved_diagram_preview_and_export_controls(
    page_context,
):
    client, _matrices_dir = page_context
    matrix = _create_matrix(client)

    response = client.get(f"/harris/{matrix['matrix_id']}")
    page = _parse(response)
    by_id = {
        attributes["id"]: (tag, attributes)
        for tag, attributes in page.elements
        if "id" in attributes
    }

    assert {
        "diagram-preview",
        "diagram-empty",
        "diagram-preview-status",
        "download-json",
        "download-svg",
        "print-matrix",
        "print-matrix-title",
        "print-matrix-footer",
    } <= set(by_id)
    assert by_id["diagram-preview"][0] == "img"
    assert by_id["diagram-preview"][1]["alt"] == ("Saved Harris Matrix diagram")
    assert by_id["download-json"][1]["href"].endswith("/export.json")
    assert by_id["download-svg"][1]["href"].endswith("/export.svg")
    assert "Print / Save as PDF" in page.buttons
    assert any(
        region.get("id") == "diagram-preview-status"
        and region.get("aria-live") == "polite"
        for region in page.live_regions
    )


def test_print_css_keeps_only_saved_diagram_content(page_context):
    client, _matrices_dir = page_context

    response = client.get("/static/harris/harris.css")
    css = response.get_data(as_text=True)
    print_css = css[css.index("@media print") :]

    assert response.status_code == 200
    assert ".harris-editor > :not(.editor-regions)" in print_css
    assert ".editor-regions > :not(.diagram-region)" in print_css
    assert ".diagram-heading-row" in print_css
    assert ".diagram-preview-status" in print_css
    assert ".print-only" in print_css
    assert ".print-matrix-footer" in print_css
