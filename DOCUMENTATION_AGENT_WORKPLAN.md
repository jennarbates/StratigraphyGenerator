# Interactive Documentation: Agent Work Plan

This document divides the documentation project into small tasks that can be
given to an AI agent one at a time. It assumes the agent needs explicit scope,
inputs, outputs, tests, and stop conditions.

For ready-to-copy chat prompts, use
[`DOCUMENTATION_AGENT_PROMPTS.md`](DOCUMENTATION_AGENT_PROMPTS.md). It contains
one fenced prompt for each chunk, so the coordinator never needs to combine
instructions manually.

Do not give an agent the entire project at once. Give it:

1. the **Global task contract** below;
2. exactly one numbered chunk;
3. the final report format; and
4. no permission to continue into the next chunk.

Each chunk should be completed, reviewed, and merged before the next chunk
starts.

## Global task contract

Copy this section into every agent assignment.

### Authority and scope

- Complete only the assigned chunk.
- Edit only the files in that chunk's **Files you may edit** list.
- Files listed as read-only may be inspected but must not be changed.
- Do not modify application behavior to make the documentation easier to
  write.
- Do not fix unrelated bugs, rename unrelated files, reformat unrelated code,
  update dependencies outside the allow-list, or continue into a later chunk.
- Do not commit, push, deploy, change repository settings, or publish anything
  unless the chunk explicitly authorizes that action.
- Existing uncommitted changes belong to the user. Record them before starting
  and do not overwrite, revert, stage, or reformat them.
- Never use destructive Git commands such as `git reset --hard`,
  `git checkout --`, or `git clean`.

### Required preflight

Run these from the repository root before editing:

```bash
pwd
git status --short
git rev-parse --short HEAD
```

Then verify that every intended output file is in the chunk's edit allow-list.
If a necessary file is not in the allow-list, stop and report the missing
permission. Do not silently expand scope.

### Sources of truth

Use sources in this order:

1. Current executable code.
2. Tests that pass against the current code.
3. Current UI text and behavior.
4. Existing documentation.
5. Git history, only when explaining historical behavior.

If code and documentation disagree, document the code's current behavior and
record the stale statement in the capability audit. Do not change the code
unless the assigned chunk explicitly allows it.

Do not describe a backend route as a user-facing feature unless it is actually
reachable from the current UI. Use precise status labels:

- `supported`
- `experimental`
- `backend-only`
- `blocked`
- `historical`

### Documentation writing rules

- Write for a reader with little experience in codebases.
- Define a term before using it.
- Use plain-language headings and short paragraphs.
- Put essential user actions before implementation detail.
- Put code/module details in an **Under the hood** section.
- Prefer one page with one purpose over one very long page.
- Link a concept at its first important use; do not link every repetition.
- Never present placeholder survey coordinates or synthetic geometry as
  scientifically verified.
- Label synthetic examples as `Synthetic documentation example`.
- Do not expose API keys, private job data, personal data, precise sensitive
  site coordinates, or unapproved scans.
- Every meaningful image must have useful alt text and a caption.
- Do not rely on color alone to communicate accepted/rejected, safe/unsafe, or
  pass/fail states.

### Standard page contract

Every new Markdown page, unless its chunk says otherwise, must start with:

```yaml
---
title: Human-readable page title
audience: beginner | operator | developer
status: current | experimental | historical
source_files:
  - relative/path/to/source.py
verified_against: SHORT_GIT_COMMIT
---
```

Workflow pages must use these sections in this order:

1. `# Page title`
2. One-sentence outcome
3. `## Before you start`
4. `## Do this`
5. `## What the application creates`
6. `## Check your result`
7. `## Common problems`
8. `## Under the hood`
9. `## Next`

Concept pages must use:

1. `# Page title`
2. Plain-language definition
3. `## Why it matters here`
4. `## Example`
5. `## How the repository represents it`
6. `## Related concepts`

### Standard validation after every editing chunk

Run every command that is available at that point in the plan:

```bash
git diff --check
./.venv/bin/python -m pytest -q
node --test tests/docs/*.test.mjs
./.venv/bin/python -m mkdocs build --strict
./.venv/bin/python tools/docs/check_docs.py
./.venv/bin/python tools/docs/validate_visual_manifest.py
```

If a command cannot run because an earlier dependency has not been installed,
report it as `NOT RUN` with the exact reason. Do not report it as passed.

Also inspect:

```bash
git status --short
git diff --name-only
```

Confirm that the agent changed only allow-listed files. Pre-existing user
changes may still appear; identify them as pre-existing and do not claim them.

### Failure and stop conditions

Stop without making further changes when:

- a dependency chunk has not been merged;
- an allow-listed file already contains overlapping user changes;
- a required feature's current status cannot be determined from code or tests;
- a visual would require publishing unapproved source material;
- a test fails outside the chunk and the failure was present before editing;
- completing the task would require changing an application file;
- required documentation dependencies cannot be installed or imported; or
- Git shows a merge conflict.

Report the blocker, evidence, and smallest permission or decision needed.

### Required final report

Use exactly this structure:

```text
Outcome:
- One or two sentences.

Files changed:
- path: what changed

Tests:
- PASS: exact command
- FAIL: exact command — short failure
- NOT RUN: exact command — reason

Scope check:
- Confirm no files outside the allow-list were changed by this task.
- List pre-existing unrelated modified files separately.

Open issues:
- None
```

## Testing strategy across chunks

There are four kinds of tests in this project:

1. **Application regression tests** — existing `pytest` tests must continue to
   pass after every chunk. Documentation work must not change those tests.
2. **Documentation structure unit tests** — introduced in Chunk 2 for links,
   images, front matter, and navigation.
3. **Fixture and asset unit tests** — introduced in Chunks 5 and 14 for
   deterministic, sanitized examples and screenshot metadata.
4. **Interactive documentation unit tests** — introduced in Chunk 15 using
   Node's built-in test runner for pure JavaScript logic.

Required review gates:

