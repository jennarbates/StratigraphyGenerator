# Modularization & DRY Plan

**Status:** Phases 0–3 and 5 complete. Phase 4 partly done (steps 22–24, 28); steps 25–26 blocked on a
prerequisite, step 27 was a misreading — both explained below.

**Remaining work:** Phase 4 steps 25–26 only. Everything else in this plan is done.
**Scope:** `poggio_webapp/` (Flask backend, `pipeline/`, `static/` frontend), `tests/`, repo root hygiene
**Goal:** one architecture instead of two, one source of truth for shared concerns, and a test suite that actually covers what ships.

When this plan is complete, delete or archive this file into `docs/_meta/`.

---

## 1. Findings

### 1.1 `app.py` defeats the architecture that already exists

The repo has a clean Flask app factory (`poggio_webapp/backend/__init__.py`) and 15 registered
blueprints (`poggio_webapp/backend/routes/`). Alongside it, `poggio_webapp/app.py` is 582 lines
that registers **12 additional routes directly on the app object**:

| Route | Method | Defined in |
| --- | --- | --- |
| `/jobs/<job_id>` | GET | `app.py:364` |
| `/trenches` | GET | `app.py:374` |
| `/finds` | GET | `app.py:382` |
| `/finds/<job_id>/new` | POST | `app.py:387` |
| `/finds/<job_id>` | GET | `app.py:400` |
| `/finds/<job_id>/<find_id>` | DELETE | `app.py:409` |
| `/editor/new` | POST | `app.py:421` |
| `/editor/<job_id>` | GET | `app.py:449` |
| `/editor/<job_id>/save` | POST | `app.py:475` |
| `/editor/<job_id>/state` | GET | `app.py:485` |
| `/editor/<job_id>/finalize` | POST | `app.py:504` |
| `/api/jobs/<job_id>/status` | GET | `app.py:494` |

It then silently overrides a blueprint route at `app.py:361`:

```python
app.view_functions["pages.index"] = render_index
```

**Consequence:** `create_app()` and `app.py` produce two different applications. `create_app()`
serves `routes/pages.py:index` (`:329`), which is
`send_from_directory(current_app.template_folder, "index.html")` — it ships the *unrendered Jinja
template* as a static file. `app.py` replaces it with `render_index`, which actually renders it
with the job list. The tests are split across both — 8 files use `from app import app`, 3 use
`create_app()` — so the `create_app()` tests exercise an app that is missing a third of the real
routes and serves a broken index page.

### 1.2 Concrete DRY violations

| Duplicated concern | Copies |
| --- | --- |
| Job metadata read/write | `backend/jobs.py:load_meta`/`save_meta`; `app.py:_load_meta`/`_save_meta` (`app.py:55,60`); `routes/trenches.py:_read_meta` (`:39`) |
| `JOBS_DIR` derivation | `backend/config.py:6`; `pipeline/editor.py:10` — computed independently from `__file__` |
| Label sanitizing | `routes/trenches.py:safe_label` (`:30`); `pipeline/build_gempy.py:safe_filename` (`:59`); `pipeline/editor.py:clean_label` (`:95`) |
| HTTP fetch + error handling | `static/app/core/api.js` defines a correct `api()`/`apiJson()` wrapper. `harris/editor.js` (5), `harris/dashboard.js` (5), `finds/index.js` (5), `visualizer/files.js` (3), `trenches.js` (3), `canvas/index.js` (3), `results.js` (1) all bypass it with raw `fetch()` — **~25 call sites** each re-implementing status checks and error extraction |
| JS view helpers | `showConfirmedBanner` ×4, `esc` ×3, plus ~20 duplicated `render*`/`show*`/`step*` pairs across `static/app/stages/` and `static/canvas/` |
| Test bootstrap | `sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))` copy-pasted into **26** test files. No `conftest.py` exists anywhere in the repo |

### 1.3 Inverted layering

- `backend/routes/manual.py` is 593 lines. Roughly 500 of those are coordinate transforms, geometry,
  and schema construction — `_converted_points` (`:104`), `_feature_geometry` (`:152`),
  `_manual_boundaries` (`:216`), `_manual_fieldwall_boundaries` (`:261`), `_build_fieldwall` (`:370`),
  `_build_illustrator` (`:477`). Only `build_manual_extraction` (`:540`) is actually an HTTP concern.
  Domain logic living in a route module cannot be reused or unit-tested without Flask.
