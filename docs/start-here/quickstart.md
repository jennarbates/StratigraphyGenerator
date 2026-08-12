---
title: Quickstart
audience: beginner
status: current
source_files:
  - poggio_webapp/app.py
  - poggio_webapp/requirements.txt
  - requirements-docs.txt
  - pyproject.toml
  - Makefile
verified_against: ae2fc1d
---

# Quickstart

Install the core dependencies and launch the local web application without an
API key, GemPy, or PDF support.

## Before you start

You need three things: a local copy of this repository, Python 3.11 or newer,
and a terminal. On macOS and Linux the built-in terminal works; on Windows,
use WSL or Git Bash, because the commands below assume a Unix-style shell. The
project does not currently publish a broader platform support matrix.

Check your Python before anything else:

```bash
python3 --version
```

If that prints `Python 3.11` or higher you are ready. If it reports that the
command is not found, install Python from [python.org](https://www.python.org/downloads/)
first.

For the smallest first run, have an approved PNG, JPEG, or TIFF trench-profile
drawing ready. Manual tracing is the primary beginner path and does not use an
API key.

The dependency groups are:

| Group | Needed for the first launch? | Purpose |
|---|---|---|
| Core Python dependencies in `poggio_webapp/requirements.txt` | Yes | Run the Flask application, image processing, data handling, and the supported manual path |
| `pytest` and `ruff` | No | Only needed to run `make test` and `make lint` |
| Poppler | No | Read PDF pages; only needed when the input is a PDF |
| GemPy and `gempy_viewer` | No | Build the experimental 3D model; deliberately excluded from the core requirements |
| Documentation dependencies in `requirements-docs.txt` | No | Build this guide; not needed to run the application |

## Do this

Run every command below **from the repository root** — the folder containing
`README.md` and `Makefile`, not the `poggio_webapp` folder inside it.

First, create the virtual environment. This is a private folder of Python
packages for this project alone, so installing them cannot disturb any other
Python on your machine:

```bash
python3 -m venv .venv
```

Activate it. Your prompt should gain a `(.venv)` prefix, which is how you know
the next commands use the project's packages:

```bash
source .venv/bin/activate
```

Install what the application needs:

```bash
python -m pip install -r poggio_webapp/requirements.txt
```

Start it:

```bash
make run
```

Leave the terminal running while you use the application. Open
[http://localhost:5000](http://localhost:5000) in a browser.

!!! warning "Keep the virtual environment at the repository root"

    There is exactly one `.venv`, and it belongs at the top of the repository.
    Every `make` target looks for it there. If you create one inside
    `poggio_webapp/` instead, `make run`, `make test`, and `make docs` will all
    fail to find their tools.

Each new terminal needs `source .venv/bin/activate` again before `make run`.
You only create the environment and install packages once.

Do not install GemPy for this quickstart. Do not enter an API key: choose
manual tracing after you add a drawing.

## What the application creates

The virtual environment lives at `.venv/` in the repository root. When you
begin work in the browser, the application creates a local directory under
`poggio_webapp/jobs/` for that job's working files. Uploaded source files and
derived data stay on the machine running the application.

The application does not automatically remove old job directories.

## Check your result

The page at `http://localhost:5000` should show **Add your trench drawing**.
Choose **Use an existing drawing**. An image upload should offer the supported
manual path through **Trace the layers** without requesting an API key.

Stopping the server with <kbd>Ctrl</kbd>+<kbd>C</kbd> and running `make run`
again should reopen the local application. Previous job directories remain on
disk.

## Common problems

- **`python` cannot import Flask or another package.** The virtual environment
  is probably not active. Run `source .venv/bin/activate` from the repository
  root — your prompt should show `(.venv)` — then rerun
  `python -m pip install -r poggio_webapp/requirements.txt`.
- **`make: *** No rule to make target` or `.venv/bin/python: No such file`.**
  You are either not in the repository root, or the virtual environment was
  created somewhere other than the root. Run `ls Makefile .venv` to confirm
  both are in the folder you are standing in.
- **Port 5000 is already in use.** Choose another local port, for example
  `PORT=5001 make run`, and open that port in the browser. On macOS, port 5000
  is often taken by the system AirPlay Receiver.
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
