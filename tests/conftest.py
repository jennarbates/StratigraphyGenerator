"""Shared test fixtures.

Import paths are configured in pyproject.toml under [tool.pytest.ini_options]
(``pythonpath``), which replaced the ``sys.path.insert`` block that used to be
copy-pasted into every test module.
"""

from pathlib import Path

import pytest

from backend import config, create_app
from backend import jobs as backend_jobs
from backend.routes import jobs as jobs_routes
from backend.routes import trenches as trenches_routes
from pipeline import editor as editor_pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
WEBAPP_ROOT = REPO_ROOT / "poggio_webapp"


@pytest.fixture
def repo_root():
    """Repo root, for tests that reach for real files on disk."""
    return REPO_ROOT


@pytest.fixture
def webapp_root():
    """``poggio_webapp/``, for tests that assert on static assets or templates."""
    return WEBAPP_ROOT


@pytest.fixture
def storage_dirs(tmp_path, monkeypatch):
    """Redirect every on-disk storage root at a fresh tmp_path.

    JOBS_DIR is defined in ``backend.config`` but re-bound at import time by
    four other modules (``from ..config import JOBS_DIR``), so patching the
    config module alone does not reach them. ``pipeline.editor`` derives its
    own copy from ``__file__`` and never consults config at all. Every target
    below is therefore load-bearing.

    Phase 2 of MODULARIZATION_PLAN.md collapses these to a single assignment;
    when it does, this fixture should shrink with it.
    """
    jobs_dir = tmp_path / "jobs"
    trenches_dir = tmp_path / "trenches"
    matrices_dir = tmp_path / "matrices"
    for directory in (jobs_dir, trenches_dir, matrices_dir):
        directory.mkdir()

    monkeypatch.setattr(config, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(config, "TRENCHES_DIR", trenches_dir)
    monkeypatch.setattr(config, "MATRICES_DIR", matrices_dir)
    monkeypatch.setattr(backend_jobs, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(jobs_routes, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(trenches_routes, "JOBS_DIR", jobs_dir)
    monkeypatch.setattr(trenches_routes, "TRENCHES_DIR", trenches_dir)
    monkeypatch.setattr(editor_pipeline, "JOBS_DIR", jobs_dir)

    return {
        "jobs": jobs_dir,
        "trenches": trenches_dir,
        "matrices": matrices_dir,
    }


@pytest.fixture
def jobs_dir(storage_dirs):
    """The tmp jobs directory, with all storage roots already redirected."""
    return storage_dirs["jobs"]


@pytest.fixture
def app(storage_dirs):
    """The full application under test.

    Phase 1 moved the last twelve routes out of app.py and into blueprints, so
    ``create_app()`` now builds the application that actually ships. app.py is
    just an entry point.
    """
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()
