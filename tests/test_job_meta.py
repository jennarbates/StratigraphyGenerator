"""The unified job-metadata contract in backend/jobs.py.

Before Phase 2 of MODULARIZATION_PLAN.md there were two implementations that
disagreed: ``load_meta``/``save_meta`` (keyed by job_id, tolerant of a missing
file, no timestamp) and ``read_meta``/``write_meta`` (keyed by directory,
raising, stamping ``updated_at``). These pin the single merged contract.
"""

import json

import pytest
from werkzeug.exceptions import NotFound

import storage
from backend import create_app
from backend.jobs import (
    load_meta,
    read_meta,
    save_meta,
    write_meta,
)


@pytest.fixture
def job(tmp_path):
    directory = storage.JOBS_DIR / "abcdef012345"
    directory.mkdir()
    return directory


@pytest.fixture
def app_ctx():
    """job_id-keyed reads abort(404), which needs a request context."""
    with create_app().test_request_context():
        yield


def test_read_meta_by_directory_raises_when_absent(job):
    with pytest.raises(FileNotFoundError):
        read_meta(job)


def test_read_meta_by_directory_returns_default_when_given_one(job):
    assert read_meta(job, {}) == {}
    assert read_meta(job, None) is None


def test_corrupt_meta_raises_without_a_default(job):
    (job / "meta.json").write_text("{not json")
    with pytest.raises(json.JSONDecodeError):
        read_meta(job)


def test_corrupt_meta_returns_the_default_when_given_one(job):
    """The listing routes scan every job directory; one damaged meta.json must
    not break the whole listing. This tolerance used to live in a third private
    copy in routes/trenches.py."""
    (job / "meta.json").write_text("{not json")
    assert read_meta(job, None) is None
    assert read_meta(job, {}) == {}


def test_write_then_read_round_trips(job):
    write_meta(job, {"job_id": "abcdef012345", "status": "editing"})
    assert read_meta(job)["status"] == "editing"


def test_write_meta_stamps_updated_at(job):
    write_meta(job, {"status": "editing"})
    assert "updated_at" in read_meta(job)


def test_write_meta_can_skip_the_stamp(job):
    write_meta(job, {"status": "editing"}, stamp=False)
    assert "updated_at" not in read_meta(job)


def test_save_meta_now_stamps_too(job, app_ctx):
    """Behaviour change: the extraction-flow writes previously left no
    updated_at, so those jobs always sorted on created_at in job_list."""
    save_meta("abcdef012345", {"job_id": "abcdef012345"})
    assert "updated_at" in json.loads((job / "meta.json").read_text())


def test_load_meta_is_tolerant_of_a_job_without_meta(job, app_ctx):
    assert load_meta("abcdef012345") == {}


def test_job_id_keyed_access_404s_for_an_unknown_job(app_ctx):
    with pytest.raises(NotFound):
        load_meta("nosuchjob0000")
