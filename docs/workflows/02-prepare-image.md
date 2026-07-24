---
title: Prepare the image
audience: beginner
status: current
source_files:
  - poggio_webapp/static/app/stages/preprocess.js
  - poggio_webapp/backend/routes/preprocess.py
verified_against: 077f108
---

# Prepare the image

This page covers the second step of the manual workflow: turn the uploaded drawing into a clearer working copy before tracing starts.

## Before you start

Have an uploaded drawing ready. If the file is a PDF, you will also need to know which page contains the trench drawing.

The preprocessing controls are optional, but the recommended defaults usually work well for a first pass.

## Do this

1. Input: the uploaded scan and the sheet type.
   - Action: open the preprocess screen and keep the defaults unless the drawing is tilted, very small, or hard to read.
   - Artifact: the app prepares a clean copy for tracing.
2. Input: a PDF upload.
   - Action: choose the page number that contains the drawing. For the first page, leave the value at 1.
   - Artifact: the selected PDF page is converted into an image for the next step.
3. Input: a scan that needs extra help.
   - Action: use the controls to make the image larger, straighten a slightly tilted scan, and optionally create a high-contrast copy. Increase the image size if the drawing is very small; use deskew only for a scan that is visibly tilted.
   - Artifact: a prepared image and a high-contrast copy if requested.

<!-- SCREENSHOT: 02-prepare-image.png
State: synthetic field-wall fixture, preprocess complete
Callouts: upscale, deskew, high-contrast, preview
-->

## What the application creates

- A prepared image in the job's preprocess folder.
- An optional high-contrast copy when that setting is enabled.
- Job metadata that records the clean-image path and the deskew angle that was applied.

## Check your result

- The prepared image appears in the browser preview.
- The original file remains unchanged.
- The next step can open the prepared drawing for tracing.

## Common problems

- A PDF page number is wrong and the app shows the wrong page.
- The drawing is still too small after preprocessing, so the lines are hard to follow.
- The deskew option is turned on for a drawing that is already straight, which can distort the image.

## Under the hood

The user controls in [poggio_webapp/static/app/stages/preprocess.js](../../poggio_webapp/static/app/stages/preprocess.js) send the requested settings to the server route in [poggio_webapp/backend/routes/preprocess.py](../../poggio_webapp/backend/routes/preprocess.py). The preprocessing pipeline uses the uploaded file and writes the outputs into the job's preprocess directory.

## Next

Continue to [Trace the layers](03-trace-layers.md) to turn the prepared image into a saved extraction.
