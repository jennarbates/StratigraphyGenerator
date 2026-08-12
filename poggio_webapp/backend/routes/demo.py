"""Routes for seeding and removing the demonstration trenches.

Seeding only. Pressing Build is left to the operator on the trenches page,
because the pair of demonstrations exists to show that one trench refuses and
one builds -- and watching that happen is the demonstration. A button that
silently did the build too would show the result and hide the thing the result
is evidence for.

The seeder itself is fast enough to answer in the request: it writes four small
JSON files per trench and runs the normalizer over each. The *build* is the
slow part, and it already has the task machinery.
"""

from flask import Blueprint, abort, jsonify, request

from demo import datasets
from demo import seed as demo_seed

bp = Blueprint("demo", __name__)


def _seeded_trenches():
    """Which demo trenches currently exist, by scenario name.

    Read from the jobs on disk rather than from a flag written at seed time:
    the operator can delete a job directory, and a page that believed a stale
    flag would offer to open a trench that is no longer there.
    """
    import storage
    from backend.jobs import read_meta

    found = {}
    if not storage.JOBS_DIR.exists():
        return found
    for directory in sorted(storage.JOBS_DIR.iterdir()):
        if not directory.is_dir() or not directory.name.startswith(
            demo_seed.JOB_PREFIX
        ):
            continue
        meta = read_meta(directory, None)
        if not isinstance(meta, dict):
            continue
        marker = meta.get("demo")
        if not isinstance(marker, dict):
            continue
        scenario = marker.get("scenario")
        label = meta.get("trench_label")
        if scenario and label:
            found.setdefault(scenario, {"trench": label, "jobs": []})
            found[scenario]["jobs"].append(meta.get("job_id", directory.name))
    return found


@bp.route("/api/demo")
def describe_demo():
    """The scenarios, the record sets behind them, and what is already seeded."""
    available = datasets.discover()
    seeded = _seeded_trenches()
    return jsonify(
        {
            "scenarios": [
                {
                    "name": scenario.name,
                    "headline": scenario.headline,
                    "dataset": scenario.dataset_label,
                    # A scenario that draws walls cannot run on a real record set,
                    # so say up front whether this one can run at all rather than
                    # letting the operator find out from a 400.
                    "available": scenario.dataset_label in available
                    and not (
                        scenario.needs_walls
                        and available[scenario.dataset_label].real_records
                    ),
                    "seeded": seeded.get(scenario.name),
                }
                # Declaration order, not alphabetical. The pair tells a story --
                # the trench that refuses, then the same trench that builds -- and
                # sorting the names put 'complete' first, which reads as a demo
                # that works followed by one that is broken.
                for scenario in demo_seed.SCENARIOS.values()
            ],
            "datasets": [
                {
                    "label": dataset.label,
                    "season": dataset.season,
                    "provenance": dataset.provenance,
                    "real_records": dataset.real_records,
                }
                for dataset in sorted(available.values(), key=lambda d: d.label)
            ],
        }
    )


@bp.route("/api/demo/seed", methods=["POST"])
def seed_demo():
    body = request.get_json(force=True, silent=True) or {}
    scenario = body.get("scenario")
    if not isinstance(scenario, str) or not scenario.strip():
        abort(400, description='which scenario? Send {"scenario": "stops"}')
    try:
        summary = demo_seed.seed(scenario.strip(), dataset_label=body.get("dataset"))
    except demo_seed.DemoError as error:
        abort(400, description=str(error))
    return jsonify(summary)


@bp.route("/api/demo", methods=["DELETE"])
def remove_demo():
    """Remove every seeded demonstration trench.

    Scoped to the trench labels the scenarios use, so this cannot reach the
    operator's own work even if a job of theirs happens to be named like a
    demo one.
    """
    labels = {
        demo_seed.trench_label_for(scenario)
        for scenario in demo_seed.SCENARIOS.values()
    }
    # Plus whatever is actually on disk, which differs from the defaults when a
    # scenario was seeded against an overridden record set.
    labels.update(
        entry["trench"] for entry in _seeded_trenches().values() if entry.get("trench")
    )

    removed = []
    for label in sorted(labels):
        removed.extend(demo_seed.reset(label))
    return jsonify({"removed": removed})
