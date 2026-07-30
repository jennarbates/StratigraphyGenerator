---
title: Troubleshooting
audience: beginner
status: current
source_files:
  - poggio_webapp/backend/errors.py
  - poggio_webapp/backend/config.py
  - poggio_webapp/backend/tasks.py
  - poggio_webapp/backend/routes/trenches.py
  - poggio_webapp/pipeline/validator.py
verified_against: d23b842
---

# Troubleshooting

Common failures, what causes them, and what to do. Grouped by where they
surface.

## Setup and installation

### A PDF upload fails to preprocess

PDF input needs Poppler installed on the host, separately from the Python
packages. On macOS, `brew install poppler`; on Debian or Ubuntu,
`apt install poppler-utils`.

PNG, JPEG, and TIFF need nothing extra. Uploading a PDF succeeds either way —
the failure appears later, at [prepare the image](../workflows/02-prepare-image.md).

### "gempy import failed"

GemPy and `gempy_viewer` are deliberately excluded from
`poggio_webapp/requirements.txt` because they are a heavy install, and the rest
of the pipeline works without them. Everything up to and including coordinate
conversion runs; only the model build needs them.

```bash
pip install gempy gempy_viewer
```

### An upload is rejected as an unsupported file type

Only `.png`, `.jpg`, `.jpeg`, `.pdf`, `.tif`, and `.tiff` are accepted. The
check is on the file extension, so a mislabelled file is caught later during
processing rather than at upload.

## Gemini extraction

Every AI-assisted step needs a Gemini API key and network access. The
application translates the errors you actually hit into what-to-do-next text;
the raw exception travels alongside as `error_detail`.

| Symptom | Meaning | What to do |
|---|---|---|
| A JSON parse error | Almost always a truncated response, cut off by the output-token limit | Raise `max_output_tokens` and re-run the extraction |
| `500`, `502`, `503`, `504` | Google's servers failed on every retry | Wait 15–30 minutes. Do not hammer re-run — each attempt re-sends the whole image and spends quota |
| `429` | Out of quota | Retrying will not help until the quota resets. Free-tier keys have daily caps a few large extractions can exhaust |
| `400`, `401`, `403` | Invalid or restricted key, or a project without the Gemini API enabled | Check the key. Retrying with the same key will keep failing |

If a `5xx` persists for more than a day, the suggested workaround is to shrink
the request — lower `max_output_tokens`, or reduce `MAX_SEND_DIMENSION` in the
extraction module.

### "api_key is required"

[Check the writing](../workflows/03-alternative-import-and-ai.md) and the other
AI steps abort with `400` when no key is supplied, either in the request or as
the `GEMINI_API_KEY` environment variable.

This step is optional. It can be skipped entirely, and the manual path needs no
key at all — see [choose your path](../start-here/choose-your-path.md).

## Validation

Errors block the next required step; warnings do not. A report can carry
warnings and still have `ok: true`, so a clean-looking result is not a
substitute for expert review. [Check for problems](../workflows/05-check-problems.md)
covers the individual codes, and [validation rules](validation-rules.md) lists
them in full.

## Building a trench from several walls

Every failure below is a deliberate refusal with a specific message. Full
detail is in [combine walls into one trench](../workflows/09-multi-wall-trench.md).

| Message | Fix |
|---|---|
| `no jobs are labelled trench …` | Set a matching trench label on each wall's job |
| `these jobs have no normalized extraction yet` | Normalize each wall first |
| `two or more sheets claim the same wall` | Give each job a distinct wall label |
| `these faces still carry the starter placeholder registration` | Enter real survey values |
| `the grid config has no entry for these faces` | Add the missing face, or that wall is dropped |
| `conversion produced no interface points` | Check that the walls' layers have boundary points |

A build that reports a **cycle** means the walls contradict each other about
layer order — one wall puts a locus above another, a second puts it below. The
message names the surfaces actually on the cycle. This is a recording
disagreement to resolve on the drawings, not a bug.

## Jobs and tasks

### Task status disappeared after a restart

Job artifacts persist on disk, but asynchronous task state lives only in
process memory. Restarting the server loses task status and logs, and there is
no durable queue. A long-running build that was in progress is orphaned — the
files it already wrote remain, but its status is unrecoverable.

### A job cannot be found

`404 unknown job id` means no folder of that name exists under
`poggio_webapp/jobs/`. That directory is gitignored, so a fresh clone has no
jobs, and anything you clean up is gone permanently.

### A file request is rejected as an invalid path

Both the job and trench file routes resolve the requested path and refuse to
escape their own directory. A rejected path is usually a leading `/` or a `..`
segment, not a missing file — a genuinely missing file returns `404`.

## Documentation build

### `mkdocs build --strict` fails on a link the checker accepted

`check_docs.py` permits links from `docs/` to files elsewhere in the
repository; MkDocs does not, because the target is not part of the site.
Reference such files as inline code rather than linking them.

### "page is absent from MkDocs navigation"

Every page under `docs/` must appear in `mkdocs.yml`'s `nav`. A page that is
written but unlisted is invisible to readers, so the checker treats it as an
error rather than a warning.

## Related

- [Capability status](../project/capability-status.md) — whether the thing you
  are trying to do is wired up at all.
- [Running the tests](running-the-tests.md) — confirm the installation itself
  is sound.
- [Configuration](configuration.md) — environment variables and paths.
