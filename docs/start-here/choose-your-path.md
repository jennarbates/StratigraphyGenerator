---
title: Choose your path
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/scan.js
  - poggio_webapp/static/app/stages/draw.js
  - poggio_webapp/static/app/stages/extract.js
  - poggio_webapp/static/app/index.js
verified_against: eac1f51
---

# Choose your path

Choose a current way to turn your drawing into structured data without
assuming that every implemented backend feature is available in the browser.

## Before you start

Identify what you have:

- a PNG, JPEG, TIFF, or PDF drawing that a person can trace;
- a JSON file previously created by this application; or
- permission to use experimental automatic reading, including a Gemini API
  key and network access.

If those terms are unfamiliar, read [What this project does](what-this-project-does.md)
and the [glossary](glossary.md) first. For the simplest path, use an image
file and trace it manually. This path does not need an API key. PDF files
need an additional system dependency, so an image file is the smaller first
setup.

## Do this

### Manual tracing — [`supported`](../project/capability-status.md#capability-table)

Choose manual tracing when you have an illustrated trench sheet or a
hand-drawn field sheet and can identify its boundaries yourself. This is the
primary beginner path and the one the application recommends.

Start with **Use an existing drawing**, upload the file, and continue to
**Trace the layers**. Manual tracing works without Gemini and without an API
key. The primary tracer creates one face from each uploaded drawing.

### Importing JSON — [`supported`](../project/capability-status.md#capability-table)

Choose import only when you already have a JSON data file made by this
application. In **Other ways to add data**, select **Choose an existing data
file**.

Import checks that the file is JSON and recognizes one of the application's
two top-level data shapes. It does not fully validate the data at import
time, so continue to the application's checking step before relying on it.
Importing does not need an API key.

### AI-assisted extraction — [`experimental`](../project/capability-status.md#capability-table)

Choose automatic reading only when you have been asked to test it and can
carefully compare its output with the original drawing. It requires a Gemini
API key, network access, and a prepared image.

Automatic reading can misread labels or invent plausible-looking geometry.
Treat its output as a transcription to review, not as verified evidence. It
is not the primary beginner path.

### Field-sheet marker workflow — [`backend-only`](../project/capability-status.md#capability-table)

Do not choose automated marker detection and assignment as a browser
workflow. Its backend routes and an unregistered frontend stage exist, but
the stage is not part of the live step list. The current application has no
user entry point for completing this path.

For a hand-drawn field sheet, use supported manual tracing instead.

## What the application creates

Each available path produces structured drawing data inside a local **job**.
Later parts of the application read that same data for cleanup, checking, and
coordinate conversion. Importing or automatically reading a drawing can
replace manual data already saved in the job, so choose one source
deliberately.

## Check your result

The application should report that the traced or imported drawing data is
ready. Compare names, boundaries, scale, and features with the source drawing
before continuing.

Recheck the [capability audit](../project/capability-status.md) whenever a
control is missing or a workflow described elsewhere seems unavailable. The
audit is authoritative for current status.

## Common problems

- **You do not have JSON made by this application.** Use manual tracing
  instead of inventing a file structure.
- **You do not have an API key.** Use manual tracing or import; neither
  requires one.
- **You expected the marker review stage.** It is backend-only and is not
  registered in the live workflow.
- **You have a PDF but want the smallest setup.** Export an approved page as
  PNG, JPEG, or TIFF, or install the optional PDF system dependency described
  in the [quickstart](quickstart.md).
- **A path produced data successfully.** Success means the application could
  read the data, not that the archaeological interpretation is correct.

## Under the hood

The live frontend registers manual tracing and the optional import/automatic
reading page. Marker modules exist in the repository but are omitted from the
registered step and renderer lists. The
[capability audit](../project/capability-status.md) records the code and test
evidence for each status.

## Next

Follow the [quickstart](quickstart.md) to launch the application, then use the
manual path unless your project has a reviewed JSON file or has explicitly
approved experimental automatic reading.