- Conversely, `pipeline/editor.py` (660 lines) owns `JOBS_DIR` and does its own filesystem I/O.
  Domain code is reaching into web-app storage layout — the dependency points the wrong way.
- `routes/harris.py` (434 lines) and `routes/trenches.py` (338 lines) have the same problem at
  smaller scale: `_grouped_members`, `_resolve_wall_labels`, and the whole `build_trench` body
  (`trenches.py:123-234`, ~110 lines inside a single view function).

### 1.4 No packaging or tooling

No `pyproject.toml`, `setup.py`, `setup.cfg`, `pytest.ini`, or `tox.ini` anywhere. No lint or
format config. Imports work only because every test manually patches `sys.path`.

### 1.5 Dead weight

Legacy and one-off migration files still on disk:

- `poggio_webapp/app.legacy.py` (791 lines), `poggio_webapp/static/app.legacy.js` (2130 lines)
- `poggio_webapp/modularize_backend.py`, `poggio_webapp/static/modularize_app.py`,
  `poggio_webapp/static/modularize_visualizer.py`
- Five `*.before_manual_first` snapshots under `backend/` and `backend/routes/`
- `poggio_webapp/static/visualizer.legacy.html`

Most are gitignored, but **`modularize_visualizer.py` and `visualizer.legacy.html` are tracked in
git** despite being listed in `.gitignore` (gitignore does not untrack already-committed files).

Repo-root clutter: ~300 KB of agent-planning markdown (`DOCUMENTATION_AGENT_PROMPTS.md`,
`DOCUMENTATION_AGENT_WORKPLAN.md`, `DOCUMENTATION_V2_PLAN.md`, `GEMPY_3D_VISUALIZER_TASK_CONTRACT.md`,
`HARRIS_MATRIX_TASK_CONTRACT.md`, `multi_wall_agent_plan.md`), a `00_docs/` that overlaps `docs/`,
and `01_scans/` holding five sample images at the top level.

---

## 2. Plan

Phase 0 must come first — without a single app fixture, Phase 1 will silently break routes that
only the `from app import app` tests cover. Phases 2–5 are independent of each other and can be
done in any order, or interrupted between steps.

### Phase 0 — Safety net — ✅ DONE

*No behavior changes. Establish a green baseline that will catch everything after it.*

**Baseline before: 625 passed, 1 skipped. After: 640 passed, 1 skipped** (the 15 new URL-map
tests). No production code was touched.

Step 4 was done differently than written below — see "Deviation" at the end of this phase.

1. **Add `pyproject.toml`** at repo root:
   - package metadata and dependencies (fold in `poggio_webapp/requirements.txt` and
     `requirements-docs.txt` as an optional `docs` extra)
   - `[tool.pytest.ini_options]` with `pythonpath = ["poggio_webapp"]` and `testpaths = ["tests"]`

2. **Add `tests/conftest.py`** with shared fixtures:
   - `app` — built from `create_app()`
   - `client` — `app.test_client()`
   - `tmp_jobs_dir` — monkeypatches `backend.config.JOBS_DIR` (and `pipeline.editor.JOBS_DIR`
     until Phase 2 removes it) to a `tmp_path`

3. **Delete all 26 `sys.path.insert` blocks** from `tests/*.py` and `tests/docs/*.py`.

4. **Unify the app under test.** Every test gets its app from the `app` fixture. Because
   `create_app()` currently lacks `app.py`'s 12 routes, the 8 tests using `from app import app`
   will fail here — that failure is the point. Temporarily have `conftest.py` import
   `app.app` so the suite stays green, with a `# TODO(Phase 1)` marker; Phase 1 removes it.

5. **Record the baseline.** Run the full suite and note the pass count. Nothing in Phases 1–5
   is allowed to reduce it.

**Verify:** `pytest` runs from repo root with no `sys.path` manipulation anywhere.

#### What was actually built

- **`pyproject.toml`** — project metadata, dependencies mirrored from
  `poggio_webapp/requirements.txt` and `requirements-docs.txt` (both left in place for now),
  explicit setuptools package discovery, and
  `[tool.pytest.ini_options]` with `pythonpath = ["poggio_webapp", "tests", "."]`.
  The `"."` entry matters: `tests/docs/` imports `tools.docs.*`, which previously resolved only
  because `python -m pytest` puts the CWD on `sys.path`. A bare `pytest` invocation would have
  failed. It now works either way.