| Gate | Run after | Reviewer checks |
|---|---|---|
| A | Chunk 4 | Site builds, existing documentation migrated, no lost content |
| B | Chunk 9 | A beginner can follow the complete operator workflow |
| C | Chunk 14 | Visuals are accurate, legible, reproducible, and safe to publish |
| D | Chunk 18 | All links/builds/tests pass and novice review is recorded |

Do not start the next gate's work until the previous gate is approved.

### Chunk map

| Chunk | Focus | Main verification |
|---|---|---|
| 0 | Record the untouched baseline | Existing tests |
| 1 | MkDocs scaffold | Strict MkDocs build |
| 2 | Documentation checker | Checker unit tests |
| 3 | Current capability audit | Human status review |
| 4 | Migrate existing public docs | Review Gate A |
| 5 | Synthetic fixtures | Schema and determinism tests |
| 6 | Beginner entry path | Build, links, glossary review |
| 7 | Upload/preprocess/manual tracing | Manual-path walkthrough |
| 8 | Alternatives/cleanup/validation | Status and warning review |
| 9 | Registration/model/view/finds | Review Gate B |
| 10 | Conceptual learning layer | Beginner-language review |
| 11 | Architecture | Source-to-doc traceability |
| 12 | Developer reference | Signature/default audit |
| 13 | Deterministic diagrams | Visual manifest review |
| 14 | Screenshot tooling/assets | Review Gate C |
| 15 | Interactive labs | Node unit tests |
| 16 | Root README | GitHub link check |
| 17 | CI and deployment preparation | Local CI command parity |
| 18 | Final audit and novice packet | Review Gate D |

---

## Chunk 0 — Establish the baseline

**Objective** — Prove the starting repository state without changing any
files.

**Depends on** — Nothing.

**Files you may edit** — None.

**Files you may read but not edit** — Entire repository.

**Deliverables**

- A final report containing:
  - current short commit;
  - all pre-existing modified/untracked files;
  - Python version;
  - Node version, if Node exists;
  - baseline application test result;
  - whether MkDocs is already installed.

**Explicit non-goals**

- Do not install packages.
- Do not create documentation.
- Do not fix failing tests.
- Do not stage or commit files.

**Inputs/outputs contract**

- Input: current repository working tree.
- Output: report only; zero filesystem changes.
- Baseline commands:

```bash
git status --short
git rev-parse --short HEAD
./.venv/bin/python --version
node --version
./.venv/bin/python -m pytest -q
./.venv/bin/python -m mkdocs --version
```

**Tests to write** — None.

**Definition of Done**

- [ ] The baseline test count and result are recorded.
- [ ] Pre-existing changes are listed.
- [ ] No file was changed.
- [ ] The report clearly distinguishes `PASS`, `FAIL`, and `NOT RUN`.

---

## Chunk 1 — Create the documentation site scaffold

**Objective** — Create the smallest MkDocs Material site that builds
successfully and provides stable navigation placeholders.

**Depends on** — Chunk 0.

**Files you may edit**

- `mkdocs.yml`
- `requirements-docs.txt`
- `.gitignore`
- `docs/index.md`
- `docs/assets/stylesheets/extra.css`
- `docs/_meta/page-template.md`

**Files you may read but not edit**

- `README.md`
- `poggio_webapp/README.md`
- `00_docs/**`
- `poggio_webapp/static/style.css`

**Deliverables**

- `requirements-docs.txt` with explicitly pinned documentation-only
  dependencies.
- `mkdocs.yml` with:
  - Material theme;
  - search;
  - Mermaid support;
  - content tabs;
  - annotations;
  - `extra.css`;
  - a minimal nav containing only pages that exist.
- A minimal `docs/index.md` explaining that the full guide is being built.
- A reusable page template containing the required front matter and section
  structures.
- Ignore only the generated `site/` directory in `.gitignore`.

**Explicit non-goals**

- Do not rewrite the root README.
- Do not migrate old documentation.
- Do not add screenshots or JavaScript.
- Do not edit application CSS to make the docs theme match.

**Inputs/outputs contract**

- Input: repository name and current visual tokens from
  `poggio_webapp/static/style.css`.
- Output: `./.venv/bin/python -m mkdocs build --strict` produces `site/`.
- `docs/index.md` must not link to nonexistent pages.

**Tests to write** — None in this chunk.

**Definition of Done**

- [ ] Documentation dependencies install from `requirements-docs.txt`.
- [ ] `mkdocs build --strict` passes.
- [ ] `site/` is ignored and untracked.
- [ ] No application file changed.
- [ ] Navigation contains no placeholder links.

---

## Chunk 2 — Add documentation validation tooling and unit tests

**Objective** — Add a small, deterministic checker that prevents broken
internal links, missing images, malformed page metadata, and orphaned pages.

**Depends on** — Chunk 1.

**Files you may edit**

- `tools/docs/check_docs.py`
- `tests/docs/test_check_docs.py`
- `tests/docs/__init__.py`
- `requirements-docs.txt`

**Files you may read but not edit**

- `mkdocs.yml`
- `docs/**`
- Existing tests.

**Deliverables**

Implement these public Python interfaces:

```python
@dataclass(frozen=True)
class Issue:
    path: Path
    message: str

def iter_markdown_files(docs_dir: Path) -> list[Path]: ...

def load_nav_paths(config_path: Path, docs_dir: Path) -> set[Path]: ...

def find_broken_relative_links(
    markdown_path: Path,
    docs_dir: Path,
    repo_root: Path,
) -> list[Issue]: ...

def find_missing_image_alt_text(markdown_path: Path) -> list[Issue]: ...

def validate_front_matter(markdown_path: Path) -> list[Issue]: ...

def find_orphan_pages(
    docs_dir: Path,
    nav_paths: set[Path],
) -> list[Issue]: ...

def run_checks(repo_root: Path) -> list[Issue]: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

Rules:

- Ignore `http:`, `https:`, `mailto:`, and same-page `#anchor` links.
- Resolve Markdown and image paths relative to the containing page.
- Permit repository-relative links that intentionally leave `docs/`.
- Run link and image checks on the root `README.md` when it exists, but do not
  require docs front matter or MkDocs navigation membership for it.
