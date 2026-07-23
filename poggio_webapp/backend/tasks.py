"""In-memory execution of long-running tasks."""

import threading
import time
import traceback
import uuid

from .errors import _friendly_error

TASKS = {}


def start_task(fn, *args, **kwargs):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running", "result": None, "error": None, "log": [],
                       "started_at": time.time()}

    def runner():
        try:
            def log_cb(msg):
                TASKS[task_id]["log"].append(str(msg))
            if "progress_cb" in fn.__code__.co_varnames:
                kwargs["progress_cb"] = log_cb
            if "log_cb" in fn.__code__.co_varnames:
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
