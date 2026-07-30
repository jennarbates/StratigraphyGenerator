"""Snapshot of the application's complete URL map.

This exists to protect the Phase 1 refactor in MODULARIZATION_PLAN.md, which
moves twelve routes out of ``app.py`` and into blueprints and deletes the
``app.view_functions["pages.index"]`` monkeypatch. Those are pure moves: the
route table before and after must be byte-identical. If a rule disappears,
gains a method, or changes shape during that move, this test says so
immediately instead of leaving a page quietly 404ing in production.

When a route is legitimately added or removed, update EXPECTED_RULES in the
same commit — that edit is the reviewable record of the change.
"""

import pytest

EXPECTED_RULES = {
    ("/", "GET"),
    ("/api/harris-matrices", "GET"),
    ("/api/harris-matrices", "POST"),
    ("/api/harris-matrices/<matrix_id>", "GET"),
    ("/api/harris-matrices/<matrix_id>", "PUT"),
    ("/api/harris-matrices/<matrix_id>/export.json", "GET"),
    ("/api/harris-matrices/<matrix_id>/export.svg", "GET"),
    ("/api/harris-matrices/<matrix_id>/sources", "POST"),
    ("/api/harris-matrices/<matrix_id>/suggestions/<suggestion_id>", "POST"),
    ("/api/harris-source-jobs", "GET"),
    ("/api/jobs", "POST"),
    ("/api/jobs/<job_id>/boundaries/manual", "POST"),
    ("/api/jobs/<job_id>/convert", "POST"),
    ("/api/jobs/<job_id>/extract", "POST"),
    ("/api/jobs/<job_id>/extract/upload", "POST"),
    ("/api/jobs/<job_id>/features/confirm", "POST"),
    ("/api/jobs/<job_id>/features/detect", "POST"),
    ("/api/jobs/<job_id>/file", "GET"),
    ("/api/jobs/<job_id>/gempy", "POST"),
    ("/api/jobs/<job_id>/gempy/result/<task_id>", "GET"),
    ("/api/jobs/<job_id>/gridconfig/starter", "GET"),
    ("/api/jobs/<job_id>/markers/assign", "POST"),
    ("/api/jobs/<job_id>/markers/confirm", "POST"),
    ("/api/jobs/<job_id>/markers/detect", "POST"),
    ("/api/jobs/<job_id>/markers/finalize", "POST"),
    ("/api/jobs/<job_id>/markers/preview", "POST"),
    ("/api/jobs/<job_id>/normalize", "POST"),
    ("/api/jobs/<job_id>/preprocess", "POST"),
    ("/api/jobs/<job_id>/scan", "POST"),
    ("/api/jobs/<job_id>/status", "GET"),
    ("/api/jobs/<job_id>/text-extraction", "GET"),
    ("/api/jobs/<job_id>/text-extraction", "POST"),
    ("/api/jobs/<job_id>/text-verification", "POST"),
    ("/api/jobs/<job_id>/text-verification/skip", "POST"),
    ("/api/jobs/<job_id>/validate", "POST"),
    ("/api/jobs/<job_id>/visualizer-files", "GET"),
    ("/api/tasks/<task_id>", "GET"),
    ("/api/trenches", "GET"),
    ("/api/trenches/<label>/build", "POST"),
    ("/api/trenches/<label>/file", "GET"),
    ("/editor/<job_id>", "GET"),
    ("/editor/<job_id>/finalize", "POST"),
    ("/editor/<job_id>/save", "POST"),
    ("/editor/<job_id>/state", "GET"),
    ("/editor/new", "POST"),
    ("/finds", "GET"),
    ("/finds/<job_id>", "GET"),
    ("/finds/<job_id>/<find_id>", "DELETE"),
    ("/finds/<job_id>/new", "POST"),
    ("/harris", "GET"),
    ("/harris/<matrix_id>", "GET"),
    ("/jobs/<job_id>", "GET"),
    ("/static/<path:filename>", "GET"),
    ("/trenches", "GET"),
    ("/visualizer", "GET"),
}

# Routes that app.py currently registers outside the blueprint system. Phase 1
# moves each into a blueprint; the set above must not change when it does.
# See MODULARIZATION_PLAN.md §1.1.
ROUTES_OWNED_BY_APP_PY = {
    ("/jobs/<job_id>", "GET"),
    ("/trenches", "GET"),
    ("/finds", "GET"),
    ("/finds/<job_id>/new", "POST"),
    ("/finds/<job_id>", "GET"),
    ("/finds/<job_id>/<find_id>", "DELETE"),
    ("/editor/new", "POST"),
    ("/editor/<job_id>", "GET"),
    ("/editor/<job_id>/save", "POST"),
    ("/editor/<job_id>/state", "GET"),
    ("/editor/<job_id>/finalize", "POST"),
    ("/api/jobs/<job_id>/status", "GET"),
}


def _rules(flask_app):
    return {
        (str(rule.rule), method)
        for rule in flask_app.url_map.iter_rules()
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }


def test_url_map_matches_snapshot(app):
    assert _rules(app) == EXPECTED_RULES


def test_every_expected_route_resolves_to_a_handler(app):
    """A rule can exist while its view function is missing or shadowed."""
    for rule in app.url_map.iter_rules():
        assert app.view_functions.get(rule.endpoint) is not None, rule.endpoint


@pytest.mark.parametrize("rule,method", sorted(ROUTES_OWNED_BY_APP_PY))
def test_app_py_routes_are_registered(app, rule, method):
    """Pinned individually so a Phase 1 regression names the lost route."""
    assert (rule, method) in _rules(app)


def test_index_is_not_the_unrendered_template(client):
    """``routes/pages.py:index`` send_from_directory's the raw Jinja template;
    ``app.py`` overrides it with a real render. Whichever handler wins after
    Phase 1, the response must not contain unrendered template syntax."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "{%" not in body
    assert "{{" not in body
