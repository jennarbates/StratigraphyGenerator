"""Shared test fixtures.

Import paths are configured in pyproject.toml under [tool.pytest.ini_options]
(``pythonpath``), which replaced the ``sys.path.insert`` block that used to be
copy-pasted into every test module.
"""

from pathlib import Path

import pytest

import storage
from backend import create_app

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


@pytest.fixture(autouse=True)
def storage_dirs(tmp_path, monkeypatch):
    """Redirect every on-disk storage root at a fresh tmp_path.

    One assignment per root reaches every consumer, because they all read
    ``storage.<ROOT>`` at call time rather than binding it at import. Before
    Phase 2 this took eight monkeypatches across five modules.

    Autouse: no test may write to the real ``poggio_webapp/jobs`` — a test that
    patched the wrong target used to pass while quietly writing into the
    developer's working tree, which is a worse failure than a red test.
    """
    for name in ("JOBS_DIR", "TRENCHES_DIR", "MATRICES_DIR"):
        directory = tmp_path / name.split("_")[0].lower()
        directory.mkdir()
        monkeypatch.setattr(storage, name, directory)

    return {
        "jobs": storage.JOBS_DIR,
        "trenches": storage.TRENCHES_DIR,
        "matrices": storage.MATRICES_DIR,
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
