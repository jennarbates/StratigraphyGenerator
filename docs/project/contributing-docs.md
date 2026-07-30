---
title: Contributing to the docs
audience: developer
status: current
source_files:
  - tools/docs/check_docs.py
  - tools/docs/generate_demo_assets.py
  - docs/_meta/page-template.md
  - mkdocs.yml
  - requirements-docs.txt
verified_against: d23b842
---

# Contributing to the docs

How to add or change a page without breaking the build.

## Setup

```bash
pip install -r requirements-docs.txt
```

Four pinned packages: MkDocs, Material for MkDocs, PyMdown Extensions, and
PyYAML. Serve the site locally with live reload:

```bash
mkdocs serve
```

## Adding a page

### 1. Copy the template

`docs/_meta/page-template.md` holds both page shapes. The `_meta` directory is
excluded from the build and from the checker, so it is a safe place to work.

Pick the shape that matches: **workflow** pages run Before you start → Do this →
What the application creates → Check your result → Common problems → Under the
hood → Next. **Concept** pages run definition → Why it matters here → Example →
How the repository represents it → Related concepts.

### 2. Fill in the front matter

All five keys are required on any page in the navigation:

```yaml
---
title: Human-readable page title
audience: beginner        # beginner | user | developer
status: current
source_files:
  - poggio_webapp/pipeline/example.py
verified_against: d23b842
---
```

`source_files` names the code the page describes, and `verified_against` is the
commit you actually checked it against. These are the mechanism that makes
staleness visible later — do not copy a hash you did not verify.

### 3. Add it to the navigation

Every page under `docs/` must appear in `mkdocs.yml`'s `nav`. An unlisted page
is invisible to readers, so the checker treats it as an error, not a warning.

### 4. Run the checks

```bash
python tools/docs/check_docs.py . && python tools/docs/check_coverage.py . && python tools/docs/validate_visual_manifest.py . && mkdocs build --strict
```

## What the checkers enforce

`tools/docs/check_docs.py` validates every page under `docs/` plus the root
`README.md`:

| Check | Rule |
|---|---|
| Relative links | Must resolve to a file that exists inside the repository |
| Image alt text | Must be non-empty |
| Front matter | The five keys above, on every page in the nav |
| Orphans | Every page under `docs/` must be in the nav |

It exits `0` and prints `Documentation checks passed.` when clean.

`tools/docs/check_coverage.py` adds one further rule: every module under
`poggio_webapp/pipeline/` and `poggio_webapp/backend/` must be named by **full
path** on some page. The full path is required so an ordinary English word
cannot cover a module by accident — `trenches.py` would otherwise look
documented because "trenches" appears throughout the prose. A `source_files`
entry satisfies it, so writing correct front matter usually satisfies it for
free.

Run `mkdocs build --strict` as well. The two overlap but neither is a superset:
**MkDocs rejects links from `docs/` to files outside it**, which the checker
permits. Reference such files as inline code rather than linking them.

## Writing conventions

- **Never document intent.** Every claim traces to a file at a known commit. If
  you cannot point at the code, do not write the sentence.
- **Say when something is unreachable.** A capability can be fully implemented
  and still have no browser control. Those pages carry a warning callout at the
  top and link to [capability status](capability-status.md).
- **Label synthetic data.** Invented coordinates, locus numbers, and Munsell
  readings must be marked as documentation examples so nobody mistakes them for
  evidence.
- **End every page with links.** `Next` for workflows, `Related` for
  everything else. No dead ends.
- **Link concepts from workflows.** A workflow's *Under the hood* section is
  where a reader is most receptive to the theory behind the step.

## Adding a visual

Every image in the guide is planned in `docs/assets/visual-manifest.yml`
**before** it is produced. Capture is manual, so deciding what a visual must
show is cheaper than re-shooting it.

1. Add an entry with `status: planned`. Write the `alt` and `caption` now —
   they are what force you to say what the visual teaches.
2. Produce the asset. Screenshots follow the capture protocol; diagrams are
   authored by hand; generated assets get a `regenerate` command.
3. Move the entry to `status: approved` once it has been reviewed.
4. Only then embed it in the page.

```bash
python tools/docs/validate_visual_manifest.py .
```

The validator works in both directions. Forward, it checks that entries are
well formed and that an `approved` entry really has its file. Reverse — the
half that matters — it checks that **every image embedded in the documentation
resolves to an `approved` entry**. An unreviewed screenshot cannot reach a
published page, and the manifest cannot quietly decay into a wishlist.

Four types, named for how the asset is maintained rather than what it depicts:

| Type | Maintained by | Extra fields |
|---|---|---|
| `screenshot` | Re-capturing from the app | `fixture`, `ui_state` |
| `diagram` | Redrawing by hand | — |
| `generated` | Running a script | `regenerate` |
| `mermaid` | Editing the fence inline | no `path` |

`ui_state` is what makes re-capture decidable after a UI change. Without it,
nobody can tell whether a screenshot is still correct.

## Images and fixtures

Regenerate the sanitized demo images and fixtures:

```bash
python tools/docs/generate_demo_assets.py
```

These are invented documentation data, not archaeological evidence, and they
carry a synthetic label. Use them for any example that would otherwise need a
real scan. See [synthetic fixtures](../fixtures/README.md).

Every image needs non-empty alt text — the checker fails the build otherwise.
Write it to describe what the image *shows*, not that it is an image.

## Continuous integration and deployment

`.github/workflows/docs.yml` runs on every push to `main` and on every pull
request. It installs both dependency sets, then runs each check as its own step
so a failure names itself:

1. `check_docs.py` — links, front matter, orphan pages
2. `check_coverage.py` — module documentation coverage
3. `validate_visual_manifest.py` — the visual manifest, both directions
4. `check_readme_sync.py` — README against the navigation
5. `pytest tests/` and the Node test suites
6. `mkdocs build --strict`
7. A regeneration check: `generate_diagrams.py` must produce no diff against
   the committed SVGs, so a hand-edited or stale diagram cannot ship

Pushes to `main` that pass then deploy the built site to GitHub Pages.

**Enabling deployment is a one-time repository setting.** Under *Settings →
Pages*, set the source to **GitHub Actions**. Until that is done the `deploy`
job fails and the published URL returns 404; the checks themselves are
unaffected.

`site/` stays gitignored. Pages deploys from the workflow artifact, never from
a committed build.

## Testing the tooling

The documentation tooling has its own tests:

```bash
python -m pytest tests/docs -q
```

These test `tools/docs/`, not the prose. The prose is checked by running the
tool itself.

## Related

- [Running the tests](../reference/running-the-tests.md) — all three suites.
- [How to read these docs](../start-here/how-to-read-these-docs.md) — the
  structure you are writing into.
- [Capability status](capability-status.md) — keep it updated when a
  capability's wiring changes.
