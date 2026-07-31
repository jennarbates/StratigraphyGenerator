"""The job file route must not serve anything outside its own job directory.

Regression tests for a real escape: ``job_id`` arrives straight off the URL,
and a Flask string converter rejects a slash but not a dot, so
``/api/jobs/../file?path=storage.py`` resolved the base to ``poggio_webapp/``
and ``safe_job_path`` then measured containment against that already-escaped
base. Every application source file, and every other job's files, were
readable through one request.
"""

import pytest
from werkzeug.exceptions import NotFound

import storage
from backend.jobs import job_dir


@pytest.fixture
def job(jobs_dir):
    directory = jobs_dir / "0123456789ab"
    directory.mkdir()
    (directory / "meta.json").write_text('{"job_id": "0123456789ab"}')
    (directory / "inside.txt").write_text("legitimate job file")
    return directory


@pytest.mark.parametrize("job_id", ["..", ".", "../..", "a/b", ""])
def test_job_dir_refuses_ids_that_are_not_children(app, jobs_dir, job_id):
    (jobs_dir.parent / "outside.txt").write_text("must stay unreachable")
    with app.test_request_context():
        with pytest.raises(NotFound):
            job_dir(job_id)


def test_job_dir_accepts_a_real_job(app, job):
    with app.test_request_context():
        assert job_dir("0123456789ab") == job


@pytest.mark.parametrize(
    "url",
    [
        "/api/jobs/../file?path=outside.txt",
        "/api/jobs/%2e%2e/file?path=outside.txt",
        "/api/jobs/../file?path=0123456789ab/inside.txt",
        "/api/jobs/./file?path=outside.txt",
    ],
)
def test_file_route_refuses_to_escape_the_jobs_root(client, jobs_dir, job, url):
    (jobs_dir.parent / "outside.txt").write_text("must stay unreachable")
    assert client.get(url).status_code == 404


def test_file_route_still_serves_a_file_inside_the_job(client, job):
    response = client.get("/api/jobs/0123456789ab/file?path=inside.txt")
    assert response.status_code == 200
    assert response.data == b"legitimate job file"


def test_file_route_still_refuses_a_traversing_path_argument(client, job):
    response = client.get("/api/jobs/0123456789ab/file?path=../../storage.py")
    assert response.status_code == 400


def test_containment_holds_when_the_jobs_root_is_a_symlink(app, tmp_path, monkeypatch):
    """resolve() is applied to both sides, so a symlinked root is not an escape.

    The test fixtures already place the jobs root under a tmp path, which is
    itself behind a symlink on macOS; this pins that the check compares
    resolved paths rather than the strings it was handed.
    """
    real_root = tmp_path / "real_jobs"
    real_root.mkdir()
    (real_root / "0123456789ab").mkdir()
    linked_root = tmp_path / "linked_jobs"
    linked_root.symlink_to(real_root, target_is_directory=True)
    monkeypatch.setattr(storage, "JOBS_DIR", linked_root)

    with app.test_request_context():
        assert job_dir("0123456789ab").exists()
        with pytest.raises(NotFound):
            job_dir("..")