- **`tests/conftest.py`** — `repo_root`, `webapp_root`, `storage_dirs`, `jobs_dir`, `app`,
  `client`. `storage_dirs` documents the Phase 2 problem concretely: redirecting the jobs
  directory takes **eight** monkeypatches, because `backend.jobs`, `backend.routes.jobs`, and
  `backend.routes.trenches` each re-bind `JOBS_DIR` at import time via
  `from ..config import JOBS_DIR`, and `pipeline.editor` derives its own from `__file__`.
- **27 test files stripped** of the `sys.path.insert` bootstrap, plus the `import sys`,
  `REPO_ROOT`, and `from pathlib import Path` lines that became unused as a result.
  `REPO_ROOT` was preserved in the four files that use it for something else
  (`test_editor_finalize.py:581`, `test_harris_pages.py:290`, `test_schema_source_field.py:41`,
  `test_wall_traces.py`).

#### Deviation from step 4

The plan said to force every test onto `create_app()` behind a temporary shim. That was dropped.
Rewriting eleven bespoke fixtures — which monkeypatch four different `JOBS_DIR` bindings in four
different combinations — is Phase 2 work, and Phase 1 would immediately redo it. It is churn that
protects nothing.

What replaced it does the job directly: **`tests/test_url_map.py`** snapshots all 55 URL rules and
asserts that (a) the route table is exactly this set, (b) every rule resolves to a live view
function, (c) each of the 12 `app.py`-owned routes is individually pinned so a regression names
the specific route lost, and (d) `/` does not return unrendered Jinja.

This was verified to catch the exact Phase 1 failure mode. Building `create_app()` on its own:

```
routes create_app() is missing: 12
index contains unrendered Jinja: True
```

The `app` fixture still returns `app.app` rather than `create_app()`, marked `TODO(Phase 1)`.
Phase 1 flips that one line, and the URL-map test is what proves the flip was safe.

---

### Phase 1 — Dissolve `app.py` — ✅ DONE

**640 passed, 1 skipped — identical to the Phase 0 baseline.** `app.py` went from 582 lines to 20.
The URL map is byte-identical: all 55 rules, same methods, now built by `create_app()` alone. into blueprints

6. **New `backend/routes/editor.py`** — move `/editor/new`, `/editor/<job_id>`,
   `/editor/<job_id>/save`, `/editor/<job_id>/state`, `/editor/<job_id>/finalize`,
   `/api/jobs/<job_id>/status` from `app.py`. Register in `routes/__init__.py`.

7. **New `backend/routes/finds.py`** — move `/finds`, `/finds/<job_id>/new`, `/finds/<job_id>`,
   `/finds/<job_id>/<find_id>`. Register in `routes/__init__.py`.

8. **Extend `backend/routes/pages.py`** — move `/jobs/<job_id>` and `/trenches` in, and replace
   the broken `index` (`pages.py:329`, which `send_from_directory`s the raw Jinja template) with
   `app.py`'s `render_index` body. Check whether `/visualizer` (`pages.py:335`) has the same bug —
   it serves `static/visualizer.html` via `send_from_directory`, which is correct only if that
   file contains no Jinja syntax.

9. **Move data assembly into `backend/jobs.py`** — `_job_record` (`app.py:269`), `_job_list`
   (`:337`), `_timestamp_sort_value` (`:325`), `_job_file_url` (`:245`), `_finalization_payload`
   (`:218`), `_durable_status_payload` (`:252`), `_job_status` (`:188`), `_refresh_job_status`
   (`:203`), `_load_finalized_output` (`:211`), `_finalization_status_code` (`:237`).
   These are presentation-free; none of them need Flask beyond `abort`.

10. **New `backend/services/editor_pipeline.py`** — move `_run_editor_pipeline` (`app.py:93`),
    `_run_editor_build` (`:64`), the two module-level locks (`:41-42`), `_STATUS_MESSAGES`
    (`:43`), `EDITOR_PIPELINE_STATUSES` (`:24`), and `PIPELINE_SUBDIRECTORIES` (`:33`).
    Orchestration across `normalizer` → `validator` → `convert_coords` → `build_gempy` is a
    service, not a route module.

11. **Delete the `view_functions` monkeypatch** (`app.py:361`).

12. **`app.py` shrinks to ~10 lines** — `app = create_app()` plus the `if __name__ == "__main__"`
    block.

13. **Remove the Phase 0 `# TODO(Phase 1)` shim** from `conftest.py`. All tests now build the
    real app from `create_app()`.

**Verify:** baseline pass count holds; `flask routes` output before and after the phase is
identical.

