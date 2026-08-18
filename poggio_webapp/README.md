# Trench Digitization Pipeline: web application

The Flask application and the pipeline modules behind it.

**This file covers installing and running the app.** How to *use* it, what each
stage does, and why it works that way live in the documentation guide:

- [Quickstart](../docs/start-here/quickstart.md): the same setup, with context
- [Workflow overview](../docs/workflows/overview.md): every step, in order
- [Architecture](../docs/architecture/system-overview.md): how the pieces fit
- [API routes](../docs/reference/api-routes.md): every endpoint
- [Troubleshooting](../docs/reference/troubleshooting.md): when something fails

The [root README](../README.md) is the illustrated tour of the whole project.

## Setup

From the repository root, not from this folder. The virtual environment
belongs at the top of the repository, because every `make` target looks for it
there:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r poggio_webapp/requirements.txt
```

That is everything the supported path needs. Three extras are deliberately
left out, because most work does not require them.

The test and lint targets need their own tools:

```bash
pip install pytest ruff
```

The 3D model build needs GemPy, a heavy install kept out of
`requirements.txt` so the rest of the pipeline works without it:

```bash
pip install gempy gempy_viewer
```

Reading PDF input needs Poppler, from the system package manager rather than
pip:

```bash
brew install poppler
```

```bash
apt install poppler-utils
```

## Running it

From the repository root:

```bash
make run
```

Open <http://localhost:5000> and leave the terminal running. `make run` is
`cd poggio_webapp && ../.venv/bin/python app.py`. The app must start with this
folder as its working directory, which is why the target exists.

| Variable | Effect |
|---|---|
| `PORT` | Serve on a different port |
| `FLASK_DEBUG=1` | Auto-reloading development server |
| `GEMINI_API_KEY` | Default key for the optional AI steps |

The AI steps are optional. Manual tracing is the supported path and needs no
key at all.

`make demo` seeds two demonstration trenches to explore without a drawing; the
sidebar's demo card offers the same pair from the browser. See
[run the demo](../docs/start-here/demo.md).

## Layout

```
app.py                 application entry point
storage.py             the single definition of where things live on disk
backend/
  __init__.py          the application factory
  routes/              one blueprint per concern
  services/            work that chains several pipeline stages together
  jobs.py, tasks.py    job folders and the in-memory task registry
pipeline/              preprocess, extract, normalize, validate, convert,
                       merge_walls, build_gempy, harris_*, and the rest
demo/                  the seedable demonstration trenches (`make demo`)
tools/                 standalone helpers not wired into the interface
static/, templates/    the browser interface, vanilla JS with no build step
jobs/                  created at runtime, one folder per sheet
trenches/              merged multi-wall output
matrices/              Harris matrix workspaces
```

The three runtime directories are gitignored, so a fresh clone has none of
them. They are created on import by `storage.py`.

## Tests

From the repository root:

```bash
make test
```

```bash
node --test "poggio_webapp/static/**/*.test.mjs" "docs/javascripts/**/*.test.mjs"
```

Neither needs GemPy, an API key, or network access. See
[running the tests](../docs/reference/running-the-tests.md) for what each suite
covers and what it does not.

## Known limits

The authoritative record is
[capability status](../docs/project/capability-status.md), which labels every
capability and cites its source. The short version:

- Starter registration values are smoke-test placeholders; the config declares
  `"source": "placeholder"`, and only the multi-wall build refuses it. A
  single-sheet build still accepts it.
- AI extraction is experimental: it needs a key and network access, and has no
  end-to-end test.
- Marker detection and feature detection are backend-only: the routes exist
  and are tested, but no browser control reaches them. The multi-wall trenches
  page works and is tested, but only the demo card links to it.
- Task state lives in process memory, so a restart loses the status of a
  running build.
