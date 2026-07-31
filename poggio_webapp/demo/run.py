"""Drive a seeded demonstration through the build and report where it lands.

This is the half of the demonstration that shows the outcome. It posts nothing
and mocks nothing: it calls ``trench_builder.build`` with the registration the
seeder wrote, which is the same call the ``/api/trenches/<label>/build`` route
makes, so whatever happens here is what happens in the interface.

Four outcomes, and the first three are all successes of a kind:

  refused    the record cannot support a model, and the application says which
             wall and why. This is the ``stops`` demonstration succeeding.
  built      the model builder ran and the mesh is on disk.
  ready      every stage converted and only gempy itself is missing. The data
             went the whole way; the optional dependency is not installed.
  failed     the build started and something else went wrong.

``built`` and ``ready`` are only distinguishable after the build task finishes,
because gempy is imported inside the worker thread. ``build()`` returns a task
id either way, so a runner that stopped at the return value would report a
model that never appeared.
"""

import argparse
import json
import time
from pathlib import Path

import storage
from backend.services import trench_builder
from backend.tasks import TASKS
from naming import safe_filename

# gempy builds are slow but not unbounded, and a demo that hangs is worse than
# one that gives up. Reported as its own outcome rather than raising.
BUILD_TIMEOUT_S = 600.0
POLL_S = 0.5

_MISSING_GEMPY = ("no module named 'gempy'", "gempy import failed")


def registration(trench_label: str):
    """The grid config the seeder wrote for this trench."""
    path = (storage.TRENCHES_DIR / safe_filename(trench_label, "trench")
            / "grid_config.json")
    if not path.is_file():
        raise FileNotFoundError(
            f"no registration for trench {trench_label} -- seed it first")
    return json.loads(path.read_text())["grid"]


def run(trench_label: str) -> dict:
    """Build one seeded trench. Returns an outcome dict; never raises for a
    refusal, because a refusal is one of the things being demonstrated."""
    grid = registration(trench_label)
    try:
        result = trench_builder.build(trench_label, {"grid": grid})
    except trench_builder.GempyUnavailableError as error:
        return {
            "trench": trench_label,
            "outcome": "ready",
            "message": str(error),
        }
    except trench_builder.TrenchBuildError as error:
        return {
            "trench": trench_label,
            "outcome": "refused",
            "message": str(error),
        }

    outcome = {
        "trench": trench_label,
        "task_id": result.get("task_id"),
        "notes": result.get("notes") or [],
        "grid_warnings": result.get("grid_warnings") or [],
    }
    outcome.update(_await_build(result.get("task_id")))
    return outcome


def _await_build(task_id, timeout_s=BUILD_TIMEOUT_S):
    """Wait for the build task and classify how it ended."""
    if not task_id:
        return {"outcome": "failed", "message": "the build returned no task"}

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        task = TASKS.get(task_id)
        if task is None:
            return {"outcome": "failed", "message": "the build task vanished"}
        if task["status"] == "done":
            return {"outcome": "built", **_built_summary(task.get("result"))}
        if task["status"] == "error":
            error = str(task.get("error") or "")
            detail = str(task.get("error_detail") or "")
            if any(marker in (error + detail).lower()
                   for marker in _MISSING_GEMPY):
                return {
                    "outcome": "ready",
                    "message": (
                        "every stage before the mesh completed. gempy is an "
                        "optional extra and is not installed here -- install "
                        "it with `pip install gempy gempy_viewer` to finish "
                        "the last stage"
                    ),
                }
            return {"outcome": "failed", "message": error}
        time.sleep(POLL_S)

    return {
        "outcome": "failed",
        "message": f"the build did not finish within {timeout_s:.0f}s",
    }


def _built_summary(result):
    """What the build produced, in the terms someone watching a demo cares
    about. ``run_build`` returns absolute paths and numpy scalars; printing
    that dict whole buries the three facts worth reading."""
    if not isinstance(result, dict):
        return {"message": str(result or "")}

    outputs = result.get("outputs") or {}
    meshes = outputs.get("meshes") or []
    extent = [float(value) for value in (result.get("extent") or [])]

    message = f"{len(meshes)} surface mesh(es): " + ", ".join(
        Path(path).stem for path in meshes)
    if len(extent) == 6:
        message += (
            f"\n  extent {extent[0]:.1f}-{extent[1]:.1f} E, "
            f"{extent[2]:.1f}-{extent[3]:.1f} N, "
            f"{extent[4]:.2f}-{extent[5]:.2f} mAE")
    if result.get("series_order"):
        message += (
            f"\n  order {' over '.join(result['series_order'])}"
            f"  ({result.get('series_order_source', 'unknown')})")
    for label in ("model", "section", "viewer_manifest"):
        if outputs.get(label):
            message += f"\n  {label:<16}{outputs[label]}"
    return {"message": message}


def _format(outcome: dict) -> str:
    headline = {
        "refused": "REFUSED — the record does not support a model",
        "ready": "MODEL-READY — every stage converted; gempy is not installed",
        "built": "BUILT — the model is on disk",
        "failed": "FAILED — the build started and did not finish",
    }[outcome["outcome"]]
    lines = [f"{outcome['trench']}: {headline}", ""]
    if outcome.get("message"):
        lines.append(f"  {outcome['message']}")
    for note in outcome.get("notes") or []:
        lines.append(f"  - {note}")
    for warning in outcome.get("grid_warnings") or []:
        lines.append(f"  ! {warning}")
    if outcome.get("task_id"):
        lines.append(f"  task {outcome['task_id']}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m demo.run",
        description="Build a seeded demonstration trench and report the outcome.")
    parser.add_argument("trench", help="trench label, e.g. T905")
    args = parser.parse_args(argv)
    print(_format(run(args.trench)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