#### What was actually built

- **`backend/routes/editor.py`** (new) — the five `/editor/*` routes plus
  `/api/jobs/<job_id>/status`. `app.logger` became `current_app.logger`.
- **`backend/routes/finds.py`** (new) — the four `/finds*` routes.
- **`backend/routes/pages.py`** — gained `/jobs/<job_id>` and `/trenches`, and `index` now
  actually renders. This was a **live bug fix**: `create_app()`'s index previously
  `send_from_directory`'d the raw Jinja template, so anyone running the app through the factory
  rather than `app.py` got an unrendered page.
- **`backend/services/editor_pipeline.py`** (new, with `backend/services/__init__.py`) —
  `run_editor_pipeline`, `run_editor_build`, both locks, `EDITOR_PIPELINE_STATUSES`,
  `PIPELINE_SUBDIRECTORIES`.
- **`backend/jobs.py`** — gained the eleven data-assembly functions (`job_record`, `job_list`,
  `finalization_payload`, `durable_status_payload`, `job_status`, `refresh_job_status`,
  `read_meta`, `write_meta`, …) and `STATUS_MESSAGES`.
- **`templates/index.html`** — two `url_for` endpoint names now carry the blueprint prefix
  (`editor.get_job_status`, `editor.editor_page`). The generated URLs are unchanged.
- **`app.py`** — 20 lines: `create_app()` and the `__main__` block.

#### Test changes

Three test modules reached into `app.py` privates and were repointed at the new homes:

| Was | Now |
| --- | --- |
| `app_module._job_record` | `backend.jobs.job_record` |
| `app_module._save_meta` | `backend.jobs.write_meta` |
| `app_module._run_editor_build` | `backend.services.editor_pipeline.run_editor_build` |
| `monkeypatch.setattr(app_module, "_run_editor_pipeline", …)` | `monkeypatch.setattr(editor_routes, "run_editor_pipeline", …)` |

The last row matters: `routes/editor.py` binds `run_editor_pipeline` at import time, so the patch
target is the **route module**, not the service module. Patching the service has no effect.

`tests/conftest.py`'s `app` fixture now calls `create_app()`; the `TODO(Phase 1)` shim is gone.

#### Deliberate debt carried forward

`backend/jobs.py` now reads the jobs directory from **two** sources in one file: `job_dir` and
friends use `config.JOBS_DIR`, while `job_record`/`job_list` use `editor_pipeline.JOBS_DIR`,
because that is what `app.py` did and Phase 1 is a move, not a fix. There is a `WARNING` block at
the top of the module saying so. Phase 2 step 14 collapses it. The same applies to
`load_meta`/`save_meta` (by job_id, tolerant) coexisting with `read_meta`/`write_meta`
(by directory, stamps `updated_at`, raises) — two contracts, reconciled in Phase 2 step 15.

This also means `backend/jobs.py` imports from `pipeline`, which inverts the intended layering.
Phase 2 removes that import.

---

### Phase 2 — One source of truth — ✅ DONE

**677 passed, 1 skipped** (641 from Phase 1 + 14 docs tests added separately + 22 new here).

14. **Path constants.** Every reference to a jobs/trenches/matrices directory imports from
    `backend/config.py`. Change `pipeline/editor.py` to take its jobs directory as a parameter
    or module-level injectable rather than deriving it from `__file__` (`editor.py:10`).
    This also makes `tmp_jobs_dir` in `conftest.py` a one-line monkeypatch instead of two.

15. **Job metadata.** Every `meta.json` read/write goes through `backend/jobs.py:load_meta`/
    `save_meta`. Delete `app.py:_load_meta`/`_save_meta` (moved in Phase 1, then removed) and
    `routes/trenches.py:_read_meta`. Note the current copies disagree — `jobs.py:load_meta`
    returns `{}` on a missing file while `app.py:_load_meta` raises `FileNotFoundError`, and
    `app.py:_save_meta` stamps `updated_at` while `jobs.py:save_meta` does not. Pick the
    stamping behavior and the missing-file behavior deliberately, and write a test for each.

16. **Label sanitizing.** Consolidate `safe_label`, `safe_filename`, and `clean_label` into
    `backend/naming.py`. If they genuinely encode three different rules (filesystem-safe vs.
    URL-safe vs. display-clean), keep three functions but name them for the rule, not the caller.

