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
python tools/docs/check_docs.py . && python tools/docs/check_coverage.py . && mkdocs build --strict
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