- Ignore files under `docs/_meta/` when finding orphan pages.
- Require `title`, `audience`, `status`, `source_files`, and
  `verified_against` front matter on navigable pages.
- Print one issue per line and exit `1` when issues exist; otherwise exit `0`.

**Explicit non-goals**

- Do not build a full Markdown parser.
- Do not make network requests.
- Do not validate external URLs.
- Do not edit documentation to hide checker failures outside this chunk.
- Do not modify existing application tests.

**Inputs/outputs contract**

Example:

```python
issues = run_checks(Path("/repo"))
assert all(isinstance(issue, Issue) for issue in issues)
```

CLI:

```bash
./.venv/bin/python tools/docs/check_docs.py
```

Success produces a short success message and exit code `0`.

**Tests to write**

- Markdown discovery excludes `_meta`.
- A valid relative Markdown link passes.
- A missing Markdown link fails.
- A valid relative image passes.
- A missing relative image fails.
- External URLs are ignored.
- Same-page anchors are ignored.
- An image with empty alt text fails.
- Complete front matter passes.
- Each missing required front-matter key fails with a useful message.
- A page absent from nav is reported as orphaned.
- A page present in nav is not reported.
- `main()` returns `0` for a clean temporary repository.
- `main()` returns `1` when an issue exists.

**Definition of Done**

- [ ] All listed unit tests exist and pass.
- [ ] The checker passes on the current scaffold.
- [ ] Existing application tests still pass.
- [ ] No application code or existing tests changed.

---

## Chunk 3 — Create the current capability audit

**Objective** — Establish a single, code-backed record of what the repository
currently supports and what remains incomplete.

**Depends on** — Chunks 1–2.

**Files you may edit**

- `docs/project/capability-status.md`
- `docs/_meta/source-map.yml`
- `mkdocs.yml`

**Files you may read but not edit**

- `README.md`
- `poggio_webapp/README.md`
- `00_docs/**`
- `poggio_webapp/app.py`
- `poggio_webapp/backend/**`
- `poggio_webapp/pipeline/**`
- `poggio_webapp/static/**`
- `poggio_webapp/templates/**`
- `tests/**`

**Deliverables**

- A capability table covering:
  - upload;
  - preprocessing;
  - manual tracing;
  - multi-face canvas/editor;
  - imported JSON;
  - AI extraction;
  - marker detection and assignment;
  - feature detection;
  - normalization;
  - validation;
  - survey registration;
  - coordinate conversion;
  - GemPy build;
  - visualizer;
  - finds;
  - jobs and asynchronous tasks.
- For every capability include:
  - status label;
  - user entry point, or `none`;
  - backend source;
  - frontend source;
  - relevant tests;
  - known limitation.
- `docs/_meta/source-map.yml` mapping each planned public page to source files.
- Add only the completed capability page to MkDocs navigation.

**Explicit non-goals**

- Do not fix stale documentation yet.
- Do not fix application bugs discovered during the audit.
- Do not claim backend-only features are accessible in the UI.
- Do not add roadmap promises.

**Inputs/outputs contract**

Each `source-map.yml` item must have:

```yaml
- page: project/capability-status.md
  sources:
    - poggio_webapp/static/app/index.js
    - poggio_webapp/backend/routes/__init__.py
  purpose: Current user-facing and backend capability matrix
```

**Tests to write** — None.

**Definition of Done**

- [ ] Every listed capability has a code citation.
- [ ] Stale README claims are called out neutrally.
- [ ] The page passes the docs checker.
- [ ] Strict site build and application tests pass.
- [ ] Human Review Gate: statuses are approved before continuing.

---

## Chunk 4 — Migrate and repair the existing public documentation

**Objective** — Move the existing useful public docs into the new structure
without losing content or publishing internal agent notes.

**Depends on** — Chunk 3.

**Files you may edit**

- `00_docs/IllusstratorGuide.md`
- `00_docs/Explanations/GeometricNormalization.md`
- `00_docs/Explanations/MarkersVsFeatures.md`
- `00_docs/deskew_visualization.png`
- `docs/reference/drawing-guidelines.md`
- `docs/concepts/geometric-normalization.md`
- `docs/concepts/markers-features-and-finds.md`
- `docs/assets/diagrams/deskew-visualization.png`
- `mkdocs.yml`

**Files you may read but not edit**

- `00_docs/CLAUDE.md`
- Relevant pipeline and route files.
- Capability audit.

**Deliverables**

- Preserve history with file moves where practical.
- Correct the `IllusstratorGuide` filename typo in the new location.
- Add required front matter.
- Repair internal links and image paths.
- Update obviously stale status statements using the approved capability
  audit.
- Extend the marker/feature explanation with a short, accurate definition of
  a `find`, using current editor/finds code.
- Leave small compatibility stub pages at the old Markdown paths that point to
  the new locations.
- Do not migrate `00_docs/CLAUDE.md` into public navigation.

**Explicit non-goals**

- Do not substantially rewrite the algorithms.
- Do not add new visuals.
- Do not modify `CLAUDE.md`.
- Do not change pipeline code.

**Inputs/outputs contract**

- Old links land on a stub with exactly one sentence and one relative link.
- New pages comply with the standard concept/reference page contract.
- The deskew image resolves in both MkDocs and repository Markdown.

**Tests to write** — None.

**Definition of Done**

- [ ] All original public information remains available.
- [ ] New filenames and links are correct.
- [ ] Stale availability statements match the capability audit.
- [ ] Docs checker, strict build, and application tests pass.
- [ ] Human Review Gate A is approved.

---

## Chunk 5 — Create sanitized, deterministic documentation fixtures

**Objective** — Provide small synthetic example drawings and schema-valid JSON
that can safely appear in tutorials, tests, and screenshots.

**Depends on** — Chunk 4.

**Files you may edit**

- `tools/docs/generate_demo_assets.py`
- `tests/docs/test_generate_demo_assets.py`
- `docs/fixtures/demo-fieldwall.json`
- `docs/fixtures/demo-illustrator.json`
- `docs/assets/source/demo-fieldwall.png`
- `docs/assets/source/demo-illustrator.png`
- `docs/fixtures/README.md`
- `mkdocs.yml`