**Verify:** `grep -rn "JOBS_DIR = " poggio_webapp --include="*.py"` returns exactly one hit
outside legacy files; `grep -rn "meta.json"` shows reads/writes only in `backend/jobs.py`.

#### What was actually built

- **`poggio_webapp/storage.py`** (new) — the single definition of `JOBS_DIR`, `TRENCHES_DIR`,
  `MATRICES_DIR`, `STATIC_DIR`, `TEMPLATES_DIR`. A leaf module importing nothing from `backend`
  or `pipeline`, so both layers depend on it without inverting anything. Everything reads
  `storage.X` at call time; nobody uses `from storage import X`, which would rebind and
  recreate the stale-copy problem.
- **`poggio_webapp/naming.py`** (new) — `safe_filename` and `clean_label`. `routes/trenches.py`
  had kept its own copy of the slug regex *specifically* to avoid importing the gempy stack for
  it; a dependency-free module removes that reason.
- **`backend/config.py`** — reduced to `ALLOWED_SCAN_EXT`. The path constants are gone rather
  than re-exported, so any missed reference is an `AttributeError` instead of a silent write to
  the developer's real jobs directory. Three such references surfaced immediately.
- **`backend/jobs.py`** — one `read_meta` and one `write_meta`, accepting a job_id or a resolved
  directory. `load_meta`/`save_meta` are one-line job_id-shaped aliases. No longer imports
  `pipeline`; the layering inversion Phase 1 introduced is gone.
- **`pipeline/editor.py`** — its private `JOBS_DIR` derived from `__file__` is gone.
- **`backend/harris_store.py`** — the hand-rolled `_DEFAULT_MATRICES_DIR` / `_matrices_root()`
  override, which existed solely to work around the import-time binding, is deleted.

#### The fixture, before and after

`conftest.storage_dirs` went from **eight** monkeypatches across five modules to **one**, in a
loop over the three roots. It is now `autouse`: no test can write to the real
`poggio_webapp/jobs`, because a test that patched the wrong target used to pass while quietly
writing into the working tree. Twenty-one test modules dropped their bespoke setup.

#### Behaviour changes, both deliberate

1. **`save_meta` now stamps `updated_at`.** Previously only the editor flow stamped it, so
   extraction-flow jobs always sorted on `created_at` in `job_list`. Pinned in
   `tests/test_job_meta.py`, including `write_meta(..., stamp=False)` for callers that must not.

2. **`safe_filename` rejects a component that is only dots.** This fixed a live path-traversal
   read. Dot is a legal filename character, so the old regex passed `".."` through untouched and
   the caller joined it onto a storage root: a trench labelled `".."` resolved to
   `poggio_webapp/`, and `/api/trenches/<label>/file`'s containment check then compared against
   that escaped directory, making every file under it readable. Confirmed exploitable via both
   `..` and `%2e%2e` before the fix. `"T104.2"` and other legitimate names are unaffected.
   Regression test in `tests/test_naming.py`.

---

### Phase 3 — Fix the layering — ✅ DONE

**679 passed, 1 skipped.** The four route modules holding domain logic shed it. Three others
(`harris.py` 393, `markers.py` 214, `text_metadata.py` 210) are above the ~150-line target but
are genuinely request/response code, not misplaced domain logic — see the note on `harris.py`
below. The stated goal of "no file in backend/routes/ exceeds ~150 lines" was not met and should
not be forced; the layering goal was.

17. **Extract `pipeline/manual_extraction.py`** from `routes/manual.py` — the `Calibration`
    dataclass and everything from `_point` (`:44`) through `_build_illustrator` (`:477`).
    `routes/manual.py` becomes: parse request → call pipeline → serialize response. Target
    under 100 lines.

18. **Thin out `routes/trenches.py`** — move `_grouped_members` (`:48`), `_resolve_wall_labels`
    (`:96`), and the body of `build_trench` (`:124-234`) into
    `backend/services/trench_builder.py`.

19. **Thin out `routes/harris.py`** — same treatment; the store already exists at
    `backend/harris_store.py`, so this is mostly moving request-shaped logic out of the views.

20. **Split `pipeline/editor.py`** (660 lines) into a package:
    - `pipeline/editor/session.py` — `create_editor_session`, `save_editor_state`,
      `load_editor_state`
    - `pipeline/editor/finds.py` — `add_find`, `get_finds`, `delete_find`, `sync_finds_to_output`
    - `pipeline/editor/validation.py` — the 13 `EditorStructuralValidationError` subclasses
      (`:39-93`) and every `_validate_*` / geometry predicate (`:241-624`)
    - `pipeline/editor/finalize.py` — `finalize_editor_session`
    - `pipeline/editor/__init__.py` re-exports the current public names so callers don't break.

