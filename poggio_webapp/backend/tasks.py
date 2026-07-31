"""In-memory execution of long-running tasks.

Task state does not survive a restart -- that is a documented limitation, not
an oversight. What this module does guarantee is that a server which stays up
does not grow without bound, and that submitting a callable it cannot
introspect fails at submission rather than inside the worker thread.
"""

import inspect
import threading
import time
import traceback
import uuid
from collections import OrderedDict

from .errors import _friendly_error

# A finished task holds its whole log, and a GemPy build logs steadily. Without
# a ceiling a long-lived server accumulates every line of every build it has
# ever run. Only finished tasks are evicted, oldest first, so a running build
# can never lose the record a poller is waiting on.
MAX_RETAINED_TASKS = 200

TASKS = OrderedDict()

# TASKS is read by request threads and written by worker threads. CPython makes
# each individual dict operation atomic, but eviction is a read-decide-delete
# sequence, which is not.
_TASKS_LOCK = threading.Lock()

_FINISHED = frozenset({"done", "error"})


def _accepts(fn, parameter_name):
    """True when ``fn`` declares a parameter with this name.

    ``inspect.signature`` rather than ``fn.__code__.co_varnames``: the code
    object exposes locals alongside parameters, so a function with a local
    variable called ``log_cb`` would have the callback injected as a keyword it
    never declared. It also has no ``__code__`` at all on a ``functools.partial``,
    a bound builtin, or a callable object, which turned an unsupported callable
    into a task that failed inside its own thread instead of at the call site.
    """
    try:
        return parameter_name in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def _evict_finished():
    """Drop the oldest finished tasks until the retention ceiling is met."""
    for task_id in list(TASKS):
        if len(TASKS) <= MAX_RETAINED_TASKS:
            return
        if TASKS[task_id]["status"] in _FINISHED:
            del TASKS[task_id]


def start_task(fn, *args, **kwargs):
    task_id = str(uuid.uuid4())
    accepts_progress = _accepts(fn, "progress_cb")
    accepts_log = _accepts(fn, "log_cb")

    with _TASKS_LOCK:
        TASKS[task_id] = {"status": "running", "result": None, "error": None,
                          "log": [], "started_at": time.time()}
        _evict_finished()

    def runner():
        try:
            def log_cb(msg):
                TASKS[task_id]["log"].append(str(msg))
            if accepts_progress:
                kwargs["progress_cb"] = log_cb
            if accepts_log:
                kwargs["log_cb"] = log_cb
            result = fn(*args, **kwargs)
            TASKS[task_id]["result"] = result
            TASKS[task_id]["status"] = "done"
        except Exception as e:
            TASKS[task_id]["error"] = _friendly_error(e)
            TASKS[task_id]["error_detail"] = f"{e}\n{traceback.format_exc()}"
            TASKS[task_id]["status"] = "error"

    threading.Thread(target=runner, daemon=True).start()
    return task_id
