---
title: Quickstart
audience: beginner
status: current
source_files:
  - poggio_webapp/app.py
  - poggio_webapp/requirements.txt
  - requirements-docs.txt
verified_against: eac1f51
---

# Quickstart

Install the core dependencies and launch the local web application without an
API key, GemPy, or PDF support.

## Before you start

You need a local checkout of this repository, `python3`, and a POSIX-style
shell. The commands below are the repository's documented local setup; the
project does not currently publish a broader platform support matrix.

For the smallest first run, have an approved PNG, JPEG, or TIFF trench-profile
drawing ready. Manual tracing is the primary beginner path and does not use an
API key.

The dependency groups are:

| Group | Needed for the first launch? | Purpose |
|---|---|---|
| Core Python dependencies in `poggio_webapp/requirements.txt` | Yes | Run the Flask application, image processing, data handling, and the supported manual path |
| Poppler | No | Read PDF pages; only needed when the input is a PDF |
| GemPy and `gempy_viewer` | No | Build the experimental 3D model; deliberately excluded from the core requirements |
| Documentation dependencies in `requirements-docs.txt` | No | Build this guide; not needed to run the application |

## Do this

From the repository root:

```bash
cd poggio_webapp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Leave the terminal running while you use the application. Open
[http://localhost:5000](http://localhost:5000) in a browser.

Do not install GemPy for this quickstart. Do not enter an API key: choose
manual tracing after you add a drawing.

## What the application creates

The virtual environment lives at `poggio_webapp/.venv/`. When you begin work
in the browser, the application creates a local directory under
`poggio_webapp/jobs/` for that job's working files. Uploaded source files and
derived data stay on the machine running the application.

The application does not automatically remove old job directories.

## Check your result

The page at `http://localhost:5000` should show **Add your trench drawing**.
Choose **Use an existing drawing**. An image upload should offer the supported
manual path through **Trace the layers** without requesting an API key.

Stopping the server with <kbd>Ctrl</kbd>+<kbd>C</kbd> and running
`python app.py` again should reopen the local application. Previous job
directories remain on disk.

## Common problems

- **`python` cannot import Flask or another package.** Activate
  `poggio_webapp/.venv/` and rerun
  `python -m pip install -r requirements.txt`.
- **Port 5000 is already in use.** Choose another local port, for example
  `PORT=5001 python app.py`, and open that port in the browser.
- **A PDF cannot be prepared.** PDF input also requires Poppler on the host.
  Install it using instructions for your own supported environment, or use an
  approved PNG, JPEG, or TIFF instead.
- **The 3D model step reports that GemPy is unavailable.** GemPy and
  `gempy_viewer` are optional and are not installed by this quickstart. The
  [capability audit](../project/capability-status.md#capability-table) labels
  model building experimental.
- **Automatic reading asks for a key.** Return to **Trace the layers**.
  Only the experimental AI-assisted path needs a Gemini API key.

## Under the hood

`poggio_webapp/app.py` creates the Flask application and listens on port 5000
unless the `PORT` environment variable changes it. The core requirements
include the libraries imported by the web application. GemPy is imported only
when a model build begins, which is why the rest of the application can run
without that optional package.

## Next

Use [Choose your path](choose-your-path.md) to confirm that manual tracing,
JSON import, or experimental automatic reading matches the material you have.
Keep the [glossary](glossary.md) nearby for unfamiliar terms.