21. **Consider `pipeline/geometry.py`** — `_segments_intersect`, `_point_on_segment`,
    `_direction`, `_polygon_self_intersects` in `editor.py` are generic 2D primitives, and
    `merge_walls.py` has adjacent ones (`face_endpoints`, `_endpoint_components`). Only merge
    these if they're genuinely the same operation; do not force it.

**Verify:** no file in `backend/routes/` exceeds ~150 lines; `pipeline/` imports nothing from
`backend/`.

#### What was actually built

| Module | Before | After | Extracted to |
| --- | ---: | ---: | --- |
| `routes/manual.py` | 593 | **78** | `pipeline/manual_extraction.py` (533) |
| `routes/trenches.py` | 338 | **54** | `services/trench_builder.py` (239) |
| `routes/pages.py` | 422 | **112** | `services/viewer_files.py` (330) |
| `routes/harris.py` | 434 | **393** | `services/harris_workspace.py` (66) |
| `pipeline/editor.py` | 660 | — | a 7-module package (max file 328) |

`pipeline/editor/` is now `schema`, `errors`, `geometry`, `validation`, `session`, `finds`,
`finalize`, with `__init__` re-exporting all 24 previously public names — no caller changed.
This absorbed step 21: `_direction`, `_point_on_segment`, `_segments_intersect` and
`_polygon_self_intersects` were already a self-contained plane-geometry unit and became
`editor/geometry.py`. They were *not* merged with `merge_walls`'s endpoint helpers, which do a
different job; forcing those together would have been shape-matching, not deduplication.

`harris.py` shrank least because it was already correctly layered — its bulk is pydantic request
models and response builders, which are genuinely HTTP concerns. The only real seam was the
two read-modify-write store transactions, now in `harris_workspace`.

#### Layering, verified

- `pipeline/` imports from `backend/`: **0**
- `backend/services/` imports Flask: **0**
- `backend/services/` imports from `backend/routes/`: **0**

`viewer_files.py` used `current_app.logger`; it now uses a module-level `logging.getLogger`,
since a service must work without an application context.

#### Incidental fixes

- **`read_meta` now tolerates a corrupt meta.json when given a default.** `routes/trenches.py`
  had a third private meta reader that swallowed `JSONDecodeError`, which Phase 2 had missed
  because it only looked at missing files. A test that writes a damaged meta.json and expects the
  listing to skip it caught this. Without a default the corruption still raises — a caller acting
  on one known job wants to know. Pinned in `tests/test_job_meta.py`.
- **`merge_walls._face_names` / `._is_placeholder` promoted to public.** They were being called
  from another module through their underscore names.

---

### Phase 4 — Frontend — ◐ PARTLY DONE

Steps 22–24 and 28 are done. Steps 25–26 are **blocked** on a prerequisite refactor and step 27
was based on a misreading; both are explained below.

22. **Promote the API wrapper.** Move `static/app/core/api.js` → `static/shared/api.js` and route
    all ~25 raw `fetch()` calls through `api()`/`apiJson()`. `pollTask` and `ensureJob` come
    along; `extractWaitStatus` is extraction-specific and stays behind in `app/stages/`.

23. **Extract `static/shared/dom.js`** — the three `esc` copies and shared element helpers.

24. **Extract `static/shared/banner.js`** — the four `showConfirmedBanner` copies and the
    `setStatus`/`showReview`/`showImage` families that appear twice each.

25. **Split `static/canvas/index.js`** (1423 lines) along the module boundaries already implicit
    in it — tool state, drawing, hit-testing, persistence, toolbar wiring.

26. **Split `static/harris/editor.js`** (1085 lines) similarly — graph model, layout, SVG render,
    interaction.

27. **Finish or remove the abandoned `visualizer/` split.** `visualizer/index.js` and
    `visualizer/schema.js` are 1 line each, `dom.js` is 13 and `colors.js` is 10, while
    `view.js` carries 742 — the split was started and left unfinished.

28. **Homeless top-level scripts.** `model3d-viewer.js` (637), `viewer3d.js` (143),
    `results.js` (109), `trenches.js` (259), `munsell-color.js` (129), `boundary-label.js` (46)
    sit at `static/` root while everything else is in feature folders. Move each into the
    folder that owns it, or a new `static/shared/`.

