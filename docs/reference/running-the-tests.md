---
title: Running the tests
audience: developer
status: current
source_files:
  - tests/test_merge_walls.py
  - tests/test_harris_schema.py
  - tests/docs/test_check_docs.py
  - tools/docs/check_docs.py
  - poggio_webapp/static/canvas/grid.test.mjs
verified_against: d23b842
---

# Running the tests

Three independent suites cover this repository: Python, JavaScript, and the
documentation checks. None of them requires GemPy, a Gemini API key, or network
access.

## The three commands

Python, from the repository root:

```bash
python -m pytest tests/ -q
```

JavaScript, using Node's built-in runner — **the glob must be quoted**, since
passing the directory alone fails to discover the files:

```bash
node --test "poggio_webapp/static/**/*.test.mjs"
```

Documentation:

```bash
python tools/docs/check_docs.py .
```

```bash
python tools/docs/check_coverage.py .
```

At `d23b842` these report 547 passed and 1 skipped, 74 passed, and two passing
documentation checks.

`check_coverage.py` reports any module under `poggio_webapp/pipeline/` or
`poggio_webapp/backend/` that no documentation page names by full path. It is a
coverage floor — it proves a module was named, not that it was explained.

## What each suite covers

### Python — `tests/`

37 modules. Grouped by area rather than filename:

| Area | Modules |
|---|---|
| Multi-wall trenches | `test_merge_walls`, `test_merge_integration`, `test_trench_routes`, `test_trench_labels` |
| Harris matrices | `test_harris_schema`, `test_harris_graph`, `test_harris_store`, `test_harris_import`, `test_harris_suggestions`, `test_harris_routes`, `test_harris_pages`, `test_harris_render` |
| Canvas editor | `test_editor_routes`, `test_editor_session`, `test_editor_finalize`, `test_editor_status` |
| Text extraction | `test_extract_text`, `test_extract_text_contract`, `test_text_metadata_routes`, `test_text_autofill_workflow`, `test_verified_text_manual_integration` |
| GemPy and visualizer | `test_gempy_mesh_export`, `test_gempy_viewer_manifest`, `test_gempy_volume_export`, `test_visualizer_files_route`, `test_visualizer_calibration_integration`, `test_visualizer_static_dependencies` |
| Tracing and boundaries | `test_manual_routes`, `test_locus_top_boundaries` |
| Finds | `test_finds`, `test_finds_routes` |
| Schema and validation | `test_validator`, `test_schema_source_field` |
| Markers | `test_markers_calibration` |

`tests/fixtures/` and `tests/fixtures_merge.py` supply shared inputs.

The densest coverage is the merge layer — 55 tests across its four modules —
because it is the part of the pipeline where a silent error produces a
plausible-looking wrong model rather than a crash.

### JavaScript — `poggio_webapp/static/`

17 files, colocated with the modules they test rather than gathered into a test
directory. They cover the pure functions the browser code depends on: grid and
coordinate maths, Munsell colour handling, boundary labelling, the Harris
schema core, the 3D surface and volume renderers, and view-mode policy.

Anything requiring a DOM is not tested here. The suites test extracted logic,
which is why they need no browser and no build step.

### Documentation — `tests/docs/`

`test_check_docs.py` and `test_generate_demo_assets.py` test the tooling in
`tools/docs/`, not the prose. The prose is checked by running the tool itself.

`check_docs.py` verifies four things across every page in `docs/` and the root
`README.md`: relative links resolve inside the repository, images have non-empty
alt text, nav pages carry the five required front-matter keys, and no page is
missing from the MkDocs navigation.

## Running a subset

One module:

```bash
python -m pytest tests/test_merge_walls.py -q
```

One test by name:

```bash
python -m pytest tests/ -k "placeholder" -q
```

One JavaScript file:

```bash
node --test poggio_webapp/static/canvas/grid.test.mjs
```

## Before a documentation change lands

Run all four. The strict build catches link problems the checker permits,
because MkDocs rejects links from `docs/` to files outside it:

```bash
python tools/docs/check_docs.py . && python tools/docs/check_coverage.py . && mkdocs build --strict && python -m pytest tests/docs -q
```

## What is not covered

Worth knowing before trusting a green run:

- **No end-to-end extraction test.** Gemini extraction requires a key and
  network access; `test_schema_source_field` covers output provenance, not the
  network call.
- **No upload, preprocessing, or normalizer test.** See
  [capability status](../project/capability-status.md), which records this per
  capability.
- **No browser-level test.** The JavaScript suites test extracted logic, so a
  wiring regression — a control that renders but calls nothing — passes.

That last gap is exactly how the canvas editor sat in a `blocked` state while
its routes and canvas tests all passed.

## Related

- [Capability status](../project/capability-status.md) — which tests back which
  capability.
- [Synthetic fixtures](../fixtures/README.md) — the sanitized inputs used by
  documentation tests.
