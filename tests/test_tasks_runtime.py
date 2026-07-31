"""Task submission introspects callables safely and retains a bounded history."""

import functools
import time

import pytest

from backend import tasks


@pytest.fixture(autouse=True)
def empty_task_table():
    tasks.TASKS.clear()
    yield
    tasks.TASKS.clear()


def _settle(task_id, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if tasks.TASKS[task_id]["status"] != "running":
            return tasks.TASKS[task_id]
        time.sleep(0.01)
    raise AssertionError("task did not finish")


def test_progress_callback_is_injected_when_declared():
    def work(progress_cb=None):
        progress_cb("halfway")
        return "done"

    task = _settle(tasks.start_task(work))
    assert task["status"] == "done"
    assert task["log"] == ["halfway"]


def test_a_local_variable_is_not_mistaken_for_a_parameter():
    """co_varnames included locals, so this function used to be handed a
    keyword argument it never declared, and died with a TypeError."""
    def work():
        log_cb = "an ordinary local"
        return log_cb

    task = _settle(tasks.start_task(work))
    assert task["status"] == "done"
    assert task["result"] == "an ordinary local"


def test_a_partial_is_accepted_rather_than_failing_inside_the_thread():
    def work(first, second):
        return first + second

    task = _settle(tasks.start_task(functools.partial(work, 1), 2))
    assert task["status"] == "done"
    assert task["result"] == 3


def test_a_callable_object_without_a_code_object_is_accepted():
    class Work:
        def __call__(self, log_cb=None):
            log_cb("from a callable object")
            return "ok"

    task = _settle(tasks.start_task(Work()))
    assert task["status"] == "done"
    assert task["log"] == ["from a callable object"]


def test_finished_tasks_are_evicted_oldest_first(monkeypatch):
    monkeypatch.setattr(tasks, "MAX_RETAINED_TASKS", 3)
    finished = [tasks.start_task(lambda: None) for _ in range(3)]
    for task_id in finished:
        _settle(task_id)

    newest = tasks.start_task(lambda: None)
    _settle(newest)

    assert len(tasks.TASKS) <= 3
    assert newest in tasks.TASKS
    assert finished[0] not in tasks.TASKS


def test_a_running_task_is_never_evicted(monkeypatch):
    monkeypatch.setattr(tasks, "MAX_RETAINED_TASKS", 1)
    release = []

    def blocked():
        while not release:
            time.sleep(0.005)

    running = tasks.start_task(blocked)
    for _ in range(4):
        _settle(tasks.start_task(lambda: None))

    assert running in tasks.TASKS
    assert tasks.TASKS[running]["status"] == "running"
    release.append(True)
    _settle(running)