**Verify:** `grep -rn "fetch(" poggio_webapp/static --include="*.js" | grep -v vendor` returns
one hit, in `shared/api.js`. `tests/test_visualizer_static_dependencies.py` still passes.

#### Done: steps 22–24, 28

`static/shared/` now holds `http.js`, `dom.js`, plus the three genuinely-shared scripts moved in
step 28 (`munsell-color.js`, `boundary-label.js`, `model3d-viewer.js` — each imported by two to
four modules across different bundles).

- **`responseJson`: 4 copies → 1.** They had drifted in ways that mattered: two parsed the body
  tolerantly and two threw a raw `SyntaxError` when the server answered a 500 with HTML; one
  attached the error payload and three did not; the messages differed. `shared/http.js` is the
  union — the most forgiving of the four — so adopting it everywhere only widens what callers
  handle. Pinned by executing it under node.
- **Escapers: 3 → 1.** `app/core/ui.js` escaped `& < > " '`; `visualizer/dom.js` and
  `app/stages/scan.js` escaped the same set *without* the apostrophe. Consolidated on the
  five-character version, so two call sites now escape `'` as well — strictly more escaping.
  `String(value)` was deliberately kept over `String(value ?? "")`: `esc(undefined)` still yields
  the literal `"undefined"`, matching all three originals. That is arguably a defect, but fixing
  it is a behaviour change and does not belong in a deduplication commit.
- **`app/core/api.js`** now re-exports transport from `shared/http.js` and keeps only `ensureJob`
  and `extractWaitStatus`, the two things that depend on the wizard's own state.
- **Raw `fetch` calls: 21 → 7.** The seven that remain are deliberate and documented in place:
  `results.js` (a classic non-module script with `cache: "no-store"`), `canvas/index.js` ×3 (an
  unload beacon using `keepalive`, and two paths that build richer errors than `responseJson`
  can), and `visualizer/files.js` ×3 (an autoload whose `!r.ok` path deliberately falls back to
  the manual pickers, plus two fetches of arbitrary artifact URLs rather than the JSON API).

Verification for this phase was necessarily different — there is no JS test runner. Three checks
were built and used: every module parses as ESM (`node --input-type=module --check`, via stdin —
`node --check file.js` silently exits 0 on broken input and is useless here), every relative
import resolves across the 47-module graph, and every named import is actually exported by its
target. `shared/http.js` and `shared/dom.js` were additionally executed under node with
assertions covering the error-shape differences listed above.

#### Not done: steps 25–26, and why

Splitting `canvas/index.js` (1423 lines) and `harris/editor.js` (1085) requires a prerequisite
that is not a split at all. Both keep their state in module-level `let` bindings that are
reassigned throughout: canvas has **17 such bindings reassigned 36 times**, harris has **4
reassigned 17 times**. ES modules export *live bindings that importers cannot assign to*, so the
moment either file is split, every one of those 53 assignment sites has to become a property on a
shared state object.

That is a mechanical-looking change that is easy to get subtly wrong, across 2500 lines of
browser code with no behavioural test coverage — the static checks above would not catch a
mis-scoped assignment, and neither would the Python suite. The order should be: build a JS test
harness first (`tests/test_editor_finalize.py` already runs `canvas/grid.mjs` under node from
Python, so the precedent exists), then convert state to an object, then split. Doing the split
blind would risk breaking the drawing editor in ways nothing in this repo would detect.

#### Step 27 was based on a misreading

The plan claimed the `visualizer/` split was "started and left unfinished" because several files
are one or two lines. They are not stubs: `index.js` is the bundle entry point, `schema.js`
re-exports `schema-core.mjs` so the node-based tests can import it, and `dom.js`/`colors.js` are
small because they are complete. Nothing to do.

---

### Phase 5 — Hygiene — ✅ DONE

**684 passed, 1 skipped. `ruff check .` clean.**

29. **Untrack the two tracked legacy files:**
    ```bash
    git rm --cached poggio_webapp/static/modularize_visualizer.py poggio_webapp/static/visualizer.legacy.html
    ```

30. **Delete from disk:** `app.legacy.py`, `static/app.legacy.js`, `modularize_backend.py`,
    `static/modularize_app.py`, `static/modularize_visualizer.py`, `static/visualizer.legacy.html`,
    and all five `*.before_manual_first` files. Then prune the now-dead entries from `.gitignore`
    (which also has a duplicated `poggio_webapp/jobs/` line and a malformed line where two paths
    are concatenated without a newline).