**Files you may read but not edit**

- `poggio_webapp/pipeline/extract_fieldwall.py`
- `poggio_webapp/pipeline/extract_illustrator.py`
- `poggio_webapp/pipeline/validator.py`
- Existing repository scans.

**Deliverables**

Implement:

```python
def build_fieldwall_fixture() -> dict: ...

def build_illustrator_fixture() -> dict: ...

def render_fieldwall_image(data: dict, output_path: Path) -> None: ...

def render_illustrator_image(data: dict, output_path: Path) -> None: ...

def write_demo_assets(output_root: Path) -> list[Path]: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

Fixture requirements:

- Clearly label both examples `Synthetic documentation example`.
- Use invented trench/face labels and non-site coordinates.
- Include at least two layers/loci.
- Include one internal feature.
- Use irregular boundary spacing so the example does not accidentally teach
  fabricated uniform sampling.
- Contain no real people, API keys, job IDs, or site coordinates.
- Be small enough for fast test and documentation builds.
- Running the generator twice must produce byte-identical JSON and images.
- Add `docs/fixtures/README.md` to navigation under a clearly labeled
  `Synthetic fixtures` reference entry so it is not orphaned.

**Explicit non-goals**

- Do not copy or modify real archaeological scans.
- Do not create a scientifically interpreted reconstruction.
- Do not create GemPy outputs.
- Do not add screenshots.
- Do not change schemas to make the fixtures pass.

**Inputs/outputs contract**

```bash
./.venv/bin/python tools/docs/generate_demo_assets.py
```

must rewrite the four generated assets deterministically and exit `0`.

Both JSON fixtures must validate against the current Pydantic models and pass
the repository validator without errors. Warnings are permitted only when
explicitly documented in the fixture README.

**Tests to write**

- Field-wall fixture validates against `FieldWallProfile`.
- Illustrator fixture validates against `ArchaeologicalDiagram`.
- Both fixtures produce zero validator errors.
- Both include two or more layers/loci.
- Both include one feature.
- Generator output is byte-identical across two temporary directories.
- Images have expected format and nonzero dimensions.
- Fixture text contains the synthetic-example label.
- Fixture values do not contain known real trench names from `01_scans`.

**Definition of Done**

- [ ] Generator and all specified tests pass.
- [ ] Generated assets are small and readable.
- [ ] Fixture README explains that the examples are synthetic.
- [ ] No real scan or job artifact was changed.
- [ ] Full test/build/check suite passes.

---

## Chunk 6 — Write the beginner entry path

**Objective** — Give a first-time reader enough context to choose a workflow,
start the app, and understand the vocabulary.

**Depends on** — Chunk 5.

**Files you may edit**

- `docs/start-here/what-this-project-does.md`
- `docs/start-here/choose-your-path.md`
- `docs/start-here/quickstart.md`
- `docs/start-here/glossary.md`
- `docs/index.md`
- `mkdocs.yml`

**Files you may read but not edit**

- Capability audit.
- Demo fixture README.
- Existing READMEs.
- Current requirements and app entry point.
- Current frontend step definitions.

**Deliverables**

- A homepage with three clear paths:
  - use the app;
  - understand the system;
  - develop the project.
- A plain-language project explanation.
- A workflow chooser for:
  - manual tracing;
  - importing JSON;
  - AI-assisted extraction;
  - field-sheet marker workflows, labeled with current status.
- A minimal setup/launch quickstart.
- A glossary defining at minimum:
  - trench profile;
  - face;
  - layer;
  - locus;
  - boundary;
  - marker;
  - feature;
  - find;
  - calibration;
  - normalization;
  - validation;
  - grid registration;
  - interface point;
  - orientation seed;
  - GemPy;
  - job.

**Explicit non-goals**

- Do not write the detailed stage tutorials.
- Do not document API routes.
- Do not promise unsupported operating systems.
- Do not install GemPy as part of quickstart.

**Inputs/outputs contract**

- A reader must reach a runnable `python app.py` command within two clicks
  from `docs/index.md`.
- The quickstart must distinguish core dependencies from optional GemPy and
  PDF dependencies.
- Every status-sensitive choice links to the capability audit.

**Tests to write** — None.

**Definition of Done**

- [ ] All glossary terms are defined without requiring source-code knowledge.
- [ ] Quickstart commands match the repository.
- [ ] No API key is required for the primary beginner path.
- [ ] Docs checker, strict build, and application tests pass.

---

## Chunk 7 — Document upload, preprocessing, and manual tracing

**Objective** — Document the primary path from a source image through a manual
extraction.

**Depends on** — Chunk 6.

**Files you may edit**

- `docs/workflows/overview.md`
- `docs/workflows/01-add-drawing.md`
- `docs/workflows/02-prepare-image.md`
- `docs/workflows/03-trace-layers.md`
- `mkdocs.yml`

**Files you may read but not edit**

- `poggio_webapp/static/app/stages/scan.js`
- `poggio_webapp/static/app/stages/preprocess.js`
- `poggio_webapp/static/app/stages/draw.js`
- `poggio_webapp/backend/routes/scans.py`
- `poggio_webapp/backend/routes/preprocess.py`
- `poggio_webapp/backend/routes/manual.py`
- `poggio_webapp/pipeline/preprocess.py`
- Demo fixtures.

**Deliverables**

- Workflow overview with inputs, branching, outputs, and status labels.
- Upload guide for both source types and accepted formats.
- Preprocessing guide explaining each control and when to use it.
- Manual tracing guide covering:
  - rotation;
  - the three calibration clicks;
  - real reference width;
  - surface line;
  - bottom boundaries;
  - layer/locus metadata;
  - optional internal features;
  - building the extraction.
- Use screenshot placeholders with stable asset names, for example:
  `../assets/screenshots/03-trace-calibration.png`.
- Placeholder syntax must be an HTML comment, not a broken image link:

```html
<!-- SCREENSHOT: 03-trace-calibration.png
State: synthetic field-wall fixture, calibration complete
Callouts: top-left, top-right, lowest point, real width
-->
```

**Explicit non-goals**

- Do not capture screenshots.
- Do not document AI or marker workflows.
- Do not explain coordinate conversion beyond calibration.
- Do not edit application copy.

**Inputs/outputs contract**

Each workflow page must follow the standard workflow page contract and identify
the exact job metadata/artifact produced by the step.

**Tests to write** — None.

**Definition of Done**

- [ ] A beginner can complete a manual extraction using only these pages.
- [ ] Both drawing types are distinguished accurately.
- [ ] Screenshot requests are explicit but do not break the build.
- [ ] Tests/build/checker pass.

---

## Chunk 8 — Document alternative extraction, cleanup, and validation

**Objective** — Explain optional ways to obtain extraction data and how the
application cleans and checks it.

**Depends on** — Chunk 7.

**Files you may edit**

- `docs/workflows/03-alternative-import-and-ai.md`
- `docs/workflows/03-markers-and-features.md`
- `docs/workflows/04-clean-data.md`
- `docs/workflows/05-check-problems.md`
- `mkdocs.yml`

**Files you may read but not edit**

- Extraction, marker, feature, normalization, and validation frontend modules.
- Corresponding backend routes.
- Corresponding pipeline modules.
- Capability audit.
- Existing marker/feature concept page.

**Deliverables**

- JSON import guide.
- AI extraction guide including API-key handling, cost/network caveat, retry
  behavior, and current UI status.
- Marker and feature workflow page that clearly separates:
  - what backend support exists;
  - what the current UI exposes;
  - what remains experimental or backend-only.
- Normalization guide with before/after JSON examples.
- Validation guide covering:
  - errors versus warnings;
  - uniform-spacing warning;
  - copied-offset boundary warning;
  - crossing layers;
  - implausible depth;
  - feature placement;
  - field-wall-specific checks.

**Explicit non-goals**

- Do not claim AI geometry is verified.
- Do not put real API keys in examples.
- Do not expose backend-only operations as clickable UI steps.
- Do not change validation thresholds or code.

**Inputs/outputs contract**

- All JSON snippets must come from the sanitized fixture or a smaller synthetic
  derivative.
- Each warning must include:
  - what triggered it;
  - whether it blocks continuation;
  - what the user should inspect.

**Tests to write** — None.

**Definition of Done**

- [ ] Optional paths are visibly secondary to manual tracing.
- [ ] Current feature statuses match the audit.
- [ ] Errors and warnings cannot be confused.
- [ ] Tests/build/checker pass.

---

## Chunk 9 — Document registration, model creation, visualization, and finds

**Objective** — Complete the user journey from valid extraction data to
site-wide coordinates, a GemPy model, downloads, and independent finds.

**Depends on** — Chunk 8.

**Files you may edit**

- `docs/workflows/06-place-on-site.md`
- `docs/workflows/07-create-model.md`
- `docs/workflows/08-view-and-download.md`
- `docs/workflows/logging-finds.md`
- `docs/start-here/first-model.md`
- `mkdocs.yml`

**Files you may read but not edit**

- Convert, GemPy, visualize, finds frontend code.
- Corresponding routes and pipeline modules.
- Editor/finalization tests.
- Finds tests.
- Capability audit and fixtures.

**Deliverables**

- Survey registration guide defining `originX`, `originY`, `surfaceZ`, and
  `bearing_deg`.
- A prominent rule that placeholder coordinates are for smoke testing only.
- GemPy build guide covering optional dependencies, series order, resolution,
  extent, section direction, vertical exaggeration, and outputs.
- Visualizer guide covering face selection, overlays, alignment, A/B
  comparison, and downloads.
- Finds guide explaining their independence from stratigraphic geometry and
  later synchronization into outputs.
- A single `first-model.md` tutorial that links the earlier workflow pages in
  order and uses the synthetic example.

**Explicit non-goals**

- Do not invent surveyed registration values.
- Do not generate or commit a scientific model.
- Do not interpret the archaeological sequence.
- Do not add batch processing.

**Inputs/outputs contract**

The coordinate page must show the repository's actual formulas:

```text
X = originX + x * sin(bearing)
Y = originY + x * cos(bearing)
Z = surfaceZ - depth
```

It must define the bearing convention as clockwise from north and explain
degrees-to-radians conversion without changing the formula.

**Tests to write** — None.

**Definition of Done**

- [ ] The eight-step user path is complete.
- [ ] Every stage identifies its output artifact.
- [ ] Placeholder/scientific-validity warnings are prominent.
- [ ] Tests/build/checker pass.
- [ ] Human Review Gate B is approved using the first-model tutorial.

---

## Chunk 10 — Write the conceptual learning layer

**Objective** — Explain the mental models behind the application without
requiring readers to inspect code.

**Depends on** — Chunk 9.

**Files you may edit**

- `docs/concepts/archaeology-to-3d.md`
- `docs/concepts/source-drawing-types.md`
- `docs/concepts/layers-and-boundaries.md`
- `docs/concepts/coordinate-spaces.md`
- `docs/concepts/accuracy-and-provenance.md`
- `mkdocs.yml`

**Files you may read but not edit**

- Existing concept pages.
- Pipeline schemas and coordinate code.
- Validator.
- Workflow pages.
- Capability audit.

**Deliverables**

- The progression from paper drawing to structured geometry to 3D model.
- A side-by-side explanation of illustrator and field-wall sources.
- Layer/locus/boundary relationships.
- Pixel, section-local, and site-wide coordinate spaces.
- Provenance distinctions among:
  - manual tracing;
  - imported data;
  - computer-vision detections;
  - AI classification/transcription;
  - placeholders;
  - surveyed values.
- Explicit explanation that a visually attractive model is not proof of
  scientifically trustworthy geometry.

**Explicit non-goals**

- Do not repeat step-by-step UI instructions.
- Do not document individual API routes.
- Do not add speculative archaeological interpretation.

**Inputs/outputs contract**

Each page follows the standard concept-page contract and links to the workflow
where the concept is used.

**Tests to write** — None.

**Definition of Done**

- [ ] Every beginner-critical concept has a plain-language example.
- [ ] Concepts link to workflows and glossary entries.
- [ ] Accuracy claims are cautious and source-backed.
- [ ] Tests/build/checker pass.

---

## Chunk 11 — Document system architecture

**Objective** — Give developers a reliable map of the frontend, Flask
backend, tasks, job storage, and pipeline modules.

**Depends on** — Chunk 10.

**Files you may edit**

- `docs/architecture/system-overview.md`
- `docs/architecture/job-lifecycle.md`
- `docs/architecture/frontend.md`
- `docs/architecture/backend.md`
- `docs/architecture/pipeline.md`
- `docs/architecture/asynchronous-tasks.md`
- `docs/architecture/files-and-artifacts.md`
- `mkdocs.yml`

**Files you may read but not edit**

- Entire `poggio_webapp/` source tree.
- Existing tests.
- Workflow and concept docs.

**Deliverables**

- Component map from browser to Flask route to pipeline to job folder.
- Frontend state, prerequisites, renderers, and downstream invalidation.
- Flask application factory and blueprint registration.
- Any legacy/duplicate route registration described accurately and neutrally.
- Job `meta.json` lifecycle and numbered artifact directories.
- Synchronous versus in-memory asynchronous tasks and restart limitation.
- One page per pipeline family, linking to source rather than copying it.

**Explicit non-goals**

- Do not refactor duplicate or legacy code.
- Do not propose new persistence architecture in current-behavior sections.
- Do not copy entire source files into docs.
- Do not change API behavior.

**Inputs/outputs contract**

Every architecture page must include:

- responsibilities;
- inputs;
- outputs;
- main source files;
- failure boundaries;
- links to related tests;
- links back to user-facing workflow pages.

**Tests to write** — None.

**Definition of Done**

- [ ] Every major runtime component is represented.
- [ ] UI availability and backend capability remain distinct.
- [ ] Job/task persistence limitations are documented.
- [ ] Tests/build/checker pass.

---

## Chunk 12 — Write the developer reference

**Objective** — Provide lookup-oriented reference pages for schemas, routes,
configuration, validation, outputs, tests, and common failures.

**Depends on** — Chunk 11.

**Files you may edit**

- `docs/reference/data-schemas.md`
- `docs/reference/api-routes.md`
- `docs/reference/configuration.md`
- `docs/reference/validation-rules.md`
- `docs/reference/output-files.md`
- `docs/reference/troubleshooting.md`
- `docs/contributing/development-setup.md`
- `docs/contributing/running-tests.md`
- `docs/contributing/adding-a-pipeline-stage.md`
- `docs/contributing/writing-documentation.md`
- `docs/project/known-limitations.md`
- `docs/project/roadmap.md`
- `docs/project/scientific-assumptions.md`
- `mkdocs.yml`

**Files you may read but not edit**

- Entire application source.
- All tests.
- Existing READMEs.
- Git log for explicitly historical facts.

**Deliverables**

- Tables for both Pydantic schemas and their shared/converged fields.
- Route table with method, path, request, response, sync/async behavior, and
  user-facing status.
- Environment/dependency/configuration reference.
- Validator rule reference with default values from code.
- Output-file inventory.
- Troubleshooting organized by symptom.
- Contributor setup and test commands.
- Checklist for adding a new stage, including docs/tests/routes/UI/state.
- Current limitations separated from future roadmap.
- Scientific assumptions and explicit non-assumptions.

**Explicit non-goals**

- Do not generate reference text from introspection at runtime.
- Do not promise dates or owners in the roadmap.
- Do not change dependency versions or add a license.
- Do not turn known limitations into code changes.

**Inputs/outputs contract**

- All defaults and signatures must match current source.
- Every route table row must link to its route module.
- Every validation rule must state `error` or `warning`.
- Historical material must be labeled historical.

**Tests to write** — None.

**Definition of Done**

- [ ] Reference pages answer lookup questions without reading source.
- [ ] No stale bug is listed as current.
- [ ] Current limits and roadmap are separate.
- [ ] Tests/build/checker pass.

---

## Chunk 13 — Add deterministic diagrams and the visual inventory

**Objective** — Add precise, implementation-specific diagrams and define
every remaining screenshot or generated visual before capture.

**Depends on** — Chunk 12.

**Files you may edit**

- `docs/_meta/visual-assets.md`
- `docs/assets/visual-manifest.yml`
- `docs/assets/diagrams/*.svg`
- Markdown pages under `docs/` only where needed to embed the new diagrams.

**Files you may read but not edit**

- Application source.
- Existing docs.
- Demo fixtures.
- Existing scans and images.

**Deliverables**

- Visual manifest entries for:
  - asset id;
  - destination page;
  - type: screenshot, SVG, Mermaid, generated illustration, or animation;
  - source fixture;
  - required UI state;
  - callouts;
  - alt text;
  - caption;
  - publication status;
  - regeneration command, if applicable.
- Deterministic SVGs for:
  - three coordinate spaces;
  - calibration clicks;
  - layer/boundary/feature/marker/find anatomy;
  - job-folder lifecycle;
  - interface points and orientation seeds.
- Mermaid diagrams embedded as source in Markdown for:
  - complete pipeline;
  - browser/backend/pipeline sequence;
  - manual versus optional extraction paths.

**Explicit non-goals**

- Do not capture live screenshots.
- Do not use an image generator for technical diagrams.
- Do not use unapproved real scans.
- Do not create decorative images with no teaching purpose.
- Do not modify application styling.

**Inputs/outputs contract**

Every SVG must:

- use a `viewBox`;
- contain a `<title>` and `<desc>`;
- remain legible at 720 CSS pixels wide;
- avoid embedded raster data;
- communicate state with shape/text as well as color.

**Tests to write** — None.

**Definition of Done**

- [ ] Every workflow page has one planned teaching visual.
- [ ] Every diagram is traceable to current implementation behavior.
- [ ] Alt text and captions are present in the manifest before capture.
- [ ] Tests/build/checker pass.

---

## Chunk 14 — Add screenshot capture tooling and approved screenshots

**Objective** — Capture reproducible, sanitized screenshots from the current
UI using only the documentation fixtures.

**Depends on** — Chunk 13 and explicit confirmation that the UI redesign is
stable.

**Files you may edit**

- `tools/docs/capture_screenshots.py`
- `tools/docs/validate_visual_manifest.py`
- `tests/docs/test_visual_manifest.py`
- `docs/assets/visual-manifest.yml`
- `docs/assets/screenshots/*.png`
- Documentation pages containing matching screenshot placeholders.
- `requirements-docs.txt`, only if the approved capture tool needs a pinned
  documentation-only dependency.

**Files you may read but not edit**

- Application HTML/CSS/JS.
- Demo fixtures and generator.
- Visual manifest.
- Existing application tests.

**Deliverables**

Implement Python validation interfaces:

```python
def load_visual_manifest(path: Path) -> list[dict]: ...

def validate_manifest_entries(
    entries: list[dict],
    repo_root: Path,
) -> list[str]: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

The capture script must:

- use a fixed desktop viewport;
- start from the synthetic fixture;
- capture only manifest-approved states;
- hide or normalize unstable job ids;
- never enter or display an API key;
- never use real survey coordinates;
- write to exact manifest paths;
- fail when the app cannot reach the required state;
- avoid silently keeping old screenshots when capture failed.

**Explicit non-goals**

- Do not change app code to expose selectors.
- Do not capture every control; follow the manifest.
- Do not capture real user jobs.
- Do not add animated GIFs yet.
- Do not publish the site.

**Inputs/outputs contract**

```bash
./.venv/bin/python tools/docs/capture_screenshots.py
./.venv/bin/python tools/docs/validate_visual_manifest.py
```

The manifest validator exits `0` only when all approved assets exist, have
nonempty alt text/captions, and contain publication status `approved`.

**Tests to write**

- Valid manifest passes.
- Missing required key fails.
- Missing asset file fails.
- Empty alt text fails.
- Empty caption fails.
- Unapproved publication status fails.
- Duplicate asset id fails.
- Asset outside `docs/assets/` fails.
- Unstable job-id pattern in a committed screenshot filename fails.

**Definition of Done**

- [ ] Each screenshot corresponds to an approved manifest entry.
- [ ] Screenshot placeholders are replaced with real image links.
- [ ] Screens contain no secrets, real coordinates, or unstable ids.
- [ ] Visual-manifest unit tests pass.
- [ ] Full tests/build/checker pass.
- [ ] Human Review Gate C approves publication safety and visual accuracy.

---

## Chunk 15 — Add small interactive documentation components

**Objective** — Add only the interactions that materially improve
understanding: image comparison and coordinate conversion.

**Depends on** — Chunk 14.

**Files you may edit**

- `docs/javascripts/coordinate-calculator.mjs`
- `docs/javascripts/before-after.mjs`
- `docs/stylesheets/interactive.css`
- `docs/labs/coordinate-converter.md`
- `docs/labs/preprocessing-comparison.md`
- `tests/docs/coordinate-calculator.test.mjs`
- `tests/docs/before-after.test.mjs`
- `mkdocs.yml`

**Files you may read but not edit**

- `poggio_webapp/pipeline/convert_coords.py`
- Preprocess documentation and images.
- Coordinate concept/workflow pages.

**Deliverables**

Implement pure coordinate functions:

```javascript
export function toRadians(degrees) {}

export function sectionToSite({
  x,
  depth,
  originX,
  originY,
  surfaceZ,
  bearingDeg,
}) {}
```

Return:

```javascript
{ X: Number, Y: Number, Z: Number }
```

Implement pure comparison state:

```javascript
export function clampDivider(value) {}

export function dividerStyle(percent) {}
```

- `clampDivider` returns a number in `[0, 100]`.
- `dividerStyle` returns the CSS percentage string used by the comparison UI.
- DOM initialization must be separate from pure functions so Node tests can
  import the modules without a browser.
- Progressive enhancement: pages remain understandable if JavaScript is
  disabled.

**Explicit non-goals**

- Do not embed the live Flask application.
- Do not build a JSON schema editor.
- Do not add a framework or bundler.
- Do not copy application business logic other than the documented coordinate
  formula.
- Do not add analytics.

**Inputs/outputs contract**

Example:

```javascript
sectionToSite({
  x: 2,
  depth: 0.5,
  originX: 100,
  originY: 200,
  surfaceZ: 50,
  bearingDeg: 90,
})
// approximately { X: 102, Y: 200, Z: 49.5 }
```

Invalid, missing, or non-finite numeric input must return a structured error or
throw one documented `TypeError`; choose one behavior and test it consistently.

**Tests to write**

- `toRadians(0)`, `toRadians(90)`, `toRadians(180)`.
- North, east, south, and west bearings.
- Depth subtracts from `surfaceZ`.
- Nonzero origins are applied.
- Floating-point results use tolerances.
- Every invalid numeric field follows the chosen error contract.
- Divider values below 0 clamp to 0.
- Divider values above 100 clamp to 100.
- Valid divider values remain unchanged.
- Divider style has a percentage suffix.

**Definition of Done**

- [ ] `node --test tests/docs/*.test.mjs` passes.
- [ ] Python tests, strict docs build, and checker pass.
- [ ] Both labs work without a build step.
- [ ] Both remain understandable without JavaScript.

---

## Chunk 16 — Rewrite the root README as the front door

**Objective** — Replace the long, stale implementation narrative with a
concise visual map into the now-complete documentation.

**Depends on** — Chunk 15.

**Files you may edit**

- `README.md`

**Files you may read but not edit**

- Entire `docs/` tree.
- Capability audit.
- Visual manifest and approved assets.
- Current app code.

**Deliverables**

The README must contain, in order:

1. Project name and one-sentence purpose.
2. Approved hero/pipeline visual.
3. What goes in and what comes out.
4. Who the project is for.
5. Three reader paths:
   - use it;
   - understand it;
   - develop it.
6. Minimal setup and launch.
7. Compact workflow diagram.
8. Scientific-validity warning.
9. Links to capability status, known limitations, tests, and full docs.

Preserve historically useful deep content by moving readers to the appropriate
existing docs pages, not by deleting the information without replacement.

**Explicit non-goals**

- Do not make the README a full manual.
- Do not include current bug statements without checking the audit.
- Do not edit `poggio_webapp/README.md` in this chunk.
- Do not add badges that depend on nonexistent workflows.

**Inputs/outputs contract**

- Every README link must resolve on GitHub using relative paths.
- The basic launch command must be visible without opening another page.
- The README must not require JavaScript to understand.
- The README must not duplicate entire reference tables.

**Tests to write** — None.

**Definition of Done**

- [ ] A new reader can choose a path in under one minute.
- [ ] No stale roadmap or fixed-bug claim remains.
- [ ] Deep material is linked, not lost.
- [ ] Tests/build/checker pass.

---

## Chunk 17 — Add CI and prepare deployment

**Objective** — Make documentation regressions visible on every pull request
and prepare, but do not activate, a GitHub Pages deployment.

**Depends on** — Chunk 16.

**Files you may edit**

- `.github/workflows/docs.yml`
- `.github/pull_request_template.md`
- `requirements-test.txt`
- `docs/contributing/writing-documentation.md`

**Files you may read but not edit**

- Existing workflows, if any.
- Requirements files.
- All tests and documentation tools.

**Deliverables**

The workflow must:

- run on pull requests and pushes to the default branch;
- install application and documentation dependencies;
- install pinned test dependencies from `requirements-test.txt`;
- run Python tests;
- run documentation unit tests;
- run Node documentation tests;
- run the docs checker;
- run `mkdocs build --strict`;
- upload the built site as a CI artifact;
- prepare a separate Pages deployment job that is disabled or environment
  gated until publication is approved.

The PR template must ask:

- Did behavior change?
- Which docs pages were checked?
- Were screenshots regenerated?
- Were capability statuses updated?
- Are new assets safe to publish?

**Explicit non-goals**

- Do not change GitHub repository settings.
- Do not publish a Pages site.
- Do not add secrets.
- Do not rewrite application CI.
- Do not push or commit.

**Inputs/outputs contract**

- Pull requests must never deploy.
- Build artifacts must contain the complete `site/` directory.
- Deployment requires an explicit protected environment or manual enablement.

**Tests to write** — None.

**Definition of Done**

- [ ] Workflow YAML is syntactically valid.
- [ ] Every local workflow command passes before handoff.
- [ ] Pull requests cannot deploy.
- [ ] Publication safety decision remains a human gate.

---

## Chunk 18 — Final audit and novice test packet

**Objective** — Verify completeness, record remaining gaps, and prepare a
repeatable usability test for people unfamiliar with the repository.

**Depends on** — Chunk 17.

**Files you may edit**

- `docs/_meta/final-audit.md`
- `docs/_meta/novice-test-script.md`
- `docs/_meta/novice-test-results-template.md`
- `docs/project/capability-status.md`
- `docs/project/known-limitations.md`

**Files you may read but not edit**

- Entire repository.

**Deliverables**

- Final audit covering:
  - all MkDocs nav pages;
  - orphan pages;
  - broken links/images;
  - status-sensitive claims;
  - screenshots and manifest;
  - public-data safety;
  - accessibility basics;
  - test results.
- A novice test script with these tasks:
  1. Explain the project in their own words.
  2. Choose the correct workflow for a field sheet.
  3. Start the application.
  4. Produce or follow the synthetic manual extraction.
  5. Explain one warning.
  6. Identify the output files.
  7. Explain which values are placeholders.
- A results template recording:
  - success/failure;
  - time;
  - hesitation point;
  - incorrect assumption;
  - page used;
  - proposed documentation fix.
- Update capability/limitation pages only if the final audit finds a
  documentation-status error.

**Explicit non-goals**

- Do not perform application feature work.
- Do not claim usability testing happened unless real participants completed
  it.
- Do not change pages merely for personal stylistic preference.
- Do not deploy.

**Inputs/outputs contract**

The final audit must list exact commands and results:

```bash
git diff --check
./.venv/bin/python -m pytest -q
node --test tests/docs/*.test.mjs
./.venv/bin/python tools/docs/check_docs.py
./.venv/bin/python tools/docs/validate_visual_manifest.py
./.venv/bin/python -m mkdocs build --strict
```

**Tests to write** — None.

**Definition of Done**

- [ ] All automated checks pass.
- [ ] No unapproved asset is referenced.
- [ ] No page is orphaned.
- [ ] No status-sensitive claim contradicts the capability audit.
- [ ] Novice test materials are ready.
- [ ] Human Review Gate D is approved.

## Coordinator notes

### How to assign a chunk

Use this prompt wrapper:

```text
You are implementing Chunk N from DOCUMENTATION_AGENT_WORKPLAN.md.

Read the Global task contract and Chunk N completely before acting.
Do not implement any other chunk.
Do not edit files outside Chunk N's allow-list.
Run the required preflight before editing.
Run every available validation command after editing.
Return the required final report and stop.
```

### What the coordinator should review

For every handoff:

- Compare the changed-file list with the allow-list.
- Look for claims that are more confident than the code.
- Confirm backend-only features were not presented as UI features.
- Confirm the agent did not hide build failures by removing pages from nav.
- Confirm no screenshot contains secrets, user job ids, or real coordinates.
- Confirm `NOT RUN` was not described as `PASS`.
- Reject drive-by code cleanup, even if the cleanup looks useful.

### If a chunk uncovers an application bug

Do not expand the documentation chunk. Record:

- exact file and line;
- reproduction or failing test;
- documentation impact;
- suggested status label.

Create a separate application task with its own allow-list and tests. Resume
the documentation chunk only after that task is resolved or the capability is
accurately labeled.

### Unit-test ownership

- Chunk 2 owns documentation checker tests.
- Chunk 5 owns fixture-generator tests.
- Chunk 14 owns visual-manifest tests.
- Chunk 15 owns interactive JavaScript tests.
- No documentation chunk may weaken or delete an existing application test.
- New behavior in documentation tooling requires a failing test first, then
  the smallest implementation that makes it pass.
