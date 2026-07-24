---
title: Poggio Civitate Trench Digitization Guide
audience: beginner
status: current
source_files:
  - README.md
  - poggio_webapp/README.md
  - poggio_webapp/app.py
verified_against: eac1f51
---

# Poggio Civitate trench digitization guide

Turn a drawing of a vertical trench wall into structured, reviewable data and,
when the optional modeling tools are available, a 3D geological model.

The supported beginner route is to upload an image and trace its boundaries
manually. It does not require an API key. Start with the
[quickstart](start-here/quickstart.md) to reach the runnable `python app.py`
command, then use the chooser to confirm the right workflow.

## Use the app

- [Launch the application](start-here/quickstart.md) with the core Python
  dependencies.
- [Choose your path](start-here/choose-your-path.md) among supported manual
  tracing and JSON import, experimental AI assistance, and the backend-only
  field-sheet marker workflow.
- Read the [drawing guidelines](reference/drawing-guidelines.md) before using
  source material.

## Understand the system

- [What this project does](start-here/what-this-project-does.md) explains the
  drawing-to-data outcome and its limits.
- The [glossary](start-here/glossary.md) defines the essential archaeological
  and modeling vocabulary.
- [Markers, features, and finds](concepts/markers-features-and-finds.md)
  separates three easily confused record types.

## Develop the project

- Use the [current capability status](project/capability-status.md) as the
  authoritative record of what is supported, experimental, backend-only,
  blocked, or historical.
- Use the [synthetic fixtures](fixtures/README.md) for safe examples and
  deterministic tests; they are invented documentation data, not
  archaeological evidence.
- Build this guide with the pinned packages in `requirements-docs.txt` and
  keep new public pages consistent with the repository's documentation
  checks.