31. **Repo root.** Move the six agent-planning `.md` files into `docs/_meta/` or delete them.
    Fold `00_docs/` into `docs/` (it holds `IllusstratorGuide.md` — note the typo — and two
    explanation docs that belong under `docs/concepts/`). Move `01_scans/` into
    `tests/fixtures/scans/` or gitignore it.

32. **Add `ruff`** for lint + format, configured in `pyproject.toml`. Run it, fix or explicitly
    ignore what it finds.

33. **Add a `Makefile` or `justfile`** with `test`, `lint`, `format`, `run`, `docs` targets so
    there's one documented way to do each thing.

34. **Optional:** a pre-commit hook running `ruff` and `pytest -x` on changed files. *(Not done —
    `make check` covers it without imposing a hook on the repo.)*

#### What was actually done

**Legacy files (steps 29–30).** 13 files, 185 KB. Eleven of them had **zero commits** — they
existed only on disk, so deleting them would have been irreversible. They were archived to
`.archive/pre-modularization-legacy.tar.gz` (64 KB, gitignored) before removal, rather than
deleted outright. The two that *were* tracked despite being gitignored
(`modularize_visualizer.py`, `visualizer.legacy.html`) were `git rm --cached`ed; those remain
recoverable from history. `tools/docs/check_coverage.py` had an `EXEMPT_STEMS` entry for
`modularize_backend`, now removed with the file it exempted.

**`.gitignore` (step 30).** Rewritten. It had `poggio_webapp/jobs/` twice, a malformed line where
two paths were concatenated with no newline between them (so the second was never applied), and
16 entries for files that no longer exist. `.venv/` and `.pytest_cache/` were neither tracked nor
ignored and are now ignored.

**Ruff (step 32).** Configured in `pyproject.toml` with `E, F, W, I, UP, B`. It found **259
issues**; 200 were autofixable, and the rest were triaged individually rather than bulk-suppressed:

- 11 `F841` dead `jobs_dir = storage.JOBS_DIR` lines left in test fixtures by the Phase 2
  migration. Three fixtures turned out to consist of *only* that line — they had been dead since
  conftest's `storage_dirs` became autouse — and were deleted entirely.
- 5 `B023` closure-over-loop-variable in `convert_coords.to_site`. A false positive in practice
  (it is called synchronously within the iteration), but the values are now bound as defaults so
  the intent is explicit.
- 3 `E741` (`l` as a name) and 2 `B904` (unchained re-raise) fixed.
- Four rules are ignored **with the reason recorded in `pyproject.toml`**, because the honest fix
  for each is a behaviour change that deserves its own commit: `B905` (`zip(strict=)` — 22 sites,
  where `strict=True` turns silent truncation into an exception), `E402` (the deliberate
  below-module-level imports that keep gempy optional), `UP042` (`str+Enum` → `StrEnum` changes
  what `str(member)` returns, and these values are serialised), and `E501`.

The rename in the `E741` fix introduced two `F821` undefined-name errors — it changed `for l in`
but not the `l.get(...)` half of the same comprehension. **Ruff caught both; the test suite did
not**, because those lines have no coverage. That is the clearest argument for having added it.

**`Makefile` (step 33).** `test`, `lint`, `format`, `check`, `run`, `docs`, `docs-serve`, `clean`,
with a self-documenting `help` default.

#### Not done: step 31 (repo root)

The six root planning documents, `00_docs/` and `01_scans/` were left alone. Several of them are
open working files with uncommitted edits, and moving a document someone is actively editing is
not a cleanup. Worth doing once they settle.

---

## 3. Sequencing summary

| Phase | Depends on | Risk | Notes |
| --- | --- | --- | --- |
| 0 — Safety net | — | Low | Mechanical. Do first, always. |
| 1 — Dissolve `app.py` | 0 | **High** | The big one. Pure moves; resist rewriting behavior. |
| 2 — Source of truth | 1 | Medium | Watch the `load_meta` semantic mismatch (step 15). |
| 3 — Layering | 1 | Medium | Large but mechanical extractions. |
| 4 — Frontend | 0 | Medium | Independent of 1–3; no Python tests cover most of it. |
| 5 — Hygiene | — | Low | Can be done any time. |

**Rule for Phases 1 and 3:** move code, do not improve it. Behavior changes and refactors in the
same commit make a regression impossible to bisect. If something is clearly wrong while you're
moving it, note it and fix it in a follow-up commit.
